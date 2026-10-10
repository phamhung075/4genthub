package httpapp

import (
	"context"
	"crypto/tls"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	authinterface "agenthub/fastmcp/auth/interface"
	"agenthub/fastmcp/seat_management/domain/repositories"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// authenticateTestUser makes currentUser resolve to a valid UUID user so the authed
// handlers run instead of returning 403.
func authenticateTestUser(t *testing.T) {
	t.Helper()
	previous := authinterface.GetCurrentUserUniversal
	authinterface.GetCurrentUserUniversal = func(context.Context, string) (*authdomain.User, error) {
		id := "11111111-1111-4111-8111-111111111111"
		return &authdomain.User{ID: &id, Email: "dev@example.com", Username: "dev"}, nil
	}
	t.Cleanup(func() { authinterface.GetCurrentUserUniversal = previous })
}

func doTestRequest(t *testing.T, mux *http.ServeMux, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	req.Header.Set("Authorization", "Bearer test-token")
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)
	return rec
}

type fakeSeatSource struct {
	resolved *repositories.ResolvedSeat
	err      error
	seeded   int
}

func (f *fakeSeatSource) ResolveSeat(_ context.Context, _, _, _ string) (*repositories.ResolvedSeat, error) {
	return f.resolved, f.err
}

func (f *fakeSeatSource) SeedSeatTypes(_ context.Context, _ string) (int, error) {
	return f.seeded, f.err
}

func seatTestMux(t *testing.T, source seatSource) *http.ServeMux {
	t.Helper()
	previous := newSeatSource
	newSeatSource = func(*database.SessionManager, string) (seatSource, error) { return source, nil }
	t.Cleanup(func() { newSeatSource = previous })
	authenticateTestUser(t)
	mux := http.NewServeMux()
	mountSeatRoutes(mux, nil)
	return mux
}

func TestResolveSeatReturnsSnapshot(t *testing.T) {
	t.Setenv(publicURLEnv, "https://api.example.test")
	mux := seatTestMux(t, &fakeSeatSource{resolved: &repositories.ResolvedSeat{
		Hash: "abc", Runtime: "claude-code",
		Files:  []repositories.ResolvedFile{{Path: "agent.yaml", Content: "name: x"}},
		Policy: map[string]any{"Seat": "coder"},
	}})
	rec := doTestRequest(t, mux, http.MethodGet, "/api/v2/openrig/seats/dev/coder", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d: %s", rec.Code, rec.Body.String())
	}
	for _, want := range []string{`"hash":"abc"`, `"room":"dev"`, `"seat":"coder"`, `"path":"agent.yaml"`, `"Seat":"coder"`} {
		if !strings.Contains(rec.Body.String(), want) {
			t.Errorf("body missing %s: %s", want, rec.Body.String())
		}
	}
}

func TestResolveSeatStatusMapping(t *testing.T) {
	t.Setenv(publicURLEnv, "https://api.example.test")
	cases := []struct {
		err  error
		want int
	}{
		{errors.New(`seat "x" not found in room "dev"`), http.StatusNotFound},
		{errors.New("database down"), http.StatusInternalServerError},
	}
	for _, c := range cases {
		mux := seatTestMux(t, &fakeSeatSource{err: c.err})
		if rec := doTestRequest(t, mux, http.MethodGet, "/api/v2/openrig/seats/dev/x", ""); rec.Code != c.want {
			t.Errorf("%v: status = %d, want %d", c.err, rec.Code, c.want)
		}
	}
}

// capturedSeatMux is seatTestMux with the mcpURL newSeatSource is constructed with captured,
// so a test can assert which origin a rendered seat rewrites its MCP server URL to.
func capturedSeatMux(t *testing.T, source seatSource) (*http.ServeMux, *string) {
	t.Helper()
	var mcpURL string
	previous := newSeatSource
	newSeatSource = func(_ *database.SessionManager, u string) (seatSource, error) {
		mcpURL = u
		return source, nil
	}
	t.Cleanup(func() { newSeatSource = previous })
	authenticateTestUser(t)
	mux := http.NewServeMux()
	mountSeatRoutes(mux, nil)
	return mux, &mcpURL
}

// authedSeatRequest is a seat GET with the given public origin signals and a bearer token.
func authedSeatRequest(host string, tlsTerminated bool, headers map[string]string) *http.Request {
	req := httptest.NewRequest(http.MethodGet, "/api/v2/openrig/seats/dev/coder", nil)
	if host != "" {
		req.Host = host
	}
	if tlsTerminated {
		req.TLS = &tls.ConnectionState{}
	}
	for k, v := range headers {
		req.Header.Set(k, v)
	}
	req.Header.Set("Authorization", "Bearer test-token")
	return req
}

func TestResolveSeatDerivesPublicURLFromRequest(t *testing.T) {
	t.Setenv(publicURLEnv, "")
	mux, mcpURL := capturedSeatMux(t, &fakeSeatSource{resolved: &repositories.ResolvedSeat{Hash: "abc", Runtime: "claude-code"}})

	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, authedSeatRequest("seats.example.test", true, nil))
	if rec.Code != http.StatusOK {
		t.Fatalf("without %s: status = %d, want 200: %s", publicURLEnv, rec.Code, rec.Body.String())
	}
	if *mcpURL != "https://seats.example.test/mcp" {
		t.Errorf("rendered MCP URL = %q, want the request origin", *mcpURL)
	}
}

func TestResolveSeatPinnedURLWinsOverRequestHost(t *testing.T) {
	t.Setenv(publicURLEnv, "https://pinned.example.test/")
	mux, mcpURL := capturedSeatMux(t, &fakeSeatSource{resolved: &repositories.ResolvedSeat{Hash: "abc", Runtime: "claude-code"}})

	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, authedSeatRequest("seats.example.test", true, nil))
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200: %s", rec.Code, rec.Body.String())
	}
	if *mcpURL != "https://pinned.example.test/mcp" {
		t.Errorf("rendered MCP URL = %q, want the pinned override", *mcpURL)
	}
}

func TestResolveSeatTrustsForwardedOrigin(t *testing.T) {
	t.Setenv(publicURLEnv, "")
	mux, mcpURL := capturedSeatMux(t, &fakeSeatSource{resolved: &repositories.ResolvedSeat{Hash: "abc", Runtime: "claude-code"}})

	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, authedSeatRequest("internal:8000", false, map[string]string{
		"X-Forwarded-Proto": "https",
		"X-Forwarded-Host":  "public.example.test, internal",
	}))
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200: %s", rec.Code, rec.Body.String())
	}
	if *mcpURL != "https://public.example.test/mcp" {
		t.Errorf("rendered MCP URL = %q, want the forwarded origin", *mcpURL)
	}
}

func TestSeatRoutesDerivePublicURLAndRequireAuth(t *testing.T) {
	t.Setenv(publicURLEnv, "")
	mux := seatTestMux(t, &fakeSeatSource{resolved: &repositories.ResolvedSeat{Hash: "abc", Runtime: "claude-code"}})
	if rec := doTestRequest(t, mux, http.MethodGet, "/api/v2/openrig/seats/dev/x", ""); rec.Code != http.StatusOK {
		t.Errorf("without %s: status = %d, want 200", publicURLEnv, rec.Code)
	}
	bare := httptest.NewRecorder()
	mux.ServeHTTP(bare, httptest.NewRequest(http.MethodGet, "/api/v2/openrig/seats/dev/x", nil))
	if bare.Code == http.StatusNotFound || bare.Code == http.StatusOK {
		t.Errorf("unauthenticated request: status = %d, want 401/403", bare.Code)
	}
}

func TestSeedSeatTypesReportsCount(t *testing.T) {
	t.Setenv(publicURLEnv, "https://api.example.test")
	mux := seatTestMux(t, &fakeSeatSource{seeded: 9})
	rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/seat-types/seed", "")
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"seat_types":9`) {
		t.Errorf("seed: %d %s", rec.Code, rec.Body.String())
	}
}

func TestSeedSeatTypesWorksWithoutPublicURL(t *testing.T) {
	t.Setenv(publicURLEnv, "")
	mux := seatTestMux(t, &fakeSeatSource{seeded: 9})
	rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/seat-types/seed", "")
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"seat_types":9`) {
		t.Errorf("seed without %s: status = %d %s", publicURLEnv, rec.Code, rec.Body.String())
	}
}

func TestSeedSeatTypesErrorMapping(t *testing.T) {
	t.Setenv(publicURLEnv, "")
	mux := seatTestMux(t, &fakeSeatSource{err: errors.New("database down")})
	rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/seat-types/seed", "")
	if rec.Code != http.StatusInternalServerError {
		t.Errorf("seed error: status = %d, want 500", rec.Code)
	}
}

// The chat window's route is the one seat route that carries no room, so its path has the same
// two-segment shape as the resolution GET. The verb is therefore the only thing that can tell the
// two apart, and this is a ROUTING test rather than a validation one: the same path answers
// differently per method, and the answer proves which pattern the mux chose.
func TestSeatMessageRouteIsVerbScoped(t *testing.T) {
	t.Setenv(publicURLEnv, "https://api.example.test")
	mux := seatTestMux(t, &fakeSeatSource{resolved: &repositories.ResolvedSeat{
		Hash: "abc", Runtime: "claude-code", Policy: map[string]any{"Seat": "coder"},
	}})

	// POST reaches the message handler. Before this route was mounted the same request was
	// answered 405 by the GET-only resolution pattern, which is the defect the row reports.
	rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/seats/coder/messages", `{"text":"hello"}`)
	if rec.Code == http.StatusMethodNotAllowed {
		t.Fatalf("POST /seats/coder/messages = 405: the un-mounted defect is back")
	}
	if rec.Code != http.StatusNotImplemented {
		t.Fatalf("POST /seats/coder/messages = %d, want 501: %s", rec.Code, rec.Body.String())
	}
	// The refusal must be a sentence: the window renders error.message verbatim, and the false
	// success this route deliberately does not send would render as nothing at all.
	if !strings.Contains(rec.Body.String(), `"detail"`) || !strings.Contains(rec.Body.String(), "not implemented") {
		t.Fatalf("refusal is not a human-readable detail: %s", rec.Body.String())
	}

	// The SAME path with GET is still the resolution route, with "messages" as the seat key: the
	// path alone cannot decide this route, and the mount must not have taken the GET away.
	getRec := doTestRequest(t, mux, http.MethodGet, "/api/v2/openrig/seats/coder/messages", "")
	if getRec.Code != http.StatusOK {
		t.Fatalf("GET /seats/coder/messages = %d, want the resolution 200: %s", getRec.Code, getRec.Body.String())
	}
	for _, want := range []string{`"room":"coder"`, `"seat":"messages"`} {
		if !strings.Contains(getRec.Body.String(), want) {
			t.Errorf("GET /seats/coder/messages body missing %s: %s", want, getRec.Body.String())
		}
	}
}

// The refusals that come from ROUTING, so that a later change cannot make this route's answer
// depend on what the caller sent.
func TestSeatMessageRouteRefusalsComeFromRouting(t *testing.T) {
	t.Setenv(publicURLEnv, "https://api.example.test")
	mux := seatTestMux(t, &fakeSeatSource{resolved: &repositories.ResolvedSeat{Hash: "abc", Runtime: "claude-code"}})

	// A malformed body is refused for being malformed, which is only reachable if routing
	// already chose this route over the resolution GET.
	if rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/seats/coder/messages", `{"text":`); rec.Code != http.StatusBadRequest {
		t.Errorf("malformed body: status = %d, want 400: %s", rec.Code, rec.Body.String())
	}
	// The body is {text} and nothing else: an unknown field is refused, the room included.
	if rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/seats/coder/messages", `{"room":"coder"}`); rec.Code != http.StatusBadRequest {
		t.Errorf("unknown field: status = %d, want 400: %s", rec.Code, rec.Body.String())
	}
	// The resolution route is GET-only, so its own pattern answers the wrong method.
	if rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/seats/dev/coder", `{"text":"x"}`); rec.Code != http.StatusMethodNotAllowed {
		t.Errorf("POST on the resolution path: status = %d, want 405", rec.Code)
	}
	// Three segments match no pattern at all.
	if rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/seats/a/b/c", `{"text":"x"}`); rec.Code != http.StatusNotFound {
		t.Errorf("unknown subpath: status = %d, want 404", rec.Code)
	}
}

// An unauthenticated window is refused by the auth layer before the handler, with a sentence the
// UI can render.
func TestSeatMessageRouteRequiresAuth(t *testing.T) {
	t.Setenv(publicURLEnv, "https://api.example.test")
	mux := http.NewServeMux()
	mountSeatRoutes(mux, nil)

	// The header is what decides: no usable bearer is the 403 the routes layer answers itself,
	// and it never reaches the handler. A present-but-unusable bearer instead goes through the
	// auth layer, whose answer is the auth layer's to give.
	for _, tc := range []struct {
		name   string
		header string
	}{
		{"no authorization header", ""},
		{"not a bearer scheme", "Basic abc"},
		{"bearer with no token", "Bearer "},
	} {
		req := httptest.NewRequest(http.MethodPost, "/api/v2/openrig/seats/coder/messages", strings.NewReader(`{"text":"hello"}`))
		if tc.header != "" {
			req.Header.Set("Authorization", tc.header)
		}
		rec := httptest.NewRecorder()
		mux.ServeHTTP(rec, req)
		if rec.Code != http.StatusForbidden || !strings.Contains(rec.Body.String(), "Not authenticated") {
			t.Errorf("%s: POST = %d %s, want 403 with a detail", tc.name, rec.Code, rec.Body.String())
		}
	}
}
