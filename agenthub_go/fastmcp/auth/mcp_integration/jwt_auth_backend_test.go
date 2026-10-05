package mcp_integration

import (
	"context"
	"encoding/base64"
	"testing"

	domServices "agenthub/fastmcp/auth/domain/services"
)

func unsignedJWT(payloadJSON string) string {
	enc := func(s string) string { return base64.RawURLEncoding.EncodeToString([]byte(s)) }
	return enc(`{"alg":"HS256","typ":"JWT"}`) + "." + enc(payloadJSON) + "."
}

func hasAll(got []string, want ...string) bool {
	set := map[string]struct{}{}
	for _, s := range got {
		set[s] = struct{}{}
	}
	for _, w := range want {
		if _, ok := set[w]; !ok {
			return false
		}
	}
	return true
}

func hasNone(got []string, unwanted ...string) bool {
	set := map[string]struct{}{}
	for _, s := range got {
		set[s] = struct{}{}
	}
	for _, w := range unwanted {
		if _, ok := set[w]; ok {
			return false
		}
	}
	return true
}

func TestMapRolesToScopes(t *testing.T) {
	b := &JWTAuthBackend{}

	admin := b.MapRolesToScopes([]string{"admin"})
	if !hasAll(admin, "mcp:access", "mcp:admin", "mcp:write", "projects:create", "tasks:delete", "contexts:delegate", "mcp:execute") {
		t.Fatalf("admin scopes missing expected: %v", admin)
	}

	dev := b.MapRolesToScopes([]string{"developer"})
	if !hasAll(dev, "mcp:access", "mcp:write", "projects:read", "projects:update", "tasks:delete", "contexts:delegate") {
		t.Fatalf("developer scopes missing expected: %v", dev)
	}
	if !hasNone(dev, "mcp:admin", "projects:create", "projects:delete", "agents:create") {
		t.Fatalf("developer scopes contain unexpected: %v", dev)
	}

	user := b.MapRolesToScopes([]string{"user"})
	if !hasAll(user, "mcp:access", "projects:read", "tasks:create", "tasks:update", "contexts:update") {
		t.Fatalf("user scopes missing expected: %v", user)
	}
	if !hasNone(user, "mcp:admin", "mcp:write", "projects:create", "tasks:delete", "contexts:delete", "contexts:delegate") {
		t.Fatalf("user scopes contain unexpected: %v", user)
	}

	none := b.MapRolesToScopes([]string{})
	if len(none) != 1 || none[0] != "mcp:access" {
		t.Fatalf("empty roles should yield only mcp:access, got %v", none)
	}
}

func TestGetCurrentUserID(t *testing.T) {
	b := &JWTAuthBackend{}
	token := unsignedJWT(`{"sub":"user-42"}`)
	got := b.GetCurrentUserID(token)
	if got == nil || *got != "user-42" {
		t.Fatalf("expected user-42, got %v", got)
	}

	if b.GetCurrentUserID("not-a-token") != nil {
		t.Fatal("invalid token should return nil")
	}
}

func TestVerifyTokenLocal(t *testing.T) {
	t.Setenv("JWT_SECRET_KEY", "0123456789abcdef0123456789abcdef")
	svc, err := domServices.NewJWTService("0123456789abcdef0123456789abcdef", domServices.DefaultIssuer)
	if err != nil {
		t.Fatal(err)
	}
	token, err := svc.CreateAccessToken("user-1", "u@example.com", []string{"user"}, nil, "mcp-server")
	if err != nil {
		t.Fatal(err)
	}

	b, err := NewJWTAuthBackend(svc, nil, nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	at := b.VerifyToken(context.Background(), token)
	if at == nil {
		t.Fatal("expected AccessToken")
	}
	if at.ClientID != "user-1" {
		t.Fatalf("client id = %q", at.ClientID)
	}
	if !hasAll(at.Scopes, "mcp:access", "tasks:create", "projects:read") {
		t.Fatalf("scopes = %v", at.Scopes)
	}
	if at.ExpiresAt == nil {
		t.Fatal("expected expires_at set")
	}
}

func TestConfigureJWTFromEnvMissingSecret(t *testing.T) {
	t.Setenv("JWT_SECRET_KEY", "")
	// LookupEnv sees the empty value, which is falsy in Python.
	if _, err := ConfigureJWTFromEnv(); err == nil {
		t.Fatal("expected ValueError for missing secret")
	}

	t.Setenv("JWT_SECRET_KEY", "0123456789abcdef0123456789abcdef")
	cfg, err := ConfigureJWTFromEnv()
	if err != nil {
		t.Fatal(err)
	}
	if keys := cfg.Keys(); len(keys) != 6 || keys[0] != "secret_key" || keys[5] != "refresh_token_expire_days" {
		t.Fatalf("unexpected config keys: %v", keys)
	}
	if v, _ := cfg.Get("audience"); v != "mcp-server" {
		t.Fatalf("audience = %v", v)
	}
	if v, _ := cfg.Get("access_token_expire_minutes"); v != 15 {
		t.Fatalf("access minutes = %v", v)
	}

	ok, err := ValidateJWTConfiguration()
	if err != nil || !ok {
		t.Fatalf("validate = %v, %v", ok, err)
	}
}

func TestValidateJWTConfigurationWeakSecret(t *testing.T) {
	t.Setenv("JWT_SECRET_KEY", "short")
	ok, err := ValidateJWTConfiguration()
	if ok || err == nil {
		t.Fatalf("expected validation error, got ok=%v err=%v", ok, err)
	}
	if err.Error() != "JWT configuration validation failed: JWT_SECRET_KEY should be at least 32 characters for security" {
		t.Fatalf("message = %q", err.Error())
	}
}
