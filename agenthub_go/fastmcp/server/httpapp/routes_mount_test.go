package httpapp

import (
	"context"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"agenthub/fastmcp/server/routes"
	"agenthub/fastmcp/task_management/domain/entities"
)

// --- fakes for the routes-level controller interfaces ---

type fakeContextController struct{}

func (fakeContextController) ok() (routes.ControllerResult, error) {
	return routes.ControllerResult{Success: true, Body: entities.NewOrderedMap[any]()}, nil
}

func (fakeContextController) CreateContext(context.Context, string, string, *entities.OrderedMap[any], string) (routes.ControllerResult, error) {
	return fakeContextController{}.ok()
}
func (fakeContextController) GetContext(context.Context, string, string, bool, string) (routes.ControllerResult, error) {
	return fakeContextController{}.ok()
}
func (fakeContextController) UpdateContext(context.Context, string, string, *entities.OrderedMap[any], string) (routes.ControllerResult, error) {
	return fakeContextController{}.ok()
}
func (fakeContextController) DeleteContext(context.Context, string, string, string) (routes.ControllerResult, error) {
	return fakeContextController{}.ok()
}
func (fakeContextController) ResolveContext(context.Context, string, string, bool, string) (routes.ControllerResult, error) {
	return fakeContextController{}.ok()
}

type fakeTokenController struct{}

func (fakeTokenController) GenerateAPIToken(context.Context, string, string, []string, int, *int) (routes.TokenOperationResult, error) {
	return routes.TokenOperationResult{Success: true, TokenData: entities.NewOrderedMap[any]()}, nil
}
func (fakeTokenController) ListUserTokens(context.Context, string) (routes.TokenRouteListResult, error) {
	return routes.TokenRouteListResult{Success: true}, nil
}
func (fakeTokenController) GetTokenDetails(context.Context, string, string) (routes.TokenOperationResult, error) {
	return routes.TokenOperationResult{Success: true, TokenData: entities.NewOrderedMap[any]()}, nil
}
func (fakeTokenController) DeleteToken(context.Context, string, string) (routes.TokenOperationResult, error) {
	return routes.TokenOperationResult{Success: true}, nil
}
func (fakeTokenController) RevokeToken(context.Context, string, string) (routes.TokenOperationResult, error) {
	return routes.TokenOperationResult{Success: true}, nil
}
func (fakeTokenController) ReactivateToken(context.Context, string, string) (routes.TokenOperationResult, error) {
	return routes.TokenOperationResult{Success: true}, nil
}
func (fakeTokenController) RotateToken(context.Context, string, string) (routes.TokenOperationResult, error) {
	return routes.TokenOperationResult{Success: true, TokenData: entities.NewOrderedMap[any]()}, nil
}
func (fakeTokenController) ValidateToken(context.Context, string) (routes.TokenValidateResult, error) {
	return routes.TokenValidateResult{Success: true, Claims: entities.NewOrderedMap[any]()}, nil
}
func (fakeTokenController) CleanupExpiredTokens(context.Context, string) (routes.TokenCleanupResult, error) {
	return routes.TokenCleanupResult{Success: true}, nil
}

type fakeTaskRoutes struct{}

func (fakeTaskRoutes) CountTasks(context.Context, *entities.OrderedMap[any], string) (routes.TaskCountResult, error) {
	return routes.TaskCountResult{Success: true}, nil
}
func (fakeTaskRoutes) ListTasksSummary(context.Context, *entities.OrderedMap[any], int, int, string) (routes.TaskListSummaryResult, error) {
	return routes.TaskListSummaryResult{Success: true}, nil
}

type fakeSubtaskRoutes struct{}

func (fakeSubtaskRoutes) ListSubtasksSummary(context.Context, string, bool, string) (routes.SubtaskSummaryResult, error) {
	return routes.SubtaskSummaryResult{Success: true}, nil
}

type fakeUserSubtasks struct{}

func (fakeUserSubtasks) ListSubtasks(context.Context, string, string) (routes.UserSubtaskResult, error) {
	return routes.UserSubtaskResult{Success: true}, nil
}

func testRouteDeps() routeDeps {
	return routeDeps{
		taskRoutes:    fakeTaskRoutes{},
		subtaskRoutes: fakeSubtaskRoutes{},
		userSubtasks:  fakeUserSubtasks{},
		contexts:      fakeContextController{},
		tokens:        fakeTokenController{},
		broadcast: func(context.Context, string, string, string, string, *entities.OrderedMap[any], *entities.OrderedMap[any]) error {
			return nil
		},
	}
}

type routeProbe struct {
	method string
	path   string
	body   string
}

// expectedProbes lists every pattern mountRoutes adds. Handler's own patterns
// are deliberately absent: the duplicate test below registers those and calls
// mountRoutes on top.
func expectedProbes() []routeProbe {
	return []routeProbe{
		{http.MethodGet, "/api/v2/connections/health", ""},
		{http.MethodGet, "/api/v2/connections/status", ""},
		{http.MethodGet, "/api/v1/alerts/rules", ""},
		{http.MethodPost, "/api/v1/alerts/rules", `{"name":"n","metric":"m","condition":"equals","threshold":1}`},
		{http.MethodPut, "/api/v1/alerts/rules/r1", `{"name":"n"}`},
		{http.MethodDelete, "/api/v1/alerts/rules/r1", ""},
		{http.MethodGet, "/api/v1/alerts/events", ""},
		{http.MethodPost, "/api/v1/alerts/events/0/acknowledge", ""},
		{http.MethodPost, "/api/v1/alerts/check-rules", ""},
		{http.MethodPost, "/api/v1/alerts/test-webhook", `{"webhook_url":""}`},
		{http.MethodGet, "/api/v1/performance/metrics/overview", ""},
		{http.MethodGet, "/api/v1/performance/metrics/timeseries", ""},
		{http.MethodGet, "/api/v1/performance/metrics/alerts", ""},
		{http.MethodPost, "/api/v1/performance/metrics/clear-cache", ""},
		{http.MethodPost, "/api/v2/broadcast/notify", `{"event_type":"e","entity_type":"t","entity_id":"i","user_id":"u"}`},
		{http.MethodPost, "/api/v2/contexts/global", `{"context_id":"me"}`},
		{http.MethodGet, "/api/v2/contexts/global/me", ""},
		{http.MethodPut, "/api/v2/contexts/global/me", `{"data":{}}`},
		{http.MethodDelete, "/api/v2/contexts/global/me", ""},
		{http.MethodGet, "/api/v2/contexts/global/me/resolve", ""},
		{http.MethodPost, "/api/v2/contexts/global/me/delegate", `{"delegate_to":"project"}`},
		{http.MethodPost, "/api/v2/contexts/global/me/insights", `{"content":"c"}`},
		{http.MethodPost, "/api/v2/contexts/global/me/progress", `{"content":"c"}`},
		{http.MethodGet, "/api/v2/contexts/global/list", ""},
		{http.MethodGet, "/api/v2/contexts/global/me/summary", ""},
		{http.MethodPost, "/api/v2/tokens", `{"name":"t"}`},
		{http.MethodPost, "/api/v2/tokens/", `{"name":"t"}`},
		{http.MethodPost, "/api/v2/tokens/generate", `{"name":"t"}`},
		{http.MethodGet, "/api/v2/tokens", ""},
		{http.MethodGet, "/api/v2/tokens/", ""},
		{http.MethodGet, "/api/v2/tokens/legacy/tokens", ""},
		{http.MethodGet, "/api/v2/tokens/health", ""},
		{http.MethodGet, "/api/v2/tokens/t1", ""},
		{http.MethodDelete, "/api/v2/tokens/t1", ""},
		{http.MethodPatch, "/api/v2/tokens/t1/revoke", ""},
		{http.MethodPatch, "/api/v2/tokens/t1/reactivate", ""},
		{http.MethodPost, "/api/v2/tokens/t1/rotate", ""},
		{http.MethodPost, "/api/v2/tokens/validate?token=x", ""},
		{http.MethodPost, "/api/v2/tokens/cleanup", ""},
		{http.MethodPost, "/api/tasks/summaries", `{"git_branch_id":"b1"}`},
		{http.MethodGet, "/api/tasks/task-1/context/summary", ""},
		{http.MethodPost, "/api/subtasks/summaries", `{"parent_task_id":"task-1"}`},
		{http.MethodGet, "/api/performance/metrics", ""},
		{http.MethodPost, "/api/v2/tasks/task-1/subtasks/summaries", ""},
	}
}

func mountedTestMux() *http.ServeMux {
	mux := http.NewServeMux()
	mountRoutes(mux, testRouteDeps())
	return mux
}

func TestMountRoutesRegistersEveryExpectedPattern(t *testing.T) {
	mux := mountedTestMux()
	for _, p := range expectedProbes() {
		req := httptest.NewRequest(p.method, p.path, strings.NewReader(p.body))
		if p.body != "" {
			req.Header.Set("Content-Type", "application/json")
		}
		rec := httptest.NewRecorder()
		mux.ServeHTTP(rec, req)
		if rec.Code == http.StatusNotFound {
			t.Errorf("%s %s: not registered (got 404)", p.method, p.path)
		}
	}
}

func TestMountRoutesDoesNotDuplicateHandlerPatterns(t *testing.T) {
	mux := http.NewServeMux()
	handlerPatterns := []string{
		"GET /health",
		"POST /api/v2/projects/",
		"GET /api/v2/projects/",
		"GET /api/v2/projects/{id}",
		"PUT /api/v2/projects/{id}",
		"DELETE /api/v2/projects/{id}",
		"POST /api/v2/projects/{id}/health-check",
		"POST /api/v2/branches/{$}",
		"GET /api/v2/branches/{id}",
		"DELETE /api/v2/branches/{id}",
		"POST /api/v2/branches/project/{project_id}/summaries",
		"POST /api/v2/branches/summaries/bulk",
		"POST /api/v2/tasks/",
		"GET /api/v2/tasks/",
		"GET /api/v2/tasks/{id}",
		"PUT /api/v2/tasks/{id}",
		"DELETE /api/v2/tasks/{id}",
		"POST /api/v2/tasks/{id}/complete",
		"POST /api/v2/subtasks",
		"GET /api/v2/subtasks/task/{id}",
		"GET /api/v2/subtasks/{id}",
		"PUT /api/v2/subtasks/{id}",
		"DELETE /api/v2/subtasks/{id}",
		"POST /api/v2/subtasks/{id}/complete",
		"GET /api/v2/sessions",
		"GET /api/v2/sessions/{id}/events",
		"POST /mcp",
		"GET /mcp",
	}
	for _, p := range handlerPatterns {
		mux.HandleFunc(p, func(http.ResponseWriter, *http.Request) {})
	}
	defer func() {
		if recovered := recover(); recovered != nil {
			t.Fatalf("mountRoutes collided with a Handler pattern: %v", recovered)
		}
	}()
	mountRoutes(mux, testRouteDeps())
}

func TestNewRouteDepsNilAppDoesNotPanic(t *testing.T) {
	deps := newRouteDeps(nil)
	if deps.taskRoutes != nil || deps.tokens != nil || deps.contexts != nil {
		t.Fatalf("newRouteDeps(nil) = %+v, want zero deps", deps)
	}
	mux := http.NewServeMux()
	mountRoutes(mux, deps)
	for _, p := range []routeProbe{
		{http.MethodGet, "/api/v2/connections/health", ""},
		{http.MethodGet, "/api/v1/performance/metrics/overview", ""},
		{http.MethodGet, "/api/performance/metrics", ""},
	} {
		req := httptest.NewRequest(p.method, p.path, strings.NewReader(p.body))
		rec := httptest.NewRecorder()
		mux.ServeHTTP(rec, req)
		if rec.Code == http.StatusNotFound {
			t.Errorf("%s %s: not registered with zero deps", p.method, p.path)
		}
	}
}

func TestNewRouteDepsEmptyAppDoesNotPanic(t *testing.T) {
	defer func() {
		if recovered := recover(); recovered != nil {
			t.Fatalf("newRouteDeps(&App{}) panicked: %v", recovered)
		}
	}()
	mux := http.NewServeMux()
	mountRoutes(mux, newRouteDeps(&App{}))
}

// TestRemovedTaskRoutesAreAbsent pins the removal of the two task routes that
// could only answer 500 (owner ruling 2026-10-08; decision note
// ai_docs/architecture-design/decision-task-stats-endpoint.md, option C).
//
// THE 404 ASSERTION IS OBSERVABLE FOR /api/tasks/{task_id} ONLY. The v2 stats
// path sits UNDER THE "GET /api/v2/tasks/" PREFIX ROUTE, which in Go's ServeMux
// matches every path in that subtree and answers 403 before auth: it returns 403
// whether or not the dedicated stats handler exists, so it can never 404 and a
// 403 there is NOT evidence of removal. (The first draft of this test asserted
// 404 for it and could not pass.) That half is evidenced instead by the
// acceptance instrument the decision note names - the symbol grep over .go
// files, 21 lines at HEAD and 0 after - and by the build, since the whole
// handler chain from route to panicking method is gone.
//
// THE CONTROL MUST STAY MOUNTED. Without it a 404 cannot distinguish "the route
// was removed" from "this mux never mounted it", which is how the first draft
// also passed VACUOUSLY on the v2 path: testRouteDeps mounts mountRoutes, while
// the v2 task routes come from App.registerTaskRoutes, which it never calls.
func TestRemovedTaskRoutesAreAbsent(t *testing.T) {
	mux := mountedTestMux()
	for _, c := range []struct {
		p       routeProbe
		want404 bool
	}{
		{routeProbe{http.MethodGet, "/api/tasks/task-1/context/summary", ""}, false}, // control: live neighbour stays mounted
		{routeProbe{http.MethodGet, "/api/tasks/task-1", ""}, true},                  // removed
	} {
		req := httptest.NewRequest(c.p.method, c.p.path, strings.NewReader(c.p.body))
		rec := httptest.NewRecorder()
		mux.ServeHTTP(rec, req)
		is404 := rec.Code == http.StatusNotFound
		if is404 != c.want404 {
			t.Errorf("%s %s: status %d, want404=%v", c.p.method, c.p.path, rec.Code, c.want404)
		}
	}
}
