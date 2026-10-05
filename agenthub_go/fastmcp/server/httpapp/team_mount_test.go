package httpapp

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/infrastructure/database"
	teamservices "agenthub/fastmcp/team_management/application/services"
	teamrepos "agenthub/fastmcp/team_management/domain/repositories"
)

// fakeTeamSource returns canned results and records the arguments the mount passes. The
// membership rules themselves are covered by the service unit tests; here the subject is
// the HTTP surface: status codes, body shape, and the acting user reaching the source.
type fakeTeamSource struct {
	team    *teamrepos.Team
	role    string
	teams   []teamrepos.Membership
	members []teamrepos.TeamMember
	member  *teamrepos.TeamMember
	err     error

	actor, teamID, memberUser, roleArg, slug, name string
}

func (f *fakeTeamSource) Create(_ context.Context, ownerUserID, slug, name string) (*teamrepos.Team, error) {
	f.actor, f.slug, f.name = ownerUserID, slug, name
	return f.team, f.err
}

func (f *fakeTeamSource) List(_ context.Context, userID string) ([]teamrepos.Membership, error) {
	f.actor = userID
	return f.teams, f.err
}

func (f *fakeTeamSource) Get(_ context.Context, userID, teamID string) (*teamrepos.Team, string, error) {
	f.actor, f.teamID = userID, teamID
	return f.team, f.role, f.err
}

func (f *fakeTeamSource) Delete(_ context.Context, userID, teamID string) error {
	f.actor, f.teamID = userID, teamID
	return f.err
}

func (f *fakeTeamSource) ListMembers(_ context.Context, userID, teamID string) ([]teamrepos.TeamMember, error) {
	f.actor, f.teamID = userID, teamID
	return f.members, f.err
}

func (f *fakeTeamSource) AddMember(_ context.Context, actorUserID, teamID, memberUserID, role string) (*teamrepos.TeamMember, error) {
	f.actor, f.teamID, f.memberUser, f.roleArg = actorUserID, teamID, memberUserID, role
	return f.member, f.err
}

func (f *fakeTeamSource) UpdateMemberRole(_ context.Context, actorUserID, teamID, memberUserID, role string) (*teamrepos.TeamMember, error) {
	f.actor, f.teamID, f.memberUser, f.roleArg = actorUserID, teamID, memberUserID, role
	return f.member, f.err
}

func (f *fakeTeamSource) RemoveMember(_ context.Context, actorUserID, teamID, memberUserID string) error {
	f.actor, f.teamID, f.memberUser = actorUserID, teamID, memberUserID
	return f.err
}

// teamTestUser is the authenticated caller authenticateTestUser installs.
const teamTestUser = "11111111-1111-4111-8111-111111111111"

func teamTestMux(t *testing.T, src teamSource) *http.ServeMux {
	t.Helper()
	previous := newTeamSource
	newTeamSource = func(*database.SessionManager) (teamSource, error) { return src, nil }
	t.Cleanup(func() { newTeamSource = previous })
	authenticateTestUser(t)
	mux := http.NewServeMux()
	mountTeamRoutes(mux, nil)
	return mux
}

func teamDo(mux *http.ServeMux, method, path, body string, withAuth bool) *httptest.ResponseRecorder {
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	if withAuth {
		req.Header.Set("Authorization", "Bearer user-jwt")
	}
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)
	return rec
}

func TestTeamRoutesRequireAuth(t *testing.T) {
	mux := teamTestMux(t, &fakeTeamSource{})
	for _, c := range []struct{ method, path string }{
		{http.MethodPost, "/api/v2/openrig/teams"},
		{http.MethodGet, "/api/v2/openrig/teams"},
		{http.MethodGet, "/api/v2/openrig/teams/eng"},
		{http.MethodDelete, "/api/v2/openrig/teams/eng"},
		{http.MethodGet, "/api/v2/openrig/teams/eng/members"},
		{http.MethodPost, "/api/v2/openrig/teams/eng/members"},
		{http.MethodPatch, "/api/v2/openrig/teams/eng/members/bob"},
		{http.MethodDelete, "/api/v2/openrig/teams/eng/members/bob"},
	} {
		rec := teamDo(mux, c.method, c.path, `{}`, false)
		if rec.Code != http.StatusForbidden {
			t.Errorf("%s %s without a bearer = %d, want 403", c.method, c.path, rec.Code)
		}
	}
}

func TestTeamRoutesCreateAndList(t *testing.T) {
	src := &fakeTeamSource{team: &teamrepos.Team{ID: "t1", Slug: "eng", Name: "Engineering", UserID: teamTestUser}}
	mux := teamTestMux(t, src)

	rec := teamDo(mux, http.MethodPost, "/api/v2/openrig/teams", `{"slug":"eng","name":"Engineering"}`, true)
	if rec.Code != http.StatusOK {
		t.Fatalf("create = %d %s", rec.Code, rec.Body.String())
	}
	if src.actor != teamTestUser || src.slug != "eng" || src.name != "Engineering" {
		t.Errorf("create args = %q %q %q", src.actor, src.slug, src.name)
	}
	var body map[string]any
	if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	if body["success"] != true || body["role"] != teamrepos.RoleOwner {
		t.Errorf("create body = %v", body)
	}
	if team, _ := body["team"].(map[string]any); team["slug"] != "eng" || team["id"] != "t1" {
		t.Errorf("create team = %v", body["team"])
	}

	src.teams = []teamrepos.Membership{{Team: teamrepos.Team{ID: "t1", Slug: "eng"}, Role: teamrepos.RoleViewer}}
	rec = teamDo(mux, http.MethodGet, "/api/v2/openrig/teams", "", true)
	if rec.Code != http.StatusOK {
		t.Fatalf("list = %d %s", rec.Code, rec.Body.String())
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	rows, _ := body["teams"].([]any)
	if len(rows) != 1 {
		t.Fatalf("list teams = %v", body["teams"])
	}
}

func TestTeamRoutesErrorMapping(t *testing.T) {
	cases := []struct {
		name string
		err  error
		want int
	}{
		{"not found", teamrepos.ErrTeamNotFound, http.StatusNotFound},
		{"team exists", teamrepos.ErrTeamExists, http.StatusConflict},
		{"member exists", teamrepos.ErrMemberExists, http.StatusConflict},
		{"team has owner", teamrepos.ErrTeamHasOwner, http.StatusConflict},
		{"second owner", teamservices.ErrSecondOwner, http.StatusConflict},
		{"last owner", teamservices.ErrLastOwner, http.StatusConflict},
		{"not owner", teamservices.ErrNotTeamOwner, http.StatusForbidden},
		{"validation", &teamservices.ValidationError{Msg: "team slug \"x.y\" must match"}, http.StatusBadRequest},
		{"internal", errors.New("boom"), http.StatusInternalServerError},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			mux := teamTestMux(t, &fakeTeamSource{err: c.err})
			rec := teamDo(mux, http.MethodGet, "/api/v2/openrig/teams/eng", "", true)
			if rec.Code != c.want {
				t.Fatalf("status = %d, want %d (%s)", rec.Code, c.want, rec.Body.String())
			}
		})
	}
}

func TestTeamRoutesPassTheActingUserAndPathValues(t *testing.T) {
	src := &fakeTeamSource{member: &teamrepos.TeamMember{ID: "m1", TeamID: "t1", UserID: "bob", Role: teamrepos.RoleViewer}}
	mux := teamTestMux(t, src)

	rec := teamDo(mux, http.MethodPatch, "/api/v2/openrig/teams/t1/members/bob", `{"role":"viewer"}`, true)
	if rec.Code != http.StatusOK {
		t.Fatalf("patch = %d %s", rec.Code, rec.Body.String())
	}
	if src.actor != teamTestUser || src.teamID != "t1" || src.memberUser != "bob" || src.roleArg != "viewer" {
		t.Errorf("patch args = actor=%q team=%q member=%q role=%q", src.actor, src.teamID, src.memberUser, src.roleArg)
	}

	rec = teamDo(mux, http.MethodDelete, "/api/v2/openrig/teams/t1/members/bob", "", true)
	if rec.Code != http.StatusOK {
		t.Fatalf("delete = %d %s", rec.Code, rec.Body.String())
	}
	if src.actor != teamTestUser || src.teamID != "t1" || src.memberUser != "bob" {
		t.Errorf("delete args = actor=%q team=%q member=%q", src.actor, src.teamID, src.memberUser)
	}
}

func TestTeamRoutesRejectUnknownBodyFields(t *testing.T) {
	mux := teamTestMux(t, &fakeTeamSource{team: &teamrepos.Team{ID: "t1", Slug: "eng"}})
	rec := teamDo(mux, http.MethodPost, "/api/v2/openrig/teams", `{"slug":"eng","name":"Engineering","extra":1}`, true)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("unknown field = %d, want 400", rec.Code)
	}
}
