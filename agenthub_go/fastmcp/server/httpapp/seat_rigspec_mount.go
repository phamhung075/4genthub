package httpapp

// seat_rigspec_mount.go serves one room as a launchable OpenRig RigSpec v0.2:
//
//	GET /api/v2/openrig/rooms/{room}/rigspec
//
// The room becomes a pod, its active seats become members resolved to their pinned
// snapshot hashes, and allowed seat links become pod-local edges. The route is authed
// and tenant-scoped by the caller's user id.

import (
	"context"
	"net/http"
	"os"
	"sort"
	"strings"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	seatservices "agenthub/fastmcp/seat_management/application/services"
	"agenthub/fastmcp/seat_management/domain/repositories"
	"agenthub/fastmcp/seat_management/domain/rigspec"
	seatorm "agenthub/fastmcp/seat_management/infrastructure/repositories/orm"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// seatRigSpecSource is the repository surface the rigspec route needs.
type seatRigSpecSource interface {
	GetRoomBySlug(ctx context.Context, userID, slug string) (*repositories.Room, error)
	ListSeatsByRoom(ctx context.Context, userID, roomID string) ([]repositories.Seat, error)
	ResolveSeat(ctx context.Context, userID, roomSlug, seatKey string) (*repositories.ResolvedSeat, error)
	ListSeatLinksFrom(ctx context.Context, userID, seatID string) ([]repositories.SeatLink, error)
	GetSeatByID(ctx context.Context, userID, seatID string) (*repositories.Seat, error)
}

// newSeatRigSpecSource is a package variable so tests can substitute a fake without a database.
var newSeatRigSpecSource = func(sessions *database.SessionManager, mcpURL string) (seatRigSpecSource, error) {
	rooms, err := seatorm.NewORMRoomRepository(sessions)
	if err != nil {
		return nil, err
	}
	seats, err := seatorm.NewORMSeatRepository(sessions)
	if err != nil {
		return nil, err
	}
	links, err := seatorm.NewORMSeatLinkRepository(sessions)
	if err != nil {
		return nil, err
	}
	modules, err := seatorm.NewORMModuleRepository(sessions)
	if err != nil {
		return nil, err
	}
	seatTypes, err := seatorm.NewORMSeatTypeRepository(sessions)
	if err != nil {
		return nil, err
	}
	overlays, err := seatorm.NewORMOverlayRepository(sessions)
	if err != nil {
		return nil, err
	}
	resolved, err := seatorm.NewORMResolvedSeatRepository(sessions)
	if err != nil {
		return nil, err
	}
	return &seatRigSpecRepos{
		rooms: rooms, seats: seats, links: links,
		resolution: &seatservices.SeatResolutionService{
			SeatTypes: seatTypes, Rooms: rooms, Seats: seats, Overlays: overlays, Links: links, Resolved: resolved,
			NewCatalog: func(userID string) seatservices.CheckedCatalog { return seatorm.NewDBCatalog(modules, userID) },
			MCPURL:     mcpURL,
		},
	}, nil
}

type seatRigSpecRepos struct {
	rooms      repositories.RoomRepository
	seats      repositories.SeatRepository
	links      repositories.SeatLinkRepository
	resolution *seatservices.SeatResolutionService
}

var _ seatRigSpecSource = (*seatRigSpecRepos)(nil)

func (s *seatRigSpecRepos) GetRoomBySlug(ctx context.Context, userID, slug string) (*repositories.Room, error) {
	return s.rooms.GetBySlug(ctx, userID, slug)
}

func (s *seatRigSpecRepos) ListSeatsByRoom(ctx context.Context, userID, roomID string) ([]repositories.Seat, error) {
	return s.seats.ListByRoom(ctx, userID, roomID)
}

func (s *seatRigSpecRepos) ResolveSeat(ctx context.Context, userID, roomSlug, seatKey string) (*repositories.ResolvedSeat, error) {
	return s.resolution.ResolveSeat(ctx, userID, roomSlug, seatKey)
}

func (s *seatRigSpecRepos) ListSeatLinksFrom(ctx context.Context, userID, seatID string) ([]repositories.SeatLink, error) {
	return s.links.ListFrom(ctx, userID, seatID)
}

func (s *seatRigSpecRepos) GetSeatByID(ctx context.Context, userID, seatID string) (*repositories.Seat, error) {
	return s.seats.GetByID(ctx, userID, seatID)
}

func mountSeatRigSpecRoutes(mux *http.ServeMux, sessions *database.SessionManager) {
	mux.HandleFunc("GET /api/v2/openrig/rooms/{room}/rigspec", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleRoomRigSpec(w, r, u, sessions)
	}))
}

func seatRigSpecSourceFor(w http.ResponseWriter, sessions *database.SessionManager) (seatRigSpecSource, bool) {
	publicURL := strings.TrimRight(os.Getenv(publicURLEnv), "/")
	if publicURL == "" {
		writeDetail(w, http.StatusInternalServerError, publicURLEnv+" is not set")
		return nil, false
	}
	source, err := newSeatRigSpecSource(sessions, publicURL+"/mcp")
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return nil, false
	}
	return source, true
}

func handleRoomRigSpec(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	source, ok := seatRigSpecSourceFor(w, sessions)
	if !ok {
		return
	}
	uid := userID(u)
	roomSlug := r.PathValue("room")
	room, err := source.GetRoomBySlug(r.Context(), uid, roomSlug)
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	if room == nil {
		writeDetail(w, http.StatusNotFound, "room \""+roomSlug+"\" not found")
		return
	}

	seats, err := source.ListSeatsByRoom(r.Context(), uid, room.ID)
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	active := make([]repositories.Seat, 0, len(seats))
	activeByID := make(map[string]repositories.Seat, len(seats))
	for _, seat := range seats {
		if seat.Status != "active" {
			continue
		}
		active = append(active, seat)
		activeByID[seat.ID] = seat
	}
	if len(active) == 0 {
		writeDetail(w, http.StatusConflict, "room has no active seats")
		return
	}
	sort.Slice(active, func(i, j int) bool { return active[i].SeatKey < active[j].SeatKey })

	specSeats := make([]rigspec.Seat, 0, len(active))
	type resolvedSeat struct{ key, hash string }
	hashes := make([]resolvedSeat, 0, len(active))
	for _, seat := range active {
		resolved, err := source.ResolveSeat(r.Context(), uid, roomSlug, seat.SeatKey)
		if err != nil {
			writeDetail(w, http.StatusInternalServerError, err.Error())
			return
		}
		if resolved == nil {
			writeDetail(w, http.StatusInternalServerError, "seat \""+seat.SeatKey+"\" has no resolved snapshot")
			return
		}
		runtime := resolved.Runtime
		if runtime == "" {
			runtime = seat.Runtime
		}
		specSeats = append(specSeats, rigspec.Seat{Key: seat.SeatKey, Runtime: runtime, Model: seat.Model})
		hashes = append(hashes, resolvedSeat{key: seat.SeatKey, hash: resolved.Hash})
	}

	edges, err := roomRigSpecEdges(r.Context(), source, uid, active, activeByID)
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	doc, err := rigspec.RenderRoom(room.Slug, room.Name, specSeats, edges)
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}

	seatBodies := make([]any, 0, len(hashes))
	for _, h := range hashes {
		entry := entities.NewOrderedMap[any]()
		entry.Set("seat", h.key)
		entry.Set("hash", h.hash)
		seatBodies = append(seatBodies, entry)
	}
	rigBody := entities.NewOrderedMap[any]()
	rigBody.Set("name", room.Slug)
	rigBody.Set("yaml", doc)
	rigBody.Set("seats", seatBodies)
	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	body.Set("rigspec", rigBody)
	writeJSON(w, http.StatusOK, body)
}

// roomRigSpecEdges keeps only allow=true links whose target is another active seat
// in the same room; allow=false links are policy denies, not topology.
func roomRigSpecEdges(ctx context.Context, source seatRigSpecSource, uid string, active []repositories.Seat, activeByID map[string]repositories.Seat) ([]rigspec.Edge, error) {
	edges := make([]rigspec.Edge, 0)
	for _, seat := range active {
		links, err := source.ListSeatLinksFrom(ctx, uid, seat.ID)
		if err != nil {
			return nil, err
		}
		for _, link := range links {
			from, ok := activeByID[link.FromSeatID]
			if !ok || !link.Allow {
				continue
			}
			target, err := source.GetSeatByID(ctx, uid, link.ToSeatID)
			if err != nil {
				return nil, err
			}
			if target == nil || target.Status != "active" || target.RoomID != from.RoomID {
				continue
			}
			edges = append(edges, rigspec.Edge{Kind: link.Kind, From: from.SeatKey, To: target.SeatKey})
		}
	}
	return edges, nil
}
