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
