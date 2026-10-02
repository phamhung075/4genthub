package authinterface

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
)

func TestValidationFunctions(t *testing.T) {
	// Email validation
	normalized, err := ValidateEmail("User.Name@Example.COM")
	if err != nil || normalized != "user.name@example.com" {
		t.Fatalf("expected valid normalized email, got %s, err: %v", normalized, err)
	}

	_, err = ValidateEmail("invalid-email")
	if err == nil {
		t.Fatalf("expected error for invalid email")
	}

	// Username validation
	if err := ValidateUsername("valid_user-123"); err != nil {
		t.Fatalf("expected valid username, got %v", err)
	}
	if err := ValidateUsername("ab"); err == nil {
		t.Fatalf("expected error for short username")
	}
	if err := ValidateUsername("user with spaces"); err == nil {
		t.Fatalf("expected error for username with spaces")
	}

	// Password validation
	if err := ValidatePassword("ValidPass123!"); err != nil {
		t.Fatalf("expected valid password, got %v", err)
	}
	if err := ValidatePassword("short1!"); err == nil {
		t.Fatalf("expected error for short password")
	}
	if err := ValidatePassword("NoSpecial123"); err == nil {
		t.Fatalf("expected error for missing special character")
	}
	if err := ValidatePassword("nodigits!"); err == nil {
		t.Fatalf("expected error for missing digit")
	}
	if err := ValidatePassword("NO_LOWER_123!"); err == nil {
		t.Fatalf("expected error for missing lowercase")
	}
	if err := ValidatePassword("no_upper_123!"); err == nil {
		t.Fatalf("expected error for missing uppercase")
	}
}

func TestPasswordRequirements(t *testing.T) {
	weakRes := ValidatePasswordRequirements("pass")
	if weakRes.Valid || weakRes.Strength != "weak" {
		t.Fatalf("expected weak invalid password, got %+v", weakRes)
	}

	strongRes := ValidatePasswordRequirements("StrongPassword123!")
	if !strongRes.Valid || strongRes.Strength != "strong" || strongRes.Score < 5 {
		t.Fatalf("expected strong password, got %+v", strongRes)
	}
}

func TestAuthEndpointsHTTP(t *testing.T) {
	os.Setenv("AUTH_PROVIDER", "test")
	defer os.Unsetenv("AUTH_PROVIDER")

	ctrl := NewAuthController()
	mux := http.NewServeMux()
	ctrl.RegisterRoutes(mux)

	// GET /api/auth/verify
	req := httptest.NewRequest("GET", "/api/auth/verify", nil)
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}

	// GET /api/auth/provider
	req = httptest.NewRequest("GET", "/api/auth/provider", nil)
	w = httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}

	// GET /api/auth/password-requirements
	req = httptest.NewRequest("GET", "/api/auth/password-requirements", nil)
	w = httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}

	// POST /api/auth/validate-password
	body, _ := json.Marshal(map[string]string{"password": "Password123!"})
	req = httptest.NewRequest("POST", "/api/auth/validate-password", bytes.NewReader(body))
	w = httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}
	var valRes PasswordValidationResult
	_ = json.NewDecoder(w.Body).Decode(&valRes)
	if !valRes.Valid {
		t.Fatalf("expected valid password result")
	}

	// POST /api/auth/register (test mode)
	regBody, _ := json.Marshal(RegisterRequest{
		Email:    "test@example.com",
		Password: "Password123!",
	})
	req = httptest.NewRequest("POST", "/api/auth/register", bytes.NewReader(regBody))
	w = httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("expected 200 for register test mode, got %d: %s", w.Code, w.Body.String())
	}

	// POST /api/auth/login (test mode)
	loginBody, _ := json.Marshal(LoginRequest{
		Email:    "test@example.com",
		Password: "Password123!",
	})
	req = httptest.NewRequest("POST", "/api/auth/login", bytes.NewReader(loginBody))
	w = httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("expected 200 for login, got %d: %s", w.Code, w.Body.String())
	}
	var loginResp LoginResponse
	_ = json.NewDecoder(w.Body).Decode(&loginResp)
	if loginResp.AccessToken == "" {
		t.Fatalf("expected non-empty access token")
	}

	// POST /api/auth/refresh (test mode)
	refBody, _ := json.Marshal(map[string]string{"refresh_token": "dummy-refresh"})
	req = httptest.NewRequest("POST", "/api/auth/refresh", bytes.NewReader(refBody))
	w = httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("expected 200 for refresh, got %d", w.Code)
	}

	// POST /api/auth/logout
	logoutBody, _ := json.Marshal(map[string]string{"refresh_token": "dummy-refresh"})
	req = httptest.NewRequest("POST", "/api/auth/logout", bytes.NewReader(logoutBody))
	w = httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("expected 200 for logout, got %d", w.Code)
	}

	// POST /api/auth/registration-success
	succBody, _ := json.Marshal(map[string]string{"user_id": "u1", "email": "test@example.com"})
	req = httptest.NewRequest("POST", "/api/auth/registration-success", bytes.NewReader(succBody))
	w = httptest.NewRecorder()
	mux.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("expected 200 for registration-success, got %d", w.Code)
	}
}
