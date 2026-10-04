package httpapp

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

// corsPreflight issues an OPTIONS preflight for origin with the headers a browser sends.
func corsPreflight(h http.Handler, origin string) *httptest.ResponseRecorder {
	req := httptest.NewRequest(http.MethodOptions, "/api/v2/projects/", nil)
	req.Header.Set("Origin", origin)
	req.Header.Set("Access-Control-Request-Method", "POST")
	req.Header.Set("Access-Control-Request-Headers", "authorization,content-type")
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

// An allowed preflight is answered by the middleware: 200, the origin echoed, credentials,
// methods, the requested headers and the 600s cache.
func TestWithCORSPreflightAllowedOrigin(t *testing.T) {
	t.Setenv("CORS_ORIGINS", "https://www.4genthub.com, https://app.4genthub.com")
	h := withCORS(http.HandlerFunc(func(http.ResponseWriter, *http.Request) {
		t.Error("preflight reached the next handler")
	}))

	rec := corsPreflight(h, "https://www.4genthub.com")
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	if got := rec.Header().Get("Access-Control-Allow-Origin"); got != "https://www.4genthub.com" {
		t.Errorf("Access-Control-Allow-Origin = %q, want the origin echoed", got)
	}
	if got := rec.Header().Get("Access-Control-Allow-Credentials"); got != "true" {
		t.Errorf("Access-Control-Allow-Credentials = %q, want true", got)
	}
	if got := rec.Header().Get("Access-Control-Allow-Methods"); got == "" {
		t.Error("missing Access-Control-Allow-Methods")
	}
	if got := rec.Header().Get("Access-Control-Allow-Headers"); got != "authorization,content-type" {
		t.Errorf("Access-Control-Allow-Headers = %q, want the requested headers", got)
	}
	if got := rec.Header().Get("Access-Control-Max-Age"); got != "600" {
		t.Errorf("Access-Control-Max-Age = %q, want 600", got)
	}
}

// The default when CORS_ORIGINS is unset is ["*"]; with credentials the preflight still
// mirrors the specific origin (Starlette behavior), never a bare "*".
func TestWithCORSPreflightDefaultWildcard(t *testing.T) {
	t.Setenv("CORS_ORIGINS", "")
	h := withCORS(http.HandlerFunc(func(http.ResponseWriter, *http.Request) {
		t.Error("preflight reached the next handler")
	}))

	rec := corsPreflight(h, "https://anything.example")
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	if got := rec.Header().Get("Access-Control-Allow-Origin"); got != "https://anything.example" {
		t.Errorf("Access-Control-Allow-Origin = %q, want the origin echoed", got)
	}
	if got := rec.Header().Get("Access-Control-Allow-Credentials"); got != "true" {
		t.Errorf("Access-Control-Allow-Credentials = %q, want true", got)
	}
}

// A disallowed origin gets no Access-Control-Allow-Origin. Starlette still answers 400 with
// the non-origin preflight headers, so that is the header that decides the policy.
func TestWithCORSPreflightDisallowedOrigin(t *testing.T) {
	t.Setenv("CORS_ORIGINS", "https://www.4genthub.com")
	h := withCORS(http.HandlerFunc(func(http.ResponseWriter, *http.Request) {
		t.Error("preflight reached the next handler")
	}))

	rec := corsPreflight(h, "https://evil.example")
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want 400 (Starlette Disallowed CORS origin)", rec.Code)
	}
	if got := rec.Header().Get("Access-Control-Allow-Origin"); got != "" {
		t.Errorf("Access-Control-Allow-Origin = %q, want empty", got)
	}
}

// A normal (non-preflight) request from an allowed origin is still stamped with the CORS
// headers so the browser can read the response.
func TestWithCORSSimpleRequestAllowedOrigin(t *testing.T) {
	t.Setenv("CORS_ORIGINS", "https://www.4genthub.com")
	h := withCORS(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusNoContent)
	}))

	req := httptest.NewRequest(http.MethodGet, "/api/v2/projects/", nil)
	req.Header.Set("Origin", "https://www.4genthub.com")
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)

	if rec.Code != http.StatusNoContent {
		t.Fatalf("status = %d, want 204", rec.Code)
	}
	if got := rec.Header().Get("Access-Control-Allow-Origin"); got != "https://www.4genthub.com" {
		t.Errorf("Access-Control-Allow-Origin = %q, want the origin echoed", got)
	}
	if got := rec.Header().Get("Access-Control-Allow-Credentials"); got != "true" {
		t.Errorf("Access-Control-Allow-Credentials = %q, want true", got)
	}
	if got := rec.Header().Get("Access-Control-Expose-Headers"); got != "*" {
		t.Errorf("Access-Control-Expose-Headers = %q, want *", got)
	}
}

// With the default wildcard and no Cookie, a simple request gets a bare "*" (Starlette's
// allow_all_origins without the cookie exception). A credentials:'include' fetch is rejected
// by the browser on this path, so it is pinned here.
func TestWithCORSSimpleRequestDefaultWildcardWithoutCookie(t *testing.T) {
	t.Setenv("CORS_ORIGINS", "")
	h := withCORS(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusNoContent)
	}))

	req := httptest.NewRequest(http.MethodGet, "/api/v2/projects/", nil)
	req.Header.Set("Origin", "https://anything.example")
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)

	if got := rec.Header().Get("Access-Control-Allow-Origin"); got != "*" {
		t.Errorf("Access-Control-Allow-Origin = %q, want * (no Cookie, wildcard default)", got)
	}
	if got := rec.Header().Get("Access-Control-Allow-Credentials"); got != "true" {
		t.Errorf("Access-Control-Allow-Credentials = %q, want true", got)
	}
}

// The same default wildcard WITH a Cookie echoes the request origin (Starlette's
// allow_all_origins + has_cookie exception), which is what a real logged-in dashboard
// session sends, so the dashboard works on the default.
func TestWithCORSSimpleRequestDefaultWildcardWithCookie(t *testing.T) {
	t.Setenv("CORS_ORIGINS", "")
	h := withCORS(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusNoContent)
	}))

	req := httptest.NewRequest(http.MethodGet, "/api/v2/projects/", nil)
	req.Header.Set("Origin", "https://www.4genthub.com")
	req.Header.Set("Cookie", "access_token=x")
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)

	if got := rec.Header().Get("Access-Control-Allow-Origin"); got != "https://www.4genthub.com" {
		t.Errorf("Access-Control-Allow-Origin = %q, want the origin echoed (Cookie present)", got)
	}
	if got := rec.Header().Get("Access-Control-Allow-Credentials"); got != "true" {
		t.Errorf("Access-Control-Allow-Credentials = %q, want true", got)
	}
}
