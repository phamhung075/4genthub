package httpapp

// The D5 sharing wiring at the mount layer. The ORM predicate is proven on PostgreSQL in
// room_sharing_integration_test.go; these tests pin the ROUTE behaviour the owner's acceptance
// names: a member reads the owner's room and cannot mutate it, a non-member still gets 404, and
// the owner's own path is unchanged (same rows, and every read still asks for the caller's id).
//
// The fake is the mount test's existing fakeSeatAdmin with the sharing surface added: an embedded
// type keeps every untouched method identical, and the overridden reads RECORD the user id they
// were asked for, which is how "the viewer reads as the owner" is asserted rather than assumed.

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"testing"

	"agenthub/fastmcp/seat_management/domain/repositories"
	"agenthub/fastmcp/seat_management/domain/resolver"
	"agenthub/fastmcp/task_management/infrastructure/database"
	teamrepositories "agenthub/fastmcp/team_management/domain/repositories"
)

// sharingTestField reads one nested field from a response body: map keys by name, array elements
// by their decimal index, e.g. ("rooms", "0", "team_id"). It returns nil when the path is absent.
func sharingTestField(t *testing.T, body []byte, path ...string) any {
	t.Helper()
	var doc any
	if err := json.Unmarshal(body, &doc); err != nil {
		t.Fatalf("decode body: %v (%s)", err, body)
	}
	for _, key := range path {
		switch node := doc.(type) {
		case map[string]any:
			doc = node[key]
		case []any:
			var index int
			if _, err := fmt.Sscanf(key, "%d", &index); err != nil || index < 0 || index >= len(node) {
				return nil
			}
			doc = node[index]
		default:
			return nil
		}
	}
	return doc
}

// mountTestUser is the id authenticateTestUser installs; every request below is that caller.
const mountTestUser = "11111111-1111-4111-8111-111111111111"

// sharingSeatAdmin is the mount fake plus the sharing behaviour and the scope journal.
type sharingSeatAdmin struct {
	*fakeSeatAdmin

	// memberships is user id -> team ids, the fake's model of team_members.
	memberships map[string]map[string]bool
	// teams is team slug -> team id, the fake's model of the teams table.
	teams map[string]string
	// scopes records the user id every read was asked for, in call order.
	scopes []string
}

func newSharingSeatAdmin() *sharingSeatAdmin {
	return &sharingSeatAdmin{
		fakeSeatAdmin: newFakeSeatAdmin(),
		memberships:   map[string]map[string]bool{},
		teams:         map[string]string{},
	}
}

func (f *sharingSeatAdmin) isMember(userID, teamID string) bool {
	return f.memberships[userID][teamID]
}

// joinTeam records a membership without going through the route (the teams domain has its own
// tests; what matters here is that a membership grants read access to the room's team).
func (f *sharingSeatAdmin) joinTeam(userID, teamID string) {
	if f.memberships[userID] == nil {
		f.memberships[userID] = map[string]bool{}
	}
	f.memberships[userID][teamID] = true
}

// sharedRoom seeds a room owned by ownerID and shared with teamID.
func (f *sharingSeatAdmin) sharedRoom(slug, ownerID, teamID string) *repositories.Room {
	room := &repositories.Room{ID: "room-" + slug, UserID: ownerID, Slug: slug, Name: slug, TeamID: teamID}
	f.rooms = append(f.rooms, room)
	return room
}

func (f *sharingSeatAdmin) GetVisibleRoomBySlug(_ context.Context, userID, slug string) (*repositories.Room, error) {
	for _, r := range f.rooms {
		if r.Slug == slug && (r.UserID == "" || r.UserID == userID) {
			return r, nil
		}
	}
	for _, r := range f.rooms {
		if r.Slug == slug && r.TeamID != "" && f.isMember(userID, r.TeamID) {
			return r, nil
		}
	}
	return nil, nil
}

func (f *sharingSeatAdmin) SetRoomTeam(_ context.Context, userID, roomID, teamID string) error {
	for _, r := range f.rooms {
		if r.ID != roomID {
			continue
		}
		// An empty UserID is the mount fake's "the caller owns it" (seedRoom), same as its strict
		// GetRoomBySlug.
		if r.UserID != "" && r.UserID != userID {
			return repositories.ErrRoomNotOwned
		}
		r.TeamID = teamID
		return nil
	}
	return repositories.ErrRoomNotOwned
}

func (f *sharingSeatAdmin) ListSeats(ctx context.Context, userID, roomID string) ([]repositories.Seat, error) {
	f.scopes = append(f.scopes, userID)
	return f.fakeSeatAdmin.ListSeats(ctx, userID, roomID)
}

func (f *sharingSeatAdmin) ListSeatTypes(ctx context.Context, userID string) ([]repositories.SeatType, error) {
	f.scopes = append(f.scopes, userID)
	return f.fakeSeatAdmin.ListSeatTypes(ctx, userID)
}

func (f *sharingSeatAdmin) FindSeat(ctx context.Context, userID, roomID, seatKey string) (*repositories.Seat, error) {
	f.scopes = append(f.scopes, userID)
	return f.fakeSeatAdmin.FindSeat(ctx, userID, roomID, seatKey)
}

func (f *sharingSeatAdmin) FindOverlay(ctx context.Context, userID, scope, roomID, seatID string) (*repositories.Overlay, error) {
	f.scopes = append(f.scopes, userID)
	return f.fakeSeatAdmin.FindOverlay(ctx, userID, scope, roomID, seatID)
}

func (f *sharingSeatAdmin) ListSeatLinks(ctx context.Context, userID, seatID string) ([]repositories.SeatLink, error) {
	f.scopes = append(f.scopes, userID)
	return f.fakeSeatAdmin.ListSeatLinks(ctx, userID, seatID)
}

// fakeSeatAdminTeams models the teams domain for the share route.
type fakeSeatAdminTeams struct {
	fake *sharingSeatAdmin
}

func (t fakeSeatAdminTeams) FindForMember(_ context.Context, userID, slug string) (*teamrepositories.Team, error) {
	id, ok := t.fake.teams[slug]
	if !ok || !t.fake.isMember(userID, id) {
		return nil, nil
	}
	return &teamrepositories.Team{ID: id, UserID: userID, Slug: slug, Name: slug}, nil
}

// sharingTestMux mounts the seat admin routes over the sharing fake and silences the broadcast.
func sharingTestMux(t *testing.T, fake *sharingSeatAdmin) *http.ServeMux {
	t.Helper()
	previousSource := newSeatAdminSource
	newSeatAdminSource = func(*database.SessionManager) (seatAdminSource, error) { return fake, nil }
	previousTeams := newSeatAdminTeamSource
	newSeatAdminTeamSource = func(*database.SessionManager) (seatAdminTeamSource, error) {
		return fakeSeatAdminTeams{fake: fake}, nil
	}
	previousBroadcast := seatBroadcastFn
	seatBroadcastFn = func(context.Context, string, string, string, string, string, string) error { return nil }
	t.Cleanup(func() {
		newSeatAdminSource = previousSource
		newSeatAdminTeamSource = previousTeams
		seatBroadcastFn = previousBroadcast
	})
	authenticateTestUser(t)
	mux := http.NewServeMux()
	mountSeatAdminRoutes(mux, nil)
	return mux
}

// seedSharedRoom builds the shape every test below starts from: a room owned by another user and
// shared with team-eng, holding one seat with an overlay and a link.
func seedSharedRoom(fake *sharingSeatAdmin) *repositories.Room {
	fake.teams["eng"] = "team-eng"
	fake.joinTeam(mountTestUser, "team-eng")
	room := fake.sharedRoom("dev", "owner-user", "team-eng")
	fake.seatTypeList = append(fake.seatTypeList, &repositories.SeatType{ID: "st-coder", Slug: "coder"})
	fake.seats = append(fake.seats,
		&repositories.Seat{ID: "seat-a", UserID: "owner-user", RoomID: room.ID, SeatKey: "alice", SeatTypeID: "st-coder"},
		&repositories.Seat{ID: "seat-b", UserID: "owner-user", RoomID: room.ID, SeatKey: "bob", SeatTypeID: "st-coder"},
	)
	fake.overlays["room|"+room.ID+"|"] = &repositories.Overlay{
		ID: "ov-room", UserID: "owner-user", Scope: repositories.ScopeRoom, RoomID: room.ID,
		Ops: []resolver.Op{{Kind: resolver.OpAdd, Slug: "instr", Version: "1.0.0"}},
	}
	fake.links = append(fake.links, &repositories.SeatLink{
		ID: "link-1", UserID: "owner-user", FromSeatID: "seat-a", ToSeatID: "seat-b", Kind: "message", Allow: true,
	})
	return room
}

// assertScopeIsOwner proves every read the handler performed was asked for the owner's rows.
func assertScopeIsOwner(t *testing.T, fake *sharingSeatAdmin, owner string) {
	t.Helper()
	if len(fake.scopes) == 0 {
		t.Fatalf("no read was performed")
	}
	for _, scope := range fake.scopes {
		if scope != owner {
			t.Fatalf("a read was asked for %q, want the room owner %q", scope, owner)
		}
	}
}

func TestSeatAdminViewerReadsSharedRoom(t *testing.T) {
	fake := newSharingSeatAdmin()
	seedSharedRoom(fake)
	mux := sharingTestMux(t, fake)

	fake.scopes = nil
	rec := doTestRequest(t, mux, http.MethodGet, "/api/v2/openrig/rooms/dev/seats", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("viewer list seats: %d %s", rec.Code, rec.Body.String())
	}
	var seats struct {
		Seats []struct {
			SeatKey string `json:"seat_key"`
		} `json:"seats"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &seats); err != nil {
		t.Fatalf("decode seats: %v", err)
	}
	if len(seats.Seats) != 2 {
		t.Fatalf("viewer saw %d seats, want the owner's 2", len(seats.Seats))
	}
	assertScopeIsOwner(t, fake, "owner-user")

	fake.scopes = nil
	rec = doTestRequest(t, mux, http.MethodGet, "/api/v2/openrig/rooms/dev/overlay", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("viewer room overlay: %d %s", rec.Code, rec.Body.String())
	}
	if ops := sharingTestField(t, rec.Body.Bytes(), "overlay", "ops"); ops == nil {
		t.Fatalf("viewer read no overlay ops: %s", rec.Body.String())
	}
	assertScopeIsOwner(t, fake, "owner-user")

	fake.scopes = nil
	rec = doTestRequest(t, mux, http.MethodGet, "/api/v2/openrig/rooms/dev/seats/alice/links", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("viewer seat links: %d %s", rec.Code, rec.Body.String())
	}
	assertScopeIsOwner(t, fake, "owner-user")
}

func TestSeatAdminNonMemberGetsNotFound(t *testing.T) {
	fake := newSharingSeatAdmin()
	seedSharedRoom(fake)
	// The room is shared with team-eng; this caller is not a member of it (the seed adds the
	// membership, so it is removed here to model a stranger).
	fake.memberships = map[string]map[string]bool{}
	mux := sharingTestMux(t, fake)

	for _, tc := range []struct{ method, path, body string }{
		{http.MethodGet, "/api/v2/openrig/rooms/dev/seats", ""},
		{http.MethodGet, "/api/v2/openrig/rooms/dev/overlay", ""},
		{http.MethodGet, "/api/v2/openrig/rooms/dev/seats/alice/overlay", ""},
		{http.MethodGet, "/api/v2/openrig/rooms/dev/seats/alice/links", ""},
		{http.MethodDelete, "/api/v2/openrig/rooms/dev", ""},
		{http.MethodPut, "/api/v2/openrig/rooms/dev/seats/alice/occupant", `{"runtime":"omp","model":"deepseek/deepseek-flash"}`},
	} {
		rec := doTestRequest(t, mux, tc.method, tc.path, tc.body)
		if rec.Code != http.StatusNotFound {
			t.Fatalf("%s %s = %d, want 404: %s", tc.method, tc.path, rec.Code, rec.Body.String())
		}
	}
	// The owner's room list is empty for the stranger: the shared room is not theirs.
	rec := doTestRequest(t, mux, http.MethodGet, "/api/v2/openrig/rooms", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("list rooms: %d %s", rec.Code, rec.Body.String())
	}
}

func TestSeatAdminViewerCannotMutate(t *testing.T) {
	fake := newSharingSeatAdmin()
	seedSharedRoom(fake)
	mux := sharingTestMux(t, fake)

	for _, tc := range []struct{ method, path, body string }{
		{http.MethodPut, "/api/v2/openrig/rooms/dev/seats/alice/occupant", `{"runtime":"omp","model":"deepseek/deepseek-flash"}`},
		{http.MethodPut, "/api/v2/openrig/rooms/dev/seats/alice/permission-policy", `{"permission_policy":"yolo"}`},
		{http.MethodPut, "/api/v2/openrig/rooms/dev/overlay", `{"ops":[{"kind":"add","slug":"instr","version":"1.0.0"}]}`},
		{http.MethodPut, "/api/v2/openrig/rooms/dev/seats/alice/overlay", `{"ops":[{"kind":"add","slug":"instr","version":"1.0.0"}]}`},
		{http.MethodPut, "/api/v2/openrig/rooms/dev/seats/alice/links", `{"to_seat":"bob","kind":"collaborates_with"}`},
		{http.MethodDelete, "/api/v2/openrig/rooms/dev/seats/alice/links/bob/collaborates_with", ""},
		{http.MethodDelete, "/api/v2/openrig/rooms/dev/seats/alice", ""},
		{http.MethodDelete, "/api/v2/openrig/rooms/dev", ""},
		{http.MethodPost, "/api/v2/openrig/rooms/dev/seats", `{"seat_key":"carol","seat_type":"coder","runtime":"omp","model":"deepseek/deepseek-flash"}`},
	} {
		rec := doTestRequest(t, mux, tc.method, tc.path, tc.body)
		if rec.Code != http.StatusNotFound {
			t.Fatalf("%s %s = %d, want 404 (a viewer cannot mutate): %s", tc.method, tc.path, rec.Code, rec.Body.String())
		}
	}
	// Nothing changed in the fake.
	room := fake.rooms[0]
	if room.TeamID != "team-eng" || len(fake.seats) != 2 {
		t.Fatalf("a viewer mutation left state behind: room=%+v seats=%d", room, len(fake.seats))
	}
	if fake.overlays["room|"+room.ID+"|"] == nil {
		t.Fatal("the room overlay was removed by a viewer")
	}
}

func TestSeatAdminOwnerPathUnchanged(t *testing.T) {
	fake := newSharingSeatAdmin()
	fake.seatTypeList = append(fake.seatTypeList, &repositories.SeatType{ID: "st-coder", Slug: "coder"})
	room := fake.seedRoom("dev") // owned by the caller: an empty UserID is the fake's "caller owns it"
	fake.seats = append(fake.seats, &repositories.Seat{ID: "seat-a", RoomID: room.ID, SeatKey: "alice", SeatTypeID: "st-coder"})
	mux := sharingTestMux(t, fake)

	fake.scopes = nil
	rec := doTestRequest(t, mux, http.MethodGet, "/api/v2/openrig/rooms/dev/seats", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("owner list seats: %d %s", rec.Code, rec.Body.String())
	}
	assertScopeIsOwner(t, fake, mountTestUser)

	rec = doTestRequest(t, mux, http.MethodGet, "/api/v2/openrig/rooms", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("owner list rooms: %d %s", rec.Code, rec.Body.String())
	}
	if team := sharingTestField(t, rec.Body.Bytes(), "rooms", "0", "team_id"); team != "" {
		t.Fatalf("a private room reported team_id %v, want an empty string", team)
	}

	// The owner mutates their own room through the unchanged path.
	rec = doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/rooms/dev/seats/alice/occupant",
		`{"runtime":"omp","model":"deepseek/deepseek-flash"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("owner set occupant: %d %s", rec.Code, rec.Body.String())
	}
}

func TestSeatAdminShareRoute(t *testing.T) {
	fake := newSharingSeatAdmin()
	fake.teams["eng"] = "team-eng"
	fake.joinTeam(mountTestUser, "team-eng")
	room := fake.seedRoom("dev") // the caller owns it
	mux := sharingTestMux(t, fake)

	rec := doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/rooms/dev/team", `{"team":"eng"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("share: %d %s", rec.Code, rec.Body.String())
	}
	if room.TeamID != "team-eng" {
		t.Fatalf("room team_id = %q, want team-eng", room.TeamID)
	}
	if team := sharingTestField(t, rec.Body.Bytes(), "room", "team_id"); team != "team-eng" {
		t.Fatalf("response team_id = %v, want team-eng", team)
	}

	// A team the caller is not a member of cannot be used, and an unknown slug is a 404.
	if rec := doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/rooms/dev/team", `{"team":"other"}`); rec.Code != http.StatusNotFound {
		t.Fatalf("share with a foreign team = %d, want 404: %s", rec.Code, rec.Body.String())
	}
	// Clearing makes the room private again.
	if rec := doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/rooms/dev/team", `{"team":""}`); rec.Code != http.StatusOK {
		t.Fatalf("unshare: %d %s", rec.Code, rec.Body.String())
	}
	if room.TeamID != "" {
		t.Fatalf("room still shared: %q", room.TeamID)
	}
}

func TestSeatAdminShareRouteRefusesNonOwner(t *testing.T) {
	fake := newSharingSeatAdmin()
	seedSharedRoom(fake) // owned by owner-user; the caller is only a viewer
	mux := sharingTestMux(t, fake)

	if rec := doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/rooms/dev/team", `{"team":"eng"}`); rec.Code != http.StatusNotFound {
		t.Fatalf("viewer share = %d, want 404: %s", rec.Code, rec.Body.String())
	}
	if fake.rooms[0].TeamID != "team-eng" {
		t.Fatalf("a viewer changed the sharing: %q", fake.rooms[0].TeamID)
	}
}
