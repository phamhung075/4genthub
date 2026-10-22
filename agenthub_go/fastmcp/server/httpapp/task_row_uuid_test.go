package httpapp

// The row-uuid guard on the task routes below the read.
//
// WHY. The task read resolves the 4-31 hex READ address, but the events and evidence routes - and the
// three writers - handed their path straight to a `$1::uuid` cast, so an 8-hex id (the form the room
// cites a task with) answered HTTP 500 "invalid input syntax for type uuid" (SQLSTATE 22P02) for every
// caller that had not resolved it first. Measured on the deployed server from four client runs
// (row qitem-20261022194113): GET /api/v2/tasks/403d16ca answered 200 while GET
// /api/v2/tasks/403d16ca/events and POST /api/v2/tasks/403d16ca/evidence answered 500.
//
// These tests drive the registered routes themselves (App.registerTaskRoutes over a mux), so the
// assertion is about the production path and not a copy of it. They need no database: the guard runs
// before any use case, and a full uuid is shown reaching the controller, which is what the route
// answers today.

import (
	"context"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	authinterface "agenthub/fastmcp/auth/interface"
	"agenthub/fastmcp/server/routes"
	dtostask "agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

const (
	rowUUID       = "403d16ca-89df-4ccf-88f3-b0084dbac309"
	rowUUIDNoDash = "403d16ca89df4ccf88f3b0084dbac309"
	idPrefix      = "403d16ca"
)

// recordingTaskController is the routes.UserTaskController fake: it answers success and remembers the
// ids the routes layer handed it, which is how a test tells "the guard refused" from "the use case ran".
type recordingTaskController struct{ ids []string }

func (c *recordingTaskController) record(id string) (routes.UserTaskResult, error) {
	c.ids = append(c.ids, id)
	return routes.UserTaskResult{Success: true}, nil
}

func (c *recordingTaskController) CreateTask(context.Context, *dtostask.CreateTaskRequest, string) (routes.UserTaskResult, error) {
	return c.record("")
}
func (c *recordingTaskController) ListTasks(context.Context, *dtostask.ListTasksRequest, string) (routes.UserTaskListResult, error) {
	return routes.UserTaskListResult{Success: true}, nil
}
func (c *recordingTaskController) GetTask(_ context.Context, id, _ string) (routes.UserTaskResult, error) {
	return c.record(id)
}
func (c *recordingTaskController) UpdateTask(_ context.Context, id string, _ *dtostask.UpdateTaskRequest, _ string) (routes.UserTaskResult, error) {
	return c.record(id)
}
func (c *recordingTaskController) DeleteTask(_ context.Context, id, _ string) (routes.UserTaskResult, error) {
	return c.record(id)
}
func (c *recordingTaskController) CompleteTask(_ context.Context, id, _ string, _ *string, _ string) (routes.UserTaskResult, error) {
	return c.record(id)
}

// taskRouteMux registers the real task routes over a fake controller and an accepted token.
func taskRouteMux(t *testing.T) (http.Handler, *recordingTaskController) {
	t.Helper()
	controller := &recordingTaskController{}
	app := &App{tasks: controller, Sessions: database.NewSessionManager(&database.DatabaseConfig{})}

	previous := authinterface.GetCurrentUserUniversal
	userID := "11111111-1111-4111-8111-111111111111"
	authinterface.GetCurrentUserUniversal = func(context.Context, string) (*authdomain.User, error) {
		return &authdomain.User{ID: &userID, Email: "seat@4genthub.com"}, nil
	}
	t.Cleanup(func() { authinterface.GetCurrentUserUniversal = previous })

	mux := http.NewServeMux()
	app.registerTaskRoutes(mux)
	return mux, controller
}

func taskRequest(t *testing.T, mux http.Handler, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	req.Header.Set("Authorization", "Bearer test-token")
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)
	return rec
}

// guardProbes is every route that takes the row uuid. GET /{id} and GET /{id}/resume are absent on
// purpose: both resolve the read address, and the test below pins that they still do.
func guardProbes() []routeProbe {
	return []routeProbe{
		{http.MethodGet, "/api/v2/tasks/%s/events", ""},
		{http.MethodPost, "/api/v2/tasks/%s/evidence", `{"base_sha":"a","head_sha":"b","numstat":"1\t0\tf"}`},
		{http.MethodPut, "/api/v2/tasks/%s", `{"task_id":"x","title":"t"}`},
		{http.MethodDelete, "/api/v2/tasks/%s", ""},
		{http.MethodPost, "/api/v2/tasks/%s/complete?completion_summary=s", ""},
	}
}

func TestTaskRowUUIDGuardRefusesAPrefixOnEveryWriteAndEventsRoute(t *testing.T) {
	mux, controller := taskRouteMux(t)
	for _, p := range guardProbes() {
		rec := taskRequest(t, mux, p.method, strings.Replace(p.path, "%s", idPrefix, 1), p.body)
		if rec.Code != http.StatusUnprocessableEntity {
			t.Errorf("%s %s: status %d, want %d; body %s", p.method, p.path, rec.Code, http.StatusUnprocessableEntity, rec.Body.String())
			continue
		}
		detail := rec.Body.String()
		if !strings.Contains(detail, `Task id \"403d16ca\" is not a task row uuid`) {
			t.Errorf("%s %s: the refusal does not name the id: %s", p.method, p.path, detail)
		}
		if !strings.Contains(detail, "GET /api/v2/tasks/403d16ca resolves it") {
			t.Errorf("%s %s: the refusal does not name the read route that takes a prefix: %s", p.method, p.path, detail)
		}
	}
	if len(controller.ids) != 0 {
		t.Fatalf("the guard let a prefix through to the controller: %v", controller.ids)
	}
}

func TestTaskRowUUIDGuardPassesTheRowUUIDToTheRouteUnchanged(t *testing.T) {
	mux, controller := taskRouteMux(t)
	for _, p := range guardProbes() {
		rec := taskRequest(t, mux, p.method, strings.Replace(p.path, "%s", rowUUID, 1), p.body)
		// A row uuid reaches the route: never the guard's refusal. The two routes that need a
		// configured database answer their own failure on this unconfigured manager; the three
		// controller routes answer 200.
		if rec.Code == http.StatusUnprocessableEntity || strings.Contains(rec.Body.String(), "is not a task row uuid") {
			t.Errorf("%s %s: a row uuid is refused: %s", p.method, p.path, rec.Body.String())
		}
	}
	// GET /{id}/events and POST /{id}/evidence both ask the task first (the task-first 404), so the
	// controller sees the id once for each of the five routes.
	want := []string{rowUUID, rowUUID, rowUUID, rowUUID, rowUUID}
	if strings.Join(controller.ids, ",") != strings.Join(want, ",") {
		t.Fatalf("the controller saw %v, want %v", controller.ids, want)
	}
}

// TestTaskRowUUIDGuardNormalizesTheDashlessForm pins that the second spelling the store casts reaches
// the route as the canonical one, so a caller is not asked to know which of the two to send.
func TestTaskRowUUIDGuardNormalizesTheDashlessForm(t *testing.T) {
	mux, controller := taskRouteMux(t)
	rec := taskRequest(t, mux, http.MethodDelete, "/api/v2/tasks/"+rowUUIDNoDash, "")
	if rec.Code != http.StatusOK {
		t.Fatalf("DELETE with the dashless 32-hex form: status %d, want 200; body %s", rec.Code, rec.Body.String())
	}
	if len(controller.ids) != 1 || controller.ids[0] != rowUUID {
		t.Fatalf("the controller saw %v, want [%s]", controller.ids, rowUUID)
	}
}

// TestTaskReadStillResolvesAPrefix is the negative of the guard: the read route is the one address that
// accepts the 4-31 hex prefix, and it must keep answering it - the client's `--task <8hex>` read path
// and the room's habit of citing a task by prefix both depend on it.
func TestTaskReadStillResolvesAPrefix(t *testing.T) {
	mux, controller := taskRouteMux(t)
	rec := taskRequest(t, mux, http.MethodGet, "/api/v2/tasks/"+idPrefix, "")
	if rec.Code != http.StatusOK {
		t.Fatalf("GET with the read address: status %d, want 200; body %s", rec.Code, rec.Body.String())
	}
	if len(controller.ids) != 1 || controller.ids[0] != idPrefix {
		t.Fatalf("the reader saw %v, want the prefix handed on unchanged for its own resolution", controller.ids)
	}
}
