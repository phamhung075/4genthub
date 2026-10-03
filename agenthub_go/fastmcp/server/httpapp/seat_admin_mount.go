package httpapp

// seat_admin_mount.go is the REST administration surface for the seat system:
//
//	POST   /api/v2/openrig/rooms
//	GET    /api/v2/openrig/rooms
//	DELETE /api/v2/openrig/rooms/{room}
//	GET    /api/v2/openrig/seat-types
//	POST   /api/v2/openrig/seat-types/{slug}/versions
//	GET    /api/v2/openrig/modules
//	GET    /api/v2/openrig/modules/{slug}/versions/{version}
//	PUT    /api/v2/openrig/modules/{slug}/versions/{version}
//	POST   /api/v2/openrig/rooms/{room}/seats
//	GET    /api/v2/openrig/rooms/{room}/seats
//	DELETE /api/v2/openrig/rooms/{room}/seats/{seat}
//	PUT    /api/v2/openrig/rooms/{room}/seats/{seat}/occupant
//	PUT    /api/v2/openrig/rooms/{room}/seats/{seat}/permission-policy
//	GET    /api/v2/openrig/overlay
//	PUT    /api/v2/openrig/overlay
//	GET    /api/v2/openrig/rooms/{room}/overlay
//	PUT    /api/v2/openrig/rooms/{room}/overlay
//	GET    /api/v2/openrig/rooms/{room}/seats/{seat}/overlay
//	PUT    /api/v2/openrig/rooms/{room}/seats/{seat}/overlay
//	PUT    /api/v2/openrig/rooms/{room}/seats/{seat}/links
//	GET    /api/v2/openrig/rooms/{room}/seats/{seat}/links
//	DELETE /api/v2/openrig/rooms/{room}/seats/{seat}/links/{to}/{kind}
//	GET    /api/v2/openrig/settings
//	PUT    /api/v2/openrig/settings
//
// Every route is authed and tenant-scoped by the caller's user id.

import (
	"context"
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"strings"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	seatservices "agenthub/fastmcp/seat_management/application/services"
	"agenthub/fastmcp/seat_management/domain/commpolicy"
	"agenthub/fastmcp/seat_management/domain/repositories"
	"agenthub/fastmcp/seat_management/domain/resolver"
	"agenthub/fastmcp/seat_management/domain/secretscan"
	seatorm "agenthub/fastmcp/seat_management/infrastructure/repositories/orm"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// seatAdminSource is the seat repository surface these routes use.
type seatAdminSource interface {
	SaveRoom(ctx context.Context, userID string, room repositories.Room) (*repositories.Room, error)
	ListRooms(ctx context.Context, userID string) ([]repositories.Room, error)
	GetRoomBySlug(ctx context.Context, userID, slug string) (*repositories.Room, error)
	ListSeatTypes(ctx context.Context, userID string) ([]repositories.SeatType, error)
	LatestSeatTypeVersion(ctx context.Context, userID, slug string) (*repositories.SeatTypeVersion, error)
	GetSeatTypeVersion(ctx context.Context, userID, slug, version string) (*repositories.SeatTypeVersion, error)
	GetModuleVersion(ctx context.Context, userID, slug, version string) (*repositories.ModuleVersion, error)
	ListLatestModuleVersions(ctx context.Context, userID string) ([]repositories.ModuleVersion, error)
	AddSeatTypeVersion(ctx context.Context, userID, slug, version, defaultRuntime string, refs []resolver.ModuleRef) (*repositories.SeatTypeVersion, error)
	SaveModule(ctx context.Context, userID, slug string, kind resolver.ModuleKind) (*repositories.Module, error)
	AddModuleVersion(ctx context.Context, userID, slug, version, content string) (*repositories.ModuleVersion, error)
	FindSeat(ctx context.Context, userID, roomID, seatKey string) (*repositories.Seat, error)
	CreateSeat(ctx context.Context, userID string, seat repositories.Seat) (*repositories.Seat, error)
	ListSeats(ctx context.Context, userID, roomID string) ([]repositories.Seat, error)
	UpdateSeatOccupant(ctx context.Context, userID, seatID, runtime, model string) error
	UpdateSeatPermissionPolicy(ctx context.Context, userID, seatID, permissionPolicy string) error
	UpsertOverlay(ctx context.Context, userID string, overlay repositories.Overlay) (*repositories.Overlay, error)
	FindOverlay(ctx context.Context, userID, scope, roomID, seatID string) (*repositories.Overlay, error)
	UpsertSeatLink(ctx context.Context, userID string, link repositories.SeatLink) (*repositories.SeatLink, error)
	ListSeatLinks(ctx context.Context, userID, seatID string) ([]repositories.SeatLink, error)
	DeleteSeatLink(ctx context.Context, userID, fromSeatID, toSeatID, kind string) (bool, error)
	DeleteSeatLinksOfSeat(ctx context.Context, userID, seatID string) error
	DeleteSeatOverlay(ctx context.Context, userID, seatID string) error
	DeleteRoomOverlay(ctx context.Context, userID, roomID string) error
	DeleteSeatStatusForRoom(ctx context.Context, userID, roomSlug string) error
	DeleteSeatStatusForSeat(ctx context.Context, userID, roomSlug, seatKey string) error
	DeleteResolvedSeats(ctx context.Context, userID, seatID string) error
	DeleteSeat(ctx context.Context, userID, seatID string) error
	DeleteRoom(ctx context.Context, userID, roomID string) error
	InTransaction(ctx context.Context, fn func(ctx context.Context) error) error
	GetSettings(ctx context.Context, userID string) (*repositories.SeatSettings, error)
	SetSettings(ctx context.Context, userID string, followLatest bool) (*repositories.SeatSettings, error)
}

// newSeatAdminSource is a package variable so tests can substitute a fake without a database.
var newSeatAdminSource = func(sessions *database.SessionManager) (seatAdminSource, error) {
	rooms, err := seatorm.NewORMRoomRepository(sessions)
	if err != nil {
		return nil, err
	}
	seatTypes, err := seatorm.NewORMSeatTypeRepository(sessions)
	if err != nil {
		return nil, err
	}
	modules, err := seatorm.NewORMModuleRepository(sessions)
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
	settings, err := seatorm.NewORMSeatSettingsRepository(sessions)
	if err != nil {
		return nil, err
	}
	resolved, err := seatorm.NewORMResolvedSeatRepository(sessions)
	if err != nil {
		return nil, err
	}
	machines, err := seatorm.NewORMMachineStatusRepository(sessions)
	if err != nil {
		return nil, err
	}
	return &seatAdminRepos{sessions: sessions, resolved: resolved, machines: machines, rooms: rooms, seatTypes: seatTypes, modules: modules, seats: seats, overlays: overlays, links: links, settings: settings}, nil
}

type seatAdminRepos struct {
	sessions  *database.SessionManager
	resolved  repositories.ResolvedSeatRepository
	machines  repositories.MachineStatusRepository
	rooms     repositories.RoomRepository
	seatTypes repositories.SeatTypeRepository
	modules   repositories.ModuleRepository
	seats     repositories.SeatRepository
	overlays  repositories.OverlayRepository
	links     repositories.SeatLinkRepository
	settings  repositories.SeatSettingsRepository
}

var _ seatAdminSource = (*seatAdminRepos)(nil)

func (s *seatAdminRepos) SaveRoom(ctx context.Context, userID string, room repositories.Room) (*repositories.Room, error) {
	return s.rooms.Save(ctx, userID, room)
}

func (s *seatAdminRepos) ListRooms(ctx context.Context, userID string) ([]repositories.Room, error) {
	return s.rooms.List(ctx, userID)
}

func (s *seatAdminRepos) GetRoomBySlug(ctx context.Context, userID, slug string) (*repositories.Room, error) {
	return s.rooms.GetBySlug(ctx, userID, slug)
}

func (s *seatAdminRepos) LatestSeatTypeVersion(ctx context.Context, userID, slug string) (*repositories.SeatTypeVersion, error) {
	return s.seatTypes.LatestVersion(ctx, userID, slug)
}

func (s *seatAdminRepos) ListSeatTypes(ctx context.Context, userID string) ([]repositories.SeatType, error) {
	return s.seatTypes.List(ctx, userID)
}

func (s *seatAdminRepos) GetSeatTypeVersion(ctx context.Context, userID, slug, version string) (*repositories.SeatTypeVersion, error) {
	return s.seatTypes.GetVersion(ctx, userID, slug, version)
}

func (s *seatAdminRepos) GetModuleVersion(ctx context.Context, userID, slug, version string) (*repositories.ModuleVersion, error) {
	return s.modules.GetVersion(ctx, userID, slug, version)
}

func (s *seatAdminRepos) ListLatestModuleVersions(ctx context.Context, userID string) ([]repositories.ModuleVersion, error) {
	return s.modules.ListLatest(ctx, userID)
}

func (s *seatAdminRepos) AddSeatTypeVersion(ctx context.Context, userID, slug, version, defaultRuntime string, refs []resolver.ModuleRef) (*repositories.SeatTypeVersion, error) {
	return s.seatTypes.AddVersion(ctx, userID, slug, version, defaultRuntime, refs)
}

func (s *seatAdminRepos) SaveModule(ctx context.Context, userID, slug string, kind resolver.ModuleKind) (*repositories.Module, error) {
	return s.modules.SaveModule(ctx, userID, slug, kind)
}

func (s *seatAdminRepos) AddModuleVersion(ctx context.Context, userID, slug, version, content string) (*repositories.ModuleVersion, error) {
	return s.modules.AddVersion(ctx, userID, slug, version, content)
}

func (s *seatAdminRepos) FindSeat(ctx context.Context, userID, roomID, seatKey string) (*repositories.Seat, error) {
	return s.seats.FindByRoomAndKey(ctx, userID, roomID, seatKey)
}

func (s *seatAdminRepos) CreateSeat(ctx context.Context, userID string, seat repositories.Seat) (*repositories.Seat, error) {
	return s.seats.Create(ctx, userID, seat)
}

func (s *seatAdminRepos) ListSeats(ctx context.Context, userID, roomID string) ([]repositories.Seat, error) {
	return s.seats.ListByRoom(ctx, userID, roomID)
}

func (s *seatAdminRepos) UpdateSeatOccupant(ctx context.Context, userID, seatID, runtime, model string) error {
	return s.seats.UpdateOccupant(ctx, userID, seatID, runtime, model)
}

func (s *seatAdminRepos) UpdateSeatPermissionPolicy(ctx context.Context, userID, seatID, permissionPolicy string) error {
	return s.seats.UpdatePermissionPolicy(ctx, userID, seatID, permissionPolicy)
}

func (s *seatAdminRepos) UpsertOverlay(ctx context.Context, userID string, overlay repositories.Overlay) (*repositories.Overlay, error) {
	return s.overlays.Upsert(ctx, userID, overlay)
}

func (s *seatAdminRepos) FindOverlay(ctx context.Context, userID, scope, roomID, seatID string) (*repositories.Overlay, error) {
	return s.overlays.Find(ctx, userID, scope, roomID, seatID)
}

func (s *seatAdminRepos) UpsertSeatLink(ctx context.Context, userID string, link repositories.SeatLink) (*repositories.SeatLink, error) {
	return s.links.Upsert(ctx, userID, link)
}

func (s *seatAdminRepos) ListSeatLinks(ctx context.Context, userID, seatID string) ([]repositories.SeatLink, error) {
	return s.links.ListFrom(ctx, userID, seatID)
}

func (s *seatAdminRepos) DeleteSeatLink(ctx context.Context, userID, fromSeatID, toSeatID, kind string) (bool, error) {
	return s.links.Delete(ctx, userID, fromSeatID, toSeatID, kind)
}

func (s *seatAdminRepos) DeleteSeatLinksOfSeat(ctx context.Context, userID, seatID string) error {
	return s.links.DeleteBySeat(ctx, userID, seatID)
}

func (s *seatAdminRepos) DeleteSeatOverlay(ctx context.Context, userID, seatID string) error {
	return s.overlays.DeleteForSeat(ctx, userID, seatID)
}

func (s *seatAdminRepos) DeleteRoomOverlay(ctx context.Context, userID, roomID string) error {
	return s.overlays.DeleteForRoom(ctx, userID, roomID)
}

func (s *seatAdminRepos) DeleteSeatStatusForSeat(ctx context.Context, userID, roomSlug, seatKey string) error {
	return s.machines.DeleteSeatStatusForSeat(ctx, userID, roomSlug, seatKey)
}

func (s *seatAdminRepos) DeleteSeatStatusForRoom(ctx context.Context, userID, roomSlug string) error {
	return s.machines.DeleteSeatStatusForRoom(ctx, userID, roomSlug)
}

func (s *seatAdminRepos) DeleteResolvedSeats(ctx context.Context, userID, seatID string) error {
	return s.resolved.DeleteBySeat(ctx, userID, seatID)
}

func (s *seatAdminRepos) DeleteSeat(ctx context.Context, userID, seatID string) error {
	return s.seats.Delete(ctx, userID, seatID)
}

func (s *seatAdminRepos) DeleteRoom(ctx context.Context, userID, roomID string) error {
	return s.rooms.Delete(ctx, userID, roomID)
}

func (s *seatAdminRepos) InTransaction(ctx context.Context, fn func(ctx context.Context) error) error {
	return s.sessions.Transaction(ctx, fn)
}

func (s *seatAdminRepos) GetSettings(ctx context.Context, userID string) (*repositories.SeatSettings, error) {
	return s.settings.Get(ctx, userID)
}

func (s *seatAdminRepos) SetSettings(ctx context.Context, userID string, followLatest bool) (*repositories.SeatSettings, error) {
	return s.settings.Set(ctx, userID, followLatest)
}

func mountSeatAdminRoutes(mux *http.ServeMux, sessions *database.SessionManager) {
	mux.HandleFunc("POST /api/v2/openrig/rooms", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleCreateRoom(w, r, u, sessions)
	}))
	mux.HandleFunc("GET /api/v2/openrig/rooms", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleListRooms(w, r, u, sessions)
	}))
	mux.HandleFunc("DELETE /api/v2/openrig/rooms/{room}", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleDeleteRoom(w, r, u, sessions)
	}))
	mux.HandleFunc("GET /api/v2/openrig/seat-types", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleListSeatTypes(w, r, u, sessions)
	}))
	mux.HandleFunc("POST /api/v2/openrig/seat-types/{slug}/versions", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleCreateSeatTypeVersion(w, r, u, sessions)
	}))
	mux.HandleFunc("GET /api/v2/openrig/modules", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleListModules(w, r, u, sessions)
	}))
	mux.HandleFunc("GET /api/v2/openrig/modules/{slug}/versions/{version}", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleGetModuleVersion(w, r, u, sessions)
	}))
	mux.HandleFunc("PUT /api/v2/openrig/modules/{slug}/versions/{version}", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handlePutModuleVersion(w, r, u, sessions)
	}))
	mux.HandleFunc("POST /api/v2/openrig/rooms/{room}/seats", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleCreateSeat(w, r, u, sessions)
	}))
	mux.HandleFunc("GET /api/v2/openrig/rooms/{room}/seats", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleListSeats(w, r, u, sessions)
	}))
	mux.HandleFunc("DELETE /api/v2/openrig/rooms/{room}/seats/{seat}", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleRemoveSeat(w, r, u, sessions)
	}))
	mux.HandleFunc("PUT /api/v2/openrig/rooms/{room}/seats/{seat}/occupant", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleSetSeatOccupant(w, r, u, sessions)
	}))
	mux.HandleFunc("PUT /api/v2/openrig/rooms/{room}/seats/{seat}/permission-policy", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleSetSeatPermissionPolicy(w, r, u, sessions)
	}))
	mux.HandleFunc("PUT /api/v2/openrig/rooms/{room}/overlay", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleRoomOverlay(w, r, u, sessions)
	}))
	mux.HandleFunc("GET /api/v2/openrig/overlay", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleGetCompanyOverlay(w, r, u, sessions)
	}))
	mux.HandleFunc("PUT /api/v2/openrig/overlay", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleCompanyOverlay(w, r, u, sessions)
	}))
	mux.HandleFunc("GET /api/v2/openrig/rooms/{room}/overlay", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleGetRoomOverlay(w, r, u, sessions)
	}))
	mux.HandleFunc("PUT /api/v2/openrig/rooms/{room}/seats/{seat}/overlay", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleSeatOverlay(w, r, u, sessions)
	}))
	mux.HandleFunc("GET /api/v2/openrig/rooms/{room}/seats/{seat}/overlay", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleGetSeatOverlay(w, r, u, sessions)
	}))
	mux.HandleFunc("PUT /api/v2/openrig/rooms/{room}/seats/{seat}/links", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleUpsertSeatLink(w, r, u, sessions)
	}))
	mux.HandleFunc("GET /api/v2/openrig/rooms/{room}/seats/{seat}/links", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleListSeatLinks(w, r, u, sessions)
	}))
	mux.HandleFunc("DELETE /api/v2/openrig/rooms/{room}/seats/{seat}/links/{to}/{kind}", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleDeleteSeatLink(w, r, u, sessions)
	}))
	mux.HandleFunc("GET /api/v2/openrig/settings", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleGetSettings(w, r, u, sessions)
	}))
	mux.HandleFunc("PUT /api/v2/openrig/settings", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handlePutSettings(w, r, u, sessions)
	}))
}

type seatAdminRoomRequest struct {
	Slug string `json:"slug"`
	Name string `json:"name"`
}

type seatAdminSeatRequest struct {
	SeatKey       string  `json:"seat_key"`
	SeatType      string  `json:"seat_type"`
	PinnedVersion *string `json:"pinned_version"`
	Runtime       string  `json:"runtime"`
	Model         string  `json:"model"`
	FollowLatest  *bool   `json:"follow_latest"`
	// PermissionPolicy defaults to resolver.DefaultPermissionPolicy when omitted.
	PermissionPolicy string `json:"permission_policy"`
}

type seatAdminSeatTypeVersionRequest struct {
	ModuleRefs     []string `json:"module_refs"`
	DefaultRuntime string   `json:"default_runtime"`
}

type seatAdminOccupantRequest struct {
	Runtime string `json:"runtime"`
	Model   string `json:"model"`
}

type seatAdminPermissionPolicyRequest struct {
	PermissionPolicy string `json:"permission_policy"`
}

type seatAdminSettingsRequest struct {
	FollowLatest *bool `json:"follow_latest"`
}

type seatAdminOp struct {
	Kind    string `json:"kind"`
	Slug    string `json:"slug"`
	Version string `json:"version"`
	Content string `json:"content"`
}

type seatAdminOverlayRequest struct {
	Ops []seatAdminOp `json:"ops"`
}

type seatAdminLinkRequest struct {
	ToSeat string `json:"to_seat"`
	Kind   string `json:"kind"`
	Allow  *bool  `json:"allow"`
}

func seatAdminSourceFor(w http.ResponseWriter, sessions *database.SessionManager) (seatAdminSource, bool) {
	source, err := newSeatAdminSource(sessions)
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return nil, false
	}
	return source, true
}

func decodeSeatAdminBody(w http.ResponseWriter, r *http.Request, target any) bool {
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(target); err != nil {
		writeDetail(w, http.StatusBadRequest, err.Error())
		return false
	}
	return true
}

func seatAdminRoom(w http.ResponseWriter, r *http.Request, source seatAdminSource, u *authdomain.User, slug string) (*repositories.Room, bool) {
	room, err := source.GetRoomBySlug(r.Context(), userID(u), slug)
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return nil, false
	}
	if room == nil {
		writeDetail(w, http.StatusNotFound, "room \""+slug+"\" not found")
		return nil, false
	}
	return room, true
}

func seatAdminSeat(w http.ResponseWriter, r *http.Request, source seatAdminSource, u *authdomain.User, roomID, seatKey string) (*repositories.Seat, bool) {
	seat, err := source.FindSeat(r.Context(), userID(u), roomID, seatKey)
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return nil, false
	}
	if seat == nil {
		writeDetail(w, http.StatusNotFound, "seat \""+seatKey+"\" not found")
		return nil, false
	}
	return seat, true
}

func handleCreateRoom(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	source, ok := seatAdminSourceFor(w, sessions)
	if !ok {
		return
	}
	var req seatAdminRoomRequest
	if !decodeSeatAdminBody(w, r, &req) {
		return
	}
	if strings.TrimSpace(req.Slug) == "" || strings.TrimSpace(req.Name) == "" {
		writeDetail(w, http.StatusBadRequest, "slug and name are required")
		return
	}
	if err := repositories.ValidateName("room slug", req.Slug); err != nil {
		writeDetail(w, http.StatusBadRequest, err.Error())
		return
	}
	if err := repositories.ValidateRoomName(req.Name); err != nil {
		writeDetail(w, http.StatusBadRequest, err.Error())
		return
	}
	existing, err := source.GetRoomBySlug(r.Context(), userID(u), req.Slug)
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	if existing != nil {
		writeDetail(w, http.StatusConflict, "room \""+req.Slug+"\" already exists")
		return
	}
	room, err := source.SaveRoom(r.Context(), userID(u), repositories.Room{Slug: req.Slug, Name: req.Name})
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	body.Set("room", seatAdminRoomBody(room))
	writeJSON(w, http.StatusOK, body)
}

func handleListRooms(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	source, ok := seatAdminSourceFor(w, sessions)
	if !ok {
		return
	}
	rooms, err := source.ListRooms(r.Context(), userID(u))
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	out := make([]any, 0, len(rooms))
	for i := range rooms {
		out = append(out, seatAdminRoomBody(&rooms[i]))
	}
	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	body.Set("rooms", out)
	writeJSON(w, http.StatusOK, body)
}

func handleListSeatTypes(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	source, ok := seatAdminSourceFor(w, sessions)
	if !ok {
		return
	}
	seatTypes, err := source.ListSeatTypes(r.Context(), userID(u))
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	out := make([]any, 0, len(seatTypes))
	for i := range seatTypes {
		entry, ok := seatAdminSeatTypeBody(w, r, source, u, &seatTypes[i])
		if !ok {
			return
		}
		out = append(out, entry)
	}
	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	body.Set("seat_types", out)
	writeJSON(w, http.StatusOK, body)
}

func seatAdminSeatTypeBody(w http.ResponseWriter, r *http.Request, source seatAdminSource, u *authdomain.User, seatType *repositories.SeatType) (*entities.OrderedMap[any], bool) {
	latest, err := source.LatestSeatTypeVersion(r.Context(), userID(u), seatType.Slug)
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return nil, false
	}
	moduleRefs := seatAdminModuleRefBodies(nil)
	var latestVersion, latestRuntime any
	if latest != nil {
		latestVersion = latest.Version
		latestRuntime = latest.DefaultRuntime
		moduleRefs = seatAdminModuleRefBodies(latest.ModuleRefs)
	}
	body := entities.NewOrderedMap[any]()
	body.Set("slug", seatType.Slug)
	body.Set("name", seatType.Name)
	body.Set("description", seatType.Description)
	body.Set("default_runtime", latestRuntime)
	body.Set("latest_version", latestVersion)
	body.Set("module_refs", moduleRefs)
	return body, true
}

func seatAdminModuleRefBodies(refs []resolver.ModuleRef) []any {
	out := make([]any, 0, len(refs))
	for _, ref := range refs {
		refBody := entities.NewOrderedMap[any]()
		refBody.Set("slug", ref.Slug)
		refBody.Set("version", ref.Version)
		out = append(out, refBody)
	}
	return out
}

func handleListModules(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	source, ok := seatAdminSourceFor(w, sessions)
	if !ok {
		return
	}
	latest, err := source.ListLatestModuleVersions(r.Context(), userID(u))
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	out := make([]any, 0, len(latest))
	for _, mv := range latest {
		entry := entities.NewOrderedMap[any]()
		entry.Set("slug", mv.Slug)
		entry.Set("kind", mv.Kind)
		entry.Set("version", mv.Version)
		entry.Set("sha256", mv.Checksum)
		out = append(out, entry)
	}
	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	body.Set("modules", out)
	writeJSON(w, http.StatusOK, body)
}

func handleCreateSeatTypeVersion(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	var req seatAdminSeatTypeVersionRequest
	if !decodeSeatAdminBody(w, r, &req) {
		return
	}
	source, ok := seatAdminSourceFor(w, sessions)
	if !ok {
		return
	}
	saved, err := seatservices.NewSeatAdminService(source).CreateSeatTypeVersion(r.Context(), userID(u), r.PathValue("slug"), req.ModuleRefs, req.DefaultRuntime)
	if err != nil {
		writeSeatAdminServiceError(w, err)
		return
	}
	entry := entities.NewOrderedMap[any]()
	entry.Set("slug", saved.Slug)
	entry.Set("version", saved.Version)
	entry.Set("default_runtime", saved.DefaultRuntime)
	entry.Set("module_refs", seatAdminModuleRefBodies(saved.ModuleRefs))
	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	body.Set("seat_type_version", entry)
	writeJSON(w, http.StatusOK, body)
}

func handleGetModuleVersion(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	source, ok := seatAdminSourceFor(w, sessions)
	if !ok {
		return
	}
	slug, version := r.PathValue("slug"), r.PathValue("version")
	module, err := source.GetModuleVersion(r.Context(), userID(u), slug, version)
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	if module == nil {
		writeDetail(w, http.StatusNotFound, "module \""+slug+"\" version \""+version+"\" not found")
		return
	}
	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	body.Set("module", seatAdminModuleBody(module))
	writeJSON(w, http.StatusOK, body)
}

const maxModuleContentBytes = 65536

type putModuleRequest struct {
	Kind    string `json:"kind"`
	Content string `json:"content"`
}

func handlePutModuleVersion(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	slug, version := r.PathValue("slug"), r.PathValue("version")
	if err := repositories.ValidateModuleSlug(slug); err != nil {
		writeDetail(w, http.StatusBadRequest, err.Error())
		return
	}
	if err := repositories.ValidateConcreteVersion(version); err != nil {
		writeDetail(w, http.StatusBadRequest, err.Error())
		return
	}
	var req putModuleRequest
	if !decodeSeatAdminBody(w, r, &req) {
		return
	}
	kind := resolver.ModuleKind(req.Kind)
	if !resolver.ValidKind(kind) {
		writeDetail(w, http.StatusBadRequest, "kind \""+req.Kind+"\" is not a module kind")
		return
	}
	if req.Content == "" || len(req.Content) > maxModuleContentBytes {
		writeDetail(w, http.StatusBadRequest, "content must be 1 to 65536 bytes")
		return
	}
	if secretscan.Contains(req.Content) {
		writeDetail(w, http.StatusUnprocessableEntity, "secret detected in content")
		return
	}
	source, ok := seatAdminSourceFor(w, sessions)
	if !ok {
		return
	}
	if _, err := source.SaveModule(r.Context(), userID(u), slug, kind); err != nil {
		writeModuleSaveError(w, err, slug, version)
		return
	}
	saved, err := source.AddModuleVersion(r.Context(), userID(u), slug, version, req.Content)
	if err != nil {
		writeModuleSaveError(w, err, slug, version)
		return
	}
	module := entities.NewOrderedMap[any]()
	module.Set("slug", saved.Slug)
	module.Set("kind", saved.Kind)
	module.Set("version", saved.Version)
	module.Set("sha256", saved.Checksum)
	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	body.Set("module", module)
	writeJSON(w, http.StatusOK, body)
}

func writeModuleSaveError(w http.ResponseWriter, err error, slug, version string) {
	switch {
	case errors.Is(err, repositories.ErrModuleKindConflict):
		writeDetail(w, http.StatusConflict, err.Error())
	case errors.Is(err, repositories.ErrModuleVersionConflict):
		writeDetail(w, http.StatusConflict, "version "+version+" of module "+slug+" already exists with different content")
	default:
		writeDetail(w, http.StatusInternalServerError, err.Error())
	}
}

func handleCreateSeat(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	source, ok := seatAdminSourceFor(w, sessions)
	if !ok {
		return
	}
	var req seatAdminSeatRequest
	if !decodeSeatAdminBody(w, r, &req) {
		return
	}
	if strings.TrimSpace(req.SeatKey) == "" || strings.TrimSpace(req.SeatType) == "" {
		writeDetail(w, http.StatusBadRequest, "seat_key and seat_type are required")
		return
	}
	if err := repositories.ValidateName("seat key", req.SeatKey); err != nil {
		writeDetail(w, http.StatusBadRequest, err.Error())
		return
	}
	if err := repositories.ValidateRuntime(req.Runtime); err != nil {
		writeDetail(w, http.StatusBadRequest, err.Error())
		return
	}
	if req.PermissionPolicy == "" {
		req.PermissionPolicy = resolver.DefaultPermissionPolicy
	}
	if err := resolver.CheckPermissionPolicy(req.PermissionPolicy); err != nil {
		writeDetail(w, http.StatusBadRequest, err.Error())
		return
	}
	room, ok := seatAdminRoom(w, r, source, u, r.PathValue("room"))
	if !ok {
		return
	}
	latest, err := source.LatestSeatTypeVersion(r.Context(), userID(u), req.SeatType)
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	if latest == nil {
		writeDetail(w, http.StatusNotFound, "seat type \""+req.SeatType+"\" not found")
		return
	}
	var pinned *string
	switch {
	case req.PinnedVersion != nil:
		version, err := source.GetSeatTypeVersion(r.Context(), userID(u), req.SeatType, *req.PinnedVersion)
		if err != nil {
			writeDetail(w, http.StatusInternalServerError, err.Error())
			return
		}
		if version == nil {
			writeDetail(w, http.StatusBadRequest, "seat type version \""+*req.PinnedVersion+"\" not found")
			return
		}
		pinned = req.PinnedVersion
	case req.FollowLatest != nil:
		if !*req.FollowLatest {
			pinned = &latest.Version
		}
	default:
		settings, err := source.GetSettings(r.Context(), userID(u))
		if err != nil {
			writeDetail(w, http.StatusInternalServerError, err.Error())
			return
		}
		if !settings.FollowLatest {
			pinned = &latest.Version
		}
	}
	existing, err := source.FindSeat(r.Context(), userID(u), room.ID, req.SeatKey)
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	if existing != nil {
		writeDetail(w, http.StatusConflict, "seat \""+req.SeatKey+"\" already exists in room \""+room.Slug+"\"")
		return
	}
	seat, err := source.CreateSeat(r.Context(), userID(u), repositories.Seat{
		RoomID: room.ID, SeatKey: req.SeatKey, SeatTypeID: latest.SeatTypeID,
		PinnedVersion: pinned, Runtime: req.Runtime, Model: req.Model, PermissionPolicy: req.PermissionPolicy,
	})
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	body.Set("seat", seatservices.SeatBody(seat, req.SeatType))
	writeJSON(w, http.StatusOK, body)
}

func handleListSeats(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	source, ok := seatAdminSourceFor(w, sessions)
	if !ok {
		return
	}
	room, ok := seatAdminRoom(w, r, source, u, r.PathValue("room"))
	if !ok {
		return
	}
	seats, err := source.ListSeats(r.Context(), userID(u), room.ID)
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	seatTypes, err := source.ListSeatTypes(r.Context(), userID(u))
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	slugByID := make(map[string]string, len(seatTypes))
	for _, st := range seatTypes {
		slugByID[st.ID] = st.Slug
	}
	out := make([]any, 0, len(seats))
	for i := range seats {
		out = append(out, seatservices.SeatBody(&seats[i], slugByID[seats[i].SeatTypeID]))
	}
	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	body.Set("seats", out)
	writeJSON(w, http.StatusOK, body)
}

func handleDeleteRoom(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	source, ok := seatAdminSourceFor(w, sessions)
	if !ok {
		return
	}
	if err := seatservices.NewRoomDeletionService(source).DeleteRoom(r.Context(), userID(u), r.PathValue("room")); err != nil {
		writeSeatAdminServiceError(w, err)
		return
	}
	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	writeJSON(w, http.StatusOK, body)
}

func handleRemoveSeat(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	source, ok := seatAdminSourceFor(w, sessions)
	if !ok {
		return
	}
	if err := seatservices.NewRoomDeletionService(source).RemoveSeat(r.Context(), userID(u), r.PathValue("room"), r.PathValue("seat")); err != nil {
		writeSeatAdminServiceError(w, err)
		return
	}
	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	writeJSON(w, http.StatusOK, body)
}

func handleSetSeatOccupant(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	source, ok := seatAdminSourceFor(w, sessions)
	if !ok {
		return
	}
	var req seatAdminOccupantRequest
	if !decodeSeatAdminBody(w, r, &req) {
		return
	}
	view, err := seatservices.NewSeatAdminService(source).SetOccupant(r.Context(), userID(u), r.PathValue("room"), r.PathValue("seat"), req.Runtime, req.Model)
	if err != nil {
		writeSeatAdminServiceError(w, err)
		return
	}
	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	body.Set("seat", seatservices.SeatBody(&view.Seat, view.SeatTypeSlug))
	writeJSON(w, http.StatusOK, body)
}

func handleSetSeatPermissionPolicy(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	source, ok := seatAdminSourceFor(w, sessions)
	if !ok {
		return
	}
	var req seatAdminPermissionPolicyRequest
	if !decodeSeatAdminBody(w, r, &req) {
		return
	}
	view, err := seatservices.NewSeatAdminService(source).SetPermissionPolicy(r.Context(), userID(u), r.PathValue("room"), r.PathValue("seat"), req.PermissionPolicy)
	if err != nil {
		writeSeatAdminServiceError(w, err)
		return
	}
	log.Printf("[SEAT] user %s set permission policy of %s/%s to %s", userID(u), r.PathValue("room"), r.PathValue("seat"), req.PermissionPolicy)
	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	body.Set("seat", seatservices.SeatBody(&view.Seat, view.SeatTypeSlug))
	writeJSON(w, http.StatusOK, body)
}

func writeSeatAdminServiceError(w http.ResponseWriter, err error) {
	switch {
	case errors.Is(err, seatservices.ErrInvalidOccupant), errors.Is(err, seatservices.ErrInvalidPermissionPolicy), errors.Is(err, seatservices.ErrInvalidSeatTypeVersion), errors.Is(err, seatservices.ErrLinkCycle):
		writeDetail(w, http.StatusBadRequest, err.Error())
	case errors.Is(err, seatservices.ErrRoomNotFound), errors.Is(err, seatservices.ErrSeatNotFound), errors.Is(err, seatservices.ErrSeatTypeNotFound):
		writeDetail(w, http.StatusNotFound, err.Error())
	case errors.Is(err, repositories.ErrSeatTypeVersionConflict):
		writeDetail(w, http.StatusConflict, err.Error())
	default:
		writeDetail(w, http.StatusInternalServerError, err.Error())
	}
}

func handleCompanyOverlay(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	source, ok := seatAdminSourceFor(w, sessions)
	if !ok {
		return
	}
	ops, ok := seatAdminOverlayOps(w, r)
	if !ok {
		return
	}
	overlay, err := source.UpsertOverlay(r.Context(), userID(u), repositories.Overlay{Scope: repositories.ScopeCompany, Ops: ops})
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeSeatAdminOverlay(w, overlay)
}

func handleRoomOverlay(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	source, ok := seatAdminSourceFor(w, sessions)
	if !ok {
		return
	}
	ops, ok := seatAdminOverlayOps(w, r)
	if !ok {
		return
	}
	room, ok := seatAdminRoom(w, r, source, u, r.PathValue("room"))
	if !ok {
		return
	}
	overlay, err := source.UpsertOverlay(r.Context(), userID(u), repositories.Overlay{Scope: repositories.ScopeRoom, RoomID: room.ID, Ops: ops})
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeSeatAdminOverlay(w, overlay)
}

func handleSeatOverlay(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	source, ok := seatAdminSourceFor(w, sessions)
	if !ok {
		return
	}
	ops, ok := seatAdminOverlayOps(w, r)
	if !ok {
		return
	}
	room, ok := seatAdminRoom(w, r, source, u, r.PathValue("room"))
	if !ok {
		return
	}
	seat, ok := seatAdminSeat(w, r, source, u, room.ID, r.PathValue("seat"))
	if !ok {
		return
	}
	overlay, err := source.UpsertOverlay(r.Context(), userID(u), repositories.Overlay{Scope: repositories.ScopeSeat, SeatID: seat.ID, Ops: ops})
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeSeatAdminOverlay(w, overlay)
}

func handleGetCompanyOverlay(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	source, ok := seatAdminSourceFor(w, sessions)
	if !ok {
		return
	}
	overlay, err := source.FindOverlay(r.Context(), userID(u), repositories.ScopeCompany, "", "")
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeSeatAdminOverlay(w, seatAdminOverlayOrEmpty(repositories.ScopeCompany, overlay))
}

func handleGetRoomOverlay(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	source, ok := seatAdminSourceFor(w, sessions)
	if !ok {
		return
	}
	room, ok := seatAdminRoom(w, r, source, u, r.PathValue("room"))
	if !ok {
		return
	}
	overlay, err := source.FindOverlay(r.Context(), userID(u), repositories.ScopeRoom, room.ID, "")
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeSeatAdminOverlay(w, seatAdminOverlayOrEmpty(repositories.ScopeRoom, overlay))
}

func handleGetSeatOverlay(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	source, ok := seatAdminSourceFor(w, sessions)
	if !ok {
		return
	}
	room, ok := seatAdminRoom(w, r, source, u, r.PathValue("room"))
	if !ok {
		return
	}
	seat, ok := seatAdminSeat(w, r, source, u, room.ID, r.PathValue("seat"))
	if !ok {
		return
	}
	overlay, err := source.FindOverlay(r.Context(), userID(u), repositories.ScopeSeat, "", seat.ID)
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeSeatAdminOverlay(w, seatAdminOverlayOrEmpty(repositories.ScopeSeat, overlay))
}

// seatAdminOverlayOrEmpty keeps an absent overlay a successful empty read, not a 404.
func seatAdminOverlayOrEmpty(scope string, overlay *repositories.Overlay) *repositories.Overlay {
	if overlay != nil {
		return overlay
	}
	return &repositories.Overlay{Scope: scope}
}

func writeSeatAdminOverlay(w http.ResponseWriter, overlay *repositories.Overlay) {
	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	body.Set("overlay", seatAdminOverlayBody(overlay))
	writeJSON(w, http.StatusOK, body)
}

func seatAdminOverlayOps(w http.ResponseWriter, r *http.Request) ([]resolver.Op, bool) {
	var req seatAdminOverlayRequest
	if !decodeSeatAdminBody(w, r, &req) {
		return nil, false
	}
	ops := make([]resolver.Op, 0, len(req.Ops))
	for _, op := range req.Ops {
		kind := resolver.OpKind(op.Kind)
		invalid := ""
		switch kind {
		case resolver.OpAdd:
			if op.Slug == "" {
				invalid = "add requires slug"
			}
		case resolver.OpRemove:
			if op.Slug == "" {
				invalid = "remove requires slug"
			}
		case resolver.OpOverride:
			if op.Slug == "" {
				invalid = "override requires slug"
			} else if op.Content == "" {
				invalid = "override requires content"
			}
		case resolver.OpPin:
			if op.Slug == "" {
				invalid = "pin requires slug"
			} else if op.Version == "" || op.Version == "latest" {
				invalid = "pin requires a concrete version"
			}
		default:
			invalid = "kind \"" + op.Kind + "\" is not add, remove, override or pin"
		}
		if invalid != "" {
			writeDetail(w, http.StatusBadRequest, invalid)
			return nil, false
		}
		if secretscan.Contains(op.Content) || secretscan.Contains(op.Slug) || secretscan.Contains(op.Version) {
			writeDetail(w, http.StatusUnprocessableEntity, "secret detected in content")
			return nil, false
		}
		ops = append(ops, resolver.Op{Kind: kind, Slug: op.Slug, Version: op.Version, Content: op.Content})
	}
	return ops, true
}

func handleUpsertSeatLink(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	source, ok := seatAdminSourceFor(w, sessions)
	if !ok {
		return
	}
	var req seatAdminLinkRequest
	if !decodeSeatAdminBody(w, r, &req) {
		return
	}
	room, ok := seatAdminRoom(w, r, source, u, r.PathValue("room"))
	if !ok {
		return
	}
	seatKey := r.PathValue("seat")
	from, ok := seatAdminSeat(w, r, source, u, room.ID, seatKey)
	if !ok {
		return
	}
	if strings.TrimSpace(req.ToSeat) == "" {
		writeDetail(w, http.StatusBadRequest, "to_seat is required")
		return
	}
	if req.ToSeat == seatKey {
		writeDetail(w, http.StatusBadRequest, "to_seat must not be the seat itself")
		return
	}
	if !seatAdminLinkKind(req.Kind) {
		writeDetail(w, http.StatusBadRequest, "kind \""+req.Kind+"\" is not a seat link kind")
		return
	}
	to, ok := seatAdminSeat(w, r, source, u, room.ID, req.ToSeat)
	if !ok {
		return
	}
	allow := true
	if req.Allow != nil {
		allow = *req.Allow
	}
	link, err := seatservices.NewSeatLinkService(source).UpsertSeatLink(r.Context(), userID(u), room.ID, repositories.SeatLink{
		FromSeatID: from.ID, ToSeatID: to.ID, Kind: req.Kind, Allow: allow,
	})
	if err != nil {
		writeSeatAdminServiceError(w, err)
		return
	}
	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	body.Set("link", seatAdminLinkBody(link))
	writeJSON(w, http.StatusOK, body)
}

// handleDeleteSeatLink deletes one link. The target may be a removed seat so that links
// left behind by a seat removal can still be cleaned up.
func handleDeleteSeatLink(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	source, ok := seatAdminSourceFor(w, sessions)
	if !ok {
		return
	}
	kind := r.PathValue("kind")
	if !seatAdminLinkKind(kind) {
		writeDetail(w, http.StatusBadRequest, "kind \""+kind+"\" is not a seat link kind")
		return
	}
	room, ok := seatAdminRoom(w, r, source, u, r.PathValue("room"))
	if !ok {
		return
	}
	from, ok := seatAdminSeat(w, r, source, u, room.ID, r.PathValue("seat"))
	if !ok {
		return
	}
	toKey := r.PathValue("to")
	to, err := source.FindSeat(r.Context(), userID(u), room.ID, toKey)
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	if to == nil {
		writeDetail(w, http.StatusNotFound, "seat \""+toKey+"\" not found")
		return
	}
	deleted, err := source.DeleteSeatLink(r.Context(), userID(u), from.ID, to.ID, kind)
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	if !deleted {
		writeDetail(w, http.StatusNotFound, "link "+from.SeatKey+" "+kind+" "+toKey+" not found")
		return
	}
	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	writeJSON(w, http.StatusOK, body)
}

func handleListSeatLinks(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	source, ok := seatAdminSourceFor(w, sessions)
	if !ok {
		return
	}
	room, ok := seatAdminRoom(w, r, source, u, r.PathValue("room"))
	if !ok {
		return
	}
	seat, ok := seatAdminSeat(w, r, source, u, room.ID, r.PathValue("seat"))
	if !ok {
		return
	}
	links, err := source.ListSeatLinks(r.Context(), userID(u), seat.ID)
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	out := make([]any, 0, len(links))
	for i := range links {
		out = append(out, seatAdminLinkBody(&links[i]))
	}
	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	body.Set("links", out)
	writeJSON(w, http.StatusOK, body)
}

func handleGetSettings(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	source, ok := seatAdminSourceFor(w, sessions)
	if !ok {
		return
	}
	settings, err := source.GetSettings(r.Context(), userID(u))
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeSeatAdminSettings(w, settings)
}

func handlePutSettings(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	source, ok := seatAdminSourceFor(w, sessions)
	if !ok {
		return
	}
	var req seatAdminSettingsRequest
	if !decodeSeatAdminBody(w, r, &req) {
		return
	}
	if req.FollowLatest == nil {
		writeDetail(w, http.StatusBadRequest, "follow_latest is required")
		return
	}
	settings, err := source.SetSettings(r.Context(), userID(u), *req.FollowLatest)
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeSeatAdminSettings(w, settings)
}

func writeSeatAdminSettings(w http.ResponseWriter, settings *repositories.SeatSettings) {
	settingsBody := entities.NewOrderedMap[any]()
	settingsBody.Set("follow_latest", settings.FollowLatest)
	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	body.Set("settings", settingsBody)
	writeJSON(w, http.StatusOK, body)
}

func seatAdminLinkKind(kind string) bool {
	return commpolicy.ValidKind(commpolicy.LinkKind(kind))
}

func seatAdminRoomBody(room *repositories.Room) *entities.OrderedMap[any] {
	body := entities.NewOrderedMap[any]()
	body.Set("id", room.ID)
	body.Set("slug", room.Slug)
	body.Set("name", room.Name)
	return body
}

func seatAdminModuleBody(module *repositories.ModuleVersion) *entities.OrderedMap[any] {
	body := entities.NewOrderedMap[any]()
	body.Set("slug", module.Slug)
	body.Set("kind", module.Kind)
	body.Set("version", module.Version)
	body.Set("content", module.Content)
	body.Set("checksum", module.Checksum)
	return body
}

func seatAdminOverlayBody(overlay *repositories.Overlay) *entities.OrderedMap[any] {
	ops := make([]any, 0, len(overlay.Ops))
	for _, op := range overlay.Ops {
		entry := entities.NewOrderedMap[any]()
		entry.Set("kind", string(op.Kind))
		entry.Set("slug", op.Slug)
		entry.Set("version", op.Version)
		entry.Set("content", op.Content)
		ops = append(ops, entry)
	}
	body := entities.NewOrderedMap[any]()
	body.Set("id", overlay.ID)
	body.Set("scope", overlay.Scope)
	body.Set("room_id", overlay.RoomID)
	body.Set("seat_id", overlay.SeatID)
	body.Set("ops", ops)
	return body
}

func seatAdminLinkBody(link *repositories.SeatLink) *entities.OrderedMap[any] {
	body := entities.NewOrderedMap[any]()
	body.Set("id", link.ID)
	body.Set("from_seat_id", link.FromSeatID)
	body.Set("to_seat_id", link.ToSeatID)
	body.Set("kind", link.Kind)
	body.Set("allow", link.Allow)
	return body
}
