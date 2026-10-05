package httpapp

// team_mount.go serves the team boundary (NEXT_GEN D5, slice 1):
//
//	POST   /api/v2/openrig/teams
//	GET    /api/v2/openrig/teams
//	GET    /api/v2/openrig/teams/{team}
//	DELETE /api/v2/openrig/teams/{team}
//	GET    /api/v2/openrig/teams/{team}/members
//	POST   /api/v2/openrig/teams/{team}/members
//	PATCH  /api/v2/openrig/teams/{team}/members/{user}
//	DELETE /api/v2/openrig/teams/{team}/members/{user}
//
// `{team}` is the team SLUG (the OpenRig convention the room routes use), looked up within
// the caller's memberships: a slug is unique per owner, not globally.
//
// A team is the account boundary its members share. Slice 1 is single-owner: the creator
// is the one owner, every membership change is owner-only, and every other member is a
// viewer with read access. Every route is authed and filtered by the caller's membership.

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"time"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/infrastructure/database"
	teamservices "agenthub/fastmcp/team_management/application/services"
	teamrepos "agenthub/fastmcp/team_management/domain/repositories"
	teamorm "agenthub/fastmcp/team_management/infrastructure/repositories/orm"
)

// teamSource is the team use-case surface these routes use.
type teamSource interface {
	Create(ctx context.Context, ownerUserID, slug, name string) (*teamrepos.Team, error)
	List(ctx context.Context, userID string) ([]teamrepos.Membership, error)
	Get(ctx context.Context, userID, teamID string) (*teamrepos.Team, string, error)
	Delete(ctx context.Context, userID, teamID string) error
	ListMembers(ctx context.Context, userID, teamID string) ([]teamrepos.TeamMember, error)
	AddMember(ctx context.Context, actorUserID, teamID, memberUserID, role string) (*teamrepos.TeamMember, error)
	UpdateMemberRole(ctx context.Context, actorUserID, teamID, memberUserID, role string) (*teamrepos.TeamMember, error)
	RemoveMember(ctx context.Context, actorUserID, teamID, memberUserID string) error
}

// newTeamSource is a package variable so tests can substitute a fake without a database.
var newTeamSource = func(sessions *database.SessionManager) (teamSource, error) {
	repo, err := teamorm.NewORMTeamRepository(sessions)
	if err != nil {
		return nil, err
	}
	return teamservices.NewTeamService(repo), nil
}

type teamCreateRequest struct {
	Slug string `json:"slug"`
	Name string `json:"name"`
}

type teamMemberAddRequest struct {
	UserID string `json:"user_id"`
	Role   string `json:"role"`
}

type teamMemberRoleRequest struct {
	Role string `json:"role"`
}

func mountTeamRoutes(mux *http.ServeMux, sessions *database.SessionManager) {
	mux.HandleFunc("POST /api/v2/openrig/teams", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleCreateTeam(w, r, u, sessions)
	}))
	mux.HandleFunc("GET /api/v2/openrig/teams", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleListTeams(w, r, u, sessions)
	}))
	mux.HandleFunc("GET /api/v2/openrig/teams/{team}", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleGetTeam(w, r, u, sessions)
	}))
	mux.HandleFunc("DELETE /api/v2/openrig/teams/{team}", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleDeleteTeam(w, r, u, sessions)
	}))
	mux.HandleFunc("GET /api/v2/openrig/teams/{team}/members", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleListTeamMembers(w, r, u, sessions)
	}))
	mux.HandleFunc("POST /api/v2/openrig/teams/{team}/members", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleAddTeamMember(w, r, u, sessions)
	}))
	mux.HandleFunc("PATCH /api/v2/openrig/teams/{team}/members/{user}", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleUpdateTeamMember(w, r, u, sessions)
	}))
	mux.HandleFunc("DELETE /api/v2/openrig/teams/{team}/members/{user}", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleRemoveTeamMember(w, r, u, sessions)
	}))
}

// teamSourceFor builds the team use cases over the request's sessions.
func teamSourceFor(w http.ResponseWriter, sessions *database.SessionManager) (teamSource, bool) {
	source, err := newTeamSource(sessions)
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return nil, false
	}
	return source, true
}

// decodeTeamBody decodes a JSON body, rejecting unknown fields.
func decodeTeamBody(w http.ResponseWriter, r *http.Request, dst any) bool {
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(dst); err != nil {
		writeDetail(w, http.StatusBadRequest, err.Error())
		return false
	}
	return true
}

// writeTeamError maps a team use-case error to its HTTP status.
func writeTeamError(w http.ResponseWriter, err error) {
	var validation *teamservices.ValidationError
	switch {
	case errors.As(err, &validation):
		writeDetail(w, http.StatusBadRequest, validation.Error())
	case errors.Is(err, teamrepos.ErrTeamNotFound):
		writeDetail(w, http.StatusNotFound, teamrepos.ErrTeamNotFound.Error())
	case errors.Is(err, teamrepos.ErrTeamExists),
		errors.Is(err, teamrepos.ErrMemberExists),
		errors.Is(err, teamservices.ErrSecondOwner),
		errors.Is(err, teamservices.ErrLastOwner):
		writeDetail(w, http.StatusConflict, err.Error())
	case errors.Is(err, teamservices.ErrNotTeamOwner):
		writeDetail(w, http.StatusForbidden, err.Error())
	default:
		writeDetail(w, http.StatusInternalServerError, err.Error())
	}
}

func handleCreateTeam(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	var req teamCreateRequest
	if !decodeTeamBody(w, r, &req) {
		return
	}
	source, ok := teamSourceFor(w, sessions)
	if !ok {
		return
	}
	team, err := source.Create(r.Context(), userID(u), req.Slug, req.Name)
	if err != nil {
		writeTeamError(w, err)
		return
	}
	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	body.Set("team", teamBody(team))
	body.Set("role", teamrepos.RoleOwner)
	writeJSON(w, http.StatusOK, body)
}

func handleListTeams(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	source, ok := teamSourceFor(w, sessions)
	if !ok {
		return
	}
	memberships, err := source.List(r.Context(), userID(u))
	if err != nil {
		writeTeamError(w, err)
		return
	}
	out := make([]any, 0, len(memberships))
	for i := range memberships {
		entry := entities.NewOrderedMap[any]()
		entry.Set("team", teamBody(&memberships[i].Team))
		entry.Set("role", memberships[i].Role)
		out = append(out, entry)
	}
	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	body.Set("teams", out)
	writeJSON(w, http.StatusOK, body)
}

func handleGetTeam(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	source, ok := teamSourceFor(w, sessions)
	if !ok {
		return
	}
	team, role, err := source.Get(r.Context(), userID(u), r.PathValue("team"))
	if err != nil {
		writeTeamError(w, err)
		return
	}
	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	body.Set("team", teamBody(team))
	body.Set("role", role)
	writeJSON(w, http.StatusOK, body)
}

func handleDeleteTeam(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	source, ok := teamSourceFor(w, sessions)
	if !ok {
		return
	}
	if err := source.Delete(r.Context(), userID(u), r.PathValue("team")); err != nil {
		writeTeamError(w, err)
		return
	}
	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	body.Set("team", r.PathValue("team"))
	writeJSON(w, http.StatusOK, body)
}

func handleListTeamMembers(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	source, ok := teamSourceFor(w, sessions)
	if !ok {
		return
	}
	members, err := source.ListMembers(r.Context(), userID(u), r.PathValue("team"))
	if err != nil {
		writeTeamError(w, err)
		return
	}
	out := make([]any, 0, len(members))
	for i := range members {
		out = append(out, teamMemberBody(&members[i]))
	}
	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	body.Set("members", out)
	writeJSON(w, http.StatusOK, body)
}

func handleAddTeamMember(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	var req teamMemberAddRequest
	if !decodeTeamBody(w, r, &req) {
		return
	}
	source, ok := teamSourceFor(w, sessions)
	if !ok {
		return
	}
	member, err := source.AddMember(r.Context(), userID(u), r.PathValue("team"), req.UserID, req.Role)
	if err != nil {
		writeTeamError(w, err)
		return
	}
	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	body.Set("member", teamMemberBody(member))
	writeJSON(w, http.StatusOK, body)
}

func handleUpdateTeamMember(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	var req teamMemberRoleRequest
	if !decodeTeamBody(w, r, &req) {
		return
	}
	source, ok := teamSourceFor(w, sessions)
	if !ok {
		return
	}
	member, err := source.UpdateMemberRole(r.Context(), userID(u), r.PathValue("team"), r.PathValue("user"), req.Role)
	if err != nil {
		writeTeamError(w, err)
		return
	}
	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	body.Set("member", teamMemberBody(member))
	writeJSON(w, http.StatusOK, body)
}

func handleRemoveTeamMember(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	source, ok := teamSourceFor(w, sessions)
	if !ok {
		return
	}
	if err := source.RemoveMember(r.Context(), userID(u), r.PathValue("team"), r.PathValue("user")); err != nil {
		writeTeamError(w, err)
		return
	}
	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	body.Set("user", r.PathValue("user"))
	writeJSON(w, http.StatusOK, body)
}

func teamBody(team *teamrepos.Team) *entities.OrderedMap[any] {
	body := entities.NewOrderedMap[any]()
	body.Set("id", team.ID)
	body.Set("slug", team.Slug)
	body.Set("name", team.Name)
	body.Set("owner_user_id", team.UserID)
	body.Set("created_at", team.CreatedAt.UTC().Format(time.RFC3339))
	body.Set("updated_at", team.UpdatedAt.UTC().Format(time.RFC3339))
	return body
}

func teamMemberBody(member *teamrepos.TeamMember) *entities.OrderedMap[any] {
	body := entities.NewOrderedMap[any]()
	body.Set("id", member.ID)
	body.Set("team_id", member.TeamID)
	body.Set("user_id", member.UserID)
	body.Set("role", member.Role)
	body.Set("created_at", member.CreatedAt.UTC().Format(time.RFC3339))
	return body
}
