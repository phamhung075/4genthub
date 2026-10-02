package auth

import (
	"context"
	"crypto"
	"crypto/rand"
	"crypto/rsa"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"math/big"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

// This file exercises the full MCPKeycloakValidator.ValidateMCPToken path
// (JWKS fetch -> kid lookup -> RS256 signature + claim verification -> MCP
// requirement checks) against a locally served JWKS. Tokens are minted with
// only crypto/rsa + encoding/base64 so no JWT dependency is introduced.
//
// MCPKeycloakValidator has no dev-mode switch: unlike MCPKeycloakAuth (which
// short-circuits on AUTH_ENABLED=false) every call to ValidateMCPToken always
// fetches the JWKS and verifies the signature. The only env knobs in the path
// are KEYCLOAK_VERIFY_TOKEN_AUDIENCE and KEYCLOAK_TOKEN_AUDIENCE, which are
// pinned below with t.Setenv.

// jwksTestGenerateKey creates a fresh RSA 2048 key for signing test tokens.
func jwksTestGenerateKey(t *testing.T) *rsa.PrivateKey {
	t.Helper()
	key, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		t.Fatalf("generate RSA key: %v", err)
	}
	return key
}

// jwksTestJWK renders the public half of a key as a single JWK entry.
func jwksTestJWK(kid string, pub *rsa.PublicKey) map[string]any {
	return map[string]any{
		"kty": "RSA",
		"kid": kid,
		"alg": "RS256",
		"use": "sig",
		"n":   base64.RawURLEncoding.EncodeToString(pub.N.Bytes()),
		"e":   base64.RawURLEncoding.EncodeToString(big.NewInt(int64(pub.E)).Bytes()),
	}
}

// jwksTestMintRS256 builds a compact RS256 JWS using only crypto/rsa and
// encoding/base64, mirroring what stdlib-only JWT verification expects.
func jwksTestMintRS256(t *testing.T, key *rsa.PrivateKey, kid string, claims map[string]any) string {
	t.Helper()
	header := map[string]any{"alg": "RS256", "typ": "JWT", "kid": kid}
	hb, err := json.Marshal(header)
	if err != nil {
		t.Fatalf("marshal JWT header: %v", err)
	}
	pb, err := json.Marshal(claims)
	if err != nil {
		t.Fatalf("marshal JWT claims: %v", err)
	}
	signingInput := base64.RawURLEncoding.EncodeToString(hb) + "." + base64.RawURLEncoding.EncodeToString(pb)
	digest := sha256.Sum256([]byte(signingInput))
	sig, err := rsa.SignPKCS1v15(rand.Reader, key, crypto.SHA256, digest[:])
	if err != nil {
		t.Fatalf("sign JWT: %v", err)
	}
	return signingInput + "." + base64.RawURLEncoding.EncodeToString(sig)
}

// jwksTestNewValidator serves a one-key JWKS over httptest and points a fresh
// validator at it. RealmURL doubles as the expected issuer.
func jwksTestNewValidator(t *testing.T, kid string, pub *rsa.PublicKey) *MCPKeycloakValidator {
	t.Helper()
	jwks := map[string]any{"keys": []any{jwksTestJWK(kid, pub)}}

	mux := http.NewServeMux()
	mux.HandleFunc("/realms/test/protocol/openid-connect/certs", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		if err := json.NewEncoder(w).Encode(jwks); err != nil {
			t.Errorf("encode JWKS: %v", err)
		}
	})
	server := httptest.NewServer(mux)
	t.Cleanup(server.Close)

	realmURL := server.URL + "/realms/test"
	return &MCPKeycloakValidator{
		ClientID:   "mcp-backend",
		Realm:      "test",
		RealmURL:   realmURL,
		JWKSURI:    realmURL + "/protocol/openid-connect/certs",
		tokenCache: map[string]cachedValidation{},
		cacheTTL:   300,
	}
}

func TestMCPKeycloakValidatorJWKS(t *testing.T) {
	// Pin the only env knobs used by ValidateMCPToken so an ambient
	// KEYCLOAK_TOKEN_AUDIENCE cannot change the expected audience.
	t.Setenv("KEYCLOAK_VERIFY_TOKEN_AUDIENCE", "true")
	t.Setenv("KEYCLOAK_TOKEN_AUDIENCE", "")

	const jwksKID = "test-kid"
	signingKey := jwksTestGenerateKey(t)
	validator := jwksTestNewValidator(t, jwksKID, &signingKey.PublicKey)

	issuer := validator.RealmURL
	audience := validator.ClientID
	now := time.Now()

	// validClaims returns a fresh copy of the claim set accepted by both the
	// JWT time/audience/issuer checks and validateMCPRequirements. The "user"
	// realm role yields non-empty MCP permissions.
	validClaims := func() map[string]any {
		return map[string]any{
			"sub":                "user-123",
			"preferred_username": "tester",
			"iat":                float64(now.Unix()),
			"exp":                float64(now.Add(time.Hour).Unix()),
			"iss":                issuer,
			"aud":                audience,
			"realm_access":       map[string]any{"roles": []any{"user"}},
		}
	}

	reject := func(t *testing.T, token string) {
		t.Helper()
		if got := validator.ValidateMCPToken(context.Background(), token); got != nil {
			t.Fatalf("expected token to be rejected, got claims %v", got)
		}
	}

	t.Run("valid token accepted", func(t *testing.T) {
		token := jwksTestMintRS256(t, signingKey, jwksKID, validClaims())
		claims := validator.ValidateMCPToken(context.Background(), token)
		if claims == nil {
			t.Fatal("expected valid RS256 token to be accepted")
		}
		if claims["sub"] != "user-123" {
			t.Fatalf("sub = %v, want user-123", claims["sub"])
		}
		if perms := validator.extractMCPPermissions(claims); len(perms) == 0 {
			t.Fatal("expected non-empty MCP permissions for realm role user")
		}
	})

	t.Run("expired token rejected", func(t *testing.T) {
		claims := validClaims()
		claims["iat"] = float64(now.Add(-2 * time.Hour).Unix())
		claims["exp"] = float64(now.Add(-time.Hour).Unix())
		reject(t, jwksTestMintRS256(t, signingKey, jwksKID, claims))
	})

	t.Run("wrong issuer rejected", func(t *testing.T) {
		claims := validClaims()
		claims["iss"] = "http://evil.example.com/realms/test"
		reject(t, jwksTestMintRS256(t, signingKey, jwksKID, claims))
	})

	t.Run("wrong audience rejected", func(t *testing.T) {
		claims := validClaims()
		claims["aud"] = "some-other-client"
		reject(t, jwksTestMintRS256(t, signingKey, jwksKID, claims))
	})

	t.Run("token signed by a different key rejected", func(t *testing.T) {
		otherKey := jwksTestGenerateKey(t)
		// Same kid and claims as the accepted token, but signed by a key the
		// JWKS does not publish: only the signature check can catch this.
		reject(t, jwksTestMintRS256(t, otherKey, jwksKID, validClaims()))
	})

	t.Run("unknown kid rejected", func(t *testing.T) {
		reject(t, jwksTestMintRS256(t, signingKey, "missing-kid", validClaims()))
	})

	t.Run("tampered payload rejected", func(t *testing.T) {
		token := jwksTestMintRS256(t, signingKey, jwksKID, validClaims())
		parts := strings.Split(token, ".")
		if len(parts) != 3 {
			t.Fatalf("unexpected compact JWS shape: %q", token)
		}
		payloadBytes, err := base64.RawURLEncoding.DecodeString(parts[1])
		if err != nil {
			t.Fatalf("decode payload: %v", err)
		}
		var payload map[string]any
		if err := json.Unmarshal(payloadBytes, &payload); err != nil {
			t.Fatalf("unmarshal payload: %v", err)
		}
		payload["sub"] = "attacker"
		tampered, err := json.Marshal(payload)
		if err != nil {
			t.Fatalf("marshal tampered payload: %v", err)
		}
		badToken := parts[0] + "." + base64.RawURLEncoding.EncodeToString(tampered) + "." + parts[2]
		reject(t, badToken)
	})
}
