package httpapp

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// branchMux mounts the branch routes on a fresh mux.
func branchMux() *http.ServeMux {
	mux := http.NewServeMux()
	(&App{}).registerBranchRoutes(mux)
	return mux
}

// The branch collection POST must match only the collection path. Before this it was a
// trailing-slash subtree pattern, so a POST to an unknown subpath under /api/v2/branches/
// matched CreateBranch and only the missing form fields stopped it - the same silent
// wrong-route class the GET collection had before it was deleted (f33db13a), and a caller
// posting a complete body to a wrong path would have created a branch at a path that does
// not exist.
func TestBranchCollectionPostMatchesOnlyTheCollectionPath(t *testing.T) {
	authenticateTestUser(t)
	mux := branchMux()

	// POST /api/v2/branches/ still reaches the handler and answers the same 422 shape
	// (FastAPI-style missing-field detail for project_id and git_branch_name).
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

	// An unknown subpath is refused, with the form fields present, so the refusal cannot
	// come from validation: before this change both paths matched the collection POST's
	// subtree and answered the 422 missing-field JSON from CreateBranch (probe: BEFORE
	// "POST /api/v2/branches/"). x/y matches no pattern (404); abc matches the GET-only
	// /{id} pattern, so the mux answers 405 for the wrong method instead of running
	// CreateBranch.
	for _, tc := range []struct {
		path string
		want int
	}{
		{"/api/v2/branches/x/y", http.StatusNotFound},
		{"/api/v2/branches/abc", http.StatusMethodNotAllowed},
	} {
		rec := httptest.NewRecorder()
		req := httptest.NewRequest(http.MethodPost, tc.path, strings.NewReader("project_id=p&git_branch_name=b"))
		req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
		req.Header.Set("Authorization", "Bearer test-token")
		mux.ServeHTTP(rec, req)
		if rec.Code != tc.want {
			t.Fatalf("POST %s = %d (%s), want %d - it must not reach CreateBranch", tc.path, rec.Code, rec.Body.String(), tc.want)
		}
		if rec.Code == http.StatusUnprocessableEntity {
			t.Fatalf("POST %s reached CreateBranch's validation (%s)", tc.path, rec.Body.String())
		}
	}
}
