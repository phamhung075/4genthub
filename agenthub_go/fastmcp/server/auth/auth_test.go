package auth_test

import (
	"testing"

	"agenthub/fastmcp/server/auth"
)

func TestOAuthCompatDefaults(t *testing.T) {
	cro := auth.NewClientRegistrationOptions()
	if cro.Enabled || cro.ClientName != nil || cro.RedirectURIs == nil || len(cro.RedirectURIs) != 0 {
		t.Fatalf("ClientRegistrationOptions defaults wrong: %+v", cro)
	}
	ro := auth.NewRevocationOptions()
	if ro.Enabled || ro.RevocationEndpoint != nil {
		t.Fatalf("RevocationOptions defaults wrong: %+v", ro)
	}
	ac := auth.NewAccessToken("tok")
	if ac.TokenType != "Bearer" || ac.ExpiresIn != nil || ac.Scope != nil {
		t.Fatalf("AccessToken defaults wrong: %+v", ac)
	}
	p := auth.NewOAuthProvider("https://issuer", nil, cro, ro, nil)
	if p.IssuerURL != "https://issuer" || p.RequiredScopes == nil || len(p.RequiredScopes) != 0 {
		t.Fatalf("OAuthProvider defaults wrong: %+v", p)
	}
	if p.ClientRegistrationOptions != cro || p.RevocationOptions != ro {
		t.Fatal("options not stored")
	}
}
