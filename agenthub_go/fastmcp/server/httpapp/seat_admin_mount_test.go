package httpapp

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

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
	f.seatTypes[slug] = &repositories.SeatTypeVersion{ID: "stv-" + slug, SeatTypeID: "st-" + slug, Slug: slug, Version: latest}
	f.seatVersions[slug] = map[string]*repositories.SeatTypeVersion{
		latest: {ID: "stv-" + slug + "-" + latest, SeatTypeID: "st-" + slug, Slug: slug, Version: latest},
	}
	for _, v := range versions {
		f.seatVersions[slug][v] = &repositories.SeatTypeVersion{ID: "stv-" + slug + "-" + v, SeatTypeID: "st-" + slug, Slug: slug, Version: v}
	}
	f.seatTypeList = append(f.seatTypeList, &repositories.SeatType{
		ID: "st-" + slug, Slug: slug, Name: slug, Description: "desc-" + slug, DefaultRuntime: "claude-code",
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

func (f *fakeSeatAdmin) GetRoomBySlug(_ context.Context, _, slug string) (*repositories.Room, error) {
	for _, r := range f.rooms {
		if r.Slug == slug {
			return r, nil
		}
	}
	return nil, nil
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

func (f *fakeSeatAdmin) GetSeatTypeVersion(_ context.Context, _, slug, version string) (*repositories.SeatTypeVersion, error) {
	return f.seatVersions[slug][version], nil
}

func (f *fakeSeatAdmin) GetModuleVersion(_ context.Context, _, slug, version string) (*repositories.ModuleVersion, error) {
	return f.moduleVersions[slug+"@"+version], nil
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
	if created.Status == "" {
		created.Status = "active"
	}
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

func (f *fakeSeatAdmin) MarkSeatRemoved(_ context.Context, _, seatID string) error {
	for _, s := range f.seats {
		if s.ID == seatID {
			s.Status = "removed"
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

func seatAdminTestMux(t *testing.T, source seatAdminSource) *http.ServeMux {
	t.Helper()
	previous := newSeatAdminSource
	newSeatAdminSource = func(*database.SessionManager) (seatAdminSource, error) { return source, nil }
	t.Cleanup(func() { newSeatAdminSource = previous })
	authenticateAgentsTestUser(t)
	mux := http.NewServeMux()
	mountSeatAdminRoutes(mux, nil)
	return mux
}

func TestSeatAdminRooms(t *testing.T) {
	mux := seatAdminTestMux(t, newFakeSeatAdmin())
	rec := doAgentsRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms", `{"slug":"dev","name":"Development"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("create room: status = %d: %s", rec.Code, rec.Body.String())
	}
	for _, want := range []string{`"slug":"dev"`, `"name":"Development"`, `"room":{"id":"room-dev"`} {
		if !strings.Contains(rec.Body.String(), want) {
			t.Errorf("create room body missing %s: %s", want, rec.Body.String())
		}
	}
	rec = doAgentsRequest(t, mux, http.MethodGet, "/api/v2/openrig/rooms", "")
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"name":"Development"`) {
		t.Errorf("list rooms: %d %s", rec.Code, rec.Body.String())
	}
}

func TestSeatAdminCreateSeatPinsByDefault(t *testing.T) {
	fake := newFakeSeatAdmin()
	fake.seedRoom("dev")
	fake.seedSeatType("coder", "1.0.0")
	mux := seatAdminTestMux(t, fake)
	rec := doAgentsRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms/dev/seats",
		`{"seat_key":"alice","seat_type":"coder","runtime":"claude-code","model":"sonnet"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("create seat: status = %d: %s", rec.Code, rec.Body.String())
	}
	for _, want := range []string{`"seat_key":"alice"`, `"seat_type_id":"st-coder"`, `"seat_type":"coder"`, `"pinned_version":"1.0.0"`, `"status":"active"`} {
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
	rec := doAgentsRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms/dev/seats",
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
	rec := doAgentsRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms/dev/seats",
		`{"seat_key":"alice","seat_type":"coder","pinned_version":"0.9.0","runtime":"claude-code","model":"sonnet"}`)
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"pinned_version":"0.9.0"`) {
		t.Errorf("explicit pin: %d %s", rec.Code, rec.Body.String())
	}
	rec = doAgentsRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms/dev/seats",
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
		ID: "st-empty", Slug: "empty", Name: "Empty", Description: "desc-empty", DefaultRuntime: "codex",
	})
	mux := seatAdminTestMux(t, fake)
	rec := doAgentsRequest(t, mux, http.MethodGet, "/api/v2/openrig/seat-types", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("list seat types: status = %d: %s", rec.Code, rec.Body.String())
	}
	for _, want := range []string{
		`"slug":"coder"`, `"name":"coder"`, `"description":"desc-coder"`,
		`"default_runtime":"claude-code"`, `"latest_version":"1.0.0"`,
		`"module_refs":[{"slug":"instr","version":"1.0.0"}]`,
		`"slug":"empty"`, `"latest_version":null`, `"module_refs":[]`,
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
	sum := sha256.Sum256([]byte("hello"))
	sha := hex.EncodeToString(sum[:])

	rec := doAgentsRequest(t, mux, http.MethodPut, path, `{"kind":"skill","content":"hello"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("create: status = %d: %s", rec.Code, rec.Body.String())
	}
	want := `{"success":true,"module":{"slug":"my-skill","kind":"skill","version":"1.0.0","sha256":"` + sha + `"}}`
	if strings.TrimSpace(rec.Body.String()) != want {
		t.Errorf("create body = %s, want %s", rec.Body.String(), want)
	}
	if rec = doAgentsRequest(t, mux, http.MethodPut, path, `{"kind":"skill","content":"hello"}`); rec.Code != http.StatusOK {
		t.Errorf("idempotent repeat: status = %d: %s", rec.Code, rec.Body.String())
	}

	rec = doAgentsRequest(t, mux, http.MethodPut, path, `{"kind":"skill","content":"changed"}`)
	if rec.Code != http.StatusConflict || !strings.Contains(rec.Body.String(), "version 1.0.0 of module my-skill already exists with different content") {
		t.Errorf("content conflict: %d %s", rec.Code, rec.Body.String())
	}
	if rec = doAgentsRequest(t, mux, http.MethodPut, path, `{"kind":"document","content":"hello"}`); rec.Code != http.StatusConflict {
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
		rec := doAgentsRequest(t, mux, http.MethodPut, c.path, c.body)
		if rec.Code != c.status {
			t.Errorf("%s: status = %d, want %d: %s", c.name, rec.Code, c.status, rec.Body.String())
		}
		if c.name == "secret" && (!strings.Contains(rec.Body.String(), "secret detected in content") || strings.Contains(rec.Body.String(), "AKIA")) {
			t.Errorf("secret body = %s", rec.Body.String())
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
	rec := doAgentsRequest(t, mux, http.MethodGet, "/api/v2/openrig/modules/instr/versions/1.0.0", "")
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
	if rec = doAgentsRequest(t, mux, http.MethodGet, "/api/v2/openrig/modules/instr/versions/9.9.9", ""); rec.Code != http.StatusNotFound {
		t.Errorf("missing module version: status = %d, want 404", rec.Code)
	}
}

func TestSeatAdminGetOverlays(t *testing.T) {
	fake := newFakeSeatAdmin()
	room := fake.seedRoom("dev")
	fake.seats = append(fake.seats, &repositories.Seat{ID: "seat-a", RoomID: room.ID, SeatKey: "alice", Status: "active"})
	mux := seatAdminTestMux(t, fake)

	for _, path := range []string{
		"/api/v2/openrig/overlay",
		"/api/v2/openrig/rooms/dev/overlay",
		"/api/v2/openrig/rooms/dev/seats/alice/overlay",
	} {
		rec := doAgentsRequest(t, mux, http.MethodGet, path, "")
		if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"ops":[]`) {
			t.Errorf("empty GET %s: %d %s", path, rec.Code, rec.Body.String())
		}
	}

	if rec := doAgentsRequest(t, mux, http.MethodPut, "/api/v2/openrig/overlay",
		`{"ops":[{"kind":"add","slug":"instr"}]}`); rec.Code != http.StatusOK {
		t.Fatalf("PUT company overlay: %d %s", rec.Code, rec.Body.String())
	}
	rec := doAgentsRequest(t, mux, http.MethodGet, "/api/v2/openrig/overlay", "")
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"scope":"company"`) || !strings.Contains(rec.Body.String(), `"slug":"instr"`) {
		t.Errorf("GET company overlay: %d %s", rec.Code, rec.Body.String())
	}

	if rec = doAgentsRequest(t, mux, http.MethodGet, "/api/v2/openrig/rooms/ghost/overlay", ""); rec.Code != http.StatusNotFound {
		t.Errorf("GET absent room overlay: status = %d, want 404", rec.Code)
	}
	if rec = doAgentsRequest(t, mux, http.MethodGet, "/api/v2/openrig/rooms/dev/seats/ghost/overlay", ""); rec.Code != http.StatusNotFound {
		t.Errorf("GET absent seat overlay: status = %d, want 404", rec.Code)
	}
}

func TestSeatAdminSettings(t *testing.T) {
	fake := newFakeSeatAdmin()
	mux := seatAdminTestMux(t, fake)

	rec := doAgentsRequest(t, mux, http.MethodGet, "/api/v2/openrig/settings", "")
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"settings":{"follow_latest":false}`) {
		t.Fatalf("default settings: %d %s", rec.Code, rec.Body.String())
	}
	rec = doAgentsRequest(t, mux, http.MethodPut, "/api/v2/openrig/settings", `{"follow_latest":true}`)
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"settings":{"follow_latest":true}`) {
		t.Fatalf("set settings: %d %s", rec.Code, rec.Body.String())
	}
	rec = doAgentsRequest(t, mux, http.MethodGet, "/api/v2/openrig/settings", "")
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"settings":{"follow_latest":true}`) {
		t.Fatalf("get settings after set: %d %s", rec.Code, rec.Body.String())
	}
	if rec = doAgentsRequest(t, mux, http.MethodPut, "/api/v2/openrig/settings", `{}`); rec.Code != http.StatusBadRequest {
		t.Errorf("missing follow_latest: status = %d, want 400", rec.Code)
	}
	if rec = doAgentsRequest(t, mux, http.MethodPut, "/api/v2/openrig/settings", `{"follow_latest":true,"bogus":1}`); rec.Code != http.StatusBadRequest {
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

	rec := doAgentsRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms/dev/seats",
		`{"seat_key":"alice","seat_type":"coder","runtime":"claude-code"}`)
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"pinned_version":null`) {
		t.Fatalf("company follow_latest=true: %d %s", rec.Code, rec.Body.String())
	}

	rec = doAgentsRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms/dev/seats",
		`{"seat_key":"bob","seat_type":"coder","runtime":"claude-code","follow_latest":false}`)
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"pinned_version":"1.0.0"`) {
		t.Errorf("explicit follow_latest=false over setting: %d %s", rec.Code, rec.Body.String())
	}

	rec = doAgentsRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms/dev/seats",
		`{"seat_key":"carol","seat_type":"coder","runtime":"claude-code","pinned_version":"0.9.0"}`)
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"pinned_version":"0.9.0"`) {
		t.Errorf("explicit pinned_version over setting: %d %s", rec.Code, rec.Body.String())
	}
}

func TestSeatAdminListExcludesRemovedSeats(t *testing.T) {
	fake := newFakeSeatAdmin()
	room := fake.seedRoom("dev")
	fake.seedSeatType("coder", "1.0.0")
	fake.seatTypeList = append(fake.seatTypeList, &repositories.SeatType{ID: "st-coder", Slug: "coder"})
	fake.seats = append(fake.seats,
		&repositories.Seat{ID: "seat-a", RoomID: room.ID, SeatKey: "alice", SeatTypeID: "st-coder", Status: "active"},
		&repositories.Seat{ID: "seat-b", RoomID: room.ID, SeatKey: "bob", Status: "removed"},
	)
	mux := seatAdminTestMux(t, fake)
	rec := doAgentsRequest(t, mux, http.MethodGet, "/api/v2/openrig/rooms/dev/seats", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("list seats: status = %d: %s", rec.Code, rec.Body.String())
	}
	if !strings.Contains(rec.Body.String(), `"seat_key":"alice"`) || !strings.Contains(rec.Body.String(), `"seat_type":"coder"`) {
		t.Errorf("active seat or its seat type slug missing: %s", rec.Body.String())
	}
	if strings.Contains(rec.Body.String(), `"seat_key":"bob"`) {
		t.Errorf("removed seat listed: %s", rec.Body.String())
	}
}

func TestSeatAdminRemoveSeat(t *testing.T) {
	fake := newFakeSeatAdmin()
	fake.seedRoom("dev")
	fake.seats = append(fake.seats, &repositories.Seat{ID: "seat-a", RoomID: "room-dev", SeatKey: "alice", Status: "active"})
	mux := seatAdminTestMux(t, fake)
	rec := doAgentsRequest(t, mux, http.MethodDelete, "/api/v2/openrig/rooms/dev/seats/alice", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("remove seat: status = %d: %s", rec.Code, rec.Body.String())
	}
	if rec = doAgentsRequest(t, mux, http.MethodDelete, "/api/v2/openrig/rooms/dev/seats/alice", ""); rec.Code != http.StatusNotFound {
		t.Errorf("remove removed seat: status = %d, want 404", rec.Code)
	}
}

func TestSeatAdminOverlays(t *testing.T) {
	fake := newFakeSeatAdmin()
	room := fake.seedRoom("dev")
	fake.seats = append(fake.seats, &repositories.Seat{ID: "seat-a", RoomID: room.ID, SeatKey: "alice", Status: "active"})
	mux := seatAdminTestMux(t, fake)
	cases := []struct {
		path string
		body string
		want string
	}{
		{"/api/v2/openrig/rooms/dev/overlay", `{"ops":[{"kind":"add","slug":"m"}]}`, `"scope":"room"`},
		{"/api/v2/openrig/overlay", `{"ops":[{"kind":"pin","slug":"m","version":"2"}]}`, `"scope":"company"`},
		{"/api/v2/openrig/rooms/dev/seats/alice/overlay", `{"ops":[{"kind":"override","slug":"m","content":"x"}]}`, `"scope":"seat"`},
	}
	for _, c := range cases {
		rec := doAgentsRequest(t, mux, http.MethodPut, c.path, c.body)
		if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), c.want) {
			t.Errorf("PUT %s: %d %s", c.path, rec.Code, rec.Body.String())
		}
	}
}

func TestSeatAdminOverlayValidation(t *testing.T) {
	mux := seatAdminTestMux(t, newFakeSeatAdmin())
	cases := []string{
		`{"ops":[{"kind":"explode","slug":"m"}]}`,
		`{"ops":[{"kind":"add"}]}`,
		`{"ops":[{"kind":"override","slug":"m"}]}`,
		`{"ops":[{"kind":"pin","slug":"m","version":"latest"}]}`,
		`{"ops":[{"kind":"add","slug":"m","bogus":true}]}`,
	}
	for _, body := range cases {
		rec := doAgentsRequest(t, mux, http.MethodPut, "/api/v2/openrig/overlay", body)
		if rec.Code != http.StatusBadRequest {
			t.Errorf("body %s: status = %d, want 400", body, rec.Code)
		}
	}
}

func TestSeatAdminLinks(t *testing.T) {
	fake := newFakeSeatAdmin()
	room := fake.seedRoom("dev")
	fake.seats = append(fake.seats,
		&repositories.Seat{ID: "seat-a", RoomID: room.ID, SeatKey: "alice", Status: "active"},
		&repositories.Seat{ID: "seat-b", RoomID: room.ID, SeatKey: "bob", Status: "active"},
	)
	mux := seatAdminTestMux(t, fake)
	rec := doAgentsRequest(t, mux, http.MethodPut, "/api/v2/openrig/rooms/dev/seats/alice/links", `{"to_seat":"bob","kind":"delegates_to"}`)
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"allow":true`) {
		t.Fatalf("upsert link: %d %s", rec.Code, rec.Body.String())
	}
	rec = doAgentsRequest(t, mux, http.MethodGet, "/api/v2/openrig/rooms/dev/seats/alice/links", "")
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"to_seat_id":"seat-b"`) {
		t.Errorf("list links: %d %s", rec.Code, rec.Body.String())
	}
	if rec = doAgentsRequest(t, mux, http.MethodPut, "/api/v2/openrig/rooms/dev/seats/alice/links", `{"to_seat":"alice","kind":"collaborates_with"}`); rec.Code != http.StatusBadRequest {
		t.Errorf("self link: status = %d, want 400", rec.Code)
	}
	if rec = doAgentsRequest(t, mux, http.MethodPut, "/api/v2/openrig/rooms/dev/seats/alice/links", `{"to_seat":"ghost","kind":"collaborates_with"}`); rec.Code != http.StatusNotFound {
		t.Errorf("unknown target: status = %d, want 404", rec.Code)
	}
	if rec = doAgentsRequest(t, mux, http.MethodPut, "/api/v2/openrig/rooms/dev/seats/alice/links", `{"to_seat":"bob","kind":"hates"}`); rec.Code != http.StatusBadRequest {
		t.Errorf("bad link kind: status = %d, want 400", rec.Code)
	}
}

func TestSeatAdminLinkKinds(t *testing.T) {
	fake := newFakeSeatAdmin()
	room := fake.seedRoom("dev")
	fake.seats = append(fake.seats,
		&repositories.Seat{ID: "seat-a", RoomID: room.ID, SeatKey: "alice", Status: "active"},
		&repositories.Seat{ID: "seat-b", RoomID: room.ID, SeatKey: "bob", Status: "active"},
	)
	mux := seatAdminTestMux(t, fake)
	for _, kind := range []string{"delegates_to", "spawned_by", "can_observe", "collaborates_with", "escalates_to"} {
		body := `{"to_seat":"bob","kind":"` + kind + `"}`
		rec := doAgentsRequest(t, mux, http.MethodPut, "/api/v2/openrig/rooms/dev/seats/alice/links", body)
		if rec.Code != http.StatusOK {
			t.Errorf("kind %q: status = %d, want 200: %s", kind, rec.Code, rec.Body.String())
		}
	}
	for _, kind := range []string{"reports_to", "consults", "notifies", "hates"} {
		body := `{"to_seat":"bob","kind":"` + kind + `"}`
		rec := doAgentsRequest(t, mux, http.MethodPut, "/api/v2/openrig/rooms/dev/seats/alice/links", body)
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
		rec := doAgentsRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms", body)
		if rec.Code != http.StatusBadRequest {
			t.Errorf("create room %s: status = %d, want 400: %s", body, rec.Code, rec.Body.String())
		}
	}
	for _, body := range []string{
		`{"seat_key":"bad.key","seat_type":"coder","runtime":"claude-code"}`,
		`{"seat_key":"bad key","seat_type":"coder","runtime":"claude-code"}`,
		`{"seat_key":"-bad","seat_type":"coder","runtime":"claude-code"}`,
	} {
		rec := doAgentsRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms/dev/seats", body)
		if rec.Code != http.StatusBadRequest {
			t.Errorf("create seat %s: status = %d, want 400: %s", body, rec.Code, rec.Body.String())
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
		{http.MethodPut, "/api/v2/openrig/rooms/ghost/overlay", `{"ops":[{"kind":"add","slug":"m"}]}`},
		{http.MethodPut, "/api/v2/openrig/rooms/dev/seats/ghost/overlay", `{"ops":[{"kind":"add","slug":"m"}]}`},
		{http.MethodGet, "/api/v2/openrig/rooms/ghost/overlay", ""},
		{http.MethodGet, "/api/v2/openrig/rooms/dev/seats/ghost/overlay", ""},
		{http.MethodGet, "/api/v2/openrig/modules/ghost/versions/1.0.0", ""},
		{http.MethodGet, "/api/v2/openrig/rooms/dev/seats/ghost/links", ""},
	}
	for _, c := range cases {
		rec := doAgentsRequest(t, mux, c.method, c.path, c.body)
		if rec.Code != http.StatusNotFound {
			t.Errorf("%s %s: status = %d, want 404: %s", c.method, c.path, rec.Code, rec.Body.String())
		}
	}
}

func TestSeatAdminRoutesNeedAuth(t *testing.T) {
	authenticateAgentsTestUser(t)
	mux := http.NewServeMux()
	mountSeatAdminRoutes(mux, nil)
	probes := []struct{ method, path string }{
		{http.MethodPost, "/api/v2/openrig/rooms"},
		{http.MethodGet, "/api/v2/openrig/rooms"},
		{http.MethodGet, "/api/v2/openrig/seat-types"},
		{http.MethodGet, "/api/v2/openrig/modules/instr/versions/1.0.0"},
		{http.MethodPut, "/api/v2/openrig/modules/instr/versions/1.0.0"},
		{http.MethodPost, "/api/v2/openrig/rooms/dev/seats"},
		{http.MethodGet, "/api/v2/openrig/rooms/dev/seats"},
		{http.MethodDelete, "/api/v2/openrig/rooms/dev/seats/alice"},
		{http.MethodGet, "/api/v2/openrig/overlay"},
		{http.MethodPut, "/api/v2/openrig/rooms/dev/overlay"},
		{http.MethodGet, "/api/v2/openrig/rooms/dev/overlay"},
		{http.MethodPut, "/api/v2/openrig/overlay"},
		{http.MethodPut, "/api/v2/openrig/rooms/dev/seats/alice/overlay"},
		{http.MethodGet, "/api/v2/openrig/rooms/dev/seats/alice/overlay"},
		{http.MethodPut, "/api/v2/openrig/rooms/dev/seats/alice/links"},
		{http.MethodGet, "/api/v2/openrig/rooms/dev/seats/alice/links"},
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
