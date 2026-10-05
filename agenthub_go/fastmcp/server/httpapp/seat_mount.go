package httpapp

// seat_mount.go serves the company-workplace seats to the OpenRig client.
//
//	GET  /api/v2/openrig/seats/{room}/{seat}   resolved, rendered and stored snapshot
//	POST /api/v2/openrig/seat-types/seed       seed the caller's seat types from the embedded library
//
// A snapshot is immutable: the same seat definition always returns the same hash, so the
// client can pin it and OpenRig materializes exactly those files.

import (
	"context"
	"net/http"
	"os"
	"strings"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	seatservices "agenthub/fastmcp/seat_management/application/services"
	"agenthub/fastmcp/seat_management/domain/repositories"
	"agenthub/fastmcp/seat_management/domain/seedlibrary"
	seatorm "agenthub/fastmcp/seat_management/infrastructure/repositories/orm"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// publicURLEnv names the externally reachable base URL of this server. Rendered specs and
// resolved-seat snapshots rewrite the MCP server URL to it. It is an override: when it is set
// the deployment's pinned value wins, and when it is not the caller's own request supplies the
// origin (see seatMCPURL).
const publicURLEnv = "AGENTHUB_PUBLIC_URL"

// seatMCPURL is the MCP server URL rendered into a seat's spec and resolved snapshot.
//
// Precedence: AGENTHUB_PUBLIC_URL when the deployment pinned it; otherwise the origin the
// caller actually reached this server by. A caller reaching the API at its own public host
// supplies exactly the URL a rendered seat needs, which is why the request is the truth only
// in the absence of an override - a deployment that pins the value must not be silently
// overridden by a Host header. The REST routes carry the request; the MCP tool dispatch
// carries the same origin in ctx (withRequestPublicOrigin), because a tool call has no
// *http.Request of its own.
func seatMCPURL(r *http.Request, ctx context.Context) string {
	base := strings.TrimRight(os.Getenv(publicURLEnv), "/")
	if base == "" {
		if r != nil {
			base = strings.TrimRight(requestPublicOrigin(r), "/")
		} else if ctx != nil {
			base = strings.TrimRight(requestPublicOriginFromContext(ctx), "/")
		}
	}
	if base == "" {
		return ""
	}
	return base + "/mcp"
}

// requestPublicOrigin is the origin the caller reached this server by, as scheme://host. It
// follows the reverse-proxy trust this server already ports from the Python
// HTTPSRedirectMiddleware: X-Forwarded-Proto decides the scheme and X-Forwarded-Host the host
// when a proxy set them; absent those, the connection decides (https when the listener
// terminated TLS, else http) and r.Host names the host.
func requestPublicOrigin(r *http.Request) string {
	scheme := "http"
	if r.TLS != nil {
		scheme = "https"
	}
	if proto := firstForwardedValue(r.Header.Get("X-Forwarded-Proto")); proto == "http" || proto == "https" {
		scheme = proto
	}
	host := firstForwardedValue(r.Header.Get("X-Forwarded-Host"))
	if host == "" {
		host = r.Host
	}
	if host == "" {
		return ""
	}
	return scheme + "://" + host
}

// firstForwardedValue returns the client-facing value of a forwarding header. A proxy chain
// appends to the right, so the leftmost element is the origin the browser used.
func firstForwardedValue(value string) string {
	if comma := strings.IndexByte(value, ','); comma >= 0 {
		value = value[:comma]
	}
	return strings.TrimSpace(value)
}

// requestPublicOriginKey carries requestPublicOrigin through a context for the MCP tool
// dispatch, which has no request of its own.
type requestPublicOriginKey struct{}

// withRequestPublicOrigin stores the caller's public origin on ctx.
func withRequestPublicOrigin(ctx context.Context, r *http.Request) context.Context {
	return context.WithValue(ctx, requestPublicOriginKey{}, requestPublicOrigin(r))
}

// requestPublicOriginFromContext returns the origin withRequestPublicOrigin stored, or "".
func requestPublicOriginFromContext(ctx context.Context) string {
	origin, _ := ctx.Value(requestPublicOriginKey{}).(string)
	return origin
}

// seatSource is what the seat routes need from the seat_management use cases.
type seatSource interface {
	ResolveSeat(ctx context.Context, userID, roomSlug, seatKey string) (*repositories.ResolvedSeat, error)
	SeedSeatTypes(ctx context.Context, userID string) (int, error)
}

// newSeatResolution is a package variable so tests can substitute a fake without a database. It
// is the single construction of the resolution service, shared by the seat routes (which
// resolve seats through it) and the overlay PUT routes (which validate candidate overlays
// through it).
var newSeatResolution = func(sessions *database.SessionManager, mcpURL string) (*seatservices.SeatResolutionService, error) {
	modules, err := seatorm.NewORMModuleRepository(sessions)
	if err != nil {
		return nil, err
	}
	seatTypes, err := seatorm.NewORMSeatTypeRepository(sessions)
	if err != nil {
		return nil, err
	}
	rooms, err := seatorm.NewORMRoomRepository(sessions)
	if err != nil {
		return nil, err
	}
	seats, err := seatorm.NewORMSeatRepository(sessions)
	if err != nil {
		return nil, err
	}
	overlays, err := seatorm.NewORMOverlayRepository(sessions)
	if err != nil {
		return nil, err
	}
	links, err := seatorm.NewORMSeatLinkRepository(sessions)
	if err != nil {
		return nil, err
	}
	resolved, err := seatorm.NewORMResolvedSeatRepository(sessions)
	if err != nil {
		return nil, err
	}
	return &seatservices.SeatResolutionService{
		SeatTypes: seatTypes, Rooms: rooms, Seats: seats, Overlays: overlays, Links: links, Resolved: resolved,
		NewCatalog: func(userID string) seatservices.CheckedCatalog { return seatorm.NewDBCatalog(modules, userID) },
		MCPURL:     mcpURL,
	}, nil
}

// newSeatSource is a package variable so tests can substitute a fake without a database.
var newSeatSource = func(sessions *database.SessionManager, mcpURL string) (seatSource, error) {
	resolution, err := newSeatResolution(sessions, mcpURL)
	if err != nil {
		return nil, err
	}
	modules, err := seatorm.NewORMModuleRepository(sessions)
	if err != nil {
		return nil, err
	}
	return &seatUseCases{modules: modules, seatTypes: resolution.SeatTypes, resolution: resolution}, nil
}

type seatUseCases struct {
	modules    repositories.ModuleRepository
	seatTypes  repositories.SeatTypeRepository
	resolution *seatservices.SeatResolutionService
}

func (u *seatUseCases) ResolveSeat(ctx context.Context, userID, roomSlug, seatKey string) (*repositories.ResolvedSeat, error) {
	return u.resolution.ResolveSeat(ctx, userID, roomSlug, seatKey)
}

func (u *seatUseCases) SeedSeatTypes(ctx context.Context, userID string) (int, error) {
	seeds, err := seedlibrary.Load()
	if err != nil {
		return 0, err
	}
	if err := seatservices.SeedSeatTypes(ctx, userID, seeds, u.modules, u.seatTypes); err != nil {
		return 0, err
	}
	return len(seeds), nil
}

func mountSeatRoutes(mux *http.ServeMux, sessions *database.SessionManager) {
	mux.HandleFunc("GET /api/v2/openrig/seats/{room}/{seat}", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleResolveSeat(w, r, u, sessions)
	}))
	mux.HandleFunc("POST /api/v2/openrig/seat-types/seed", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleSeedSeatTypes(w, r, u, sessions)
	}))
}

func seatSourceFor(w http.ResponseWriter, r *http.Request, sessions *database.SessionManager) (seatSource, bool) {
	source, err := newSeatSource(sessions, seatMCPURL(r, r.Context()))
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return nil, false
	}
	return source, true
}

func handleResolveSeat(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	source, ok := seatSourceFor(w, r, sessions)
	if !ok {
		return
	}
	room, seat := r.PathValue("room"), r.PathValue("seat")
	resolved, err := source.ResolveSeat(r.Context(), userID(u), room, seat)
	if err != nil {
		status := http.StatusInternalServerError
		if strings.Contains(err.Error(), "not found") {
			status = http.StatusNotFound
		}
		writeDetail(w, status, err.Error())
		return
	}
	files := make([]any, 0, len(resolved.Files))
	for _, f := range resolved.Files {
		file := entities.NewOrderedMap[any]()
		file.Set("path", f.Path)
		file.Set("content", f.Content)
		files = append(files, file)
	}
	seatBody := entities.NewOrderedMap[any]()
	seatBody.Set("room", room)
	seatBody.Set("seat", seat)
	seatBody.Set("hash", resolved.Hash)
	seatBody.Set("runtime", resolved.Runtime)
	seatBody.Set("files", files)
	seatBody.Set("policy", resolved.Policy)
	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	body.Set("resolved_seat", seatBody)
	writeJSON(w, http.StatusOK, body)
}

func handleSeedSeatTypes(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	source, ok := seatSourceFor(w, r, sessions)
	if !ok {
		return
	}
	count, err := source.SeedSeatTypes(r.Context(), userID(u))
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	body.Set("seat_types", count)
	writeJSON(w, http.StatusOK, body)
}
