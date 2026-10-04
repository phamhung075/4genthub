package mcp_controllers

import (
	"context"
	"errors"
	"strings"
	"testing"

	"agenthub/fastmcp/seat_management/domain/repositories"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
)

type fakeResolver struct {
	resolved         *repositories.ResolvedSeat
	err              error
	gotRoom, gotSeat string
}

func (f *fakeResolver) ResolveSeat(_ context.Context, _, roomSlug, seatKey string) (*repositories.ResolvedSeat, error) {
	f.gotRoom, f.gotSeat = roomSlug, seatKey
	return f.resolved, f.err
}

func newCallSeatControllerForTest(auth AuthenticationService, resolved *repositories.ResolvedSeat, err error) (*CallSeatController, *fakeResolver) {
	resolver := &fakeResolver{resolved: resolved, err: err}
	return NewCallSeatController(auth, resolver), resolver
}

func TestCallSeatResolvesTheSeat(t *testing.T) {
	resolved := &repositories.ResolvedSeat{
		Hash:    "abc123",
		Runtime: "omp",
		Policy:  map[string]any{"permission_policy": "yolo"},
		Files: []repositories.ResolvedFile{
			{Path: "guidance/role.md", Content: "You are the lead."},
		},
	}
	c, resolver := newCallSeatControllerForTest(&fakeAuth{id: "u"}, resolved, nil)

	resp := c.CallSeat(context.Background(), ptr("4genthub-dev"), ptr("lead"), nil)
	if field(t, resp, "success") != true {
		t.Fatalf("call_seat = %v", resp)
	}
	if field(t, resp, "room") != "4genthub-dev" || field(t, resp, "seat") != "lead" {
		t.Errorf("echoed address = %v", resp)
	}
	if field(t, resp, "hash") != "abc123" || field(t, resp, "runtime") != "omp" {
		t.Errorf("resolved seat = %v", resp)
	}
	files, _ := field(t, resp, "files").([]any)
	if len(files) != 1 {
		t.Fatalf("files = %v", field(t, resp, "files"))
	}
	first := files[0].(*tmentities.OrderedMap[any])
	if field(t, first, "path") != "guidance/role.md" || field(t, first, "content") != "You are the lead." {
		t.Errorf("first file = %v", first)
	}
	if resolver.gotRoom != "4genthub-dev" || resolver.gotSeat != "lead" {
		t.Errorf("resolver got %s/%s", resolver.gotRoom, resolver.gotSeat)
	}
}

func TestCallSeatFailures(t *testing.T) {
	cases := []struct {
		name         string
		room, seat   *string
		resolverErr  error
		wantContains string
	}{
		{"no room", nil, ptr("lead"), nil, "room and seat are required"},
		{"no seat", ptr("4genthub-dev"), nil, nil, "room and seat are required"},
		{"unknown seat", ptr("4genthub-dev"), ptr("ghost"), errors.New("seat not found"), "seat not found"},
	}
	for _, tc := range cases {
		c, _ := newCallSeatControllerForTest(&fakeAuth{id: "u"}, nil, tc.resolverErr)
		resp := c.CallSeat(context.Background(), tc.room, tc.seat, nil)
		if field(t, resp, "success") != false {
			t.Errorf("%s: response = %v", tc.name, resp)
			continue
		}
		if got, _ := field(t, resp, "error").(string); !strings.Contains(got, tc.wantContains) {
			t.Errorf("%s: error = %q, want it to mention %q", tc.name, got, tc.wantContains)
		}
	}
}

func TestCallSeatAuthFailure(t *testing.T) {
	c, resolver := newCallSeatControllerForTest(&fakeAuth{err: errors.New("no token")}, &repositories.ResolvedSeat{}, nil)
	resp := c.CallSeat(context.Background(), ptr("4genthub-dev"), ptr("lead"), nil)
	if field(t, resp, "success") != false || field(t, resp, "error") != "no token" {
		t.Errorf("auth failure = %v", resp)
	}
	if resolver.gotRoom != "" {
		t.Errorf("the resolver ran without a tenant: %s", resolver.gotRoom)
	}
}

func TestCallSeatRegisterTools(t *testing.T) {
	c, _ := newCallSeatControllerForTest(&fakeAuth{id: "u"}, &repositories.ResolvedSeat{}, nil)
	server := &recordingServer{}
	c.RegisterTools(server)
	if server.name != "call_seat" || server.description != CallSeatToolDescription || server.fn == nil {
		t.Fatalf("registered %+v", server)
	}
	c.RegisterTools(nil)
}

func TestCallSeatInputSchema(t *testing.T) {
	schema := CallSeatInputSchema()
	props, _ := field(t, schema, "properties").(*tmentities.OrderedMap[any])
	want := []string{"room", "seat", "user_id"}
	if got := props.Keys(); len(got) != len(want) {
		t.Fatalf("properties = %v", got)
	}
	for i, key := range want {
		if props.Keys()[i] != key {
			t.Errorf("property %d = %s, want %s", i, props.Keys()[i], key)
		}
	}
	required, _ := field(t, schema, "required").([]any)
	if len(required) != 2 || required[0] != "room" || required[1] != "seat" {
		t.Errorf("required = %v, want room and seat", field(t, schema, "required"))
	}
}
