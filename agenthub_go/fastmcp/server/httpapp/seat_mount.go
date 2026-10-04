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
// resolved-seat snapshots rewrite the MCP server URL to it.
const publicURLEnv = "AGENTHUB_PUBLIC_URL"

// seatSource is what the seat routes need from the seat_management use cases.
type seatSource interface {
	ResolveSeat(ctx context.Context, userID, roomSlug, seatKey string) (*repositories.ResolvedSeat, error)
	SeedSeatTypes(ctx context.Context, userID string) (int, error)
}

// newSeatSource is a package variable so tests can substitute a fake without a database.
var newSeatSource = func(sessions *database.SessionManager, mcpURL string) (seatSource, error) {
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
	return &seatUseCases{
		modules: modules, seatTypes: seatTypes,
		resolution: &seatservices.SeatResolutionService{
			SeatTypes: seatTypes, Rooms: rooms, Seats: seats, Overlays: overlays, Links: links, Resolved: resolved,
			NewCatalog: func(userID string) seatservices.CheckedCatalog { return seatorm.NewDBCatalog(modules, userID) },
			MCPURL:     mcpURL,
		},
	}, nil
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

func seatSourceFor(w http.ResponseWriter, sessions *database.SessionManager) (seatSource, bool) {
	var mcpURL string
	if publicURL := strings.TrimRight(os.Getenv(publicURLEnv), "/"); publicURL != "" {
		mcpURL = publicURL + "/mcp"
	}
	source, err := newSeatSource(sessions, mcpURL)
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return nil, false
	}
	return source, true
}

func handleResolveSeat(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	if publicURL := strings.TrimRight(os.Getenv(publicURLEnv), "/"); publicURL == "" {
		writeDetail(w, http.StatusInternalServerError, publicURLEnv+" is not set")
		return
	}
	source, ok := seatSourceFor(w, sessions)
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
	source, ok := seatSourceFor(w, sessions)
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
