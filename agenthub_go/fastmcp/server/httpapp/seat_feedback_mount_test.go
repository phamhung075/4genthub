package httpapp

// Route tests for the seat friction channel, over in-memory repositories: real requests through
// the mounted routes, no database. The three things pinned here are the ones a consumer depends
// on — the grouped read shape, the refusals, and who a row is attributed to.

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	authinterface "agenthub/fastmcp/auth/interface"
	"agenthub/fastmcp/seat_management/application/services"
	"agenthub/fastmcp/seat_management/domain/repositories"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// A fixed clock, so created_at is asserted rather than tolerated.
var seatFeedbackTestNow = time.Date(2026, 10, 6, 16, 33, 13, 0, time.UTC)

type fakeSeatFeedback struct {
	reports   []repositories.SeatFeedback
	createErr error
	listErr   error
	lastUser  string
}

func (f *fakeSeatFeedback) Create(_ context.Context, report repositories.SeatFeedback) (*repositories.SeatFeedback, error) {
	if f.createErr != nil {
		return nil, f.createErr
	}
	report.ID = fmt.Sprintf("fb-%04d", len(f.reports)+1)
	// Newest first, the order the ORM repository returns.
	f.reports = append([]repositories.SeatFeedback{report}, f.reports...)
	stored := report
	return &stored, nil
}

func (f *fakeSeatFeedback) List(_ context.Context, userID string) ([]repositories.SeatFeedback, error) {
	if f.listErr != nil {
		return nil, f.listErr
	}
	f.lastUser = userID
	out := []repositories.SeatFeedback{}
	for _, report := range f.reports {
		if report.UserID == userID {
			out = append(out, report)
		}
	}
	return out, nil
}

type feedbackFixture struct {
	t      *testing.T
	mux    *http.ServeMux
	source *fakeSeatFeedback
	user   string
}

func newFeedbackFixture(t *testing.T) *feedbackFixture {
	t.Helper()
	return newFeedbackFixtureWithStore(t, &fakeSeatFeedback{})
}

// newFeedbackFixtureWithStore mounts the routes over a caller-supplied store, so a test can drive
// the HTTP path and the MCP path into the SAME store and compare what each wrote.
func newFeedbackFixtureWithStore(t *testing.T, store *fakeSeatFeedback) *feedbackFixture {
	t.Helper()
	f := &feedbackFixture{t: t, source: store, user: tokenTestUserA}
	previousUsers := authinterface.GetCurrentUserUniversal
	authinterface.GetCurrentUserUniversal = func(_ context.Context, token string) (*authdomain.User, error) {
		id := f.user
		return &authdomain.User{ID: &id, Email: "dev@example.com", Username: "dev"}, nil
	}
	previousSource, previousNow := newSeatFeedbackService, seatFeedbackNow
	newSeatFeedbackService = func(*database.SessionManager) (*services.SeatFeedbackService, error) {
		return services.NewSeatFeedbackService(f.source), nil
	}
	seatFeedbackNow = func() time.Time { return seatFeedbackTestNow }
	t.Cleanup(func() {
		authinterface.GetCurrentUserUniversal = previousUsers
		newSeatFeedbackService, seatFeedbackNow = previousSource, previousNow
	})
	f.mux = http.NewServeMux()
	mountSeatFeedbackRoutes(f.mux, nil)
	return f
}

func (f *feedbackFixture) do(method, path, bearer, body string) *httptest.ResponseRecorder {
	f.t.Helper()
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	if bearer != "" {
		req.Header.Set("Authorization", "Bearer "+bearer)
	}
	rec := httptest.NewRecorder()
	f.mux.ServeHTTP(rec, req)
	return rec
}

func (f *feedbackFixture) submit(bearer, body string) *httptest.ResponseRecorder {
	f.t.Helper()
	return f.do(http.MethodPost, "/api/v2/openrig/feedback", bearer, body)
}

type feedbackReadBody struct {
	Success bool `json:"success"`
	Total   int  `json:"total"`
	Layers  []struct {
		Layer   string           `json:"layer"`
		Count   int              `json:"count"`
		Reports []map[string]any `json:"reports"`
	} `json:"layers"`
}

func readFeedback(t *testing.T, rec *httptest.ResponseRecorder) feedbackReadBody {
	t.Helper()
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d: %s", rec.Code, rec.Body.String())
	}
	var body feedbackReadBody
	if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil {
		t.Fatalf("decode %s: %v", rec.Body.String(), err)
	}
	return body
}

// TestSeatFeedbackReadIsGroupedByLayerInVocabularyOrder is the contract the page renders: the
// grouping, the order of the groups, the counts, and the exact row keys.
func TestSeatFeedbackReadIsGroupedByLayerInVocabularyOrder(t *testing.T) {
	f := newFeedbackFixture(t)

	// Submitted cloud first, runtime second: the read must group by the vocabulary, not by when
	// the rows arrived. The ids the POSTs answer with are the ids the read must carry.
	submitted := make([]string, 0, 3)
	for _, body := range []string{
		`{"room":"4genthub-min","seat":"go-dev","session":"4genthub-min-go-dev@4genthub-min","layer":"cloud","text":"the snapshot hash disagreed"}`,
		`{"room":"4genthub-min","seat":"go-dev","layer":"runtime","text":"the permission prompt never appeared"}`,
		`{"room":"4genthub-min","seat":"fe-dev","layer":"runtime","text":"the harness dropped the pane id"}`,
	} {
		rec := f.submit("user-jwt", body)
		if rec.Code != http.StatusOK {
			t.Fatalf("submit %s: %d %s", body, rec.Code, rec.Body.String())
		}
		var created struct {
			Success bool   `json:"success"`
			ID      string `json:"id"`
			Layer   string `json:"layer"`
		}
		if err := json.Unmarshal(rec.Body.Bytes(), &created); err != nil || !created.Success || created.ID == "" {
			t.Fatalf("submit %s answered %s (%v)", body, rec.Body.String(), err)
		}
		submitted = append(submitted, created.ID)
	}

	body := readFeedback(t, f.do(http.MethodGet, "/api/v2/openrig/feedback", "user-jwt", ""))
	if !body.Success || body.Total != 3 {
		t.Fatalf("success=%v total=%d, want true and 3", body.Success, body.Total)
	}
	if len(body.Layers) != 2 {
		t.Fatalf("layers = %d (%v), want 2: a layer with no reports is absent", len(body.Layers), body.Layers)
	}
	if body.Layers[0].Layer != "runtime" || body.Layers[1].Layer != "cloud" {
		t.Fatalf("layer order = %q,%q want runtime,cloud (the vocabulary's order)",
			body.Layers[0].Layer, body.Layers[1].Layer)
	}
	if body.Layers[0].Count != 2 || body.Layers[1].Count != 1 {
		t.Fatalf("counts = %d,%d want 2,1", body.Layers[0].Count, body.Layers[1].Count)
	}
	// Newest first inside a group: fe-dev's report was written last.
	if first := body.Layers[0].Reports[0]; first["seat"] != "fe-dev" {
		t.Fatalf("first runtime report = %v, want the newest (fe-dev)", first)
	}

	row := body.Layers[1].Reports[0]
	want := map[string]any{
		"id": submitted[0], "room": "4genthub-min", "seat": "go-dev",
		"session": "4genthub-min-go-dev@4genthub-min", "layer": "cloud",
		"text": "the snapshot hash disagreed", "machine_id": "",
		"created_at": "2026-10-06T16:33:13Z",
	}
	if len(row) != len(want) {
		t.Fatalf("row keys = %v, want exactly %v", row, want)
	}
	for key, value := range want {
		if row[key] != value {
			t.Errorf("row[%s] = %v, want %v", key, row[key], value)
		}
	}
	// session and machine_id are absent-but-empty, never null: the second runtime report sent no
	// session, and an empty string is what the page reads.
	if got := body.Layers[0].Reports[1]["session"]; got != "" {
		t.Errorf("omitted session = %v, want an empty string", got)
	}
}

func TestSeatFeedbackRefusesMalformedAndUnknownLayers(t *testing.T) {
	const vocabulary = "runtime, openrig, cloud, seat-context, workspace, other"
	cases := []struct {
		name   string
		body   string
		status int
		miss   string
	}{
		{"malformed json", `{"room":`, http.StatusBadRequest, "unexpected EOF"},
		{"unknown field", `{"room":"r","seat":"s","layer":"runtime","text":"t","colour":"red"}`, http.StatusBadRequest, "unknown field"},
		{"unknown layer", `{"room":"r","seat":"s","layer":"harness","text":"t"}`, http.StatusBadRequest, vocabulary},
		{"layer is a tag when it should be a column", `{"room":"r","seat":"s","layer":"seat_context","text":"t"}`, http.StatusBadRequest, vocabulary},
		{"empty text", `{"room":"r","seat":"s","layer":"runtime","text":"   "}`, http.StatusBadRequest, "text must not be empty"},
		{"missing room", `{"seat":"s","layer":"runtime","text":"t"}`, http.StatusBadRequest, "room slug"},
		{"session too long", `{"room":"r","seat":"s","layer":"runtime","text":"t","session":"` + strings.Repeat("x", 129) + `"}`, http.StatusBadRequest, "session cannot exceed"},
		{"text too long", `{"room":"r","seat":"s","layer":"runtime","text":"` + strings.Repeat("x", 2001) + `"}`, http.StatusBadRequest, "text cannot exceed"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			f := newFeedbackFixture(t)
			rec := f.submit("user-jwt", tc.body)
			if rec.Code != tc.status {
				t.Fatalf("status = %d want %d: %s", rec.Code, tc.status, rec.Body.String())
			}
			if !strings.Contains(rec.Body.String(), tc.miss) {
				t.Fatalf("body %s does not name %q", rec.Body.String(), tc.miss)
			}
			if len(f.source.reports) != 0 {
				t.Fatalf("a refused submission was stored: %+v", f.source.reports)
			}
		})
	}
}

// TestSeatFeedbackRefusesASecretWithoutEchoingIt: the write path scans every string field and
// the refusal names the JSON path only.
func TestSeatFeedbackRefusesASecretWithoutEchoingIt(t *testing.T) {
	f := newFeedbackFixture(t)
	const secret = "ghp_0123456789012345678901234567890123"
	rec := f.submit("user-jwt", `{"room":"r","seat":"s","layer":"cloud","text":"the call failed with `+secret+` in the header"}`)
	if rec.Code != http.StatusUnprocessableEntity {
		t.Fatalf("status = %d want 422: %s", rec.Code, rec.Body.String())
	}
	if !strings.Contains(rec.Body.String(), "secret detected in field text") {
		t.Fatalf("body %s does not name the field path", rec.Body.String())
	}
	if strings.Contains(rec.Body.String(), secret) {
		t.Fatalf("the refusal echoed the credential: %s", rec.Body.String())
	}
	if len(f.source.reports) != 0 {
		t.Fatalf("a submission holding a credential was stored: %+v", f.source.reports)
	}
}

// TestSeatFeedbackReadIsTenantScopedAndEmptyIsAnEmptyEnvelope: another user's rows are invisible,
// and an empty channel answers 200 with total 0 rather than 404.
func TestSeatFeedbackReadIsTenantScopedAndEmptyIsAnEmptyEnvelope(t *testing.T) {
	f := newFeedbackFixture(t)
	if rec := f.submit("user-jwt", `{"room":"r","seat":"s","layer":"workspace","text":"the build cache lied"}`); rec.Code != http.StatusOK {
		t.Fatalf("submit: %d %s", rec.Code, rec.Body.String())
	}

	body := readFeedback(t, f.do(http.MethodGet, "/api/v2/openrig/feedback", "user-jwt", ""))
	if body.Total != 1 || len(body.Layers) != 1 || body.Layers[0].Layer != "workspace" {
		t.Fatalf("user A read = %+v, want the one workspace report", body)
	}
	if f.source.lastUser != tokenTestUserA {
		t.Fatalf("list was scoped to %q, want user A", f.source.lastUser)
	}

	f.user = tokenTestUserB
	rec := f.do(http.MethodGet, "/api/v2/openrig/feedback", "user-jwt", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d want 200: %s", rec.Code, rec.Body.String())
	}
	if got := rec.Body.String(); got != `{"success":true,"total":0,"layers":[]}` {
		t.Fatalf("empty channel = %s, want the empty envelope", got)
	}
}

// TestSeatFeedbackUnauthenticatedIsForbidden pins the shared auth failure the page must expect:
// no header, or a header that is not a bearer, is 403 {"detail":"Not authenticated"} before any
// provider logic runs.
func TestSeatFeedbackUnauthenticatedIsForbidden(t *testing.T) {
	f := newFeedbackFixture(t)
	for _, tc := range []struct {
		name   string
		header string
	}{
		{"no authorization header", ""},
		{"not a bearer scheme", "Basic abc"},
		{"bearer with no token", "Bearer "},
	} {
		t.Run(tc.name, func(t *testing.T) {
			for _, method := range []string{http.MethodGet, http.MethodPost} {
				req := httptest.NewRequest(method, "/api/v2/openrig/feedback", strings.NewReader(`{}`))
				if tc.header != "" {
					req.Header.Set("Authorization", tc.header)
				}
				rec := httptest.NewRecorder()
				f.mux.ServeHTTP(rec, req)
				if rec.Code != http.StatusForbidden || !strings.Contains(rec.Body.String(), "Not authenticated") {
					t.Fatalf("%s: %d %s", method, rec.Code, rec.Body.String())
				}
			}
		})
	}
}
