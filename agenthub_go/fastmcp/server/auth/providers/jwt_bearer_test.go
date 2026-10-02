package providers_test

import (
	"testing"

	"agenthub/fastmcp/server/auth/providers"
)

func TestJWTBearerRequiresSecret(t *testing.T) {
	t.Setenv("JWT_SECRET_KEY", "")
	p, err := providers.NewJWTBearerAuthProvider(nil, "agenthub", nil, nil, true)
	if err == nil || p != nil {
		t.Fatalf("expected missing secret error, got p=%v err=%v", p, err)
	}
	if err.Error() != "JWT_SECRET_KEY must be provided or set in environment" {
		t.Fatalf("message = %q", err.Error())
	}
}

func TestJWTBearerDefaults(t *testing.T) {
	secret := "s3cr3t"
	p, err := providers.NewJWTBearerAuthProvider(&secret, "agenthub", nil, nil, true)
	if err != nil {
		t.Fatal(err)
	}
	if p.SecretKey != secret || p.Issuer != "agenthub" || !p.CheckDatabase {
		t.Fatalf("provider fields wrong: %+v", p)
	}
	if len(p.RequiredScopes) != 1 || p.RequiredScopes[0] != "mcp:access" {
		t.Fatalf("RequiredScopes = %v", p.RequiredScopes)
	}
}

// Expectations from jwt_bearer.py _validate_user_token.
func TestValidateUserToken(t *testing.T) {
	secret := "s"
	p, _ := providers.NewJWTBearerAuthProvider(&secret, "agenthub", nil, nil, true)

	if got := p.ValidateUserToken("t", map[string]any{"token_type": "refresh", "sub": "u"}); got != nil {
		t.Fatalf("non-access token should be nil, got %+v", got)
	}
	if got := p.ValidateUserToken("t", map[string]any{"token_type": "access"}); got != nil {
		t.Fatalf("missing user id should be nil, got %+v", got)
	}

	got := p.ValidateUserToken("tok", map[string]any{
		"token_type": "access",
		"sub":        "user-1",
		"roles":      []any{"developer"},
		"exp":        123,
	})
	if got == nil {
		t.Fatal("expected token")
	}
	want := []string{"mcp:access", "mcp:write", "mcp:read"}
	if len(got.Scopes) != len(want) {
		t.Fatalf("scopes = %v", got.Scopes)
	}
	for i := range want {
		if got.Scopes[i] != want[i] {
			t.Fatalf("scopes = %v want %v", got.Scopes, want)
		}
	}
	if got.ClientID != "user-1" || got.Token != "tok" || got.ExpiresAt == nil || *got.ExpiresAt != 123 {
		t.Fatalf("token fields wrong: %+v", got)
	}

	admin := p.ValidateUserToken("t", map[string]any{"token_type": "access", "user_id": "u2", "roles": []string{"admin"}})
	if admin.ClientID != "u2" || len(admin.Scopes) != 4 {
		t.Fatalf("admin mapping wrong: %+v", admin)
	}
}

// Expectations from jwt_bearer.py _map_scopes_to_mcp.
func TestMapScopesToMCP(t *testing.T) {
	got := providers.MapScopesToMCP([]string{"read:tasks", "execute:mcp", "read:tasks", "unknown"})
	want := []string{"mcp:read", "mcp:execute"}
	if len(got) != len(want) {
		t.Fatalf("got %v want %v", got, want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("got %v want %v", got, want)
		}
	}
	if providers.MapScopesToMCP(nil) == nil {
		t.Fatal("expected empty non-nil slice")
	}
}
