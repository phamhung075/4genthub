package middleware

import (
	"net/http"
	"net/http/httptest"
	"reflect"
	"testing"

	domainservices "agenthub/fastmcp/auth/domain/services"
)

// Expectations transcribed from jwt_auth_middleware.py.

func TestGetAuthStatus(t *testing.T) {
	m := NewJWTAuthMiddleware("some-secret", "HS256", true)
	status := m.GetAuthStatus()

	want := []string{"enabled", "algorithm", "secret_configured", "middleware", "features"}
	if !reflect.DeepEqual(status.Keys(), want) {
		t.Fatalf("status keys = %v, want %v", status.Keys(), want)
	}
	if v, _ := status.Get("middleware"); v != "JWTAuthMiddleware" {
		t.Fatalf("middleware = %v", v)
	}
	if _, ok := status.Get("features"); !ok {
		t.Fatal("features missing")
	}
}

func TestExtractUserFromToken(t *testing.T) {
	secret := "test-secret-key"
	svc, err := domainservices.NewJWTService(secret, domainservices.DefaultIssuer)
	if err != nil {
		t.Fatal(err)
	}

	token, err := svc.CreateAccessToken("user-uuid-1", "u@example.com", nil, nil, "authenticated")
	if err != nil {
		t.Fatal(err)
	}

	m := NewJWTAuthMiddleware(secret, "HS256", true)
	if got := m.ExtractUserFromToken(token); got == nil || *got != "user-uuid-1" {
		t.Fatalf("audience token user = %v", got)
	}
	// Bearer prefix is stripped.
	if got := m.ExtractUserFromToken("Bearer " + token); got == nil || *got != "user-uuid-1" {
		t.Fatalf("bearer token user = %v", got)
	}
	// Wrong secret must fail.
	other := NewJWTAuthMiddleware("different-secret", "HS256", true)
	if got := other.ExtractUserFromToken(token); got != nil {
		t.Fatalf("wrong secret user = %v, want nil", got)
	}
}

func TestCreateAuthMiddleware(t *testing.T) {
	m := CreateAuthMiddleware("k", "HS256")
	if m == nil || m.Algorithm != "HS256" || !m.Enabled {
		t.Fatalf("unexpected middleware %+v", m)
	}
}

func TestDualDetectRequestType(t *testing.T) {
	m := &DualAuthMiddleware{}

	cases := []struct {
		method, target, contentType, accept, userAgent string
		want                                           string
	}{
		{"POST", "/mcp", "", "", "", "mcp"},
		{"POST", "/api/v2/tasks", "", "", "", "frontend"},
		{"GET", "/api/things", "", "", "", "frontend"},
		{"GET", "/other", "", "", "Mozilla/5.0", "frontend"},
		{"GET", "/other", "application/json", "application/json, jsonrpc", "", "mcp"},
		{"GET", "/other", "", "", "", "unknown"},
	}
	for _, c := range cases {
		r := httptest.NewRequest(c.method, c.target, nil)
		if c.contentType != "" {
			r.Header.Set("content-type", c.contentType)
		}
		if c.accept != "" {
			r.Header.Set("accept", c.accept)
		}
		if c.userAgent != "" {
			r.Header.Set("user-agent", c.userAgent)
		}
		if got := m.DetectRequestType(r); got != c.want {
			t.Errorf("DetectRequestType(%s/%s) = %q, want %q", c.method, c.target, got, c.want)
		}
	}

	r := httptest.NewRequest("POST", "/x", nil)
	r.Header.Set("mcp-protocol-version", "2024-11-05")
	if got := m.DetectRequestType(r); got != "mcp" {
		t.Fatalf("mcp-protocol-version header = %q", got)
	}
}

func TestDualShouldSkipAuth(t *testing.T) {
	m := &DualAuthMiddleware{}
	for _, path := range []string{"/health", "/ai_docs/x", "/redoc", "/openapi.json", "/favicon.ico", "/static/x"} {
		if !m.ShouldSkipAuth(httptest.NewRequest("GET", path, nil)) {
			t.Errorf("ShouldSkipAuth(%s) = false, want true", path)
		}
	}
	if m.ShouldSkipAuth(httptest.NewRequest("GET", "/api/v2/tasks", nil)) {
		t.Fatal("ShouldSkipAuth(/api/v2/tasks) = true, want false")
	}
}

func TestDualExtractToken(t *testing.T) {
	m := &DualAuthMiddleware{}

	r := httptest.NewRequest("GET", "/", nil)
	r.Header.Set("authorization", "Bearer abc")
	if got := m.ExtractToken(r); got == nil || *got != "abc" {
		t.Fatalf("bearer = %v", got)
	}

	r = httptest.NewRequest("GET", "/", nil)
	r.Header.Set("authorization", "Token tok")
	if got := m.ExtractToken(r); got == nil || *got != "tok" {
		t.Fatalf("token prefix = %v", got)
	}

	r = httptest.NewRequest("GET", "/", nil)
	r.Header.Set("x-mcp-token", "mcp1")
	if got := m.ExtractToken(r); got == nil || *got != "mcp1" {
		t.Fatalf("x-mcp-token = %v", got)
	}

	r = httptest.NewRequest("GET", "/", nil)
	r.AddCookie(&http.Cookie{Name: "access_token", Value: "cookie-tok"})
	if got := m.ExtractToken(r); got == nil || *got != "cookie-tok" {
		t.Fatalf("cookie = %v", got)
	}

	r = httptest.NewRequest("GET", "/?token=query-tok", nil)
	if got := m.ExtractToken(r); got == nil || *got != "query-tok" {
		t.Fatalf("query = %v", got)
	}

	if got := m.ExtractToken(httptest.NewRequest("GET", "/", nil)); got != nil {
		t.Fatalf("no token = %v, want nil", got)
	}
}

func TestDualErrorResponses(t *testing.T) {
	m := &DualAuthMiddleware{}

	mcp := m.CreateAuthErrorResponse("mcp", "bad")
	if mcp.StatusCode != 401 {
		t.Fatalf("mcp status = %d", mcp.StatusCode)
	}
	if !reflect.DeepEqual(mcp.Content.Keys(), []string{"jsonrpc", "error", "id"}) {
		t.Fatalf("mcp content keys = %v", mcp.Content.Keys())
	}
	if v, _ := mcp.Content.Get("id"); v != nil {
		t.Fatalf("mcp id = %v, want nil", v)
	}

	front := m.CreateAuthErrorResponse("frontend", "bad")
	if front.StatusCode != 401 {
		t.Fatalf("frontend status = %d", front.StatusCode)
	}
	if !reflect.DeepEqual(front.Content.Keys(), []string{"detail", "auth_type"}) {
		t.Fatalf("frontend content keys = %v", front.Content.Keys())
	}
	if v, _ := front.Content.Get("auth_type"); v != "bearer_or_cookie_required" {
		t.Fatalf("frontend auth_type = %v", v)
	}
}

func TestDualAuthenticateRequestNoToken(t *testing.T) {
	m := &DualAuthMiddleware{}
	r := httptest.NewRequest("GET", "/api/v2/x", nil)
	got, err := m.AuthenticateRequest(r.Context(), r, "frontend")
	if err != nil {
		t.Fatal(err)
	}
	if got != nil {
		t.Fatalf("no token result = %v, want nil", got)
	}
}
