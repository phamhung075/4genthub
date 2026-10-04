package httpapp

import (
	"net/http"
	"strconv"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	"agenthub/fastmcp/server/routes"
)

func (a *App) registerSessionStreamRoutes(mux *http.ServeMux) {
	const base = "/api/v2/sessions"

	mux.HandleFunc("GET "+base, authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		res, err := routes.ListSessions(r.Context(), u, a.Sessions)
		writeKeyedSliceResult(w, "sessions", res, err)
	}))

	mux.HandleFunc("GET "+base+"/{id}/events", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		sessionID := r.PathValue("id")
		afterSeq := 0
		if q := r.URL.Query().Get("after_seq"); q != "" {
			if n, err := strconv.Atoi(q); err == nil {
				afterSeq = n
			}
		}
		limit := 500
		if q := r.URL.Query().Get("limit"); q != "" {
			if n, err := strconv.Atoi(q); err == nil {
				limit = n
			}
		}
		res, err := routes.GetSessionEvents(r.Context(), sessionID, afterSeq, limit, u, a.Sessions)
		writeKeyedSliceResult(w, "events", res, err)
	}))
}
