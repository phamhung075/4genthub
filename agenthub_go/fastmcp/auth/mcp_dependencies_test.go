package auth

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"testing"
	"time"
)

func mcpTestSignHS256(t *testing.T, secret string, payload map[string]any) string {
	t.Helper()
	enc := func(v any) string {
		b, err := json.Marshal(v)
		if err != nil {
			t.Fatal(err)
		}
		return base64.RawURLEncoding.EncodeToString(b)
	}
	header := map[string]any{"alg": "HS256", "typ": "JWT"}
	signingInput := enc(header) + "." + enc(payload)
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write([]byte(signingInput))
	return signingInput + "." + base64.RawURLEncoding.EncodeToString(mac.Sum(nil))
}

func TestGetCurrentMCPUser(t *testing.T) {
	exp := float64(time.Now().Add(time.Hour).Unix())
	token := mcpTestSignHS256(t, frontendJWTSecret, map[string]any{
		"sub":           "user-7",
		"email":         "seven@example.com",
		"username":      "seven",
		"auth_provider": "keycloak",
		"exp":           exp,
	})

	user, httpErr := GetCurrentMCPUser(token)
	if httpErr != nil {
		t.Fatalf("unexpected error: %v", httpErr)
	}
	if user.ID == nil || *user.ID != "user-7" {
		t.Fatalf("id = %v", user.ID)
	}
	if user.Email != "seven@example.com" || user.Username != "seven" {
		t.Fatalf("email/username = %q/%q", user.Email, user.Username)
	}
	if user.PasswordHash != "keycloak-authenticated" {
		t.Fatalf("password_hash = %q", user.PasswordHash)
	}
}

func TestGetCurrentMCPUserMissingID(t *testing.T) {
	token := mcpTestSignHS256(t, frontendJWTSecret, map[string]any{
		"email": "anon@example.com",
		"exp":   float64(time.Now().Add(time.Hour).Unix()),
	})
	_, httpErr := GetCurrentMCPUser(token)
	if httpErr == nil || httpErr.StatusCode != 401 || httpErr.Detail != "Invalid token: missing user ID" {
		t.Fatalf("error = %v", httpErr)
	}
}

func TestGetCurrentMCPUserExpired(t *testing.T) {
	token := mcpTestSignHS256(t, frontendJWTSecret, map[string]any{
		"sub": "user-7",
		"exp": float64(time.Now().Add(-time.Hour).Unix()),
	})
	_, httpErr := GetCurrentMCPUser(token)
	if httpErr == nil || httpErr.StatusCode != 401 || httpErr.Detail != "Token expired" {
		t.Fatalf("error = %v", httpErr)
	}
}

func TestGetOptionalMCPUser(t *testing.T) {
	if GetOptionalMCPUser(nil) != nil {
		t.Fatal("nil token should return nil")
	}
	invalid := "not-a-token"
	if GetOptionalMCPUser(&invalid) != nil {
		t.Fatal("invalid token should return nil")
	}
}
