package httpapp

// seat_mount.go serves the company-workplace seats to the OpenRig client.
//
//	GET  /api/v2/openrig/seats/{room}/{seat}   resolved, rendered and stored snapshot
//	POST /api/v2/openrig/rooms/{room}/seats/{seat}/messages           one message to a seat's session
//	GET  /api/v2/openrig/rooms/{room}/seats/{seat}/messages           the seat's PENDING messages
//	POST /api/v2/openrig/rooms/{room}/seats/{seat}/messages/{id}/ack  a client delivered one message
//	POST /api/v2/openrig/seat-types/seed       seed the caller's seat types from the embedded library
//
// A snapshot is immutable: the same seat definition always returns the same hash, so the
// client can pin it and OpenRig materializes exactly those files.
//
// WHY THE MESSAGE STORE EXISTS, AND WHAT DELIVERY CANNOT BE. Delivery in this product is CLIENT-side:
// only the OpenRig client running on the machine that holds a seat's terminal can put text into that
// seat's session, and this server cannot reach that terminal. So the sender's route STORES the text,
// and the client PULLS it and delivers it locally. The store is the server's only row on this axis
// that a client consumes rather than authors.
//
// THE DELIVERY CONTRACT IS AT-LEAST-ONCE. The pull hands out PENDING messages and the client acks
// each one AFTER the text reached the terminal, so an interruption redelivers instead of losing text,
// and the client dedupes — the same contract the session stream's connector already imposes on it.
// THERE IS NO TTL: a message for a seat that never comes back stays readable, and any bound would be
// explicit policy rather than a sweep (missed_notifications is the precedent).
//
// THE RESIDUAL LIMIT OF THE PULL, STATED RATHER THAN LEFT TO BE DISCOVERED: the pull is
// TENANT-SCOPED by the user token and nothing narrower. Any client holding the tenant's token can pull
// ANY seat's messages in that tenant. THAT IS A CHOSEN LIMIT: binding the pull to the machine that
// REPORTED the seat refuses the pull in exactly the case this store exists for, a seat that is DOWN
// and therefore unreported. The ack records the machine that actually took each message (the
// machine_id in its body), so the audit says which one did.

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

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
	// The chat window's route carries the room, like every other seat sub-resource (/overlay,
	// /links, /occupant), because a bare seat key cannot name a seat: a seat is unique per
	// (room_id, seat_key) - the schema's uq_seats_room_seat_key - so a key-only path could name
	// one only by guessing its room, and the guess would be silently wrong for every user with
	// two rooms carrying the same seat key. With the room in the path the handler resolves the
	// seat the URL names and can answer 404 for one that is not in it, which the key-only shape
	// could not do at all.
	mux.HandleFunc("POST /api/v2/openrig/rooms/{room}/seats/{seat}/messages", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleSendSeatMessage(w, r, u, sessions)
	}))
	// The client's half of the same path, and it is MACHINE-authenticated because the component that
	// can reach a seat's terminal is the client on the machine that holds it — see the residual limit
	// at the top of this file. The ack is a POST on the message rather than a second GET: it RECORDS
	// that one message reached the terminal, and a GET must not have that effect.
	mux.HandleFunc("GET /api/v2/openrig/rooms/{room}/seats/{seat}/messages", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handlePullSeatMessages(w, r, u, sessions)
	}))
	mux.HandleFunc("POST /api/v2/openrig/rooms/{room}/seats/{seat}/messages/{id}/ack", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleAckSeatMessage(w, r, u, sessions)
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
		writeSeatResolutionError(w, err)
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

// writeSeatResolutionError answers a seat resolution failure for both seat routes that resolve
// one. To the caller a seat that does not exist and a seat the caller cannot see are the same
// "not found" - a resolver that has to say which would leak the other user's seat key - and
// anything else is this server's own failure.
func writeSeatResolutionError(w http.ResponseWriter, err error) {
	status := http.StatusInternalServerError
	if strings.Contains(err.Error(), "not found") {
		status = http.StatusNotFound
	}
	writeDetail(w, status, err.Error())
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

// newSeatMessageService is a package variable so tests can substitute a service without a database.
var newSeatMessageService = func(sessions *database.SessionManager) (*seatservices.SeatMessageService, error) {
	repo, err := seatorm.NewORMSeatMessageRepository(sessions)
	if err != nil {
		return nil, err
	}
	return seatservices.NewSeatMessageService(repo), nil
}

// seatMessageNow is the server clock; tests substitute a fixed one, so the instant the store holds is
// the instant the route answered with.
var seatMessageNow = time.Now

// seatMessageServiceFor builds the message service, or answers the caller and returns false.
func seatMessageServiceFor(w http.ResponseWriter, sessions *database.SessionManager) (*seatservices.SeatMessageService, bool) {
	svc, err := newSeatMessageService(sessions)
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return nil, false
	}
	return svc, true
}

// writeSeatMessageRejection answers a request the message contract refuses, and reports whether it was
// one. A CREDENTIAL is the 422 body the seat-status report and the friction channel already answer
// with, so the window and the client read one shape for it; every other refusal is a sentence about
// the caller's own request, which is a 400.
func writeSeatMessageRejection(w http.ResponseWriter, err error) bool {
	var rejection *seatservices.SeatMessageRejection
	if !errors.As(err, &rejection) {
		return false
	}
	if rejection.SecretField != "" {
		writeSeatStatusError(w, http.StatusUnprocessableEntity, rejection.Message)
		return true
	}
	writeDetail(w, http.StatusBadRequest, rejection.Message)
	return true
}

// resolveSeatInTheRoomTheURLNames resolves the seat a message route acts on, IN the room the URL
// names, and reports whether it resolved. A seat that is not in that room and a seat that is not the
// caller's are the SAME 404, so the pair cannot be probed seat by seat, and the pair the resolver is
// asked for is the pair the URL carries rather than a guessed room.
func resolveSeatInTheRoomTheURLNames(w http.ResponseWriter, r *http.Request, sessions *database.SessionManager, callerUserID string) bool {
	source, ok := seatSourceFor(w, r, sessions)
	if !ok {
		return false
	}
	if _, err := source.ResolveSeat(r.Context(), callerUserID, r.PathValue("room"), r.PathValue("seat")); err != nil {
		writeSeatResolutionError(w, err)
		return false
	}
	return true
}

// handleSendSeatMessage answers the seat chat window by STORING the text. The server cannot reach a
// seat's terminal, so holding the message until the client on that terminal's machine pulls it is the
// whole delivery this side can do — and the answer is a success with the id, because the message IS
// stored rather than lost. It resolves the seat first, so a seat that is not in the room the URL names
// is the same 404 it always was, and THE ROOM AND SEAT STORED ARE THE URL'S, never anything the body
// says.
//
// THE BODY IS DECODED FIRST, so a malformed request is refused for being malformed rather than for the
// seat it names: the window renders the detail verbatim, and "unknown field" is a sentence about the
// caller's own bytes.
func handleSendSeatMessage(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	var request struct {
		Text string `json:"text"`
	}
	if !decodeSeatAdminBody(w, r, &request) {
		return
	}
	if !resolveSeatInTheRoomTheURLNames(w, r, sessions, userID(u)) {
		return
	}
	svc, ok := seatMessageServiceFor(w, sessions)
	if !ok {
		return
	}
	stored, err := svc.Send(r.Context(), userID(u), seatservices.SeatMessageInput{
		Room: r.PathValue("room"),
		Seat: r.PathValue("seat"),
		Text: request.Text,
	}, seatMessageNow().UTC())
	if err != nil {
		if writeSeatMessageRejection(w, err) {
			return
		}
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	body.Set("id", stored.ID)
	body.Set("room", stored.Room)
	body.Set("seat", stored.Seat)
	body.Set("created_at", stored.CreatedAt.UTC().Format(time.RFC3339))
	writeJSON(w, http.StatusOK, body)
}

// handlePullSeatMessages is the client's half: the seat's PENDING messages plus the opaque cursor to
// continue after them. It resolves the seat in the room the URL names FIRST, for the same reason the
// write route does, so a seat that is not there is the same 404 rather than an empty page — an empty
// page would read as "nothing is waiting" and silently drop a backlog the caller cannot see.
//
// THE PAGE BOUNDS COME FROM THE SERVICE (ClampSeatMessageLimit) rather than from this route, so the
// numbers a client pages by have one home; the route only reads the two query parameters.
func handlePullSeatMessages(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	if !resolveSeatInTheRoomTheURLNames(w, r, sessions, userID(u)) {
		return
	}
	svc, ok := seatMessageServiceFor(w, sessions)
	if !ok {
		return
	}
	limit := 0
	if raw := r.URL.Query().Get("limit"); raw != "" {
		if n, convErr := strconv.Atoi(raw); convErr == nil {
			limit = n
		}
	}
	messages, cursor, err := svc.Pull(r.Context(), userID(u), r.PathValue("room"), r.PathValue("seat"), r.URL.Query().Get("after"), limit)
	if err != nil {
		if writeSeatMessageRejection(w, err) {
			return
		}
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	body.Set("messages", seatMessageRows(messages))
	body.Set("cursor", cursor)
	writeJSON(w, http.StatusOK, body)
}

// seatMessageAckRequest names the machine that typed the message, which the audit records.
type seatMessageAckRequest struct {
	MachineID string `json:"machine_id"`
}

// handleAckSeatMessage records that a client put one message into the seat's session, which is what
// stops the next pull returning it. THE STATE, NOT THE ID, IS WHAT A CALLER CAN GET WRONG: an id that
// is unknown and an id already delivered answer the same 409 with one sentence, because neither
// redelivers and a client retrying a dropped ack should hear that rather than a 404 that reads like a
// mistyped id.
func handleAckSeatMessage(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	if !resolveSeatInTheRoomTheURLNames(w, r, sessions, userID(u)) {
		return
	}
	svc, ok := seatMessageServiceFor(w, sessions)
	if !ok {
		return
	}
	var req seatMessageAckRequest
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(&req); err != nil {
		writeDetail(w, http.StatusBadRequest, err.Error())
		return
	}
	if err := repositories.ValidateName("machine id", req.MachineID); err != nil {
		writeDetail(w, http.StatusBadRequest, err.Error())
		return
	}
	err := svc.Ack(r.Context(), userID(u), r.PathValue("room"), r.PathValue("seat"), r.PathValue("id"), req.MachineID, seatMessageNow().UTC())
	switch {
	case err == nil:
	case errors.Is(err, seatservices.ErrSeatMessageNotPending):
		writeDetail(w, http.StatusConflict, err.Error())
		return
	default:
		if writeSeatMessageRejection(w, err) {
			return
		}
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	body.Set("delivered", true)
	writeJSON(w, http.StatusOK, body)
}

// seatMessageRows is the pulled page as the client reads it: every key always present, and created_at
// RFC3339 in UTC so a client never has to interpret a zone. The delivery state is deliberately NOT
// here — a pulled row is pending by definition, and the ack is what changes that.
func seatMessageRows(messages []repositories.SeatMessage) []any {
	rows := make([]any, 0, len(messages))
	for _, m := range messages {
		row := entities.NewOrderedMap[any]()
		row.Set("id", m.ID)
		row.Set("room", m.Room)
		row.Set("seat", m.Seat)
		row.Set("text", m.Text)
		row.Set("created_at", m.CreatedAt.UTC().Format(time.RFC3339))
		rows = append(rows, row)
	}
	return rows
}
