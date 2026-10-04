package httpapp

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"agenthub/fastmcp/server/routes"
	"agenthub/fastmcp/task_management/domain/entities"
)

// branchMux mounts the branch routes on a fresh mux.
func branchMux() *http.ServeMux {
	mux := http.NewServeMux()
	(&App{}).registerBranchRoutes(mux)
	return mux
}

// stubBranchController records CreateBranch calls so the test can tell the collection
// prefix from an unknown subpath without a database.
type stubBranchController struct {
	createCalls int
	lastProject string
	lastName    string
}

func (s *stubBranchController) CreateBranch(_ context.Context, projectID, name, _, _ string) routes.BranchResult {
	s.createCalls++
	s.lastProject = projectID
	s.lastName = name
	return stubBranchResult{}
}

func (s *stubBranchController) GetBranch(context.Context, string, string) routes.BranchResult {
	return stubBranchResult{}
}

func (s *stubBranchController) DeleteBranch(context.Context, string, string) routes.BranchResult {
	return stubBranchResult{}
}

func (s *stubBranchController) GetBranchesWithTaskCounts(context.Context, string, string) routes.BranchResult {
	return stubBranchResult{}
}

// GET /{id}/task-counts was deleted with the other orphaned branch routes (no consumer
// anywhere: only the Python mirror defined it), so the path must no longer be served.
func TestDeletedBranchTaskCountsRouteIsNotServed(t *testing.T) {
	authenticateTestUser(t)
	rec := doTestRequest(t, branchMux(), http.MethodGet, "/api/v2/branches/b1/task-counts", "")
	if rec.Code != http.StatusNotFound {
		t.Fatalf("GET /api/v2/branches/b1/task-counts = %d, want 404 (%s)", rec.Code, rec.Body.String())
	}
}

func (s *stubBranchController) GetBulkSummaries(context.Context, []string, string, bool) routes.BranchResult {
	return stubBranchResult{}
}

type stubBranchResult struct{}

func (stubBranchResult) Success() bool    { return true }
func (stubBranchResult) Message() *string { return nil }
func (stubBranchResult) Error() *string   { return nil }

func (stubBranchResult) ModelDump() *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("id", "branch-1")
	m.Set("git_branch_name", "feat")
	return m
}

func branchFormPost(t *testing.T, mux *http.ServeMux, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(http.MethodPost, path, strings.NewReader(body))
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	req.Header.Set("Authorization", "Bearer test-token")
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)
	return rec
}

// The branch collection POST must match only the collection path. Before this it was a
// trailing-slash subtree pattern, so a POST to an unknown subpath under /api/v2/branches/
// matched CreateBranch and only the missing form fields stopped it - the same silent
// wrong-route class the GET collection had before it was deleted (f33db13a), and a caller
// posting a complete body to a wrong path would have created a branch at a path that does
// not exist.
func TestBranchCollectionPostMatchesOnlyTheCollectionPath(t *testing.T) {
	authenticateTestUser(t)
	stub := &stubBranchController{}
	app := &App{branches: stub}
	mux := http.NewServeMux()
	app.registerBranchRoutes(mux)

	// The collection POST still reaches CreateBranch with the form fields, and answers 200.
	rec := branchFormPost(t, mux, "/api/v2/branches/", "project_id=p1&git_branch_name=feat")
	if rec.Code != http.StatusOK {
		t.Fatalf("POST /api/v2/branches/ = %d, want 200 (%s)", rec.Code, rec.Body.String())
	}
	if stub.createCalls != 1 || stub.lastProject != "p1" || stub.lastName != "feat" {
		t.Fatalf("CreateBranch calls=%d project=%q name=%q, want 1/p1/feat", stub.createCalls, stub.lastProject, stub.lastName)
	}

	// An unknown subpath with the SAME complete body is refused by routing, so the refusal
	// cannot come from validation: x/y matches no pattern (404); abc matches the GET-only
	// /{id} pattern, so the mux answers 405 for the wrong method. Before this change both
	// matched the collection POST's subtree and created a branch.
	for _, tc := range []struct {
		path string
		want int
	}{
		{"/api/v2/branches/x/y", http.StatusNotFound},
		{"/api/v2/branches/abc", http.StatusMethodNotAllowed},
	} {
		rec := branchFormPost(t, mux, tc.path, "project_id=p1&git_branch_name=feat")
		if rec.Code != tc.want {
			t.Fatalf("POST %s = %d (%s), want %d - it must not reach CreateBranch", tc.path, rec.Code, rec.Body.String(), tc.want)
		}
	}
	if stub.createCalls != 1 {
		t.Fatalf("CreateBranch ran %d times, want 1: an unknown subpath reached it", stub.createCalls)
	}
}

// The empty-body shape of the collection POST is unchanged (FastAPI-style 422 missing-field
// detail for project_id and git_branch_name).
func TestBranchCollectionPostKeepsTheMissingFieldShape(t *testing.T) {
	authenticateTestUser(t)
	mux := branchMux()

	rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/branches/", "")
	if rec.Code != http.StatusUnprocessableEntity {
		t.Fatalf("POST /api/v2/branches/ = %d, want 422 (%s)", rec.Code, rec.Body.String())
	}
	var body struct {
		Detail []struct {
			Type string   `json:"type"`
			Loc  []string `json:"loc"`
		} `json:"detail"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil {
		t.Fatalf("response is not the missing-field JSON: %v (%s)", err, rec.Body.String())
	}
	locs := make([]string, 0, len(body.Detail))
	for _, d := range body.Detail {
		if d.Type != "missing" {
			t.Fatalf("detail type = %q, want missing (%s)", d.Type, rec.Body.String())
		}
		locs = append(locs, strings.Join(d.Loc, "."))
	}
	joined := strings.Join(locs, ",")
	if !strings.Contains(joined, "body.project_id") || !strings.Contains(joined, "body.git_branch_name") {
		t.Fatalf("missing-field locs = %v, want body.project_id and body.git_branch_name", locs)
	}
}
