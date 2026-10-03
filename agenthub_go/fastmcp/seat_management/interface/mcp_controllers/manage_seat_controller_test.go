package mcp_controllers

import (
	"context"
	"errors"
	"testing"

	seatservices "agenthub/fastmcp/seat_management/application/services"
	"agenthub/fastmcp/seat_management/domain/repositories"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
)

type fakeAuth struct {
	id  string
	err error
}

func (a *fakeAuth) GetAuthenticatedUserID(context.Context, *string, string) (string, error) {
	return a.id, a.err
}

type fakeStore struct{ seats []*repositories.Seat }

func (f *fakeStore) ListRooms(context.Context, string) ([]repositories.Room, error) {
	return []repositories.Room{{ID: "r1", Slug: "dev"}}, nil
}

func (f *fakeStore) GetRoomBySlug(_ context.Context, _, slug string) (*repositories.Room, error) {
	if slug == "dev" {
		return &repositories.Room{ID: "r1", Slug: "dev"}, nil
	}
	return nil, nil
}

func (f *fakeStore) ListSeatTypes(context.Context, string) ([]repositories.SeatType, error) {
	return []repositories.SeatType{{ID: "st1", Slug: "coder"}}, nil
}

func (f *fakeStore) FindSeat(_ context.Context, _, _, seatKey string) (*repositories.Seat, error) {
	for _, s := range f.seats {
		if s.SeatKey == seatKey {
			copied := *s
			return &copied, nil
		}
	}
	return nil, nil
}

func (f *fakeStore) ListSeats(context.Context, string, string) ([]repositories.Seat, error) {
	out := []repositories.Seat{}
	for _, s := range f.seats {
		out = append(out, *s)
	}
	return out, nil
}

func (f *fakeStore) UpdateSeatOccupant(_ context.Context, _, seatID, runtime, model string) error {
	for _, s := range f.seats {
		if s.ID == seatID {
			s.Runtime, s.Model = runtime, model
		}
	}
	return nil
}

func newController(auth AuthenticationService) (*ManageSeatController, *fakeStore) {
	store := &fakeStore{seats: []*repositories.Seat{
		{ID: "s1", RoomID: "r1", SeatKey: "alice", SeatTypeID: "st1", Runtime: "claude-code", Model: "sonnet", Status: "active"},
		{ID: "s2", RoomID: "r1", SeatKey: "bob", SeatTypeID: "st1", Runtime: "codex", Status: "removed"},
	}}
	return NewManageSeatController(auth, seatservices.NewSeatAdminService(store)), store
}

func ptr(s string) *string { return &s }

func field(t *testing.T, m *tmentities.OrderedMap[any], key string) any {
	t.Helper()
	v, ok := m.Get(key)
	if !ok {
		t.Fatalf("response has no %q: %v", key, m.Keys())
	}
	return v
}

// TestManageSeatList also checks that the removed seat bob is not listed.
func TestManageSeatList(t *testing.T) {
	c, _ := newController(&fakeAuth{id: "u"})
	resp := c.ManageSeat(context.Background(), "list", nil, nil, nil, nil, nil)
	seats, _ := field(t, resp, "seats").([]any)
	if field(t, resp, "success") != true || len(seats) != 1 {
		t.Fatalf("list = %v", resp)
	}
	first := seats[0].(*tmentities.OrderedMap[any])
	if field(t, first, "seat_key") != "alice" || field(t, first, "room") != "dev" || field(t, first, "seat_type") != "coder" {
		t.Errorf("first seat = %v", first)
	}
}

func TestManageSeatGetAndSetOccupant(t *testing.T) {
	c, store := newController(&fakeAuth{id: "u"})
	ctx := context.Background()

	resp := c.ManageSeat(ctx, "get", ptr("dev"), ptr("alice"), nil, nil, nil)
	seat := field(t, resp, "seat").(*tmentities.OrderedMap[any])
	if field(t, resp, "success") != true || field(t, seat, "runtime") != "claude-code" || field(t, seat, "model") != "sonnet" {
		t.Fatalf("get = %v", resp)
	}

	resp = c.ManageSeat(ctx, "set_occupant", ptr("dev"), ptr("alice"), ptr("codex"), ptr("gpt-5.1"), nil)
	seat = field(t, resp, "seat").(*tmentities.OrderedMap[any])
	if field(t, resp, "success") != true || field(t, seat, "runtime") != "codex" || field(t, seat, "model") != "gpt-5.1" {
		t.Fatalf("set_occupant = %v", resp)
	}
	if store.seats[0].Runtime != "codex" || store.seats[0].Model != "gpt-5.1" {
		t.Errorf("stored seat = %+v", store.seats[0])
	}

	resp = c.ManageSeat(ctx, "set_occupant", ptr("dev"), ptr("alice"), ptr("claude-code"), nil, nil)
	if field(t, resp, "success") != true || store.seats[0].Model != "" {
		t.Errorf("omitted model should clear it: %v %+v", resp, store.seats[0])
	}
}

func TestManageSeatFailures(t *testing.T) {
	c, store := newController(&fakeAuth{id: "u"})
	ctx := context.Background()
	cases := []struct {
		name                       string
		action                     string
		room, seat, runtime, model *string
	}{
		{"unknown action", "delete", nil, nil, nil, nil},
		{"get without seat", "get", ptr("dev"), nil, nil, nil},
		{"set without runtime", "set_occupant", ptr("dev"), ptr("alice"), nil, nil},
		{"bad runtime", "set_occupant", ptr("dev"), ptr("alice"), ptr("gemini"), nil},
		{"bad model", "set_occupant", ptr("dev"), ptr("alice"), ptr("codex"), ptr("a b")},
		{"unknown room", "get", ptr("ghost"), ptr("alice"), nil, nil},
		{"unknown seat", "get", ptr("dev"), ptr("ghost"), nil, nil},
		{"removed seat", "set_occupant", ptr("dev"), ptr("bob"), ptr("claude-code"), nil},
	}
	for _, tc := range cases {
		resp := c.ManageSeat(ctx, tc.action, tc.room, tc.seat, tc.runtime, tc.model, nil)
		if field(t, resp, "success") != false || field(t, resp, "error") == "" {
			t.Errorf("%s: response = %v", tc.name, resp)
		}
	}
	if store.seats[0].Runtime != "claude-code" || store.seats[1].Runtime != "codex" {
		t.Errorf("a failed call changed a seat: %+v %+v", store.seats[0], store.seats[1])
	}
}

func TestManageSeatAuthFailure(t *testing.T) {
	c, _ := newController(&fakeAuth{err: errors.New("no token")})
	resp := c.ManageSeat(context.Background(), "list", nil, nil, nil, nil, nil)
	if field(t, resp, "success") != false || field(t, resp, "error") != "no token" {
		t.Errorf("auth failure = %v", resp)
	}
}

type recordingServer struct {
	name, description string
	fn                any
}

func (r *recordingServer) Tool(name, description string, fn any) {
	r.name, r.description, r.fn = name, description, fn
}

func TestManageSeatRegisterTools(t *testing.T) {
	c, _ := newController(&fakeAuth{id: "u"})
	server := &recordingServer{}
	c.RegisterTools(server)
	if server.name != "manage_seat" || server.description != ManageSeatToolDescription || server.fn == nil {
		t.Fatalf("registered %+v", server)
	}
	c.RegisterTools(nil)
}

func TestManageSeatInputSchema(t *testing.T) {
	schema := ManageSeatInputSchema()
	props, _ := field(t, schema, "properties").(*tmentities.OrderedMap[any])
	want := []string{"action", "room", "seat", "runtime", "model", "user_id"}
	if got := props.Keys(); len(got) != len(want) {
		t.Fatalf("properties = %v", got)
	}
	for i, key := range want {
		if props.Keys()[i] != key {
			t.Errorf("property %d = %s, want %s", i, props.Keys()[i], key)
		}
	}
	if required, _ := field(t, schema, "required").([]any); len(required) != 1 || required[0] != "action" {
		t.Errorf("required = %v", field(t, schema, "required"))
	}
}
