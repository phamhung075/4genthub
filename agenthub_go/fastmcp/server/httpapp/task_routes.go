package httpapp

import (
	"encoding/json"
	"net/http"
	"strconv"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	"agenthub/fastmcp/server/routes"
	dtostask "agenthub/fastmcp/task_management/application/dtos/task"
)

// jsonBody decodes the request JSON object; a malformed or non-object body is FastAPI's 422.
func jsonBody(w http.ResponseWriter, r *http.Request) (map[string]any, bool) {
	var m map[string]any
	if err := json.NewDecoder(r.Body).Decode(&m); err != nil || m == nil {
		b, _ := json.Marshal(map[string]any{"detail": []map[string]any{{"type": "model_attributes_type", "loc": []string{"body"}, "msg": "Input should be a valid dictionary or object to extract fields from", "input": nil}}})
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusUnprocessableEntity)
		_, _ = w.Write(b)
		return nil, false
	}
	return m, true
}

func optString(m map[string]any, key string) *string {
	if s, ok := m[key].(string); ok {
		return &s
	}
	return nil
}

func stringList(m map[string]any, key string) []string {
	raw, ok := m[key].([]any)
	if !ok {
		return nil
	}
	out := make([]string, 0, len(raw))
	for _, v := range raw {
		if s, ok := v.(string); ok {
			out = append(out, s)
		}
	}
	return out
}

func (a *App) registerTaskRoutes(mux *http.ServeMux) {
	const base = "/api/v2/tasks"
	c := a.tasks
	mux.HandleFunc("POST "+base+"/", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		m, ok := jsonBody(w, r)
		if !ok {
			return
		}
		var missing []string
		for _, f := range []string{"title", "git_branch_id"} {
			if _, isStr := m[f].(string); !isStr {
				missing = append(missing, f)
			}
		}
		if len(missing) > 0 {
			writeMissing(w, "body", missing...)
			return
		}
		req := dtostask.CreateTaskRequest{
			Title: m["title"].(string), GitBranchID: m["git_branch_id"].(string),
			Description: optString(m, "description"), Status: optString(m, "status"), Priority: optString(m, "priority"),
			Assignees: stringList(m, "assignees"), Labels: stringList(m, "labels"),
			DueDate: optString(m, "due_date"), Dependencies: stringList(m, "dependencies"), UserID: optString(m, "user_id"),
		}
		if s := optString(m, "details"); s != nil {
			req.Details = *s
		}
		if s := optString(m, "estimated_effort"); s != nil {
			req.EstimatedEffort = *s
		}
		built, err := dtostask.NewCreateTaskRequest(req)
		if err != nil {
			writeDetail(w, http.StatusUnprocessableEntity, err.Error())
			return
		}
		body, herr := routes.CreateUserTask(r.Context(), built, u, c)
		writeResult(w, body, herr)
	}))
	mux.HandleFunc("GET "+base+"/", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		limit := 50
		if q := r.URL.Query().Get("limit"); r.URL.Query().Has("limit") {
			n, err := strconv.Atoi(q)
			if err != nil {
				writeDetail(w, http.StatusUnprocessableEntity, "Input should be a valid integer, unable to parse string as an integer")
				return
			}
			limit = n
		}
		req := &dtostask.ListTasksRequest{GitBranchID: queryOpt(r, "git_branch_id"), Status: queryOpt(r, "task_status"), Priority: queryOpt(r, "priority"), Limit: &limit}
		body, err := routes.ListUserTasks(r.Context(), req, u, c)
		writeResult(w, body, err)
	}))
	mux.HandleFunc("GET "+base+"/stats/summary", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		body, err := routes.GetUserTaskStats(r.Context(), u, c)
		writeResult(w, body, err)
	}))
	mux.HandleFunc("GET "+base+"/{id}", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		body, err := routes.GetUserTask(r.Context(), r.PathValue("id"), u, c)
		writeResult(w, body, err)
	}))
	mux.HandleFunc("PUT "+base+"/{id}", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		m, ok := jsonBody(w, r)
		if !ok {
			return
		}
		if _, has := m["task_id"]; !has {
			writeMissing(w, "body", "task_id")
			return
		}
		req := &dtostask.UpdateTaskRequest{
			TaskID: m["task_id"], Title: optString(m, "title"), Description: optString(m, "description"),
			Status: optString(m, "status"), Priority: optString(m, "priority"), Details: optString(m, "details"),
			EstimatedEffort: optString(m, "estimated_effort"), Assignees: stringList(m, "assignees"), Labels: stringList(m, "labels"),
			DueDate: optString(m, "due_date"), ContextID: optString(m, "context_id"), CompletionSummary: optString(m, "completion_summary"),
			TestingNotes: optString(m, "testing_notes"), CompletedAt: optString(m, "completed_at"),
		}
		if f, isNum := m["progress_percentage"].(float64); isNum {
			p := int(f)
			req.ProgressPercentage = &p
		}
		body, err := routes.UpdateUserTask(r.Context(), r.PathValue("id"), req, u, c)
		writeResult(w, body, err)
	}))
	mux.HandleFunc("DELETE "+base+"/{id}", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		body, err := routes.DeleteUserTask(r.Context(), r.PathValue("id"), u, c)
		writeResult(w, body, err)
	}))
	mux.HandleFunc("POST "+base+"/{id}/complete", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		summary, ok := queryReq(w, r, "completion_summary")
		if !ok {
			return
		}
		body, err := routes.CompleteUserTask(r.Context(), r.PathValue("id"), summary, queryOpt(r, "testing_notes"), u, c)
		writeResult(w, body, err)
	}))
}
