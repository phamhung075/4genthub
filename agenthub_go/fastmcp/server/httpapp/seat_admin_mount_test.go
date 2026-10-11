package httpapp

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"net/http/httptest"
	"sort"
	"strconv"
	"strings"
	"testing"

	seatservices "agenthub/fastmcp/seat_management/application/services"
	"agenthub/fastmcp/seat_management/domain/repositories"
	"agenthub/fastmcp/seat_management/domain/resolver"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

type fakeSeatAdmin struct {
	rooms          []*repositories.Room
	seatTypes      map[string]*repositories.SeatTypeVersion
	seatVersions   map[string]map[string]*repositories.SeatTypeVersion
	seatTypeList   []*repositories.SeatType
	moduleVersions map[string]*repositories.ModuleVersion
	moduleKinds    map[string]resolver.ModuleKind
	seats          []*repositories.Seat
	overlays       map[string]*repositories.Overlay
	links          []*repositories.SeatLink
	settings       map[string]*repositories.SeatSettings

	deletedResolved []string
	addVersionErr   error

	deletedStatusRooms []string
	deletedStatusSeats []string
	deletedEdgeRooms   []string
	// The message store's two, so a deletion test can assert that undelivered text went with the seat
	// or the room rather than being left behind.
	deletedMessageRooms []string
	deletedMessageSeats []string
}

func newFakeSeatAdmin() *fakeSeatAdmin {
	return &fakeSeatAdmin{
		seatTypes:      map[string]*repositories.SeatTypeVersion{},
		seatVersions:   map[string]map[string]*repositories.SeatTypeVersion{},
		moduleVersions: map[string]*repositories.ModuleVersion{},
		moduleKinds:    map[string]resolver.ModuleKind{},
		overlays:       map[string]*repositories.Overlay{},
		settings:       map[string]*repositories.SeatSettings{},
	}
}

func (f *fakeSeatAdmin) seedRoom(slug string) *repositories.Room {
	room := &repositories.Room{ID: "room-" + slug, Slug: slug, Name: slug}
	f.rooms = append(f.rooms, room)
	return room
}

func (f *fakeSeatAdmin) seedSeatType(slug, latest string, versions ...string) {
	f.seatTypes[slug] = &repositories.SeatTypeVersion{ID: "stv-" + slug, SeatTypeID: "st-" + slug, Slug: slug, Version: latest, DefaultRuntime: "claude-code"}
	f.seatVersions[slug] = map[string]*repositories.SeatTypeVersion{
		latest: {ID: "stv-" + slug + "-" + latest, SeatTypeID: "st-" + slug, Slug: slug, Version: latest, DefaultRuntime: "claude-code"},
	}
	for _, v := range versions {
		f.seatVersions[slug][v] = &repositories.SeatTypeVersion{ID: "stv-" + slug + "-" + v, SeatTypeID: "st-" + slug, Slug: slug, Version: v, DefaultRuntime: "claude-code"}
	}
	f.seatTypeList = append(f.seatTypeList, &repositories.SeatType{
		ID: "st-" + slug, Slug: slug, Name: slug, Description: "desc-" + slug,
	})
}

func (f *fakeSeatAdmin) SaveRoom(_ context.Context, userID string, room repositories.Room) (*repositories.Room, error) {
	for _, r := range f.rooms {
		if r.Slug == room.Slug {
			return r, nil
		}
	}
	saved := &repositories.Room{ID: "room-" + room.Slug, UserID: userID, Slug: room.Slug, Name: room.Name}
	f.rooms = append(f.rooms, saved)
	return saved, nil
}

func (f *fakeSeatAdmin) ListRooms(_ context.Context, _ string) ([]repositories.Room, error) {
	out := make([]repositories.Room, 0, len(f.rooms))
	for _, r := range f.rooms {
		out = append(out, *r)
	}
	return out, nil
}

func (f *fakeSeatAdmin) GetRoomBySlug(_ context.Context, userID, slug string) (*repositories.Room, error) {
	for _, r := range f.rooms {
		if r.Slug == slug && (r.UserID == "" || r.UserID == userID) {
			return r, nil
		}
	}
	return nil, nil
}

// GetVisibleRoomBySlug is the read-scoped lookup (D5 sharing). This fake has no memberships, so it
// answers with the caller's own room; sharingSeatAdmin in seat_admin_team_sharing_test.go is the
// fake that models teams and is the one that exercises sharing.
func (f *fakeSeatAdmin) GetVisibleRoomBySlug(ctx context.Context, userID, slug string) (*repositories.Room, error) {
	return f.GetRoomBySlug(ctx, userID, slug)
}

// SetRoomTeam is the sharing write: owner-only, as the repository's owner-scoped UPDATE is.
func (f *fakeSeatAdmin) SetRoomTeam(_ context.Context, userID, roomID, teamID string) error {
	for _, r := range f.rooms {
		if r.ID != roomID {
			continue
		}
		if r.UserID != "" && r.UserID != userID {
			return repositories.ErrRoomNotOwned
		}
		r.TeamID = teamID
		return nil
	}
	return repositories.ErrRoomNotOwned
}

func (f *fakeSeatAdmin) LatestSeatTypeVersion(_ context.Context, _, slug string) (*repositories.SeatTypeVersion, error) {
	return f.seatTypes[slug], nil
}

func (f *fakeSeatAdmin) ListSeatTypes(_ context.Context, _ string) ([]repositories.SeatType, error) {
	out := make([]repositories.SeatType, 0, len(f.seatTypeList))
	for _, st := range f.seatTypeList {
		out = append(out, *st)
	}
	return out, nil
}

func (f *fakeSeatAdmin) SaveSeatType(_ context.Context, userID string, seatType repositories.SeatType) (*repositories.SeatType, error) {
	saved := &repositories.SeatType{ID: "st-" + seatType.Slug, UserID: userID, Slug: seatType.Slug, Name: seatType.Name, Description: seatType.Description}
	f.seatTypeList = append(f.seatTypeList, saved)
	if f.seatVersions[seatType.Slug] == nil {
		f.seatVersions[seatType.Slug] = map[string]*repositories.SeatTypeVersion{}
	}
	return saved, nil
}

func (f *fakeSeatAdmin) GetSeatTypeVersion(_ context.Context, _, slug, version string) (*repositories.SeatTypeVersion, error) {
	return f.seatVersions[slug][version], nil
}

func (f *fakeSeatAdmin) GetModuleVersion(_ context.Context, _, slug, version string) (*repositories.ModuleVersion, error) {
	return f.moduleVersions[slug+"@"+version], nil
}

func (f *fakeSeatAdmin) ListLatestModuleVersions(_ context.Context, _ string) ([]repositories.ModuleVersion, error) {
	out := make([]repositories.ModuleVersion, 0, len(f.moduleVersions))
	for _, mv := range f.moduleVersions {
		out = append(out, *mv)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Slug < out[j].Slug })
	return out, nil
}

func (f *fakeSeatAdmin) AddSeatTypeVersion(_ context.Context, _, slug, version, defaultRuntime string, refs []resolver.ModuleRef) (*repositories.SeatTypeVersion, error) {
	if f.addVersionErr != nil {
		return nil, f.addVersionErr
	}
	created := &repositories.SeatTypeVersion{SeatTypeID: "st-" + slug, Slug: slug, Version: version, DefaultRuntime: defaultRuntime, ModuleRefs: refs}
	f.seatVersions[slug][version] = created
	f.seatTypes[slug] = created
	return created, nil
}

func (f *fakeSeatAdmin) SaveModule(_ context.Context, _, slug string, kind resolver.ModuleKind) (*repositories.Module, error) {
	if existing, ok := f.moduleKinds[slug]; ok && existing != kind {
		return nil, fmt.Errorf("module %q already exists with kind %q: %w", slug, existing, repositories.ErrModuleKindConflict)
	}
	f.moduleKinds[slug] = kind
	return &repositories.Module{Slug: slug, Kind: kind}, nil
}

func (f *fakeSeatAdmin) AddModuleVersion(_ context.Context, _, slug, version, content string) (*repositories.ModuleVersion, error) {
	sum := sha256.Sum256([]byte(content))
	checksum := hex.EncodeToString(sum[:])
	key := slug + "@" + version
	if existing, ok := f.moduleVersions[key]; ok {
		if existing.Checksum != checksum {
			return nil, fmt.Errorf("different checksum: %w", repositories.ErrModuleVersionConflict)
		}
		return existing, nil
	}
	created := &repositories.ModuleVersion{Slug: slug, Kind: f.moduleKinds[slug], Version: version, Content: content, Checksum: checksum}
	f.moduleVersions[key] = created
	return created, nil
}

func (f *fakeSeatAdmin) FindSeat(_ context.Context, _, roomID, seatKey string) (*repositories.Seat, error) {
	for _, s := range f.seats {
		if s.RoomID == roomID && s.SeatKey == seatKey {
			return s, nil
		}
	}
	return nil, nil
}

func (f *fakeSeatAdmin) CreateSeat(_ context.Context, userID string, seat repositories.Seat) (*repositories.Seat, error) {
	created := seat
	created.ID = "seat-" + seat.RoomID + "-" + seat.SeatKey
	created.UserID = userID
	f.seats = append(f.seats, &created)
	return &created, nil
}

func (f *fakeSeatAdmin) ListSeats(_ context.Context, _, roomID string) ([]repositories.Seat, error) {
	out := make([]repositories.Seat, 0)
	for _, s := range f.seats {
		if s.RoomID == roomID {
			out = append(out, *s)
		}
	}
	return out, nil
}

func (f *fakeSeatAdmin) UpdateSeatPermissionPolicy(_ context.Context, _, seatID, permissionPolicy string) error {
	for _, s := range f.seats {
		if s.ID == seatID {
			s.PermissionPolicy = permissionPolicy
		}
	}
	return nil
}

func (f *fakeSeatAdmin) UpdateSeatPinnedVersion(_ context.Context, _, seatID, pinnedVersion string) error {
	for _, s := range f.seats {
		if s.ID == seatID {
			s.PinnedVersion = &pinnedVersion
		}
	}
	return nil
}

func (f *fakeSeatAdmin) UpdateSeatOccupant(_ context.Context, _, seatID, runtime, model string) error {
	for _, s := range f.seats {
		if s.ID == seatID {
			s.Runtime, s.Model = runtime, model
		}
	}
	return nil
}

func (f *fakeSeatAdmin) UpsertOverlay(_ context.Context, userID string, overlay repositories.Overlay) (*repositories.Overlay, error) {
	if err := overlay.ValidateTarget(); err != nil {
		return nil, err
	}
	key := overlay.Scope + "|" + overlay.RoomID + "|" + overlay.SeatID
	saved := overlay
	saved.ID = "overlay-" + key
	saved.UserID = userID
	f.overlays[key] = &saved
	return &saved, nil
}

func (f *fakeSeatAdmin) FindOverlay(_ context.Context, _, scope, roomID, seatID string) (*repositories.Overlay, error) {
	return f.overlays[scope+"|"+roomID+"|"+seatID], nil
}

func (f *fakeSeatAdmin) UpsertSeatLink(_ context.Context, userID string, link repositories.SeatLink) (*repositories.SeatLink, error) {
	for _, l := range f.links {
		if l.FromSeatID == link.FromSeatID && l.ToSeatID == link.ToSeatID && l.Kind == link.Kind {
			l.Allow = link.Allow
			return l, nil
		}
	}
	saved := link
	saved.ID = "link-" + link.FromSeatID + "-" + link.ToSeatID
	saved.UserID = userID
	f.links = append(f.links, &saved)
	return &saved, nil
}

func (f *fakeSeatAdmin) ListSeatLinks(_ context.Context, _, seatID string) ([]repositories.SeatLink, error) {
	out := make([]repositories.SeatLink, 0)
	for _, l := range f.links {
		if l.FromSeatID == seatID {
			out = append(out, *l)
		}
	}
	return out, nil
}

func (f *fakeSeatAdmin) DeleteSeatLink(_ context.Context, _, fromSeatID, toSeatID, kind string) (bool, error) {
	for i, l := range f.links {
		if l.FromSeatID == fromSeatID && l.ToSeatID == toSeatID && l.Kind == kind {
			f.links = append(f.links[:i], f.links[i+1:]...)
			return true, nil
		}
	}
	return false, nil
}

func (f *fakeSeatAdmin) DeleteSeatLinksOfSeat(_ context.Context, _, seatID string) error {
	kept := f.links[:0]
	for _, l := range f.links {
		if l.FromSeatID != seatID && l.ToSeatID != seatID {
			kept = append(kept, l)
		}
	}
	f.links = kept
	return nil
}

func (f *fakeSeatAdmin) DeleteSeatOverlay(_ context.Context, _, seatID string) error {
	delete(f.overlays, repositories.ScopeSeat+"||"+seatID)
	return nil
}

func (f *fakeSeatAdmin) DeleteRoomOverlay(_ context.Context, _, roomID string) error {
	delete(f.overlays, repositories.ScopeRoom+"|"+roomID+"|")
	return nil
}

func (f *fakeSeatAdmin) DeleteSeatStatusForRoom(_ context.Context, _, roomSlug string) error {
	f.deletedStatusRooms = append(f.deletedStatusRooms, roomSlug)
	return nil
}

func (f *fakeSeatAdmin) DeleteSeatStatusForSeat(_ context.Context, _, roomSlug, seatKey string) error {
	f.deletedStatusSeats = append(f.deletedStatusSeats, roomSlug+"/"+seatKey)
	return nil
}

func (f *fakeSeatAdmin) DeleteMachineEdgesForRoom(_ context.Context, _, roomSlug string) error {
	f.deletedEdgeRooms = append(f.deletedEdgeRooms, roomSlug)
	return nil
}

func (f *fakeSeatAdmin) DeleteSeatMessagesForSeat(_ context.Context, _, roomSlug, seatKey string) error {
	f.deletedMessageSeats = append(f.deletedMessageSeats, roomSlug+"/"+seatKey)
	return nil
}

func (f *fakeSeatAdmin) DeleteSeatMessagesForRoom(_ context.Context, _, roomSlug string) error {
	f.deletedMessageRooms = append(f.deletedMessageRooms, roomSlug)
	return nil
}

func (f *fakeSeatAdmin) DeleteResolvedSeats(_ context.Context, _, seatID string) error {
	f.deletedResolved = append(f.deletedResolved, seatID)
	return nil
}

func (f *fakeSeatAdmin) DeleteSeat(_ context.Context, _, seatID string) error {
	kept := f.seats[:0]
	for _, seat := range f.seats {
		if seat.ID != seatID {
			kept = append(kept, seat)
		}
	}
	f.seats = kept
	return nil
}

func (f *fakeSeatAdmin) DeleteRoom(_ context.Context, _, roomID string) error {
	kept := f.rooms[:0]
	for _, room := range f.rooms {
		if room.ID != roomID {
			kept = append(kept, room)
		}
	}
	f.rooms = kept
	return nil
}

func (f *fakeSeatAdmin) InTransaction(ctx context.Context, fn func(ctx context.Context) error) error {
	return fn(ctx)
}

func (f *fakeSeatAdmin) GetSettings(_ context.Context, userID string) (*repositories.SeatSettings, error) {
	if settings, ok := f.settings[userID]; ok {
		return settings, nil
	}
	return &repositories.SeatSettings{UserID: userID}, nil
}

func (f *fakeSeatAdmin) SetSettings(_ context.Context, userID string, followLatest bool) (*repositories.SeatSettings, error) {
	settings := &repositories.SeatSettings{UserID: userID, FollowLatest: followLatest}
	f.settings[userID] = settings
	return settings, nil
}

// fakeResolutionService adapts the admin fake's seeded data to the repositories the resolution
// service holds, so the overlay PUT routes exercise the real candidate-overlay validation.
func fakeResolutionService(fake *fakeSeatAdmin) *seatservices.SeatResolutionService {
	return &seatservices.SeatResolutionService{
		Rooms:      fakeResolutionRooms{fake: fake},
		Seats:      fakeResolutionSeats{fake: fake},
		SeatTypes:  fakeResolutionSeatTypes{fake: fake},
		Overlays:   fakeResolutionOverlays{fake: fake},
		Links:      fakeResolutionLinks{fake: fake},
		Resolved:   fakeResolutionResolved{fake: fake},
		NewCatalog: func(string) seatservices.CheckedCatalog { return fakeResolutionCatalog{fake: fake} },
	}
}

type fakeResolutionRooms struct {
	repositories.RoomRepository
	fake *fakeSeatAdmin
}

func (r fakeResolutionRooms) List(ctx context.Context, userID string) ([]repositories.Room, error) {
	return r.fake.ListRooms(ctx, userID)
}

func (r fakeResolutionRooms) GetBySlug(ctx context.Context, userID, slug string) (*repositories.Room, error) {
	return r.fake.GetRoomBySlug(ctx, userID, slug)
}

type fakeResolutionSeats struct {
	repositories.SeatRepository
	fake *fakeSeatAdmin
}

func (s fakeResolutionSeats) ListByRoom(ctx context.Context, userID, roomID string) ([]repositories.Seat, error) {
	return s.fake.ListSeats(ctx, userID, roomID)
}

func (s fakeResolutionSeats) FindByRoomAndKey(ctx context.Context, userID, roomID, seatKey string) (*repositories.Seat, error) {
	return s.fake.FindSeat(ctx, userID, roomID, seatKey)
}

func (s fakeResolutionSeats) GetByID(_ context.Context, _, seatID string) (*repositories.Seat, error) {
	for _, seat := range s.fake.seats {
		if seat.ID == seatID {
			return seat, nil
		}
	}
	return nil, nil
}

type fakeResolutionSeatTypes struct {
	repositories.SeatTypeRepository
	fake *fakeSeatAdmin
}

func (t fakeResolutionSeatTypes) GetByID(_ context.Context, _, seatTypeID string) (*repositories.SeatType, error) {
	for _, seatType := range t.fake.seatTypeList {
		if seatType.ID == seatTypeID {
			return seatType, nil
		}
	}
	return nil, nil
}

func (t fakeResolutionSeatTypes) List(ctx context.Context, userID string) ([]repositories.SeatType, error) {
	return t.fake.ListSeatTypes(ctx, userID)
}

func (t fakeResolutionSeatTypes) LatestVersion(ctx context.Context, userID, slug string) (*repositories.SeatTypeVersion, error) {
	return t.fake.LatestSeatTypeVersion(ctx, userID, slug)
}

func (t fakeResolutionSeatTypes) GetVersion(ctx context.Context, userID, slug, version string) (*repositories.SeatTypeVersion, error) {
	return t.fake.GetSeatTypeVersion(ctx, userID, slug, version)
}

type fakeResolutionOverlays struct {
	repositories.OverlayRepository
	fake *fakeSeatAdmin
}

func (o fakeResolutionOverlays) Find(ctx context.Context, userID, scope, roomID, seatID string) (*repositories.Overlay, error) {
	return o.fake.FindOverlay(ctx, userID, scope, roomID, seatID)
}

// fakeResolutionLinks exposes the admin fake's seat_links rows to the resolution service, so a
// test can prove the links the resolver consults are exactly the ones the admin routes leave
// behind.
type fakeResolutionLinks struct {
	repositories.SeatLinkRepository
	fake *fakeSeatAdmin
}

func (l fakeResolutionLinks) ListFrom(ctx context.Context, userID, seatID string) ([]repositories.SeatLink, error) {
	return l.fake.ListSeatLinks(ctx, userID, seatID)
}

type fakeResolutionResolved struct {
	repositories.ResolvedSeatRepository
	fake *fakeSeatAdmin
}

func (r fakeResolutionResolved) Save(_ context.Context, _ string, seat repositories.ResolvedSeat) (*repositories.ResolvedSeat, error) {
	return &seat, nil
}

type fakeResolutionCatalog struct{ fake *fakeSeatAdmin }

func (c fakeResolutionCatalog) Get(slug, version string) (resolver.ModuleVersion, bool) {
	module, err := c.fake.GetModuleVersion(context.Background(), "", slug, version)
	if err != nil || module == nil {
		return resolver.ModuleVersion{}, false
	}
	return resolver.ModuleVersion{Slug: module.Slug, Version: module.Version, Kind: module.Kind, Content: module.Content}, true
}

func (fakeResolutionCatalog) Err() error { return nil }

func seatAdminTestMux(t *testing.T, fake *fakeSeatAdmin) *http.ServeMux {
	t.Helper()
	previousSource := newSeatAdminSource
	newSeatAdminSource = func(*database.SessionManager) (seatAdminSource, error) { return fake, nil }
	previousResolution := newSeatResolution
	newSeatResolution = func(*database.SessionManager, string) (*seatservices.SeatResolutionService, error) {
		return fakeResolutionService(fake), nil
	}
	t.Cleanup(func() {
		newSeatAdminSource = previousSource
		newSeatResolution = previousResolution
	})
	authenticateTestUser(t)
	mux := http.NewServeMux()
	mountSeatAdminRoutes(mux, nil)
	return mux
}

func TestSeatAdminMutationsBroadcastOneSeatFrame(t *testing.T) {
	type frame struct{ action, entity, id, room, seatKey, userID string }
	var frames []frame
	previous := seatBroadcastFn
	seatBroadcastFn = func(_ context.Context, action, entity, id, room, seatKey, userID string) error {
		frames = append(frames, frame{action, entity, id, room, seatKey, userID})
		return nil
	}
	defer func() { seatBroadcastFn = previous }()

	fake := newFakeSeatAdmin()
	fake.seedRoom("dev")
	fake.seedSeatType("coder", "1.0.0")
	mux := seatAdminTestMux(t, fake)
	overlay := func(slug string) string {
		return `{"ops":[{"kind":"add","slug":"` + slug + `","version":"1.0.0"}]}`
	}
	// Each scope adds a distinct module: the same slug in two scopes would be a duplicate add
	// on every shared seat, which the overlay fold now refuses.
	for _, slug := range []string{"instr-room", "instr-company", "instr-seat"} {
		if rec := doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/modules/"+slug+"/versions/1.0.0", `{"kind":"instruction","content":"c"}`); rec.Code != http.StatusOK {
			t.Fatalf("seed module %s: %d %s", slug, rec.Code, rec.Body.String())
		}
	}
	frames = nil // the module PUTs above are not seat-domain mutations; start the observation here

	steps := []struct {
		name, method, path, body, entity, action, id string
	}{
		{"room create", http.MethodPost, "/api/v2/openrig/rooms", `{"slug":"team","name":"Team"}`, "room", "created", "team"},
		{"seat create", http.MethodPost, "/api/v2/openrig/rooms/dev/seats", `{"seat_key":"alice","seat_type":"coder","runtime":"claude-code"}`, "seat", "created", "dev/alice"},
		{"permission policy", http.MethodPut, "/api/v2/openrig/rooms/dev/seats/alice/permission-policy", `{"permission_policy":"yolo"}`, "seat", "updated", "dev/alice"},
		{"room overlay", http.MethodPut, "/api/v2/openrig/rooms/dev/overlay", overlay("instr-room"), "room", "updated", "dev"},
		{"company overlay", http.MethodPut, "/api/v2/openrig/overlay", overlay("instr-company"), "room", "updated", "company"},
		{"seat overlay", http.MethodPut, "/api/v2/openrig/rooms/dev/seats/alice/overlay", overlay("instr-seat"), "seat", "updated", "dev/alice"},
		{"seat create bob", http.MethodPost, "/api/v2/openrig/rooms/dev/seats", `{"seat_key":"bob","seat_type":"coder","runtime":"claude-code"}`, "seat", "created", "dev/bob"},
		{"link upsert", http.MethodPut, "/api/v2/openrig/rooms/dev/seats/alice/links", `{"to_seat":"bob","kind":"delegates_to"}`, "seat", "updated", "dev/alice"},
		{"occupant", http.MethodPut, "/api/v2/openrig/rooms/dev/seats/alice/occupant", `{"runtime":"omp","model":"deepseek/deepseek-flash"}`, "seat", "updated", "dev/alice"},
		{"settings", http.MethodPut, "/api/v2/openrig/settings", `{"follow_latest":true}`, "room", "updated", "company"},
		{"seat delete", http.MethodDelete, "/api/v2/openrig/rooms/dev/seats/alice", "", "seat", "deleted", "dev/alice"},
		{"seat delete bob", http.MethodDelete, "/api/v2/openrig/rooms/dev/seats/bob", "", "seat", "deleted", "dev/bob"},
		{"room delete", http.MethodDelete, "/api/v2/openrig/rooms/dev", "", "room", "deleted", "dev"},
	}
	for _, step := range steps {
		before := len(frames)
		rec := doTestRequest(t, mux, step.method, step.path, step.body)
		if rec.Code != http.StatusOK {
			t.Fatalf("%s: status = %d: %s", step.name, rec.Code, rec.Body.String())
		}
		if len(frames) != before+1 {
			t.Fatalf("%s: emitted %d frames, want exactly 1", step.name, len(frames)-before)
		}
		got := frames[len(frames)-1]
		if got.entity != step.entity || got.action != step.action || got.id != step.id {
			t.Fatalf("%s: frame = %+v, want %s/%s/%s", step.name, got, step.entity, step.action, step.id)
		}
		if got.userID == "" {
			t.Fatalf("%s: frame carries no user id, so it cannot be tenant-scoped", step.name)
		}
		if step.entity == "seat" && (got.room == "" || got.seatKey == "") {
			t.Fatalf("%s: seat frame is missing room/seat_key: %+v", step.name, got)
		}
	}

	// A rejected mutation must not announce anything.
	before := len(frames)
	if rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms", `{"slug":"team","name":"Again"}`); rec.Code != http.StatusConflict {
		t.Fatalf("duplicate room: status = %d, want 409", rec.Code)
	}
	if len(frames) != before {
		t.Fatalf("a rejected mutation emitted %d frames", len(frames)-before)
	}
}

func TestSeatAdminLinkRestrictedToClaudeCodeSeats(t *testing.T) {
	fake := newFakeSeatAdmin()
	fake.seedRoom("dev")
	fake.seedSeatType("coder", "1.0.0")
	mux := seatAdminTestMux(t, fake)

	create := func(seatKey, runtime string) {
		t.Helper()
		body := `{"seat_key":"` + seatKey + `","seat_type":"coder","runtime":"` + runtime + `"}`
		if rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms/dev/seats", body); rec.Code != http.StatusOK {
			t.Fatalf("create %s/%s: %d %s", seatKey, runtime, rec.Code, rec.Body.String())
		}
	}
	create("alpha", "claude-code")
	create("coderx", "codex")
	create("gamma", "claude-code")

	link := "/api/v2/openrig/rooms/dev/seats/alpha/links"
	// An allowing link into a codex seat is refused: no verified deny path there (G3 owner decision).
	rec := doTestRequest(t, mux, http.MethodPut, link, `{"to_seat":"coderx","kind":"delegates_to"}`)
	if rec.Code != http.StatusBadRequest || !strings.Contains(rec.Body.String(), "restricted to claude-code seats") {
		t.Fatalf("allowing link to codex: %d %s", rec.Code, rec.Body.String())
	}
	// A deny link only removes a channel, so it stays legal for any runtime.
	rec = doTestRequest(t, mux, http.MethodPut, link, `{"to_seat":"coderx","kind":"delegates_to","allow":false}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("deny link to codex: %d %s", rec.Code, rec.Body.String())
	}
	// Between two claude-code seats an allowing link still works.
	rec = doTestRequest(t, mux, http.MethodPut, link, `{"to_seat":"gamma","kind":"delegates_to"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("allowing link between claude-code seats: %d %s", rec.Code, rec.Body.String())
	}
}

func TestSeatAdminRooms(t *testing.T) {
	mux := seatAdminTestMux(t, newFakeSeatAdmin())
	rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms", `{"slug":"dev","name":"Development"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("create room: status = %d: %s", rec.Code, rec.Body.String())
	}
	for _, want := range []string{`"slug":"dev"`, `"name":"Development"`, `"room":{"id":"room-dev"`} {
		if !strings.Contains(rec.Body.String(), want) {
			t.Errorf("create room body missing %s: %s", want, rec.Body.String())
		}
	}
	rec = doTestRequest(t, mux, http.MethodGet, "/api/v2/openrig/rooms", "")
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"name":"Development"`) {
		t.Errorf("list rooms: %d %s", rec.Code, rec.Body.String())
	}

	// A second create of the same slug is a conflict that keeps the stored name.
	rec = doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms", `{"slug":"dev","name":"Renamed"}`)
	if rec.Code != http.StatusConflict || !strings.Contains(rec.Body.String(), "already exists") {
		t.Errorf("duplicate room: status = %d, want 409 already exists: %s", rec.Code, rec.Body.String())
	}
	rec = doTestRequest(t, mux, http.MethodGet, "/api/v2/openrig/rooms", "")
	if !strings.Contains(rec.Body.String(), `"name":"Development"`) || strings.Contains(rec.Body.String(), "Renamed") {
		t.Errorf("duplicate create changed the room: %s", rec.Body.String())
	}
}

func TestSeatAdminCreateRoomRejectsLongName(t *testing.T) {
	mux := seatAdminTestMux(t, newFakeSeatAdmin())
	for name, want := range map[string]int{strings.Repeat("n", 200): http.StatusOK, strings.Repeat("n", 201): http.StatusBadRequest} {
		slug := "r" + strconv.Itoa(len(name))
		rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms", `{"slug":"`+slug+`","name":"`+name+`"}`)
		if rec.Code != want {
			t.Errorf("name of %d chars: status = %d, want %d: %s", len(name), rec.Code, want, rec.Body.String())
		}
	}
}

func TestSeatAdminCreateSeatPinsByDefault(t *testing.T) {
	fake := newFakeSeatAdmin()
	fake.seedRoom("dev")
	fake.seedSeatType("coder", "1.0.0")
	mux := seatAdminTestMux(t, fake)
	rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms/dev/seats",
		`{"seat_key":"alice","seat_type":"coder","runtime":"claude-code","model":"sonnet"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("create seat: status = %d: %s", rec.Code, rec.Body.String())
	}
	for _, want := range []string{`"seat_key":"alice"`, `"seat_type_id":"st-coder"`, `"seat_type":"coder"`, `"pinned_version":"1.0.0"`} {
		if !strings.Contains(rec.Body.String(), want) {
			t.Errorf("create seat body missing %s: %s", want, rec.Body.String())
		}
	}
}

func TestSeatAdminCreateSeatFollowLatest(t *testing.T) {
	fake := newFakeSeatAdmin()
	fake.seedRoom("dev")
	fake.seedSeatType("coder", "1.0.0")
	mux := seatAdminTestMux(t, fake)
	rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms/dev/seats",
		`{"seat_key":"bob","seat_type":"coder","runtime":"codex","model":"gpt","follow_latest":true}`)
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"pinned_version":null`) {
		t.Errorf("follow_latest: %d %s", rec.Code, rec.Body.String())
	}
}

func TestSeatAdminCreateSeatExplicitPin(t *testing.T) {
	fake := newFakeSeatAdmin()
	fake.seedRoom("dev")
	fake.seedSeatType("coder", "1.0.0", "0.9.0")
	mux := seatAdminTestMux(t, fake)
	rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms/dev/seats",
		`{"seat_key":"alice","seat_type":"coder","pinned_version":"0.9.0","runtime":"claude-code","model":"sonnet"}`)
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"pinned_version":"0.9.0"`) {
		t.Errorf("explicit pin: %d %s", rec.Code, rec.Body.String())
	}
	rec = doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms/dev/seats",
		`{"seat_key":"carol","seat_type":"coder","pinned_version":"9.9.9","runtime":"claude-code","model":"sonnet"}`)
	if rec.Code != http.StatusBadRequest {
		t.Errorf("missing pinned version: status = %d, want 400", rec.Code)
	}
}

func TestSeatAdminListSeatTypes(t *testing.T) {
	fake := newFakeSeatAdmin()
	fake.seedSeatType("coder", "1.0.0")
	fake.seatTypes["coder"].ModuleRefs = []resolver.ModuleRef{{Slug: "instr", Version: "1.0.0"}}
	fake.seatTypeList = append(fake.seatTypeList, &repositories.SeatType{
		ID: "st-empty", Slug: "empty", Name: "Empty", Description: "desc-empty",
	})
	mux := seatAdminTestMux(t, fake)
	rec := doTestRequest(t, mux, http.MethodGet, "/api/v2/openrig/seat-types", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("list seat types: status = %d: %s", rec.Code, rec.Body.String())
	}
	for _, want := range []string{
		`"slug":"coder"`, `"name":"coder"`, `"description":"desc-coder"`,
		`"default_runtime":"claude-code"`, `"latest_version":"1.0.0"`,
		`"module_refs":[{"slug":"instr","version":"1.0.0"}]`,
		`"slug":"empty"`, `"default_runtime":null`, `"latest_version":null`, `"module_refs":[]`,
	} {
		if !strings.Contains(rec.Body.String(), want) {
			t.Errorf("list seat types missing %s: %s", want, rec.Body.String())
		}
	}
}

func TestSeatAdminPutModuleVersion(t *testing.T) {
	fake := newFakeSeatAdmin()
	mux := seatAdminTestMux(t, fake)
	const path = "/api/v2/openrig/modules/my-skill/versions/1.0.0"
	block := testSkillBlock(t, "# A skill\n")
	sum := sha256.Sum256([]byte(block))
	sha := hex.EncodeToString(sum[:])

	rec := doTestRequest(t, mux, http.MethodPut, path, testModuleBody(t, "skill", block))
	if rec.Code != http.StatusOK {
		t.Fatalf("create: status = %d: %s", rec.Code, rec.Body.String())
	}
	want := `{"success":true,"module":{"slug":"my-skill","kind":"skill","version":"1.0.0","sha256":"` + sha + `"}}`
	if strings.TrimSpace(rec.Body.String()) != want {
		t.Errorf("create body = %s, want %s", rec.Body.String(), want)
	}
	if rec = doTestRequest(t, mux, http.MethodPut, path, testModuleBody(t, "skill", block)); rec.Code != http.StatusOK {
		t.Errorf("idempotent repeat: status = %d: %s", rec.Code, rec.Body.String())
	}

	rec = doTestRequest(t, mux, http.MethodPut, path, testModuleBody(t, "skill", testSkillBlock(t, "# Another skill\n")))
	if rec.Code != http.StatusConflict || !strings.Contains(rec.Body.String(), "version 1.0.0 of module my-skill already exists with different content") {
		t.Errorf("content conflict: %d %s", rec.Code, rec.Body.String())
	}
	if rec = doTestRequest(t, mux, http.MethodPut, path, testModuleBody(t, "document", block)); rec.Code != http.StatusConflict {
		t.Errorf("kind mismatch: status = %d, want 409: %s", rec.Code, rec.Body.String())
	}
}

func TestSeatAdminPutModuleVersionRejectsInvalidInput(t *testing.T) {
	mux := seatAdminTestMux(t, newFakeSeatAdmin())
	cases := []struct {
		name, path, body string
		status           int
	}{
		{"bad slug", "/api/v2/openrig/modules/Bad_Slug/versions/1.0.0", `{"kind":"skill","content":"x"}`, http.StatusBadRequest},
		{"latest version", "/api/v2/openrig/modules/m/versions/latest", `{"kind":"skill","content":"x"}`, http.StatusBadRequest},
		{"partial version", "/api/v2/openrig/modules/m/versions/1.0", `{"kind":"skill","content":"x"}`, http.StatusBadRequest},
		{"bad kind", "/api/v2/openrig/modules/m/versions/1.0.0", `{"kind":"widget","content":"x"}`, http.StatusBadRequest},
		{"empty content", "/api/v2/openrig/modules/m/versions/1.0.0", `{"kind":"skill","content":""}`, http.StatusBadRequest},
		{"oversize content", "/api/v2/openrig/modules/m/versions/1.0.0", `{"kind":"skill","content":"` + strings.Repeat("a", 65537) + `"}`, http.StatusBadRequest},
		{"unknown field", "/api/v2/openrig/modules/m/versions/1.0.0", `{"kind":"skill","content":"x","extra":1}`, http.StatusBadRequest},
		{"secret", "/api/v2/openrig/modules/m/versions/1.0.0", `{"kind":"skill","content":"key AKIAABCDEFGHIJKLMNOP"}`, http.StatusUnprocessableEntity},
	}
	for _, c := range cases {
		rec := doTestRequest(t, mux, http.MethodPut, c.path, c.body)
		if rec.Code != c.status {
			t.Errorf("%s: status = %d, want %d: %s", c.name, rec.Code, c.status, rec.Body.String())
		}
		if c.name == "secret" && (!strings.Contains(rec.Body.String(), "secret detected in content") || strings.Contains(rec.Body.String(), "AKIA")) {
			t.Errorf("secret body = %s", rec.Body.String())
		}
	}
}

func TestSeatAdminListModules(t *testing.T) {
	fake := newFakeSeatAdmin()
	mux := seatAdminTestMux(t, fake)
	rec := doTestRequest(t, mux, http.MethodGet, "/api/v2/openrig/modules", "")
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"modules":[]`) {
		t.Fatalf("empty list: %d %s", rec.Code, rec.Body.String())
	}
	if rec = doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/modules/zeta/versions/1.0.0", testModuleBody(t, "skill", testSkillBlock(t, "# zeta\n"))); rec.Code != http.StatusOK {
		t.Fatalf("put module: %d %s", rec.Code, rec.Body.String())
	}
	if rec = doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/modules/alpha/versions/1.2.0", `{"kind":"instruction","content":"a"}`); rec.Code != http.StatusOK {
		t.Fatalf("put module: %d %s", rec.Code, rec.Body.String())
	}
	rec = doTestRequest(t, mux, http.MethodGet, "/api/v2/openrig/modules", "")
	body := rec.Body.String()
	alpha := strings.Index(body, `"slug":"alpha","kind":"instruction","version":"1.2.0","sha256":"`)
	zeta := strings.Index(body, `"slug":"zeta","kind":"skill","version":"1.0.0","sha256":"`)
	if rec.Code != http.StatusOK || alpha < 0 || zeta < alpha || strings.Contains(body, `"content"`) {
		t.Errorf("list modules: %d %s", rec.Code, body)
	}
}

func TestSeatAdminCreateSeatTypeVersion(t *testing.T) {
	fake := newFakeSeatAdmin()
	fake.seedSeatType("coder", "1.0.0")
	mux := seatAdminTestMux(t, fake)
	for _, put := range []string{"instr/versions/1.0.0", "skill-x/versions/2.1.0"} {
		kind, content := "instruction", "c"
		if strings.HasPrefix(put, "skill") {
			kind, content = "skill", testSkillBlock(t, "# skill-x\n")
		}
		if rec := doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/modules/"+put, testModuleBody(t, kind, content)); rec.Code != http.StatusOK {
			t.Fatalf("put module %s: %d %s", put, rec.Code, rec.Body.String())
		}
	}
	rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/seat-types/coder/versions",
		`{"module_refs":["instr@1.0.0","skill-x@2.1.0"],"default_runtime":"codex"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("create version: %d %s", rec.Code, rec.Body.String())
	}
	for _, want := range []string{`"slug":"coder"`, `"version":"1.0.1"`, `"default_runtime":"codex"`,
		`"module_refs":[{"slug":"instr","version":"1.0.0"},{"slug":"skill-x","version":"2.1.0"}]`} {
		if !strings.Contains(rec.Body.String(), want) {
			t.Errorf("body missing %s: %s", want, rec.Body.String())
		}
	}
	rec = doTestRequest(t, mux, http.MethodGet, "/api/v2/openrig/seat-types", "")
	if !strings.Contains(rec.Body.String(), `"default_runtime":"codex","latest_version":"1.0.1"`) {
		t.Errorf("seat type listing does not show the new version's runtime: %s", rec.Body.String())
	}
	if fake.seatVersions["coder"]["1.0.0"].DefaultRuntime != "claude-code" {
		t.Error("the new version changed the runtime of the earlier version")
	}
}

func TestSeatAdminCreateSeatTypeVersionRejects(t *testing.T) {
	fake := newFakeSeatAdmin()
	fake.seedSeatType("coder", "1.0.0")
	mux := seatAdminTestMux(t, fake)
	if rec := doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/modules/instr/versions/1.0.0", `{"kind":"instruction","content":"c"}`); rec.Code != http.StatusOK {
		t.Fatalf("put module: %d", rec.Code)
	}
	cases := []struct {
		name, path, body string
		want             int
	}{
		{"unknown seat type", "/api/v2/openrig/seat-types/ghost/versions", `{"module_refs":[],"default_runtime":"codex"}`, http.StatusNotFound},
		{"unknown module", "/api/v2/openrig/seat-types/coder/versions", `{"module_refs":["ghost@1.0.0"],"default_runtime":"codex"}`, http.StatusBadRequest},
		{"unknown module version", "/api/v2/openrig/seat-types/coder/versions", `{"module_refs":["instr@9.9.9"],"default_runtime":"codex"}`, http.StatusBadRequest},
		{"no at sign", "/api/v2/openrig/seat-types/coder/versions", `{"module_refs":["instr"],"default_runtime":"codex"}`, http.StatusBadRequest},
		{"latest alias", "/api/v2/openrig/seat-types/coder/versions", `{"module_refs":["instr@latest"],"default_runtime":"codex"}`, http.StatusBadRequest},
		{"duplicate slug", "/api/v2/openrig/seat-types/coder/versions", `{"module_refs":["instr@1.0.0","instr@1.0.0"],"default_runtime":"codex"}`, http.StatusBadRequest},
		{"bad runtime", "/api/v2/openrig/seat-types/coder/versions", `{"module_refs":[],"default_runtime":"gemini"}`, http.StatusBadRequest},
		{"unknown field", "/api/v2/openrig/seat-types/coder/versions", `{"module_refs":[],"default_runtime":"codex","x":1}`, http.StatusBadRequest},
	}
	for _, c := range cases {
		if rec := doTestRequest(t, mux, http.MethodPost, c.path, c.body); rec.Code != c.want {
			t.Errorf("%s: status = %d, want %d: %s", c.name, rec.Code, c.want, rec.Body.String())
		}
	}
	if fake.seatVersions["coder"]["1.0.1"] != nil {
		t.Error("a rejected request created a version")
	}
}

func TestSeatAdminCreateSeatTypeVersionMapsStoreErrors(t *testing.T) {
	fake := newFakeSeatAdmin()
	fake.seedSeatType("coder", "1.0.0")
	mux := seatAdminTestMux(t, fake)
	cases := []struct {
		name string
		err  error
		want int
	}{
		{"concurrent writer took the version", fmt.Errorf("exists: %w", repositories.ErrSeatTypeVersionConflict), http.StatusConflict},
		{"database failure", errors.New("connection reset"), http.StatusInternalServerError},
	}
	for _, c := range cases {
		fake.addVersionErr = c.err
		rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/seat-types/coder/versions", `{"module_refs":[],"default_runtime":"codex"}`)
		if rec.Code != c.want {
			t.Errorf("%s: status = %d, want %d: %s", c.name, rec.Code, c.want, rec.Body.String())
		}
	}
}

func TestSeatAdminGetModuleVersion(t *testing.T) {
	fake := newFakeSeatAdmin()
	fake.moduleVersions["instr@1.0.0"] = &repositories.ModuleVersion{
		ID: "mv-1", Slug: "instr", Kind: resolver.KindInstruction, Version: "1.0.0",
		Content: "hello", Checksum: "abc",
	}
	mux := seatAdminTestMux(t, fake)
	rec := doTestRequest(t, mux, http.MethodGet, "/api/v2/openrig/modules/instr/versions/1.0.0", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("get module version: status = %d: %s", rec.Code, rec.Body.String())
	}
	for _, want := range []string{
		`"slug":"instr"`, `"kind":"instruction"`, `"version":"1.0.0"`, `"content":"hello"`, `"checksum":"abc"`,
	} {
		if !strings.Contains(rec.Body.String(), want) {
			t.Errorf("get module version missing %s: %s", want, rec.Body.String())
		}
	}
	if rec = doTestRequest(t, mux, http.MethodGet, "/api/v2/openrig/modules/instr/versions/9.9.9", ""); rec.Code != http.StatusNotFound {
		t.Errorf("missing module version: status = %d, want 404", rec.Code)
	}
}

func TestSeatAdminGetOverlays(t *testing.T) {
	fake := newFakeSeatAdmin()
	fake.moduleVersions["instr@1"] = &repositories.ModuleVersion{Slug: "instr", Version: "1"}
	fake.seedSeatType("coder", "1.0.0")
	room := fake.seedRoom("dev")
	fake.seats = append(fake.seats, &repositories.Seat{ID: "seat-a", RoomID: room.ID, SeatKey: "alice", SeatTypeID: "st-coder", PermissionPolicy: "standard"})
	mux := seatAdminTestMux(t, fake)

	for _, path := range []string{
		"/api/v2/openrig/overlay",
		"/api/v2/openrig/rooms/dev/overlay",
		"/api/v2/openrig/rooms/dev/seats/alice/overlay",
	} {
		rec := doTestRequest(t, mux, http.MethodGet, path, "")
		if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"ops":[]`) {
			t.Errorf("empty GET %s: %d %s", path, rec.Code, rec.Body.String())
		}
	}

	if rec := doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/overlay",
		`{"ops":[{"kind":"add","slug":"instr","version":"1"}]}`); rec.Code != http.StatusOK {
		t.Fatalf("PUT company overlay: %d %s", rec.Code, rec.Body.String())
	}
	rec := doTestRequest(t, mux, http.MethodGet, "/api/v2/openrig/overlay", "")
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"scope":"company"`) || !strings.Contains(rec.Body.String(), `"slug":"instr"`) {
		t.Errorf("GET company overlay: %d %s", rec.Code, rec.Body.String())
	}

	if rec = doTestRequest(t, mux, http.MethodGet, "/api/v2/openrig/rooms/ghost/overlay", ""); rec.Code != http.StatusNotFound {
		t.Errorf("GET absent room overlay: status = %d, want 404", rec.Code)
	}
	if rec = doTestRequest(t, mux, http.MethodGet, "/api/v2/openrig/rooms/dev/seats/ghost/overlay", ""); rec.Code != http.StatusNotFound {
		t.Errorf("GET absent seat overlay: status = %d, want 404", rec.Code)
	}
}

func TestSeatAdminSettings(t *testing.T) {
	fake := newFakeSeatAdmin()
	mux := seatAdminTestMux(t, fake)

	rec := doTestRequest(t, mux, http.MethodGet, "/api/v2/openrig/settings", "")
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"settings":{"follow_latest":false}`) {
		t.Fatalf("default settings: %d %s", rec.Code, rec.Body.String())
	}
	rec = doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/settings", `{"follow_latest":true}`)
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"settings":{"follow_latest":true}`) {
		t.Fatalf("set settings: %d %s", rec.Code, rec.Body.String())
	}
	rec = doTestRequest(t, mux, http.MethodGet, "/api/v2/openrig/settings", "")
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"settings":{"follow_latest":true}`) {
		t.Fatalf("get settings after set: %d %s", rec.Code, rec.Body.String())
	}
	if rec = doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/settings", `{}`); rec.Code != http.StatusBadRequest {
		t.Errorf("missing follow_latest: status = %d, want 400", rec.Code)
	}
	if rec = doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/settings", `{"follow_latest":true,"bogus":1}`); rec.Code != http.StatusBadRequest {
		t.Errorf("unknown settings field: status = %d, want 400", rec.Code)
	}
}

func TestSeatAdminCreateSeatHonorsSetting(t *testing.T) {
	fake := newFakeSeatAdmin()
	fake.seedRoom("dev")
	fake.seedSeatType("coder", "1.0.0", "0.9.0")
	fake.settings["11111111-1111-4111-8111-111111111111"] = &repositories.SeatSettings{
		UserID: "11111111-1111-4111-8111-111111111111", FollowLatest: true,
	}
	mux := seatAdminTestMux(t, fake)

	rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms/dev/seats",
		`{"seat_key":"alice","seat_type":"coder","runtime":"claude-code"}`)
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"pinned_version":null`) {
		t.Fatalf("company follow_latest=true: %d %s", rec.Code, rec.Body.String())
	}

	rec = doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms/dev/seats",
		`{"seat_key":"bob","seat_type":"coder","runtime":"claude-code","follow_latest":false}`)
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"pinned_version":"1.0.0"`) {
		t.Errorf("explicit follow_latest=false over setting: %d %s", rec.Code, rec.Body.String())
	}

	rec = doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms/dev/seats",
		`{"seat_key":"carol","seat_type":"coder","runtime":"claude-code","pinned_version":"0.9.0"}`)
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"pinned_version":"0.9.0"`) {
		t.Errorf("explicit pinned_version over setting: %d %s", rec.Code, rec.Body.String())
	}
}

func TestSeatAdminListSeats(t *testing.T) {
	fake := newFakeSeatAdmin()
	room := fake.seedRoom("dev")
	fake.seedSeatType("coder", "1.0.0")
	fake.seatTypeList = append(fake.seatTypeList, &repositories.SeatType{ID: "st-coder", Slug: "coder"})
	fake.seats = append(fake.seats,
		&repositories.Seat{ID: "seat-a", RoomID: room.ID, SeatKey: "alice", SeatTypeID: "st-coder"},
	)
	mux := seatAdminTestMux(t, fake)
	rec := doTestRequest(t, mux, http.MethodGet, "/api/v2/openrig/rooms/dev/seats", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("list seats: status = %d: %s", rec.Code, rec.Body.String())
	}
	if !strings.Contains(rec.Body.String(), `"seat_key":"alice"`) || !strings.Contains(rec.Body.String(), `"seat_type":"coder"`) {
		t.Errorf("seat or its seat type slug missing: %s", rec.Body.String())
	}
}

func TestSeatAdminRemoveSeatIsAHardDelete(t *testing.T) {
	t.Setenv(publicURLEnv, "https://api.example.test")
	fake := newFakeSeatAdmin()
	room := fake.seedRoom("dev")
	fake.seedSeatType("coder", "1.0.0")
	fake.seats = append(fake.seats,
		&repositories.Seat{ID: "seat-a", RoomID: room.ID, SeatKey: "alice", PermissionPolicy: "standard"},
		&repositories.Seat{ID: "seat-b", RoomID: room.ID, SeatKey: "bob", PermissionPolicy: "standard"},
	)
	fake.links = append(fake.links,
		&repositories.SeatLink{FromSeatID: "seat-a", ToSeatID: "seat-b", Kind: "delegates_to", Allow: true},
		&repositories.SeatLink{FromSeatID: "seat-b", ToSeatID: "seat-a", Kind: "can_observe", Allow: true},
	)
	if _, err := fake.UpsertOverlay(context.Background(), "u", repositories.Overlay{Scope: repositories.ScopeSeat, SeatID: "seat-a", Ops: []resolver.Op{{Kind: resolver.OpAdd, Slug: "m", Version: "1.0.0"}}}); err != nil {
		t.Fatal(err)
	}
	mux := seatAdminTestMux(t, fake)
	rigMux := seatRigSpecTestMux(t, rigSpecOverAdminFake{fake})
	seatPath := "/api/v2/openrig/rooms/dev/seats/alice"

	room.UserID = "another-user"
	if rec := doTestRequest(t, mux, http.MethodDelete, seatPath, ""); rec.Code != http.StatusNotFound {
		t.Fatalf("other user's seat: status = %d, want 404", rec.Code)
	}
	if len(fake.seats) != 2 || len(fake.links) != 2 {
		t.Fatalf("another user's request deleted rows: %d seats, %d links", len(fake.seats), len(fake.links))
	}
	room.UserID = ""

	if rec := doTestRequest(t, mux, http.MethodDelete, seatPath, ""); rec.Code != http.StatusOK {
		t.Fatalf("remove seat: status = %d: %s", rec.Code, rec.Body.String())
	}
	if len(fake.seats) != 1 || fake.seats[0].SeatKey != "bob" {
		t.Errorf("seats left = %+v, want only bob", fake.seats)
	}
	if len(fake.links) != 0 {
		t.Errorf("links of the removed seat left in either direction: %+v", fake.links)
	}
	if len(fake.overlays) != 0 {
		t.Errorf("overlay of the removed seat left: %+v", fake.overlays)
	}
	if strings.Join(fake.deletedResolved, ",") != "seat-a" || strings.Join(fake.deletedStatusSeats, ",") != "dev/alice" ||
		strings.Join(fake.deletedMessageSeats, ",") != "dev/alice" {
		t.Errorf("snapshots deleted = %v, statuses deleted = %v, messages deleted = %v, want seat-a and dev/alice for both",
			fake.deletedResolved, fake.deletedStatusSeats, fake.deletedMessageSeats)
	}
	if rec := doTestRequest(t, mux, http.MethodDelete, seatPath, ""); rec.Code != http.StatusNotFound {
		t.Errorf("second delete: status = %d, want 404", rec.Code)
	}
	rec := doTestRequest(t, rigMux, http.MethodGet, "/api/v2/openrig/rooms/dev/rigspec", "")
	doc := decodeRigSpec(t, rec)
	if strings.Contains(doc.RigSpec.YAML, "alice") || strings.Contains(doc.RigSpec.YAML, "delegates_to") || strings.Contains(doc.RigSpec.YAML, "can_observe") {
		t.Errorf("rigspec after delete still mentions the seat or its edges: %s", doc.RigSpec.YAML)
	}

	rec = doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms/dev/seats", `{"seat_key":"alice","seat_type":"coder","runtime":"claude-code"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("re-add the same seat key: status = %d: %s", rec.Code, rec.Body.String())
	}
	rec = doTestRequest(t, mux, http.MethodGet, seatPath+"/links", "")
	if strings.Contains(rec.Body.String(), "delegates_to") || strings.Contains(rec.Body.String(), "can_observe") {
		t.Errorf("re-added seat has the old links: %s", rec.Body.String())
	}
	if len(fake.overlays) != 0 {
		t.Errorf("re-added seat has the old overlay: %+v", fake.overlays)
	}
}

// rigSpecOverAdminFake serves the rigspec route from the admin fake's rows so a test can
// change links through the admin API and render the result.
type rigSpecOverAdminFake struct{ *fakeSeatAdmin }

func (f rigSpecOverAdminFake) ListSeatsByRoom(ctx context.Context, userID, roomID string) ([]repositories.Seat, error) {
	return f.ListSeats(ctx, userID, roomID)
}

func (f rigSpecOverAdminFake) ResolveSeat(_ context.Context, _, _, seatKey string) (*repositories.ResolvedSeat, error) {
	return &repositories.ResolvedSeat{Hash: "h-" + seatKey, Runtime: "claude-code"}, nil
}

func (f rigSpecOverAdminFake) ListSeatLinksFrom(ctx context.Context, userID, seatID string) ([]repositories.SeatLink, error) {
	return f.ListSeatLinks(ctx, userID, seatID)
}

func (f rigSpecOverAdminFake) GetSeatByID(_ context.Context, _, seatID string) (*repositories.Seat, error) {
	for _, seat := range f.seats {
		if seat.ID == seatID {
			return seat, nil
		}
	}
	return nil, nil
}

func TestSeatAdminDeleteLink(t *testing.T) {
	t.Setenv(publicURLEnv, "https://api.example.test")
	fake := newFakeSeatAdmin()
	room := fake.seedRoom("dev")
	fake.seats = append(fake.seats,
		&repositories.Seat{ID: "seat-a", RoomID: room.ID, SeatKey: "alice", PermissionPolicy: "standard"},
		&repositories.Seat{ID: "seat-b", RoomID: room.ID, SeatKey: "bob", PermissionPolicy: "standard"},
	)
	mux := seatAdminTestMux(t, fake)
	rigMux := seatRigSpecTestMux(t, rigSpecOverAdminFake{fake})
	linkPath := "/api/v2/openrig/rooms/dev/seats/alice/links"
	if rec := doTestRequest(t, mux, http.MethodPut, linkPath, `{"to_seat":"bob","kind":"delegates_to"}`); rec.Code != http.StatusOK {
		t.Fatalf("upsert link: %d %s", rec.Code, rec.Body.String())
	}
	if rec := doTestRequest(t, mux, http.MethodPut, linkPath, `{"to_seat":"bob","kind":"can_observe"}`); rec.Code != http.StatusOK {
		t.Fatalf("upsert second link: %d %s", rec.Code, rec.Body.String())
	}
	rec := doTestRequest(t, rigMux, http.MethodGet, "/api/v2/openrig/rooms/dev/rigspec", "")
	if !strings.Contains(rec.Body.String(), "delegates_to") {
		t.Fatalf("rigspec before delete lacks the link: %d %s", rec.Code, rec.Body.String())
	}

	if rec = doTestRequest(t, mux, http.MethodDelete, linkPath+"/bob/delegates_to", ""); rec.Code != http.StatusOK {
		t.Fatalf("delete link: %d %s", rec.Code, rec.Body.String())
	}
	rec = doTestRequest(t, mux, http.MethodGet, linkPath, "")
	if strings.Contains(rec.Body.String(), "delegates_to") || !strings.Contains(rec.Body.String(), "can_observe") {
		t.Errorf("list after delete should keep only the other kind: %s", rec.Body.String())
	}
	rec = doTestRequest(t, rigMux, http.MethodGet, "/api/v2/openrig/rooms/dev/rigspec", "")
	var doc rigSpecHTTPResponse = decodeRigSpec(t, rec)
	if strings.Contains(doc.RigSpec.YAML, "delegates_to") || !strings.Contains(doc.RigSpec.YAML, "can_observe") {
		t.Errorf("rigspec after delete: %s", doc.RigSpec.YAML)
	}

	cases := []struct {
		name, path string
		want       int
	}{
		{"already deleted", linkPath + "/bob/delegates_to", http.StatusNotFound},
		{"unknown target", linkPath + "/ghost/can_observe", http.StatusNotFound},
		{"unknown source", "/api/v2/openrig/rooms/dev/seats/ghost/links/bob/can_observe", http.StatusNotFound},
		{"unknown room", "/api/v2/openrig/rooms/ghost/seats/alice/links/bob/can_observe", http.StatusNotFound},
		{"bad kind", linkPath + "/bob/hates", http.StatusBadRequest},
	}
	for _, c := range cases {
		if rec := doTestRequest(t, mux, http.MethodDelete, c.path, ""); rec.Code != c.want {
			t.Errorf("%s: status = %d, want %d: %s", c.name, rec.Code, c.want, rec.Body.String())
		}
	}

	room.UserID = "another-user"
	if rec := doTestRequest(t, mux, http.MethodDelete, linkPath+"/bob/can_observe", ""); rec.Code != http.StatusNotFound {
		t.Errorf("other user's room: status = %d, want 404", rec.Code)
	}
	if len(fake.links) != 1 {
		t.Errorf("another user's request changed links: %d left, want 1", len(fake.links))
	}
}

// Deleting a link removes it from the enforcing set the resolver consults, not merely from the
// list view: the sending seat's resolved communication policy carried the link before the delete
// and carries it no longer after, so a runtime's comm-guard would stop admitting the message.
func TestSeatAdminDeleteLinkRemovesItFromTheResolvedPolicy(t *testing.T) {
	fake := newFakeSeatAdmin()
	dev := fake.seedRoom("dev")
	fake.seedSeatType("coder", "1.0.0")
	fake.seats = append(fake.seats,
		&repositories.Seat{ID: "seat-a", RoomID: dev.ID, SeatKey: "alice", SeatTypeID: "st-coder", Runtime: "claude-code"},
		&repositories.Seat{ID: "seat-b", RoomID: dev.ID, SeatKey: "bob", SeatTypeID: "st-coder", Runtime: "claude-code"},
	)
	mux := seatAdminTestMux(t, fake)
	resolution := fakeResolutionService(fake)

	policy := func() string {
		t.Helper()
		resolved, err := resolution.ResolveSeat(context.Background(), "u", "dev", "alice")
		if err != nil {
			t.Fatalf("ResolveSeat: %v", err)
		}
		encoded, err := json.Marshal(resolved.Policy)
		if err != nil {
			t.Fatalf("marshal policy: %v", err)
		}
		return string(encoded)
	}

	linkPath := "/api/v2/openrig/rooms/dev/seats/alice/links"
	if rec := doTestRequest(t, mux, http.MethodPut, linkPath, `{"to_seat":"bob","kind":"delegates_to"}`); rec.Code != http.StatusOK {
		t.Fatalf("upsert link: %d %s", rec.Code, rec.Body.String())
	}
	if got := policy(); !strings.Contains(got, `"To":"bob"`) || !strings.Contains(got, `"delegates_to"`) {
		t.Fatalf("policy before delete lacks the enforcing link: %s", got)
	}

	if rec := doTestRequest(t, mux, http.MethodDelete, linkPath+"/bob/delegates_to", ""); rec.Code != http.StatusOK {
		t.Fatalf("delete link: %d %s", rec.Code, rec.Body.String())
	}
	if got := policy(); strings.Contains(got, `"To":"bob"`) || strings.Contains(got, `"delegates_to"`) {
		t.Errorf("policy after delete still enforces the deleted link: %s", got)
	}
}

func TestSeatAdminDeleteRoom(t *testing.T) {
	fake := newFakeSeatAdmin()
	dev := fake.seedRoom("dev")
	ops := repositories.Overlay{Scope: repositories.ScopeRoom, RoomID: dev.ID, Ops: []resolver.Op{{Kind: resolver.OpAdd, Slug: "m", Version: "1.0.0"}}}
	other := fake.seedRoom("other")
	fake.seats = append(fake.seats,
		&repositories.Seat{ID: "seat-a", RoomID: dev.ID, SeatKey: "alice"},
		&repositories.Seat{ID: "seat-b", RoomID: dev.ID, SeatKey: "bob"},
		&repositories.Seat{ID: "seat-x", RoomID: other.ID, SeatKey: "xena"},
	)
	fake.links = append(fake.links,
		&repositories.SeatLink{FromSeatID: "seat-a", ToSeatID: "seat-b", Kind: "delegates_to", Allow: true},
		&repositories.SeatLink{FromSeatID: "seat-b", ToSeatID: "seat-a", Kind: "escalates_to", Allow: true},
	)
	mux := seatAdminTestMux(t, fake)
	if _, err := fake.UpsertOverlay(context.Background(), "u", ops); err != nil {
		t.Fatal(err)
	}
	if _, err := fake.UpsertOverlay(context.Background(), "u", repositories.Overlay{Scope: repositories.ScopeSeat, SeatID: "seat-a", Ops: ops.Ops}); err != nil {
		t.Fatal(err)
	}
	if _, err := fake.UpsertOverlay(context.Background(), "u", repositories.Overlay{Scope: repositories.ScopeCompany, Ops: ops.Ops}); err != nil {
		t.Fatal(err)
	}

	dev.UserID = "another-user"
	if rec := doTestRequest(t, mux, http.MethodDelete, "/api/v2/openrig/rooms/dev", ""); rec.Code != http.StatusNotFound {
		t.Fatalf("other user's room: status = %d, want 404", rec.Code)
	}
	if len(fake.rooms) != 2 || len(fake.seats) != 3 || len(fake.links) != 2 {
		t.Fatalf("another user's request deleted rows: %d rooms, %d seats, %d links", len(fake.rooms), len(fake.seats), len(fake.links))
	}
	dev.UserID = ""

	// A room that still holds seats is refused, naming the count, and nothing is deleted: the
	// seats are never cascaded away.
	rec := doTestRequest(t, mux, http.MethodDelete, "/api/v2/openrig/rooms/dev", "")
	if rec.Code != http.StatusConflict {
		t.Fatalf("delete room with seats: %d %s, want 409", rec.Code, rec.Body.String())
	}
	if !strings.Contains(rec.Body.String(), `still holds 2 seat(s)`) {
		t.Errorf("refusal does not name the count: %s", rec.Body.String())
	}
	if len(fake.rooms) != 2 || len(fake.seats) != 3 || len(fake.links) != 2 || len(fake.overlays) != 3 {
		t.Fatalf("a refused delete changed rows: %d rooms, %d seats, %d links, %d overlays",
			len(fake.rooms), len(fake.seats), len(fake.links), len(fake.overlays))
	}

	// Removing the seats first empties the room, and then the room itself deletes.
	for _, seat := range []string{"alice", "bob"} {
		if rec := doTestRequest(t, mux, http.MethodDelete, "/api/v2/openrig/rooms/dev/seats/"+seat, ""); rec.Code != http.StatusOK {
			t.Fatalf("remove seat %s: %d %s", seat, rec.Code, rec.Body.String())
		}
	}
	if rec := doTestRequest(t, mux, http.MethodDelete, "/api/v2/openrig/rooms/dev", ""); rec.Code != http.StatusOK {
		t.Fatalf("delete empty room: %d %s", rec.Code, rec.Body.String())
	}
	if len(fake.rooms) != 1 || fake.rooms[0].Slug != "other" {
		t.Errorf("rooms left = %+v, want only other", fake.rooms)
	}
	if len(fake.seats) != 1 || fake.seats[0].SeatKey != "xena" {
		t.Errorf("seats left = %+v, want only xena", fake.seats)
	}
	if len(fake.links) != 0 {
		t.Errorf("links left = %d, want 0", len(fake.links))
	}
	if len(fake.overlays) != 1 || fake.overlays[repositories.ScopeCompany+"||"] == nil {
		t.Errorf("overlays left = %v, want only the company overlay", fake.overlays)
	}
	if strings.Join(fake.deletedResolved, ",") != "seat-a,seat-b" {
		t.Errorf("resolved snapshots deleted for %v, want seat-a,seat-b", fake.deletedResolved)
	}
	if strings.Join(fake.deletedStatusRooms, ",") != "dev" {
		t.Errorf("seat status deleted for rooms %v, want only dev", fake.deletedStatusRooms)
	}
	if strings.Join(fake.deletedEdgeRooms, ",") != "dev" {
		t.Errorf("topology edges deleted for rooms %v, want only dev", fake.deletedEdgeRooms)
	}
	if strings.Join(fake.deletedMessageRooms, ",") != "dev" {
		t.Errorf("seat messages deleted for rooms %v, want only dev", fake.deletedMessageRooms)
	}
	if rec := doTestRequest(t, mux, http.MethodDelete, "/api/v2/openrig/rooms/dev", ""); rec.Code != http.StatusNotFound {
		t.Errorf("delete again: status = %d, want 404", rec.Code)
	}
}

func TestSeatAdminOverlays(t *testing.T) {
	fake := newFakeSeatAdmin()
	fake.seedSeatType("coder", "1.0.0")
	fake.seatTypes["coder"].ModuleRefs = []resolver.ModuleRef{{Slug: "m", Version: "1"}}
	fake.moduleVersions["m@1"] = &repositories.ModuleVersion{Slug: "m", Version: "1"}
	fake.moduleVersions["m@2"] = &repositories.ModuleVersion{Slug: "m", Version: "2"}
	fake.moduleVersions["n@1"] = &repositories.ModuleVersion{Slug: "n", Version: "1"}
	room := fake.seedRoom("dev")
	fake.seats = append(fake.seats, &repositories.Seat{ID: "seat-a", RoomID: room.ID, SeatKey: "alice", SeatTypeID: "st-coder", PermissionPolicy: "standard"})
	mux := seatAdminTestMux(t, fake)
	cases := []struct {
		path string
		body string
		want string
	}{
		{"/api/v2/openrig/rooms/dev/overlay", `{"ops":[{"kind":"add","slug":"n","version":"1"}]}`, `"scope":"room"`},
		{"/api/v2/openrig/overlay", `{"ops":[{"kind":"pin","slug":"m","version":"2"}]}`, `"scope":"company"`},
		{"/api/v2/openrig/rooms/dev/seats/alice/overlay", `{"ops":[{"kind":"override","slug":"m","content":"x"}]}`, `"scope":"seat"`},
	}
	for _, c := range cases {
		rec := doTestRequest(t, mux, http.MethodPut, c.path, c.body)
		if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), c.want) {
			t.Errorf("PUT %s: %d %s", c.path, rec.Code, rec.Body.String())
		}
	}
}

// A room overlay that would make an affected seat unresolvable is refused before the write,
// with the failing op and scope named, and nothing is stored.
func TestSeatAdminOverlayPutRefusesUnresolvableStack(t *testing.T) {
	fake := newFakeSeatAdmin()
	fake.seedSeatType("coder", "1.0.0")
	fake.seatTypes["coder"].ModuleRefs = []resolver.ModuleRef{{Slug: "m", Version: "1"}}
	fake.moduleVersions["m@1"] = &repositories.ModuleVersion{Slug: "m", Version: "1"}
	room := fake.seedRoom("dev")
	fake.seats = append(fake.seats, &repositories.Seat{ID: "seat-a", RoomID: room.ID, SeatKey: "alice", SeatTypeID: "st-coder"})
	mux := seatAdminTestMux(t, fake)

	rec := doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/rooms/dev/overlay", `{"ops":[{"kind":"add","slug":"m","version":"1"}]}`)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want 400: %s", rec.Code, rec.Body.String())
	}
	if detail := seatAdminDetail(t, rec); !strings.Contains(detail, `add "m"`) || !strings.Contains(detail, "module already present") || !strings.Contains(detail, "overlay room") {
		t.Errorf("detail %q does not name the failing op and scope", detail)
	}
	if len(fake.overlays) != 0 {
		t.Errorf("overlay stored despite the broken stack: %+v", fake.overlays)
	}
}

// A legal overlay PUT still succeeds and is stored.
func TestSeatAdminOverlayPutStoresResolvingStack(t *testing.T) {
	fake := newFakeSeatAdmin()
	fake.seedSeatType("coder", "1.0.0")
	fake.seatTypes["coder"].ModuleRefs = []resolver.ModuleRef{{Slug: "m", Version: "1"}}
	fake.moduleVersions["m@1"] = &repositories.ModuleVersion{Slug: "m", Version: "1"}
	fake.moduleVersions["n@1"] = &repositories.ModuleVersion{Slug: "n", Version: "1"}
	room := fake.seedRoom("dev")
	fake.seats = append(fake.seats, &repositories.Seat{ID: "seat-a", RoomID: room.ID, SeatKey: "alice", SeatTypeID: "st-coder"})
	mux := seatAdminTestMux(t, fake)

	rec := doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/overlay", `{"ops":[{"kind":"add","slug":"n","version":"1"}]}`)
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"scope":"company"`) {
		t.Fatalf("legal overlay PUT: %d %s", rec.Code, rec.Body.String())
	}
	if fake.overlays[repositories.ScopeCompany+"||"] == nil {
		t.Errorf("legal overlay not stored: %+v", fake.overlays)
	}
}

func TestSeatAdminOverlayRejectsUnknownModules(t *testing.T) {
	cases := []struct {
		name string
		body string
		code int
	}{
		{"add unknown version", `{"ops":[{"kind":"add","slug":"m","version":"9"}]}`, http.StatusUnprocessableEntity},
		{"pin unknown module", `{"ops":[{"kind":"pin","slug":"ghost","version":"1"}]}`, http.StatusUnprocessableEntity},
		{"add known version", `{"ops":[{"kind":"add","slug":"m","version":"2"}]}`, http.StatusOK},
		{"remove a type-supplied module", `{"ops":[{"kind":"remove","slug":"ghost"}]}`, http.StatusOK},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			fake := newFakeSeatAdmin()
			fake.moduleVersions["m@2"] = &repositories.ModuleVersion{Slug: "m", Version: "2"}
			mux := seatAdminTestMux(t, fake)
			rec := doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/overlay", c.body)
			if rec.Code != c.code {
				t.Fatalf("status = %d, body %s, want %d", rec.Code, rec.Body.String(), c.code)
			}
			if c.code == http.StatusUnprocessableEntity {
				if !strings.Contains(rec.Body.String(), "not found in catalog") {
					t.Errorf("body %s lacks the catalog message", rec.Body.String())
				}
				if len(fake.overlays) != 0 {
					t.Errorf("overlay stored despite the unknown module: %+v", fake.overlays)
				}
			}
		})
	}
}

func TestSeatAdminOverlayValidation(t *testing.T) {
	mux := seatAdminTestMux(t, newFakeSeatAdmin())
	cases := []string{
		`{"ops":[{"kind":"explode","slug":"m"}]}`,
		`{"ops":[{"kind":"add"}]}`,
		`{"ops":[{"kind":"add","slug":"m"}]}`,
		`{"ops":[{"kind":"add","slug":"m","version":"latest"}]}`,
		`{"ops":[{"kind":"override","slug":"m"}]}`,
		`{"ops":[{"kind":"pin","slug":"m","version":"latest"}]}`,
		`{"ops":[{"kind":"add","slug":"m","bogus":true}]}`,
	}
	for _, body := range cases {
		rec := doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/overlay", body)
		if rec.Code != http.StatusBadRequest {
			t.Errorf("body %s: status = %d, want 400", body, rec.Code)
		}
	}
}

func TestSeatAdminLinks(t *testing.T) {
	fake := newFakeSeatAdmin()
	room := fake.seedRoom("dev")
	fake.seats = append(fake.seats,
		&repositories.Seat{ID: "seat-a", RoomID: room.ID, SeatKey: "alice", PermissionPolicy: "standard"},
		&repositories.Seat{ID: "seat-b", RoomID: room.ID, SeatKey: "bob", PermissionPolicy: "standard"},
	)
	mux := seatAdminTestMux(t, fake)
	rec := doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/rooms/dev/seats/alice/links", `{"to_seat":"bob","kind":"delegates_to"}`)
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"allow":true`) {
		t.Fatalf("upsert link: %d %s", rec.Code, rec.Body.String())
	}
	rec = doTestRequest(t, mux, http.MethodGet, "/api/v2/openrig/rooms/dev/seats/alice/links", "")
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"to_seat_id":"seat-b"`) {
		t.Errorf("list links: %d %s", rec.Code, rec.Body.String())
	}
	if rec = doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/rooms/dev/seats/alice/links", `{"to_seat":"alice","kind":"collaborates_with"}`); rec.Code != http.StatusBadRequest {
		t.Errorf("self link: status = %d, want 400", rec.Code)
	}
	if rec = doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/rooms/dev/seats/alice/links", `{"to_seat":"ghost","kind":"collaborates_with"}`); rec.Code != http.StatusNotFound {
		t.Errorf("unknown target: status = %d, want 404", rec.Code)
	}
	if rec = doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/rooms/dev/seats/alice/links", `{"to_seat":"bob","kind":"hates"}`); rec.Code != http.StatusBadRequest {
		t.Errorf("bad link kind: status = %d, want 400", rec.Code)
	}
}

func TestSeatAdminLinkKinds(t *testing.T) {
	fake := newFakeSeatAdmin()
	room := fake.seedRoom("dev")
	fake.seats = append(fake.seats,
		&repositories.Seat{ID: "seat-a", RoomID: room.ID, SeatKey: "alice", PermissionPolicy: "standard"},
		&repositories.Seat{ID: "seat-b", RoomID: room.ID, SeatKey: "bob", PermissionPolicy: "standard"},
		&repositories.Seat{ID: "seat-c", RoomID: room.ID, SeatKey: "carol"},
	)
	mux := seatAdminTestMux(t, fake)
	for _, kind := range []string{"delegates_to", "spawned_by", "can_observe", "collaborates_with", "escalates_to"} {
		target := "bob"
		if kind == "spawned_by" {
			// alice delegates_to bob and alice spawned_by bob would be a launch cycle
			target = "carol"
		}
		body := `{"to_seat":"` + target + `","kind":"` + kind + `"}`
		rec := doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/rooms/dev/seats/alice/links", body)
		if rec.Code != http.StatusOK {
			t.Errorf("kind %q: status = %d, want 200: %s", kind, rec.Code, rec.Body.String())
		}
	}
	for _, kind := range []string{"reports_to", "consults", "notifies", "hates"} {
		body := `{"to_seat":"bob","kind":"` + kind + `"}`
		rec := doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/rooms/dev/seats/alice/links", body)
		if rec.Code != http.StatusBadRequest {
			t.Errorf("kind %q: status = %d, want 400: %s", kind, rec.Code, rec.Body.String())
		}
	}
}

func TestSeatAdminNameValidation(t *testing.T) {
	fake := newFakeSeatAdmin()
	fake.seedRoom("dev")
	fake.seedSeatType("coder", "1.0.0")
	mux := seatAdminTestMux(t, fake)

	for _, body := range []string{
		`{"slug":"bad.slug","name":"Bad"}`,
		`{"slug":"bad slug","name":"Bad"}`,
		`{"slug":"-bad","name":"Bad"}`,
	} {
		rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms", body)
		if rec.Code != http.StatusBadRequest {
			t.Errorf("create room %s: status = %d, want 400: %s", body, rec.Code, rec.Body.String())
		}
	}
	for _, body := range []string{
		`{"seat_key":"bad.key","seat_type":"coder","runtime":"claude-code"}`,
		`{"seat_key":"bad key","seat_type":"coder","runtime":"claude-code"}`,
		`{"seat_key":"-bad","seat_type":"coder","runtime":"claude-code"}`,
	} {
		rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms/dev/seats", body)
		if rec.Code != http.StatusBadRequest {
			t.Errorf("create seat %s: status = %d, want 400: %s", body, rec.Code, rec.Body.String())
		}
	}
}

func TestSeatAdminSetOccupant(t *testing.T) {
	fake := newFakeSeatAdmin()
	room := fake.seedRoom("dev")
	fake.seedSeatType("coder", "1.0.0")
	pinned := "1.0.0"
	fake.seats = append(fake.seats, &repositories.Seat{
		ID: "seat-a", RoomID: room.ID, SeatKey: "alice", SeatTypeID: "st-coder", PinnedVersion: &pinned,
		Runtime: "claude-code", Model: "sonnet",
	})
	mux := seatAdminTestMux(t, fake)
	const path = "/api/v2/openrig/rooms/dev/seats/alice/occupant"

	rec := doTestRequest(t, mux, http.MethodPut, path, `{"runtime":"codex","model":"gpt-5.1:high"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("set occupant: status = %d: %s", rec.Code, rec.Body.String())
	}
	for _, want := range []string{`"success":true`, `"seat_key":"alice"`, `"seat_type":"coder"`, `"pinned_version":"1.0.0"`, `"runtime":"codex"`, `"model":"gpt-5.1:high"`} {
		if !strings.Contains(rec.Body.String(), want) {
			t.Errorf("set occupant body missing %s: %s", want, rec.Body.String())
		}
	}
	if got := fake.seats[0]; got.Runtime != "codex" || got.Model != "gpt-5.1:high" || got.PinnedVersion == nil || *got.PinnedVersion != "1.0.0" {
		t.Errorf("stored seat = %+v", got)
	}

	// A blank model now KEEPS the seat's model (owner ruling, 2026-10-05: a blank field never
	// clears a field), so the runtime still changes and the model stays gpt-5.1:high from the
	// call above. Pinned by TestSeatAdminSetOccupantBlankModelKeepsIt.
	rec = doTestRequest(t, mux, http.MethodPut, path, `{"runtime":"claude-code","model":""}`)
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"model":"gpt-5.1:high"`) {
		t.Errorf("blank model did not keep the model: %d %s", rec.Code, rec.Body.String())
	}
}

func TestSeatAdminSetOccupantRejectsInvalidInput(t *testing.T) {
	fake := newFakeSeatAdmin()
	room := fake.seedRoom("dev")
	fake.seats = append(fake.seats, &repositories.Seat{ID: "seat-a", RoomID: room.ID, SeatKey: "alice", Runtime: "claude-code", PermissionPolicy: "standard"})
	mux := seatAdminTestMux(t, fake)
	const path = "/api/v2/openrig/rooms/dev/seats/alice/occupant"
	// `{"runtime":""}` and `{"model":"sonnet"}` are deliberately NOT rejected any more: a blank or
	// omitted runtime keeps the seat's current runtime (owner ruling, 2026-10-05), so both are
	// accepted and covered by seat_occupant_runtime_test.go.
	for _, body := range []string{
		`{"runtime":"gemini"}`,
		`{"runtime":"codex","model":"-bad"}`,
		`{"runtime":"codex","model":"has space"}`,
		`{"runtime":"codex","model":"claude-sonnet-5-5"}`,
		`{"runtime":"codex","model":"` + strings.Repeat("a", 129) + `"}`,
		`{"runtime":"codex","extra":1}`,
		`not json`,
	} {
		if rec := doTestRequest(t, mux, http.MethodPut, path, body); rec.Code != http.StatusBadRequest {
			t.Errorf("body %q: status = %d, want 400: %s", body, rec.Code, rec.Body.String())
		}
	}
	if fake.seats[0].Runtime != "claude-code" {
		t.Errorf("a rejected request changed the seat: %+v", fake.seats[0])
	}
}

// A runtime the renderer cannot render is a 400 that names the supported ones.
func TestSeatAdminSetOccupantRuntimeNamesSupportedRuntimes(t *testing.T) {
	fake := newFakeSeatAdmin()
	room := fake.seedRoom("dev")
	fake.seats = append(fake.seats, &repositories.Seat{ID: "seat-a", RoomID: room.ID, SeatKey: "alice", Runtime: "claude-code", PermissionPolicy: "standard"})
	mux := seatAdminTestMux(t, fake)

	// omp is supported: it is the runtime that carries a non-Anthropic provider (DeepSeek via
	// "provider/id" model ids), so an occupant switch to it is accepted.
	rec := doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/rooms/dev/seats/alice/occupant", `{"runtime":"omp"}`)
	if rec.Code != http.StatusOK {
		t.Errorf("runtime omp: status = %d, body %s, want 200", rec.Code, rec.Body.String())
	}

	// pi is still not renderable, so it stays a 400 that names every supported runtime.
	rec = doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/rooms/dev/seats/alice/occupant", `{"runtime":"pi"}`)
	if rec.Code != http.StatusBadRequest || !strings.Contains(rec.Body.String(), `claude-code, codex, agy, omp`) {
		t.Errorf("runtime pi: status = %d, body %s, want 400 naming the supported runtimes", rec.Code, rec.Body.String())
	}
}

func TestSeatAdminSetOccupantNotFound(t *testing.T) {
	fake := newFakeSeatAdmin()
	fake.seedRoom("dev")
	fake.seedRoom("dev")
	mux := seatAdminTestMux(t, fake)
	body := `{"runtime":"codex","model":""}`
	for path, want := range map[string]int{
		"/api/v2/openrig/rooms/ghost/seats/bob/occupant": http.StatusNotFound,
		"/api/v2/openrig/rooms/dev/seats/ghost/occupant": http.StatusNotFound,
	} {
		if rec := doTestRequest(t, mux, http.MethodPut, path, body); rec.Code != want {
			t.Errorf("PUT %s: status = %d, want %d: %s", path, rec.Code, want, rec.Body.String())
		}
	}
}

func TestSeatAdminNotFound(t *testing.T) {
	fake := newFakeSeatAdmin()
	fake.seedRoom("dev")
	mux := seatAdminTestMux(t, fake)
	cases := []struct{ method, path, body string }{
		{http.MethodPost, "/api/v2/openrig/rooms/ghost/seats", `{"seat_key":"a","seat_type":"coder","runtime":"claude-code"}`},
		{http.MethodPost, "/api/v2/openrig/rooms/dev/seats", `{"seat_key":"a","seat_type":"ghost","runtime":"claude-code"}`},
		{http.MethodGet, "/api/v2/openrig/rooms/ghost/seats", ""},
		{http.MethodDelete, "/api/v2/openrig/rooms/dev/seats/ghost", ""},
		{http.MethodPut, "/api/v2/openrig/rooms/ghost/overlay", `{"ops":[{"kind":"add","slug":"m","version":"1"}]}`},
		{http.MethodPut, "/api/v2/openrig/rooms/dev/seats/ghost/overlay", `{"ops":[{"kind":"add","slug":"m","version":"1"}]}`},
		{http.MethodGet, "/api/v2/openrig/rooms/ghost/overlay", ""},
		{http.MethodGet, "/api/v2/openrig/rooms/dev/seats/ghost/overlay", ""},
		{http.MethodGet, "/api/v2/openrig/modules/ghost/versions/1.0.0", ""},
		{http.MethodGet, "/api/v2/openrig/rooms/dev/seats/ghost/links", ""},
		{http.MethodDelete, "/api/v2/openrig/rooms/ghost", ""},
	}
	for _, c := range cases {
		rec := doTestRequest(t, mux, c.method, c.path, c.body)
		if rec.Code != http.StatusNotFound {
			t.Errorf("%s %s: status = %d, want 404: %s", c.method, c.path, rec.Code, rec.Body.String())
		}
	}
}

func TestSeatAdminRoutesNeedAuth(t *testing.T) {
	authenticateTestUser(t)
	mux := http.NewServeMux()
	mountSeatAdminRoutes(mux, nil)
	probes := []struct{ method, path string }{
		{http.MethodPost, "/api/v2/openrig/rooms"},
		{http.MethodGet, "/api/v2/openrig/rooms"},
		{http.MethodGet, "/api/v2/openrig/seat-types"},
		{http.MethodGet, "/api/v2/openrig/modules/instr/versions/1.0.0"},
		{http.MethodPut, "/api/v2/openrig/modules/instr/versions/1.0.0"},
		{http.MethodGet, "/api/v2/openrig/modules"},
		{http.MethodPost, "/api/v2/openrig/seat-types/coder/versions"},
		{http.MethodPost, "/api/v2/openrig/rooms/dev/seats"},
		{http.MethodGet, "/api/v2/openrig/rooms/dev/seats"},
		{http.MethodDelete, "/api/v2/openrig/rooms/dev/seats/alice"},
		{http.MethodPut, "/api/v2/openrig/rooms/dev/seats/alice/occupant"},
		{http.MethodPut, "/api/v2/openrig/rooms/dev/seats/alice/permission-policy"},
		{http.MethodGet, "/api/v2/openrig/overlay"},
		{http.MethodPut, "/api/v2/openrig/rooms/dev/overlay"},
		{http.MethodGet, "/api/v2/openrig/rooms/dev/overlay"},
		{http.MethodPut, "/api/v2/openrig/overlay"},
		{http.MethodPut, "/api/v2/openrig/rooms/dev/seats/alice/overlay"},
		{http.MethodGet, "/api/v2/openrig/rooms/dev/seats/alice/overlay"},
		{http.MethodPut, "/api/v2/openrig/rooms/dev/seats/alice/links"},
		{http.MethodGet, "/api/v2/openrig/rooms/dev/seats/alice/links"},
		{http.MethodDelete, "/api/v2/openrig/rooms/dev/seats/alice/links/bob/delegates_to"},
		{http.MethodDelete, "/api/v2/openrig/rooms/dev"},
		{http.MethodGet, "/api/v2/openrig/settings"},
		{http.MethodPut, "/api/v2/openrig/settings"},
	}
	for _, p := range probes {
		rec := httptest.NewRecorder()
		mux.ServeHTTP(rec, httptest.NewRequest(p.method, p.path, nil))
		if rec.Code == http.StatusNotFound || rec.Code == http.StatusOK {
			t.Errorf("%s %s: status = %d, want 401/403", p.method, p.path, rec.Code)
		}
	}
}

func TestSeatAdminLinkRejectsLaunchCycles(t *testing.T) {
	setup := func() (*fakeSeatAdmin, *http.ServeMux) {
		fake := newFakeSeatAdmin()
		room := fake.seedRoom("dev")
		for _, key := range []string{"a", "b", "c"} {
			fake.seats = append(fake.seats, &repositories.Seat{ID: "seat-" + key, RoomID: room.ID, SeatKey: key, Runtime: "claude-code"})
		}
		return fake, seatAdminTestMux(t, fake)
	}
	put := func(mux *http.ServeMux, from, to, kind, extra string) *httptest.ResponseRecorder {
		return doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/rooms/dev/seats/"+from+"/links",
			`{"to_seat":"`+to+`","kind":"`+kind+`"`+extra+`}`)
	}

	t.Run("opposite delegates_to", func(t *testing.T) {
		fake, mux := setup()
		if rec := put(mux, "a", "b", "delegates_to", ""); rec.Code != http.StatusOK {
			t.Fatalf("first link: %d %s", rec.Code, rec.Body.String())
		}
		rec := put(mux, "b", "a", "delegates_to", "")
		if rec.Code != http.StatusBadRequest || !strings.Contains(seatAdminDetail(t, rec), "launch cycle: a -> b -> a") {
			t.Fatalf("opposite link: %d %s, want 400 naming the cycle", rec.Code, rec.Body.String())
		}
		if len(fake.links) != 1 {
			t.Fatalf("the rejected link was stored: %d links", len(fake.links))
		}
	})
	t.Run("three seats", func(t *testing.T) {
		_, mux := setup()
		put(mux, "a", "b", "delegates_to", "")
		put(mux, "b", "c", "delegates_to", "")
		rec := put(mux, "c", "a", "delegates_to", "")
		if rec.Code != http.StatusBadRequest || !strings.Contains(seatAdminDetail(t, rec), "a -> b -> c -> a") {
			t.Fatalf("3-seat cycle: %d %s", rec.Code, rec.Body.String())
		}
	})
	t.Run("spawned_by closes a delegates_to cycle", func(t *testing.T) {
		_, mux := setup()
		put(mux, "a", "b", "delegates_to", "")
		// b spawned_by a means a launches first: same direction as a delegates_to b, no cycle
		if rec := put(mux, "b", "a", "spawned_by", ""); rec.Code != http.StatusOK {
			t.Fatalf("agreeing spawned_by: %d %s", rec.Code, rec.Body.String())
		}
		if rec := put(mux, "a", "b", "spawned_by", ""); rec.Code != http.StatusBadRequest {
			t.Fatalf("spawned_by against delegates_to: %d %s, want 400", rec.Code, rec.Body.String())
		}
	})
	t.Run("descriptive kinds and disallowed links never cycle", func(t *testing.T) {
		_, mux := setup()
		put(mux, "a", "b", "delegates_to", "")
		for _, kind := range []string{"collaborates_with", "escalates_to", "can_observe"} {
			if rec := put(mux, "b", "a", kind, ""); rec.Code != http.StatusOK {
				t.Errorf("%s back-link: %d %s, want 200", kind, rec.Code, rec.Body.String())
			}
		}
		if rec := put(mux, "b", "a", "delegates_to", `,"allow":false`); rec.Code != http.StatusOK {
			t.Errorf("disallowed opposite link: %d %s, want 200 (it is not rendered)", rec.Code, rec.Body.String())
		}
	})
	t.Run("re-putting an existing link is not a cycle", func(t *testing.T) {
		_, mux := setup()
		put(mux, "a", "b", "delegates_to", "")
		if rec := put(mux, "a", "b", "delegates_to", ""); rec.Code != http.StatusOK {
			t.Fatalf("same link again: %d %s", rec.Code, rec.Body.String())
		}
	})
	t.Run("deleting a seat removes its links from the cycle check", func(t *testing.T) {
		_, mux := setup()
		put(mux, "a", "b", "delegates_to", "")
		put(mux, "b", "c", "delegates_to", "")
		if rec := put(mux, "c", "a", "delegates_to", ""); rec.Code != http.StatusBadRequest {
			t.Fatalf("c -> a while a -> b -> c exists: %d %s, want 400", rec.Code, rec.Body.String())
		}
		if rec := doTestRequest(t, mux, http.MethodDelete, "/api/v2/openrig/rooms/dev/seats/b", ""); rec.Code != http.StatusOK {
			t.Fatalf("delete seat b: %d %s", rec.Code, rec.Body.String())
		}
		if rec := put(mux, "c", "a", "delegates_to", ""); rec.Code != http.StatusOK {
			t.Fatalf("c -> a after b is deleted: %d %s, want 200", rec.Code, rec.Body.String())
		}
	})
}

// seatAdminDetail returns the decoded "detail" of an error response (JSON escapes ">").
func seatAdminDetail(t *testing.T, rec *httptest.ResponseRecorder) string {
	t.Helper()
	var body struct {
		Detail string `json:"detail"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil {
		t.Fatalf("decode %s: %v", rec.Body.String(), err)
	}
	return body.Detail
}

func TestSeatAdminOverlayRoutesRejectSecretContent(t *testing.T) {
	const secret = "AKIAABCDEFGHIJKLMNOP"
	bodies := []string{
		`{"ops":[{"kind":"override","slug":"m","content":"key ` + secret + `"}]}`,
		`{"ops":[{"kind":"add","slug":"` + secret + `","version":"1"}]}`,
		`{"ops":[{"kind":"pin","slug":"m","version":"` + secret + `"}]}`,
	}
	for _, path := range []string{
		"/api/v2/openrig/overlay",
		"/api/v2/openrig/rooms/dev/overlay",
		"/api/v2/openrig/rooms/dev/seats/alice/overlay",
	} {
		t.Run(path, func(t *testing.T) {
			fake := newFakeSeatAdmin()
			fake.seedSeatType("coder", "1.0.0")
			fake.seatTypes["coder"].ModuleRefs = []resolver.ModuleRef{{Slug: "m", Version: "1"}}
			fake.moduleVersions["m@1"] = &repositories.ModuleVersion{Slug: "m", Version: "1"}
			room := fake.seedRoom("dev")
			fake.seats = append(fake.seats, &repositories.Seat{ID: "seat-a", RoomID: room.ID, SeatKey: "alice", SeatTypeID: "st-coder", PermissionPolicy: "standard"})
			mux := seatAdminTestMux(t, fake)
			for _, body := range bodies {
				rec := doTestRequest(t, mux, http.MethodPut, path, body)
				if rec.Code != http.StatusUnprocessableEntity || !strings.Contains(rec.Body.String(), "secret detected in content") {
					t.Fatalf("%s: status = %d, body %s, want 422 secret detected", body, rec.Code, rec.Body.String())
				}
				if strings.Contains(rec.Body.String(), secret) {
					t.Errorf("response echoes the secret: %s", rec.Body.String())
				}
			}
			if len(fake.overlays) != 0 {
				t.Errorf("overlay stored despite the secret: %+v", fake.overlays)
			}
			clean := `{"ops":[{"kind":"override","slug":"m","content":"no secret here"}]}`
			if rec := doTestRequest(t, mux, http.MethodPut, path, clean); rec.Code != http.StatusOK {
				t.Errorf("clean overlay: status = %d: %s", rec.Code, rec.Body.String())
			}
		})
	}
}

func TestSeatAdminSetPermissionPolicy(t *testing.T) {
	fake := newFakeSeatAdmin()
	room := fake.seedRoom("dev")
	fake.seats = append(fake.seats, &repositories.Seat{ID: "seat-a", RoomID: room.ID, SeatKey: "alice", Runtime: "claude-code", PermissionPolicy: "standard"})
	mux := seatAdminTestMux(t, fake)
	const path = "/api/v2/openrig/rooms/dev/seats/alice/permission-policy"

	rec := doTestRequest(t, mux, http.MethodPut, path, `{"permission_policy":"yolo"}`)
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"permission_policy":"yolo"`) || fake.seats[0].PermissionPolicy != "yolo" {
		t.Fatalf("set policy: %d %s; stored %q", rec.Code, rec.Body.String(), fake.seats[0].PermissionPolicy)
	}
	for _, body := range []string{`{"permission_policy":"strict"}`, `{"permission_policy":""}`, `{}`, `{"permission_policy":"open","extra":1}`, `not json`} {
		if rec := doTestRequest(t, mux, http.MethodPut, path, body); rec.Code != http.StatusBadRequest {
			t.Errorf("body %q: status = %d, want 400: %s", body, rec.Code, rec.Body.String())
		}
	}
	if fake.seats[0].PermissionPolicy != "yolo" {
		t.Errorf("a rejected request changed the seat: %+v", fake.seats[0])
	}
	for _, p := range []string{"/api/v2/openrig/rooms/ghost/seats/alice/permission-policy", "/api/v2/openrig/rooms/dev/seats/ghost/permission-policy"} {
		if rec := doTestRequest(t, mux, http.MethodPut, p, `{"permission_policy":"open"}`); rec.Code != http.StatusNotFound {
			t.Errorf("PUT %s: status = %d, want 404", p, rec.Code)
		}
	}
}

// A new seat is conservative unless the caller picks a policy: omitted means standard, never yolo.
func TestSeatAdminCreateSeatPermissionPolicy(t *testing.T) {
	fake := newFakeSeatAdmin()
	fake.seedRoom("dev")
	fake.seedSeatType("coder", "1.0.0")
	mux := seatAdminTestMux(t, fake)
	const path = "/api/v2/openrig/rooms/dev/seats"

	rec := doTestRequest(t, mux, http.MethodPost, path, `{"seat_key":"alice","seat_type":"coder","runtime":"claude-code"}`)
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"permission_policy":"standard"`) {
		t.Fatalf("default policy: %d %s", rec.Code, rec.Body.String())
	}
	rec = doTestRequest(t, mux, http.MethodPost, path, `{"seat_key":"bob","seat_type":"coder","runtime":"codex","permission_policy":"locked"}`)
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"permission_policy":"locked"`) {
		t.Fatalf("explicit policy: %d %s", rec.Code, rec.Body.String())
	}
	rec = doTestRequest(t, mux, http.MethodPost, path, `{"seat_key":"carol","seat_type":"coder","runtime":"codex","permission_policy":"strict"}`)
	if rec.Code != http.StatusBadRequest || !strings.Contains(rec.Body.String(), "permission policy") {
		t.Errorf("invalid policy: %d %s", rec.Code, rec.Body.String())
	}
	if len(fake.seats) != 2 {
		t.Errorf("a rejected create stored a seat: %d seats", len(fake.seats))
	}
}

// The policy chosen through the PUT route is what the rigspec renders for that member, and
// another user's request neither changes nor reveals the seat.
func TestSeatAdminPermissionPolicyIsRenderedAndTenantScoped(t *testing.T) {
	t.Setenv(publicURLEnv, "https://api.example.test")
	fake := newFakeSeatAdmin()
	room := fake.seedRoom("dev")
	fake.seats = append(fake.seats, &repositories.Seat{ID: "seat-a", RoomID: room.ID, SeatKey: "alice", Runtime: "claude-code", PermissionPolicy: "standard"})
	mux := seatAdminTestMux(t, fake)
	rigMux := seatRigSpecTestMux(t, rigSpecOverAdminFake{fake})
	const path = "/api/v2/openrig/rooms/dev/seats/alice/permission-policy"
	render := func() string {
		t.Helper()
		rec := doTestRequest(t, rigMux, http.MethodGet, "/api/v2/openrig/rooms/dev/rigspec", "")
		if rec.Code != http.StatusOK {
			t.Fatalf("rigspec: %d %s", rec.Code, rec.Body.String())
		}
		return decodeRigSpec(t, rec).RigSpec.YAML
	}
	if yaml := render(); !strings.Contains(yaml, "permission_policy: builtin:standard") || strings.Contains(yaml, "builtin:yolo") {
		t.Fatalf("before the change the member renders standard: %s", yaml)
	}

	room.UserID = "another-user"
	if rec := doTestRequest(t, mux, http.MethodPut, path, `{"permission_policy":"yolo"}`); rec.Code != http.StatusNotFound {
		t.Fatalf("other user's seat: status = %d, want 404: %s", rec.Code, rec.Body.String())
	}
	if fake.seats[0].PermissionPolicy != "standard" {
		t.Fatalf("another user's request changed the seat: %+v", fake.seats[0])
	}
	room.UserID = ""

	if rec := doTestRequest(t, mux, http.MethodPut, path, `{"permission_policy":"strict"}`); rec.Code != http.StatusBadRequest {
		t.Fatalf("invalid value: status = %d, want 400", rec.Code)
	}
	if yaml := render(); strings.Contains(yaml, "builtin:strict") || !strings.Contains(yaml, "builtin:standard") {
		t.Errorf("a rejected value reached the render: %s", yaml)
	}
	if rec := doTestRequest(t, mux, http.MethodPut, path, `{"permission_policy":"yolo"}`); rec.Code != http.StatusOK {
		t.Fatalf("valid value: %d %s", rec.Code, rec.Body.String())
	}
	if yaml := render(); !strings.Contains(yaml, "permission_policy: builtin:yolo") || strings.Contains(yaml, "builtin:standard") {
		t.Errorf("after the change the member renders yolo: %s", yaml)
	}
}

// Creating a seat validates the occupant like switching it: a Claude model never lands on codex and
// a model id with spaces or shell characters is rejected before anything is stored.
func TestSeatAdminCreateSeatValidatesOccupant(t *testing.T) {
	fake := newFakeSeatAdmin()
	fake.seedRoom("dev")
	fake.seedSeatType("coder", "1.0.0")
	mux := seatAdminTestMux(t, fake)
	const path = "/api/v2/openrig/rooms/dev/seats"
	for _, body := range []string{
		`{"seat_key":"a","seat_type":"coder","runtime":"codex","model":"claude-sonnet-5-5"}`,
		`{"seat_key":"b","seat_type":"coder","runtime":"codex","model":"a b; rm -rf"}`,
		`{"seat_key":"c","seat_type":"coder","runtime":"claude-code","model":"-bad"}`,
	} {
		if rec := doTestRequest(t, mux, http.MethodPost, path, body); rec.Code != http.StatusBadRequest {
			t.Errorf("%s: status = %d, want 400: %s", body, rec.Code, rec.Body.String())
		}
	}
	if len(fake.seats) != 0 {
		t.Fatalf("a rejected request stored seats: %+v", fake.seats)
	}
	for _, body := range []string{
		`{"seat_key":"d","seat_type":"coder","runtime":"codex","model":"gpt-5.1"}`,
		`{"seat_key":"e","seat_type":"coder","runtime":"claude-code","model":"claude-sonnet-5-5"}`,
		`{"seat_key":"f","seat_type":"coder","runtime":"claude-code"}`,
	} {
		if rec := doTestRequest(t, mux, http.MethodPost, path, body); rec.Code != http.StatusOK {
			t.Errorf("%s: status = %d, want 200: %s", body, rec.Code, rec.Body.String())
		}
	}
}

func TestSeatAdminCreateSeatType(t *testing.T) {
	fake := newFakeSeatAdmin()
	mux := seatAdminTestMux(t, fake)

	rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/seat-types",
		`{"slug":"custom-coder","name":"Custom Coder","description":"A user seat type"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("create: %d %s", rec.Code, rec.Body.String())
	}
	want := `{"success":true,"seat_type":{"slug":"custom-coder","name":"Custom Coder","description":"A user seat type"}}`
	if strings.TrimSpace(rec.Body.String()) != want {
		t.Errorf("create body = %s, want %s", rec.Body.String(), want)
	}
	// The created type is listed, with no version yet (the version route adds the first one).
	rec = doTestRequest(t, mux, http.MethodGet, "/api/v2/openrig/seat-types", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("list: %d %s", rec.Code, rec.Body.String())
	}
	if !strings.Contains(rec.Body.String(), `"slug":"custom-coder","name":"Custom Coder","description":"A user seat type","default_runtime":null,"latest_version":null,"module_refs":[]`) {
		t.Errorf("listing does not show the created, versionless type: %s", rec.Body.String())
	}

	// A duplicate slug is a conflict: the store's Save is a get-or-create, so the service
	// refuses the duplicate rather than silently return the existing type with a 200.
	rec = doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/seat-types", `{"slug":"custom-coder","name":"Again"}`)
	if rec.Code != http.StatusConflict || !strings.Contains(rec.Body.String(), "already exists") {
		t.Fatalf("duplicate: %d %s, want 409", rec.Code, rec.Body.String())
	}
	if len(fake.seatTypeList) != 1 || fake.seatTypeList[0].Name != "Custom Coder" {
		t.Errorf("a rejected duplicate changed the stored type: %+v", fake.seatTypeList)
	}
}

func TestSeatAdminCreateSeatTypeRejectsInput(t *testing.T) {
	mux := seatAdminTestMux(t, newFakeSeatAdmin())
	cases := []struct {
		name, body string
		status     int
	}{
		{"uppercase slug", `{"slug":"Custom","name":"N"}`, http.StatusBadRequest},
		{"underscore slug", `{"slug":"custom_coder","name":"N"}`, http.StatusBadRequest},
		{"empty slug", `{"slug":"","name":"N"}`, http.StatusBadRequest},
		{"leading hyphen", `{"slug":"-custom","name":"N"}`, http.StatusBadRequest},
		{"dot slug", `{"slug":"custom.coder","name":"N"}`, http.StatusBadRequest},
		{"empty name", `{"slug":"custom","name":""}`, http.StatusBadRequest},
		{"blank name", `{"slug":"custom","name":"   "}`, http.StatusBadRequest},
		{"missing name", `{"slug":"custom"}`, http.StatusBadRequest},
		{"unknown field", `{"slug":"custom","name":"N","x":1}`, http.StatusBadRequest},
	}
	for _, c := range cases {
		rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/seat-types", c.body)
		if rec.Code != c.status {
			t.Errorf("%s: status = %d, want %d: %s", c.name, rec.Code, c.status, rec.Body.String())
		}
	}
}

// The version route gates on the seat type existing (it lists the types before writing), so a
// type created through the new route no longer 404s; its first version is 1.0.0 and it lists as
// the latest version.
func TestSeatAdminCreatedSeatTypeVersionRouteAcceptsTheSlug(t *testing.T) {
	fake := newFakeSeatAdmin()
	mux := seatAdminTestMux(t, fake)
	if rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/seat-types", `{"slug":"custom-coder","name":"Custom Coder"}`); rec.Code != http.StatusOK {
		t.Fatalf("create type: %d %s", rec.Code, rec.Body.String())
	}
	if rec := doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/modules/custom-role/versions/1.0.0", `{"kind":"instruction","content":"c"}`); rec.Code != http.StatusOK {
		t.Fatalf("put module: %d %s", rec.Code, rec.Body.String())
	}
	rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/seat-types/custom-coder/versions",
		`{"module_refs":["custom-role@1.0.0"],"default_runtime":"claude-code"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("first version of a created type: %d %s", rec.Code, rec.Body.String())
	}
	for _, want := range []string{`"slug":"custom-coder"`, `"version":"1.0.0"`, `"default_runtime":"claude-code"`, `"module_refs":[{"slug":"custom-role","version":"1.0.0"}]`} {
		if !strings.Contains(rec.Body.String(), want) {
			t.Errorf("version body missing %s: %s", want, rec.Body.String())
		}
	}
	rec = doTestRequest(t, mux, http.MethodGet, "/api/v2/openrig/seat-types", "")
	if !strings.Contains(rec.Body.String(), `"slug":"custom-coder","name":"Custom Coder","description":"","default_runtime":"claude-code","latest_version":"1.0.0"`) {
		t.Errorf("listing does not show the created type's first version: %s", rec.Body.String())
	}
}

// KEY ACCEPTANCE: a seat type a user creates through the new route renders exactly like a
// seeded one. The type is created, its role is authored as an instruction module, the version
// is added through the existing version route, a seat is created and resolved through the real
// resolver and renderer; the rendered guidance/role.md must carry the authored role text.
func TestSeatAdminCreatedSeatTypeResolvesAndRenders(t *testing.T) {
	t.Setenv(publicURLEnv, "https://api.example.test")
	const roleText = "You are the custom coder: keep the acceptance test honest."
	fake := newFakeSeatAdmin()
	fake.seedRoom("dev")
	mux := seatAdminTestMux(t, fake)
	mountSeatRoutes(mux, nil)
	previousSource := newSeatSource
	newSeatSource = func(*database.SessionManager, string) (seatSource, error) {
		return createdTypeSeatSource{resolution: createdSeatTypeResolution(fake)}, nil
	}
	t.Cleanup(func() { newSeatSource = previousSource })

	if rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/seat-types", `{"slug":"custom-coder","name":"Custom Coder","description":"Made by a user"}`); rec.Code != http.StatusOK {
		t.Fatalf("create type: %d %s", rec.Code, rec.Body.String())
	}
	if rec := doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/modules/custom-role/versions/1.0.0", `{"kind":"instruction","content":"`+roleText+`"}`); rec.Code != http.StatusOK {
		t.Fatalf("author role module: %d %s", rec.Code, rec.Body.String())
	}
	if rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/seat-types/custom-coder/versions", `{"module_refs":["custom-role@1.0.0"],"default_runtime":"claude-code"}`); rec.Code != http.StatusOK {
		t.Fatalf("add version: %d %s", rec.Code, rec.Body.String())
	}
	if rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms/dev/seats", `{"seat_key":"alice","seat_type":"custom-coder","runtime":"claude-code"}`); rec.Code != http.StatusOK {
		t.Fatalf("create seat on the created type: %d %s", rec.Code, rec.Body.String())
	}

	rec := doTestRequest(t, mux, http.MethodGet, "/api/v2/openrig/seats/dev/alice", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("resolve seat: %d %s", rec.Code, rec.Body.String())
	}
	var wire struct {
		ResolvedSeat struct {
			Runtime string `json:"runtime"`
			Files   []struct {
				Path    string `json:"path"`
				Content string `json:"content"`
			} `json:"files"`
		} `json:"resolved_seat"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &wire); err != nil {
		t.Fatalf("decode resolve: %v: %s", err, rec.Body.String())
	}
	if wire.ResolvedSeat.Runtime != "claude-code" {
		t.Errorf("resolved runtime = %q", wire.ResolvedSeat.Runtime)
	}
	var guidance string
	for _, f := range wire.ResolvedSeat.Files {
		if f.Path == "guidance/role.md" {
			guidance = f.Content
		}
	}
	if guidance == "" {
		t.Fatalf("render has no guidance/role.md: %s", rec.Body.String())
	}
	if !strings.Contains(guidance, roleText) {
		t.Errorf("rendered guidance/role.md does not carry the created role text:\n%s", guidance)
	}
	if !strings.Contains(guidance, "## custom-role") {
		t.Errorf("the created instruction module is not under its own heading:\n%s", guidance)
	}
}

// createdTypeSeatSource is the seatSource the resolve route uses: the real resolution service
// over the admin fake, so only persistence is in-memory.
type createdTypeSeatSource struct {
	resolution *seatservices.SeatResolutionService
}

func (s createdTypeSeatSource) ResolveSeat(ctx context.Context, userID, roomSlug, seatKey string) (*repositories.ResolvedSeat, error) {
	return s.resolution.ResolveSeat(ctx, userID, roomSlug, seatKey)
}

func (createdTypeSeatSource) SeedSeatTypes(context.Context, string) (int, error) { return 0, nil }

// createdSeatTypeResolution builds the real SeatResolutionService (resolver + renderer) over
// the admin fake, so the KEY test renders through the production path with a fake store.
func createdSeatTypeResolution(fake *fakeSeatAdmin) *seatservices.SeatResolutionService {
	return &seatservices.SeatResolutionService{
		SeatTypes:  createdTypeSeatTypes{fake: fake},
		Rooms:      createdTypeRooms{fake: fake},
		Seats:      createdTypeSeats{fake: fake},
		Overlays:   createdTypeOverlays{fake: fake},
		Links:      createdTypeLinks{fake: fake},
		Resolved:   createdTypeSnapshots{},
		NewCatalog: func(string) seatservices.CheckedCatalog { return fakeResolutionCatalog{fake: fake} },
		MCPURL:     "https://api.example.test/mcp",
	}
}

type createdTypeRooms struct {
	repositories.RoomRepository
	fake *fakeSeatAdmin
}

func (r createdTypeRooms) GetBySlug(ctx context.Context, userID, slug string) (*repositories.Room, error) {
	return r.fake.GetRoomBySlug(ctx, userID, slug)
}

type createdTypeSeatTypes struct {
	repositories.SeatTypeRepository
	fake *fakeSeatAdmin
}

func (t createdTypeSeatTypes) GetByID(_ context.Context, _, seatTypeID string) (*repositories.SeatType, error) {
	for _, st := range t.fake.seatTypeList {
		if st.ID == seatTypeID {
			copied := *st
			return &copied, nil
		}
	}
	return nil, nil
}

func (t createdTypeSeatTypes) GetVersion(ctx context.Context, userID, slug, version string) (*repositories.SeatTypeVersion, error) {
	return t.fake.GetSeatTypeVersion(ctx, userID, slug, version)
}

func (t createdTypeSeatTypes) LatestVersion(ctx context.Context, userID, slug string) (*repositories.SeatTypeVersion, error) {
	return t.fake.LatestSeatTypeVersion(ctx, userID, slug)
}

type createdTypeSeats struct {
	repositories.SeatRepository
	fake *fakeSeatAdmin
}

func (s createdTypeSeats) FindByRoomAndKey(ctx context.Context, userID, roomID, seatKey string) (*repositories.Seat, error) {
	return s.fake.FindSeat(ctx, userID, roomID, seatKey)
}

type createdTypeOverlays struct {
	repositories.OverlayRepository
	fake *fakeSeatAdmin
}

func (o createdTypeOverlays) Find(ctx context.Context, userID, scope, roomID, seatID string) (*repositories.Overlay, error) {
	return o.fake.FindOverlay(ctx, userID, scope, roomID, seatID)
}

type createdTypeLinks struct {
	repositories.SeatLinkRepository
	fake *fakeSeatAdmin
}

func (l createdTypeLinks) ListFrom(ctx context.Context, userID, seatID string) ([]repositories.SeatLink, error) {
	return l.fake.ListSeatLinks(ctx, userID, seatID)
}

type createdTypeSnapshots struct {
	repositories.ResolvedSeatRepository
}

func (createdTypeSnapshots) Save(_ context.Context, _ string, seat repositories.ResolvedSeat) (*repositories.ResolvedSeat, error) {
	return &seat, nil
}
