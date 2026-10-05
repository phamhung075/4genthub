package httpapp

import (
	"net/http"
	"strconv"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	"agenthub/fastmcp/server/routes"
)

func (a *App) registerSubtaskRoutes(mux *http.ServeMux) {
	const base = "/api/v2/subtasks"
	c := a.subtasks
	mux.HandleFunc("POST "+base, authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		var missing []string
		for _, f := range []string{"task_id", "title"} {
			if !r.URL.Query().Has(f) {
				missing = append(missing, f)
			}
		}
		if len(missing) > 0 {
			writeMissing(w, "query", missing...)
			return
		}
		body, err := routes.CreateSubtask(r.Context(), r.URL.Query().Get("task_id"), r.URL.Query().Get("title"), queryOpt(r, "description"), u, c)
		writeResult(w, body, err)
	}))
	mux.HandleFunc("GET "+base+"/task/{id}", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		body, err := routes.ListSubtasks(r.Context(), r.PathValue("id"), u, c)
		writeResult(w, body, err)
	}))
	mux.HandleFunc("GET "+base+"/{id}", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		body, err := routes.GetSubtask(r.Context(), r.PathValue("id"), u, c)
		writeResult(w, body, err)
	}))
	mux.HandleFunc("PUT "+base+"/{id}", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		var progress *int
		if q := r.URL.Query(); q.Has("progress_percentage") {
			n, err := strconv.Atoi(q.Get("progress_percentage"))
			if err != nil {
				writeDetail(w, http.StatusUnprocessableEntity, "Input should be a valid integer, unable to parse string as an integer")
				return
			}
			progress = &n
		}
		body, err := routes.UpdateSubtask(r.Context(), r.PathValue("id"), queryOpt(r, "title"), queryOpt(r, "description"), queryOpt(r, "status"), progress, u, c)
		writeResult(w, body, err)
	}))
	mux.HandleFunc("DELETE "+base+"/{id}", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		body, err := routes.DeleteSubtask(r.Context(), r.PathValue("id"), u, c)
		writeResult(w, body, err)
	}))
	mux.HandleFunc("POST "+base+"/{id}/complete", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		body, err := routes.CompleteSubtask(r.Context(), r.PathValue("id"), queryOpt(r, "completion_notes"), u, c)
		writeResult(w, body, err)
	}))
}
