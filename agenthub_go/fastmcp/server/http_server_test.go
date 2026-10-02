package server

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"

	"agenthub/fastmcp/auth/mcp_integration"
)

type fakeVerifier struct{ got string }

func (f *fakeVerifier) VerifyToken(ctx context.Context, token string) *mcp_integration.AccessToken {
	f.got = token
	return &mcp_integration.AccessToken{Token: token, ClientID: "verify-provider"}
}

type fakeLoader struct{}

func (fakeLoader) LoadAccessToken(ctx context.Context, token string) *mcp_integration.AccessToken {
	return &mcp_integration.AccessToken{Token: token, ClientID: "oauth-provider"}
}

type fakeExtractor struct{}

func (fakeExtractor) ExtractUserFromToken(token string) string { return "user-42" }

type fakeExtractorEmpty struct{}

func (fakeExtractorEmpty) ExtractUserFromToken(token string) string { return "" }

func TestTokenVerifierAdapterVerifyToken(t *testing.T) {
	v := &fakeVerifier{}
	tok := NewTokenVerifierAdapter(v).VerifyToken(context.Background(), "abc")
	if tok == nil || tok.ClientID != "verify-provider" || v.got != "abc" {
		t.Fatalf("verify branch: got %+v", tok)
	}
}

func TestTokenVerifierAdapterLoadAccessToken(t *testing.T) {
	tok := NewTokenVerifierAdapter(fakeLoader{}).VerifyToken(context.Background(), "abc")
	if tok == nil || tok.ClientID != "oauth-provider" {
		t.Fatalf("load branch: got %+v", tok)
	}
}

func TestTokenVerifierAdapterExtractUser(t *testing.T) {
	tok := NewTokenVerifierAdapter(fakeExtractor{}).VerifyToken(context.Background(), "abc")
	if tok == nil || tok.ClientID != "user-42" || tok.Token != "abc" {
		t.Fatalf("extract branch: got %+v", tok)
	}
	if len(tok.Scopes) != 1 || tok.Scopes[0] != "execute:mcp" {
		t.Fatalf("extract scopes: got %+v", tok.Scopes)
	}
	if got := NewTokenVerifierAdapter(fakeExtractorEmpty{}).VerifyToken(context.Background(), "abc"); got != nil {
		t.Fatalf("empty extractor expected nil, got %+v", got)
	}
}

func TestTokenVerifierAdapterUnknownProvider(t *testing.T) {
	if got := NewTokenVerifierAdapter(struct{}{}).VerifyToken(context.Background(), "abc"); got != nil {
		t.Fatalf("unknown provider expected nil, got %+v", got)
	}
}

func newMiddleware(next http.Handler, origins []string) http.Handler {
	return NewMCPHeaderValidationMiddleware(next, origins)
}

func TestMCPHeaderValidationContentType(t *testing.T) {
	called := false
	h := newMiddleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { called = true }), []string{"https://app.example"})
	rec := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/mcp", nil)
	req.Header.Set("Content-Type", "text/plain")
	req.Header.Set("Origin", "https://app.example")
	h.ServeHTTP(rec, req)
	if called || rec.Code != 415 {
		t.Fatalf("expected 415 and no next, got %d called=%v", rec.Code, called)
	}
	if body := rec.Body.String(); body != `{"error":"Content-Type must be application/json"}` {
		t.Fatalf("body: %s", body)
	}
	if got := rec.Header().Get("Access-Control-Allow-Origin"); got != "https://app.example" {
		t.Fatalf("ACAO: %q", got)
	}
}

func TestMCPHeaderValidationAcceptPost(t *testing.T) {
	h := newMiddleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {}), nil)
	rec := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/mcp", nil)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/json")
	h.ServeHTTP(rec, req)
	if rec.Code != 406 {
		t.Fatalf("expected 406, got %d", rec.Code)
	}
	if body := rec.Body.String(); body != `{"error":"Accept header must include both application/json and text/event-stream"}` {
		t.Fatalf("body: %s", body)
	}
}

func TestMCPHeaderValidationAcceptGet(t *testing.T) {
	h := newMiddleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {}), nil)
	rec := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/mcp", nil)
	req.Header.Set("Accept", "application/json")
	h.ServeHTTP(rec, req)
	if rec.Code != 406 {
		t.Fatalf("expected 406, got %d", rec.Code)
	}
	if body := rec.Body.String(); body != `{"error":"Accept header must include text/event-stream for SSE"}` {
		t.Fatalf("body: %s", body)
	}
}

func TestMCPHeaderValidationPassThrough(t *testing.T) {
	called := false
	h := newMiddleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { called = true; w.WriteHeader(http.StatusNoContent) }), nil)
	rec := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/mcp/initialize", nil)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/json, text/event-stream")
	h.ServeHTTP(rec, req)
	if !called || rec.Code != http.StatusNoContent {
		t.Fatalf("expected next, got %d called=%v", rec.Code, called)
	}

	called = false
	rec = httptest.NewRecorder()
	req = httptest.NewRequest(http.MethodGet, "/other", nil)
	h.ServeHTTP(rec, req)
	if !called {
		t.Fatal("non-/mcp path should pass through")
	}
}

func TestMCPHeaderValidationCORSFallback(t *testing.T) {
	h := newMiddleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {}), []string{"https://a.example", "https://b.example"})
	rec := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/mcp", nil)
	req.Header.Set("Content-Type", "text/plain")
	req.Header.Set("Origin", "https://other.example")
	h.ServeHTTP(rec, req)
	if got := rec.Header().Get("Access-Control-Allow-Origin"); got != "https://a.example" {
		t.Fatalf("fallback ACAO: %q", got)
	}
	if got := rec.Header().Get("Access-Control-Allow-Credentials"); got != "true" {
		t.Fatalf("ACAC: %q", got)
	}
}
