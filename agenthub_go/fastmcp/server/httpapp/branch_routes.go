package httpapp

import (
	"encoding/json"
	"net/http"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	"agenthub/fastmcp/auth/middleware"
	"agenthub/fastmcp/server/routes"
)

// authed is Depends(get_current_user) around a handler.
func authed(h func(w http.ResponseWriter, r *http.Request, u *authdomain.User)) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if u, ok := currentUser(w, r); ok {
			h(w, withAuthContext(r, u), u)
		}
	}
}

// withAuthContext is what DualAuthMiddleware + RequestContextMiddleware leave on the request
// for an authenticated user: the context-var values the facades read (get_current_user_id).
func withAuthContext(r *http.Request, u *authdomain.User) *http.Request {
	info := map[string]any{}
	if u.Email != "" {
		info["email"] = u.Email
	}
	state := middleware.AuthState{UserID: u.ID, AuthInfo: info}
	return r.WithContext(middleware.WithRequestAuthContext(r.Context(), middleware.CaptureAuthContextFromState(state)))
}

// userID is current_user.id.
func userID(u *authdomain.User) string {
	if u == nil || u.ID == nil {
		return ""
	}
	return *u.ID
}

// queryOpt is an optional FastAPI query parameter (nil when absent).
func queryOpt(r *http.Request, key string) *string {
	if !r.URL.Query().Has(key) {
		return nil
	}
	v := r.URL.Query().Get(key)
	return &v
}

// queryReq is a required FastAPI query parameter; absent yields a 422.
func queryReq(w http.ResponseWriter, r *http.Request, key string) (string, bool) {
	if !r.URL.Query().Has(key) {
		writeMissing(w, "query", key)
		return "", false
	}
	return r.URL.Query().Get(key), true
}

func (a *App) registerBranchRoutes(mux *http.ServeMux) {
	const base = "/api/v2/branches"
	c := a.branches
	mux.HandleFunc("POST "+base+"/{$}", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		_ = r.ParseForm()
		if miss := missingForm(r, "project_id", "git_branch_name"); len(miss) > 0 {
			writeMissing(w, "body", miss...)
			return
		}
		body, err := routes.CreateBranch(r.Context(), r.PostForm.Get("project_id"), r.PostForm.Get("git_branch_name"), r.PostForm.Get("description"), userID(u), c)
		writeResult(w, body, err)
	}))
	mux.HandleFunc("GET "+base+"/{id}", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		body, err := routes.GetBranch(r.Context(), r.PathValue("id"), userID(u), c)
		writeResult(w, body, err)
	}))
	mux.HandleFunc("DELETE "+base+"/{id}", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		body, err := routes.DeleteBranch(r.Context(), r.PathValue("id"), userID(u), c)
		writeResult(w, body, err)
	}))
	mux.HandleFunc("POST "+base+"/project/{project_id}/summaries", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		body, err := routes.GetProjectBranchesWithTaskCounts(r.Context(), r.PathValue("project_id"), userID(u), c)
		writeResult(w, body, err)
	}))
	mux.HandleFunc("POST "+base+"/summaries/bulk", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		var req struct {
			ProjectIDs      []string `json:"project_ids"`
			IncludeArchived bool     `json:"include_archived"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			writeDetail(w, http.StatusUnprocessableEntity, "Invalid JSON body")
			return
		}
		body, err := routes.GetBulkSummaries(r.Context(), routes.BulkSummaryRequest{ProjectIDs: req.ProjectIDs, IncludeArchived: req.IncludeArchived}, userID(u), c)
		writeResult(w, body, err)
	}))
}
