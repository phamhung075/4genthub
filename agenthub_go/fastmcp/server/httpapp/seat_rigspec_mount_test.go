package httpapp

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"sort"
	"strings"
	"testing"

	"agenthub/fastmcp/seat_management/domain/repositories"
	"agenthub/fastmcp/task_management/infrastructure/database"

	"gopkg.in/yaml.v3"
)

type fakeSeatRigSpec struct {
	rooms      map[string]*repositories.Room
	seats      []*repositories.Seat
	links      map[string][]*repositories.SeatLink
	resolved   map[string]*repositories.ResolvedSeat
	roomErr    error
	resolveErr error
}

func (f *fakeSeatRigSpec) GetRoomBySlug(_ context.Context, _, slug string) (*repositories.Room, error) {
	if f.roomErr != nil {
		return nil, f.roomErr
	}
	return f.rooms[slug], nil
}

func (f *fakeSeatRigSpec) ListSeatsByRoom(_ context.Context, _, roomID string) ([]repositories.Seat, error) {
	out := make([]repositories.Seat, 0)
	for _, s := range f.seats {
		if s.RoomID == roomID {
			out = append(out, *s)
		}
	}
	return out, nil
}

func (f *fakeSeatRigSpec) ResolveSeat(_ context.Context, _, _, seatKey string) (*repositories.ResolvedSeat, error) {
	if f.resolveErr != nil {
		return nil, f.resolveErr
	}
	return f.resolved[seatKey], nil
}

func (f *fakeSeatRigSpec) ListSeatLinksFrom(_ context.Context, _, seatID string) ([]repositories.SeatLink, error) {
	out := make([]repositories.SeatLink, 0)
	for _, l := range f.links[seatID] {
		out = append(out, *l)
	}
	return out, nil
}

func (f *fakeSeatRigSpec) GetSeatByID(_ context.Context, _, seatID string) (*repositories.Seat, error) {
	for _, s := range f.seats {
		if s.ID == seatID {
			return s, nil
		}
	}
	return nil, nil
}

func seatRigSpecTestMux(t *testing.T, source seatRigSpecSource) *http.ServeMux {
	t.Helper()
	previous := newSeatRigSpecSource
	newSeatRigSpecSource = func(*database.SessionManager, string) (seatRigSpecSource, error) { return source, nil }
	t.Cleanup(func() { newSeatRigSpecSource = previous })
	authenticateAgentsTestUser(t)
	mux := http.NewServeMux()
	mountSeatRigSpecRoutes(mux, nil)
	return mux
}

type rigSpecHTTPResponse struct {
	Success bool `json:"success"`
	RigSpec struct {
		Name  string `json:"name"`
		YAML  string `json:"yaml"`
		Seats []struct {
			Seat string `json:"seat"`
			Hash string `json:"hash"`
		} `json:"seats"`
	} `json:"rigspec"`
}

type parsedRigDoc struct {
	Pods []struct {
		ID      string `yaml:"id"`
		Members []struct {
			ID       string `yaml:"id"`
			AgentRef string `yaml:"agent_ref"`
		} `yaml:"members"`
		Edges []struct {
			Kind string `yaml:"kind"`
			From string `yaml:"from"`
			To   string `yaml:"to"`
		} `yaml:"edges"`
	} `yaml:"pods"`
}

func decodeRigSpec(t *testing.T, rec *httptest.ResponseRecorder) rigSpecHTTPResponse {
	t.Helper()
	var body rigSpecHTTPResponse
	if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil {
		t.Fatalf("decode response: %v\n%s", err, rec.Body.String())
	}
	return body
}

func TestRoomRigSpecRendersSeatsEdgesAndHashes(t *testing.T) {
	t.Setenv(publicURLEnv, "https://api.example.test")
	room := &repositories.Room{ID: "room-dev", Slug: "dev", Name: "Development"}
	fake := &fakeSeatRigSpec{
		rooms: map[string]*repositories.Room{"dev": room},
		seats: []*repositories.Seat{
			{ID: "seat-lead", RoomID: "room-dev", SeatKey: "lead", Runtime: "claude-code", PermissionPolicy: "standard"},
			{ID: "seat-dev", RoomID: "room-dev", SeatKey: "dev", Runtime: "codex", Model: "gpt-5", PermissionPolicy: "standard"},
			{ID: "seat-qa", RoomID: "room-dev", SeatKey: "qa", Runtime: "claude-code", PermissionPolicy: "standard"},
		},
		links: map[string][]*repositories.SeatLink{
			"seat-lead": {
				{FromSeatID: "seat-lead", ToSeatID: "seat-dev", Kind: "delegates_to", Allow: true},
				{FromSeatID: "seat-lead", ToSeatID: "seat-qa", Kind: "can_observe", Allow: true},
				{FromSeatID: "seat-lead", ToSeatID: "seat-ghost", Kind: "delegates_to", Allow: true},
			},
			"seat-dev": {
				{FromSeatID: "seat-dev", ToSeatID: "seat-lead", Kind: "delegates_to", Allow: false},
			},
			"seat-qa": {
				{FromSeatID: "seat-qa", ToSeatID: "seat-lead", Kind: "escalates_to", Allow: true},
			},
		},
		resolved: map[string]*repositories.ResolvedSeat{
			"lead": {SeatID: "seat-lead", Hash: "h-lead", Runtime: "claude-code"},
			"dev":  {SeatID: "seat-dev", Hash: "h-dev", Runtime: "codex"},
			"qa":   {SeatID: "seat-qa", Hash: "h-qa", Runtime: "claude-code"},
		},
	}
	mux := seatRigSpecTestMux(t, fake)

	rec := doAgentsRequest(t, mux, http.MethodGet, "/api/v2/openrig/rooms/dev/rigspec", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d: %s", rec.Code, rec.Body.String())
	}
	body := decodeRigSpec(t, rec)
	if !body.Success || body.RigSpec.Name != "dev" {
		t.Fatalf("success/name = %v/%q: %s", body.Success, body.RigSpec.Name, rec.Body.String())
	}

	hashes := map[string]string{}
	for _, s := range body.RigSpec.Seats {
		hashes[s.Seat] = s.Hash
	}
	if len(hashes) != 3 {
		t.Fatalf("seats = %+v, want only the three active seats", body.RigSpec.Seats)
	}
	for _, want := range []struct{ seat, hash string }{{"lead", "h-lead"}, {"dev", "h-dev"}, {"qa", "h-qa"}} {
		if hashes[want.seat] != want.hash {
			t.Errorf("hash[%s] = %q, want %q", want.seat, hashes[want.seat], want.hash)
		}
	}

	sort.Slice(body.RigSpec.Seats, func(i, j int) bool { return body.RigSpec.Seats[i].Seat < body.RigSpec.Seats[j].Seat })
	if body.RigSpec.Seats[0].Seat != "dev" || body.RigSpec.Seats[2].Seat != "qa" {
		t.Errorf("seats not sorted by key: %+v", body.RigSpec.Seats)
	}

	var doc parsedRigDoc
	if err := yaml.Unmarshal([]byte(body.RigSpec.YAML), &doc); err != nil {
		t.Fatalf("parse rendered yaml: %v\n%s", err, body.RigSpec.YAML)
	}
	if len(doc.Pods) != 1 || doc.Pods[0].ID != "dev" {
		t.Fatalf("pods = %+v", doc.Pods)
	}
	memberIDs := make([]string, len(doc.Pods[0].Members))
	for i, m := range doc.Pods[0].Members {
		memberIDs[i] = m.ID
	}
	wantMembers := []string{"dev", "lead", "qa"}
	if strings.Join(memberIDs, ",") != strings.Join(wantMembers, ",") {
		t.Fatalf("members = %v, want %v", memberIDs, wantMembers)
	}
	for _, m := range doc.Pods[0].Members {
		if m.AgentRef != "local:agents/"+m.ID {
			t.Errorf("member %s agent_ref = %q", m.ID, m.AgentRef)
		}
	}
	wantEdges := []struct{ Kind, From, To string }{
		{"can_observe", "lead", "qa"},
		{"delegates_to", "lead", "dev"},
		{"escalates_to", "qa", "lead"},
	}
	if len(doc.Pods[0].Edges) != len(wantEdges) {
		t.Fatalf("edges = %+v, want %+v", doc.Pods[0].Edges, wantEdges)
	}
	for i, want := range wantEdges {
		got := doc.Pods[0].Edges[i]
		if got.Kind != want.Kind || got.From != want.From || got.To != want.To {
			t.Fatalf("edge %d = %+v, want %+v", i, got, want)
		}
	}
	if strings.Contains(body.RigSpec.YAML, "ghost") {
		t.Errorf("removed seat leaked into the rig spec:\n%s", body.RigSpec.YAML)
	}
}

func TestRoomRigSpecAbsentRoomAndNoActiveSeats(t *testing.T) {
	t.Setenv(publicURLEnv, "https://api.example.test")

	empty := &fakeSeatRigSpec{rooms: map[string]*repositories.Room{}}
	mux := seatRigSpecTestMux(t, empty)
	if rec := doAgentsRequest(t, mux, http.MethodGet, "/api/v2/openrig/rooms/ghost/rigspec", ""); rec.Code != http.StatusNotFound {
		t.Errorf("absent room: status = %d, want 404: %s", rec.Code, rec.Body.String())
	}

	room := &repositories.Room{ID: "room-dev", Slug: "dev", Name: "Development"}
	none := &fakeSeatRigSpec{rooms: map[string]*repositories.Room{"dev": room}}
	mux = seatRigSpecTestMux(t, none)
	rec := doAgentsRequest(t, mux, http.MethodGet, "/api/v2/openrig/rooms/dev/rigspec", "")
	if rec.Code != http.StatusConflict {
		t.Fatalf("empty room: status = %d, want 409: %s", rec.Code, rec.Body.String())
	}
	if !strings.Contains(rec.Body.String(), "room has no seats") {
		t.Errorf("empty room message = %s", rec.Body.String())
	}
}

func TestRoomRigSpecNeedsPublicURLAndAuth(t *testing.T) {
	t.Setenv(publicURLEnv, "")
	mux := seatRigSpecTestMux(t, &fakeSeatRigSpec{})
	if rec := doAgentsRequest(t, mux, http.MethodGet, "/api/v2/openrig/rooms/dev/rigspec", ""); rec.Code != http.StatusInternalServerError {
		t.Errorf("without %s: status = %d", publicURLEnv, rec.Code)
	}

	t.Setenv(publicURLEnv, "https://api.example.test")
	bare := http.NewServeMux()
	mountSeatRigSpecRoutes(bare, nil)
	rec := httptest.NewRecorder()
	bare.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/api/v2/openrig/rooms/dev/rigspec", nil))
	if rec.Code == http.StatusNotFound || rec.Code == http.StatusOK {
		t.Errorf("unauthenticated request: status = %d, want 401/403", rec.Code)
	}
}

// Each member carries its own seat's policy; there is no request-level override.
func TestRoomRigSpecRendersPermissionPolicyPerSeat(t *testing.T) {
	t.Setenv(publicURLEnv, "https://api.example.test")
	room := &repositories.Room{ID: "room-dev", Slug: "dev", Name: "Development"}
	fake := &fakeSeatRigSpec{
		rooms: map[string]*repositories.Room{"dev": room},
		seats: []*repositories.Seat{
			{ID: "seat-lead", RoomID: "room-dev", SeatKey: "lead", Runtime: "claude-code", PermissionPolicy: "standard"},
			{ID: "seat-dev", RoomID: "room-dev", SeatKey: "dev", Runtime: "codex", PermissionPolicy: "yolo"},
			{ID: "seat-qa", RoomID: "room-dev", SeatKey: "qa", Runtime: "claude-code", PermissionPolicy: "none"},
		},
		resolved: map[string]*repositories.ResolvedSeat{
			"lead": {SeatID: "seat-lead", Hash: "h-lead", Runtime: "claude-code"},
			"dev":  {SeatID: "seat-dev", Hash: "h-dev", Runtime: "codex"},
			"qa":   {SeatID: "seat-qa", Hash: "h-qa", Runtime: "claude-code"},
		},
	}
	mux := seatRigSpecTestMux(t, fake)
	const path = "/api/v2/openrig/rooms/dev/rigspec"

	rec := doAgentsRequest(t, mux, http.MethodGet, path, "")
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d: %s", rec.Code, rec.Body.String())
	}
	doc := decodeRigSpec(t, rec).RigSpec.YAML
	for member, line := range map[string]string{
		"dev":  "id: dev\n        agent_ref: local:agents/dev\n        profile: default\n        runtime: codex\n        cwd: .\n        permission_policy: builtin:yolo\n",
		"lead": "id: lead\n        agent_ref: local:agents/lead\n        profile: default\n        runtime: claude-code\n        cwd: .\n        permission_policy: builtin:standard\n",
		"qa":   "id: qa\n        agent_ref: local:agents/qa\n        profile: default\n        runtime: claude-code\n        cwd: .\n        permission_policy: none\n",
	} {
		if !strings.Contains(doc, line) {
			t.Errorf("member %s does not carry its own policy:\n%s", member, doc)
		}
	}
	if strings.Count(doc, "permission_policy") != 3 || strings.Contains(doc, "\nname: dev\npermission_policy") {
		t.Errorf("want exactly one policy line per member and none on the rig:\n%s", doc)
	}

	// The old request-level override is gone: the query string changes nothing.
	again := doAgentsRequest(t, mux, http.MethodGet, path+"?permission_policy=yolo", "")
	if again.Code != http.StatusOK || decodeRigSpec(t, again).RigSpec.YAML != doc {
		t.Errorf("a permission_policy query changed the render: %d", again.Code)
	}
}
