package auth_test

import (
	"errors"
	"testing"

	"agenthub/fastmcp/server/auth"
	"agenthub/fastmcp/server/auth/providers"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

func TestCreateMCPAuthProviderNoneAndEnv(t *testing.T) {
	p, err := auth.CreateMCPAuthProvider("none", nil, nil, true)
	if err != nil || p != nil {
		t.Fatalf("none: %v %v", p, err)
	}
	p, err = auth.CreateMCPAuthProvider("env", nil, nil, true)
	if err != nil || p != nil {
		t.Fatalf("env: %v %v", p, err)
	}
}

func TestCreateMCPAuthProviderJWT(t *testing.T) {
	secret := "k"
	p, err := auth.CreateMCPAuthProvider("jwt", &secret, nil, true)
	if err != nil {
		t.Fatal(err)
	}
	if _, ok := p.(*providers.JWTBearerAuthProvider); !ok {
		t.Fatalf("expected JWTBearerAuthProvider, got %T", p)
	}
}

func TestCreateMCPAuthProviderUnknown(t *testing.T) {
	_, err := auth.CreateMCPAuthProvider("bogus", nil, nil, true)
	var ve *value_objects.ValueError
	if !errors.As(err, &ve) || ve.Msg != "Unknown auth_type: bogus" {
		t.Fatalf("err = %v", err)
	}
}

func TestGetDefaultAuthProviderDisabled(t *testing.T) {
	t.Setenv("AUTH_ENABLED", "false")
	p, err := auth.GetDefaultAuthProvider()
	if err != nil || p != nil {
		t.Fatalf("got %v %v", p, err)
	}
}

func TestGetDefaultAuthProviderAutoDetect(t *testing.T) {
	t.Setenv("AUTH_ENABLED", "true")
	t.Setenv("MCP_AUTH_TYPE", "")
	t.Setenv("JWT_SECRET_KEY", "k")
	t.Setenv("MCP_BEARER_TOKEN", "")
	p, err := auth.GetDefaultAuthProvider()
	if err != nil {
		t.Fatal(err)
	}
	if _, ok := p.(*providers.JWTBearerAuthProvider); !ok {
		t.Fatalf("expected JWT provider, got %T", p)
	}
}

func TestConfigureMCPServerAuth(t *testing.T) {
	t.Setenv("AUTH_ENABLED", "false")
	srv := &auth.MCPServerInstance{}
	got, err := auth.ConfigureMCPServerAuth(srv)
	if err != nil || got != srv || got.Auth != nil {
		t.Fatalf("got %v %v", got, err)
	}
}
