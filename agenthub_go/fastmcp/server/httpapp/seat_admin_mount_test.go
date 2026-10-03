package httpapp

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"net/http"
	"net/http/httptest"
	"sort"
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

	deletedResolved []string
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

func (f *fakeSeatAdmin) GetRoomBySlug(_ context.Context, userID, slug string) (*repositories.Room, error) {
	for _, r := range f.rooms {
		if r.Slug == slug && (r.UserID == "" || r.UserID == userID) {
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

func (f *fakeSeatAdmin) ListLatestModuleVersions(_ context.Context, _ string) ([]repositories.ModuleVersion, error) {
	out := make([]repositories.ModuleVersion, 0, len(f.moduleVersions))
	for _, mv := range f.moduleVersions {
		out = append(out, *mv)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Slug < out[j].Slug })
	return out, nil
}

func (f *fakeSeatAdmin) AddSeatTypeVersion(_ context.Context, _, slug, version string, refs []resolver.ModuleRef) (*repositories.SeatTypeVersion, error) {
	created := &repositories.SeatTypeVersion{SeatTypeID: "st-" + slug, Slug: slug, Version: version, ModuleRefs: refs}
	f.seatVersions[slug][version] = created
	f.seatTypes[slug] = created
	return created, nil
}

func (f *fakeSeatAdmin) SetSeatTypeDefaultRuntime(_ context.Context, _, slug, runtime string) error {
	for _, st := range f.seatTypeList {
		if st.Slug == slug {
			st.DefaultRuntime = runtime
		}
	}
	return nil
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

func TestSeatAdminListModules(t *testing.T) {
	fake := newFakeSeatAdmin()
	mux := seatAdminTestMux(t, fake)
	rec := doAgentsRequest(t, mux, http.MethodGet, "/api/v2/openrig/modules", "")
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"modules":[]`) {
		t.Fatalf("empty list: %d %s", rec.Code, rec.Body.String())
	}
	if rec = doAgentsRequest(t, mux, http.MethodPut, "/api/v2/openrig/modules/zeta/versions/1.0.0", `{"kind":"skill","content":"z"}`); rec.Code != http.StatusOK {
		t.Fatalf("put module: %d %s", rec.Code, rec.Body.String())
	}
	if rec = doAgentsRequest(t, mux, http.MethodPut, "/api/v2/openrig/modules/alpha/versions/1.2.0", `{"kind":"instruction","content":"a"}`); rec.Code != http.StatusOK {
		t.Fatalf("put module: %d %s", rec.Code, rec.Body.String())
	}
	rec = doAgentsRequest(t, mux, http.MethodGet, "/api/v2/openrig/modules", "")
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
		kind := "instruction"
		if strings.HasPrefix(put, "skill") {
			kind = "skill"
		}
		if rec := doAgentsRequest(t, mux, http.MethodPut, "/api/v2/openrig/modules/"+put, `{"kind":"`+kind+`","content":"c"}`); rec.Code != http.StatusOK {
			t.Fatalf("put module %s: %d %s", put, rec.Code, rec.Body.String())
		}
	}
	rec := doAgentsRequest(t, mux, http.MethodPost, "/api/v2/openrig/seat-types/coder/versions",
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
	rec = doAgentsRequest(t, mux, http.MethodGet, "/api/v2/openrig/seat-types", "")
	if !strings.Contains(rec.Body.String(), `"default_runtime":"codex","latest_version":"1.0.1"`) {
		t.Errorf("seat type not updated: %s", rec.Body.String())
	}
}

func TestSeatAdminCreateSeatTypeVersionRejects(t *testing.T) {
	fake := newFakeSeatAdmin()
	fake.seedSeatType("coder", "1.0.0")
	mux := seatAdminTestMux(t, fake)
	if rec := doAgentsRequest(t, mux, http.MethodPut, "/api/v2/openrig/modules/instr/versions/1.0.0", `{"kind":"instruction","content":"c"}`); rec.Code != http.StatusOK {
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
		if rec := doAgentsRequest(t, mux, http.MethodPost, c.path, c.body); rec.Code != c.want {
			t.Errorf("%s: status = %d, want %d: %s", c.name, rec.Code, c.want, rec.Body.String())
		}
	}
	if fake.seatVersions["coder"]["1.0.1"] != nil {
		t.Error("a rejected request created a version")
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
		&repositories.Seat{ID: "seat-a", RoomID: room.ID, SeatKey: "alice", Status: "active"},
		&repositories.Seat{ID: "seat-b", RoomID: room.ID, SeatKey: "bob", Status: "active"},
	)
	mux := seatAdminTestMux(t, fake)
	rigMux := seatRigSpecTestMux(t, rigSpecOverAdminFake{fake})
	linkPath := "/api/v2/openrig/rooms/dev/seats/alice/links"
	if rec := doAgentsRequest(t, mux, http.MethodPut, linkPath, `{"to_seat":"bob","kind":"delegates_to"}`); rec.Code != http.StatusOK {
		t.Fatalf("upsert link: %d %s", rec.Code, rec.Body.String())
	}
	if rec := doAgentsRequest(t, mux, http.MethodPut, linkPath, `{"to_seat":"bob","kind":"can_observe"}`); rec.Code != http.StatusOK {
		t.Fatalf("upsert second link: %d %s", rec.Code, rec.Body.String())
	}
	rec := doAgentsRequest(t, rigMux, http.MethodGet, "/api/v2/openrig/rooms/dev/rigspec", "")
	if !strings.Contains(rec.Body.String(), "delegates_to") {
		t.Fatalf("rigspec before delete lacks the link: %d %s", rec.Code, rec.Body.String())
	}

	if rec = doAgentsRequest(t, mux, http.MethodDelete, linkPath+"/bob/delegates_to", ""); rec.Code != http.StatusOK {
		t.Fatalf("delete link: %d %s", rec.Code, rec.Body.String())
	}
	rec = doAgentsRequest(t, mux, http.MethodGet, linkPath, "")
	if strings.Contains(rec.Body.String(), "delegates_to") || !strings.Contains(rec.Body.String(), "can_observe") {
		t.Errorf("list after delete should keep only the other kind: %s", rec.Body.String())
	}
	rec = doAgentsRequest(t, rigMux, http.MethodGet, "/api/v2/openrig/rooms/dev/rigspec", "")
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
		if rec := doAgentsRequest(t, mux, http.MethodDelete, c.path, ""); rec.Code != c.want {
			t.Errorf("%s: status = %d, want %d: %s", c.name, rec.Code, c.want, rec.Body.String())
		}
	}

	room.UserID = "another-user"
	if rec := doAgentsRequest(t, mux, http.MethodDelete, linkPath+"/bob/can_observe", ""); rec.Code != http.StatusNotFound {
		t.Errorf("other user's room: status = %d, want 404", rec.Code)
	}
	if len(fake.links) != 1 {
		t.Errorf("another user's request changed links: %d left, want 1", len(fake.links))
	}
}

func TestSeatAdminDeleteRoom(t *testing.T) {
	fake := newFakeSeatAdmin()
	dev := fake.seedRoom("dev")
	ops := repositories.Overlay{Scope: repositories.ScopeRoom, RoomID: dev.ID, Ops: []resolver.Op{{Kind: resolver.OpAdd, Slug: "m", Version: "1.0.0"}}}
	other := fake.seedRoom("other")
	fake.seats = append(fake.seats,
		&repositories.Seat{ID: "seat-a", RoomID: dev.ID, SeatKey: "alice", Status: "active"},
		&repositories.Seat{ID: "seat-b", RoomID: dev.ID, SeatKey: "bob", Status: "removed"},
		&repositories.Seat{ID: "seat-x", RoomID: other.ID, SeatKey: "xena", Status: "active"},
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
	if rec := doAgentsRequest(t, mux, http.MethodDelete, "/api/v2/openrig/rooms/dev", ""); rec.Code != http.StatusNotFound {
		t.Fatalf("other user's room: status = %d, want 404", rec.Code)
	}
	if len(fake.rooms) != 2 || len(fake.seats) != 3 || len(fake.links) != 2 {
		t.Fatalf("another user's request deleted rows: %d rooms, %d seats, %d links", len(fake.rooms), len(fake.seats), len(fake.links))
	}
	dev.UserID = ""

	if rec := doAgentsRequest(t, mux, http.MethodDelete, "/api/v2/openrig/rooms/dev", ""); rec.Code != http.StatusOK {
		t.Fatalf("delete room: %d %s", rec.Code, rec.Body.String())
	}
	if len(fake.rooms) != 1 || fake.rooms[0].Slug != "other" {
		t.Errorf("rooms left = %+v, want only other", fake.rooms)
	}
	if len(fake.seats) != 1 || fake.seats[0].SeatKey != "xena" {
		t.Errorf("seats left = %+v, want only xena (removed seats go too)", fake.seats)
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
	if rec := doAgentsRequest(t, mux, http.MethodDelete, "/api/v2/openrig/rooms/dev", ""); rec.Code != http.StatusNotFound {
		t.Errorf("delete again: status = %d, want 404", rec.Code)
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

func TestSeatAdminSetOccupant(t *testing.T) {
	fake := newFakeSeatAdmin()
	room := fake.seedRoom("dev")
	fake.seedSeatType("coder", "1.0.0")
	pinned := "1.0.0"
	fake.seats = append(fake.seats, &repositories.Seat{
		ID: "seat-a", RoomID: room.ID, SeatKey: "alice", SeatTypeID: "st-coder", PinnedVersion: &pinned,
		Runtime: "claude-code", Model: "sonnet", Status: "active",
	})
	mux := seatAdminTestMux(t, fake)
	const path = "/api/v2/openrig/rooms/dev/seats/alice/occupant"

	rec := doAgentsRequest(t, mux, http.MethodPut, path, `{"runtime":"codex","model":"gpt-5.1:high"}`)
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

	rec = doAgentsRequest(t, mux, http.MethodPut, path, `{"runtime":"claude-code","model":""}`)
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"model":""`) {
		t.Errorf("empty model: %d %s", rec.Code, rec.Body.String())
	}
}

func TestSeatAdminSetOccupantRejectsInvalidInput(t *testing.T) {
	fake := newFakeSeatAdmin()
	room := fake.seedRoom("dev")
	fake.seats = append(fake.seats, &repositories.Seat{ID: "seat-a", RoomID: room.ID, SeatKey: "alice", Runtime: "claude-code", Status: "active"})
	mux := seatAdminTestMux(t, fake)
	const path = "/api/v2/openrig/rooms/dev/seats/alice/occupant"
	for _, body := range []string{
		`{"runtime":"gemini"}`,
		`{"runtime":""}`,
		`{"model":"sonnet"}`,
		`{"runtime":"codex","model":"-bad"}`,
		`{"runtime":"codex","model":"has space"}`,
		`{"runtime":"codex","model":"` + strings.Repeat("a", 129) + `"}`,
		`{"runtime":"codex","extra":1}`,
		`not json`,
	} {
		if rec := doAgentsRequest(t, mux, http.MethodPut, path, body); rec.Code != http.StatusBadRequest {
			t.Errorf("body %q: status = %d, want 400: %s", body, rec.Code, rec.Body.String())
		}
	}
	if fake.seats[0].Runtime != "claude-code" {
		t.Errorf("a rejected request changed the seat: %+v", fake.seats[0])
	}
}

func TestSeatAdminSetOccupantNotFoundAndRemoved(t *testing.T) {
	fake := newFakeSeatAdmin()
	room := fake.seedRoom("dev")
	fake.seats = append(fake.seats, &repositories.Seat{ID: "seat-b", RoomID: room.ID, SeatKey: "bob", Status: "removed"})
	mux := seatAdminTestMux(t, fake)
	body := `{"runtime":"codex","model":""}`
	for path, want := range map[string]int{
		"/api/v2/openrig/rooms/ghost/seats/bob/occupant": http.StatusNotFound,
		"/api/v2/openrig/rooms/dev/seats/ghost/occupant": http.StatusNotFound,
		"/api/v2/openrig/rooms/dev/seats/bob/occupant":   http.StatusConflict,
	} {
		if rec := doAgentsRequest(t, mux, http.MethodPut, path, body); rec.Code != want {
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
		{http.MethodPut, "/api/v2/openrig/rooms/ghost/overlay", `{"ops":[{"kind":"add","slug":"m"}]}`},
		{http.MethodPut, "/api/v2/openrig/rooms/dev/seats/ghost/overlay", `{"ops":[{"kind":"add","slug":"m"}]}`},
		{http.MethodGet, "/api/v2/openrig/rooms/ghost/overlay", ""},
		{http.MethodGet, "/api/v2/openrig/rooms/dev/seats/ghost/overlay", ""},
		{http.MethodGet, "/api/v2/openrig/modules/ghost/versions/1.0.0", ""},
		{http.MethodGet, "/api/v2/openrig/rooms/dev/seats/ghost/links", ""},
		{http.MethodDelete, "/api/v2/openrig/rooms/ghost", ""},
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
		{http.MethodGet, "/api/v2/openrig/modules"},
		{http.MethodPost, "/api/v2/openrig/seat-types/coder/versions"},
		{http.MethodPost, "/api/v2/openrig/rooms/dev/seats"},
		{http.MethodGet, "/api/v2/openrig/rooms/dev/seats"},
		{http.MethodDelete, "/api/v2/openrig/rooms/dev/seats/alice"},
		{http.MethodPut, "/api/v2/openrig/rooms/dev/seats/alice/occupant"},
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
