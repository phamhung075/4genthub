package api

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
)

func TestExtractBearerToken(t *testing.T) {
	req := httptest.NewRequest("GET", "/", nil)
	_, err := ExtractBearerToken(req)
	if err == nil {
		t.Fatalf("expected error for missing header")
	}

	req.Header.Set("Authorization", "InvalidFormat")
	_, err = ExtractBearerToken(req)
	if err == nil {
		t.Fatalf("expected error for invalid format")
	}

	req.Header.Set("Authorization", "Bearer valid-token-123")
	tok, err := ExtractBearerToken(req)
	if err != nil || tok != "valid-token-123" {
		t.Fatalf("expected valid token, got %s, err: %v", tok, err)
	}
}

func TestSupabaseEndpointsHTTP(t *testing.T) {
	ctrl := NewSupabaseAuthController()
	mux := http.NewServeMux()
	ctrl.RegisterRoutes(mux)

	// GET /auth/supabase/health
	req := httptest.NewRequest("GET", "/auth/supabase/health", nil)
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	// Even if unconfigured, returns 503 or 200 with status info
	if w.Code != http.StatusOK && w.Code != http.StatusServiceUnavailable {
		t.Fatalf("expected 200 or 503, got %d", w.Code)
	}

	// POST /auth/supabase/signup with invalid password
	body, _ := json.Marshal(SignUpRequest{
		Email:    "test@example.com",
		Password: "123", // too short
	})
	req = httptest.NewRequest("POST", "/auth/supabase/signup", bytes.NewReader(body))
	w = httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	if w.Code != http.StatusBadRequest && w.Code != http.StatusInternalServerError {
		t.Fatalf("expected 400 or 500, got %d", w.Code)
	}

	// GET /auth/supabase/oauth/google
	os.Setenv("SUPABASE_URL", "http://localhost:54321")
	os.Setenv("SUPABASE_ANON_KEY", "dummy-anon-key")
	defer os.Unsetenv("SUPABASE_URL")
	defer os.Unsetenv("SUPABASE_ANON_KEY")
	req = httptest.NewRequest("GET", "/auth/supabase/oauth/google", nil)
	w = httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("expected 200 for oauth url, got %d: %s", w.Code, w.Body.String())
	}
}
