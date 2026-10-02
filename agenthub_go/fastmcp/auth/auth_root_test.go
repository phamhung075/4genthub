package auth

import (
	"context"
	"crypto"
	"crypto/rand"
	"crypto/rsa"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"errors"
	"math/big"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"
	"time"

	taskentities "agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// --- ssl_config -----------------------------------------------------------

func TestConfigureSSLForSelfHosted(t *testing.T) {
	t.Setenv("SUPABASE_URL", "http://192.168.1.10:8000")
	if !ConfigureSSLForSelfHosted() {
		t.Fatal("expected self-hosted detection for IP URL")
	}
	for _, key := range []string{"HTTPX_SSL_VERIFY", "CURL_CA_BUNDLE", "REQUESTS_CA_BUNDLE", "SSL_CERT_FILE", "SSL_CERT_DIR"} {
		if _, ok := os.LookupEnv(key); !ok {
			t.Fatalf("expected %s to be set", key)
		}
	}
	if got := os.Getenv("HTTPX_SSL_VERIFY"); got != "0" {
		t.Fatalf("HTTPX_SSL_VERIFY = %q, want 0", got)
	}

	t.Setenv("SUPABASE_URL", "https://abcdefgh.supabase.co")
	if ConfigureSSLForSelfHosted() {
		t.Fatal("expected cloud URL not to be self-hosted")
	}
}

// --- supabase_client ------------------------------------------------------

func TestSupabaseTokenClientDetectionAndHash(t *testing.T) {
	t.Setenv("SUPABASE_URL", "http://10.0.0.5:8000")
	t.Setenv("SUPABASE_ANON_KEY", "anon")
	t.Setenv("SUPABASE_SERVICE_KEY", "")

	c := NewSupabaseTokenClient()
	if !c.IsSelfHosted {
		t.Fatal("expected IsSelfHosted true")
	}
	if !c.Enabled {
		t.Fatal("expected Enabled true")
	}
	if c.APIKey == nil || *c.APIKey != "anon" {
		t.Fatalf("APIKey = %v, want anon", c.APIKey)
	}

	// sha256("hello")
	want := "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
	if got := c.HashToken("hello"); got != want {
		t.Fatalf("HashToken = %q, want %q", got, want)
	}

	token := c.GenerateToken()
	if len(token) != 64 {
		t.Fatalf("GenerateToken length = %d, want 64", len(token))
	}
	for _, r := range token {
		if !strings.ContainsRune("0123456789abcdef", r) {
			t.Fatalf("GenerateToken = %q, not lowercase hex", token)
		}
	}
}

func TestSupabaseTokenClientDisabledWithoutConfig(t *testing.T) {
	t.Setenv("SUPABASE_URL", "")
	t.Setenv("SUPABASE_ANON_KEY", "")
	t.Setenv("SUPABASE_SERVICE_KEY", "")
	c := NewSupabaseTokenClient()
	if c.Enabled {
		t.Fatal("expected client disabled without URL and key")
	}
	if c.ValidateToken(context.Background(), "x") != nil {
		t.Fatal("expected nil from disabled client")
	}
}

func TestSupabaseValidateTokenHTTP(t *testing.T) {
	mux := http.NewServeMux()
	mux.HandleFunc("/rest/v1/api_tokens", func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case http.MethodGet:
			w.Header().Set("Content-Type", "application/json")
			_, _ = w.Write([]byte(`[{"token_hash":"x","user_id":"user-1","created_at":"2024-01-01T00:00:00+00:00","expires_at":"2099-01-01T00:00:00+00:00","is_active":true,"usage_count":3,"last_used":null}]`))
		case http.MethodPatch:
			w.WriteHeader(http.StatusNoContent)
		default:
			w.WriteHeader(http.StatusMethodNotAllowed)
		}
	})
	server := httptest.NewServer(mux)
	defer server.Close()

	t.Setenv("SUPABASE_URL", server.URL)
	t.Setenv("SUPABASE_ANON_KEY", "anon")
	t.Setenv("SUPABASE_SERVICE_KEY", "")

	c := NewSupabaseTokenClient()
	info := c.ValidateToken(context.Background(), "hello")
	if info == nil {
		t.Fatal("expected token info")
	}
	if info.UserID != "user-1" || info.UsageCount != 3 || !info.IsActive {
		t.Fatalf("unexpected token info: %+v", info)
	}
	if info.ExpiresAt == nil {
		t.Fatal("expected expires_at set")
	}
	if !c.RevokeToken(context.Background(), "hello") {
		t.Fatal("expected revoke to succeed on 204")
	}
}

func TestSupabaseValidateTokenExpired(t *testing.T) {
	mux := http.NewServeMux()
	mux.HandleFunc("/rest/v1/api_tokens", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`[{"user_id":"u","created_at":"2000-01-01T00:00:00+00:00","expires_at":"2000-01-02T00:00:00+00:00","is_active":true}]`))
	})
	server := httptest.NewServer(mux)
	defer server.Close()

	t.Setenv("SUPABASE_URL", server.URL)
	t.Setenv("SUPABASE_ANON_KEY", "anon")

	c := NewSupabaseTokenClient()
	if info := c.ValidateToken(context.Background(), "t"); info != nil {
		t.Fatalf("expected nil for expired token, got %+v", info)
	}
}

// --- hook_auth ------------------------------------------------------------

func TestHookTokenRoundTrip(t *testing.T) {
	t.Setenv("HOOK_JWT_SECRET", "test-secret")
	t.Setenv("AUTH_ENABLED", "true")

	validator, err := NewHookAuthValidator()
	if err != nil {
		t.Fatalf("NewHookAuthValidator: %v", err)
	}
	token, err := CreateHookToken("hook-user", 30)
	if err != nil {
		t.Fatalf("CreateHookToken: %v", err)
	}
	claims, err := validator.ValidateHookToken(token)
	if err != nil {
		t.Fatalf("ValidateHookToken: %v", err)
	}
	if claims["sub"] != "hook-user" || claims["iss"] != "agenthub" || claims["type"] != "api_token" {
		t.Fatalf("unexpected claims: %+v", claims)
	}
	if claims["aud"] != "mcp-server" {
		t.Fatalf("aud = %v, want mcp-server", claims["aud"])
	}
	scopes, ok := claims["scopes"].([]any)
	if !ok || len(scopes) != 7 {
		t.Fatalf("scopes = %v, want 7 entries", claims["scopes"])
	}
}

func TestHookTokenErrorBranches(t *testing.T) {
	t.Setenv("HOOK_JWT_SECRET", "test-secret")
	t.Setenv("AUTH_ENABLED", "true")

	validator := &HookAuthValidator{Algorithm: "HS256", Secret: "test-secret"}
	token, err := CreateHookToken("hook-user", 30)
	if err != nil {
		t.Fatalf("CreateHookToken: %v", err)
	}

	// Wrong secret -> invalid signature.
	wrong := &HookAuthValidator{Algorithm: "HS256", Secret: "wrong-secret"}
	if _, err := wrong.ValidateHookToken(token); err == nil {
		t.Fatal("expected invalid signature error")
	} else {
		var httpErr *HTTPException
		if !errors.As(err, &httpErr) || httpErr.StatusCode != 401 || httpErr.Detail != "Invalid hook token signature" {
			t.Fatalf("unexpected error: %v", err)
		}
	}

	// Not a hook token.
	other := taskentities.NewOrderedMap[any]()
	other.Set("sub", "u")
	other.Set("type", "access")
	other.Set("iss", "other")
	notHook, err := jwtEncodeHS256(other, "test-secret", "HS256")
	if err != nil {
		t.Fatalf("jwtEncodeHS256: %v", err)
	}
	if _, err := validator.ValidateHookToken(notHook); err == nil {
		t.Fatal("expected not-a-hook-token error")
	} else {
		var httpErr *HTTPException
		if !errors.As(err, &httpErr) || httpErr.Detail != "Not a valid hook token" {
			t.Fatalf("unexpected error: %v", err)
		}
	}

	// Expired hook token.
	expired := taskentities.NewOrderedMap[any]()
	expired.Set("sub", "u")
	expired.Set("type", "api_token")
	expired.Set("iss", "agenthub")
	expired.Set("aud", "mcp-server")
	expired.Set("exp", float64(time.Now().Add(-time.Hour).UnixNano())/1e9)
	expiredToken, err := jwtEncodeHS256(expired, "test-secret", "HS256")
	if err != nil {
		t.Fatalf("jwtEncodeHS256: %v", err)
	}
	if _, err := validator.ValidateHookToken(expiredToken); err == nil {
		t.Fatal("expected expired error")
	} else {
		var httpErr *HTTPException
		if !errors.As(err, &httpErr) || httpErr.Detail != "Token expired" {
			t.Fatalf("unexpected error: %v", err)
		}
	}

	// Missing secret.
	t.Setenv("HOOK_JWT_SECRET", "")
	if _, err := NewHookAuthValidator(); err == nil {
		t.Fatal("expected ValueError for missing HOOK_JWT_SECRET")
	} else {
		var verr *value_objects.ValueError
		if !errors.As(err, &verr) {
			t.Fatalf("expected ValueError, got %T", err)
		}
	}
}

func TestIsHookRequest(t *testing.T) {
	if !IsHookRequest(map[string]string{"user-agent": "claude-hook/1.0"}) {
		t.Fatal("expected claude-hook user agent to match")
	}
	if !IsHookRequest(map[string]string{"User-Agent": "python-requests/2.0"}) {
		t.Fatal("expected python user agent to match")
	}
	if IsHookRequest(map[string]string{"user-agent": "Mozilla/5.0"}) {
		t.Fatal("expected browser user agent not to match")
	}
}

// --- token_validator ------------------------------------------------------

func TestTokenValidatorRateLimit(t *testing.T) {
	t.Setenv("SUPABASE_URL", "")
	t.Setenv("SUPABASE_ANON_KEY", "")

	validator := NewTokenValidator(&RateLimitConfig{RequestsPerMinute: 1, RequestsPerHour: 100, BurstLimit: 100})

	if _, err := validator.ValidateToken(context.Background(), "", nil); err == nil {
		t.Fatal("expected TokenValidationError for empty token")
	} else {
		var verr *TokenValidationError
		if !errors.As(err, &verr) || verr.Msg != "Token is required" {
			t.Fatalf("unexpected error: %v", err)
		}
	}

	// First call records the request then fails validation (Supabase disabled).
	if _, err := validator.ValidateToken(context.Background(), "token", nil); err == nil {
		t.Fatal("expected invalid token error")
	} else {
		var verr *TokenValidationError
		if !errors.As(err, &verr) || verr.Msg != "Invalid or expired token" {
			t.Fatalf("unexpected error: %v", err)
		}
	}

	// Second call exceeds requests-per-minute.
	if _, err := validator.ValidateToken(context.Background(), "token", nil); err == nil {
		t.Fatal("expected rate limit error")
	} else {
		var rerr *RateLimitError
		if !errors.As(err, &rerr) || rerr.Msg != "Rate limit exceeded: 1/1 requests per minute" {
			t.Fatalf("unexpected error: %v", err)
		}
	}

	status := validator.GetRateLimitStatus("token")
	if v, _ := status.Get("requests_per_minute"); v != 1 {
		t.Fatalf("requests_per_minute = %v, want 1", v)
	}
}

func TestTokenValidatorBurstLimit(t *testing.T) {
	t.Setenv("SUPABASE_URL", "")
	t.Setenv("SUPABASE_ANON_KEY", "")

	validator := NewTokenValidator(&RateLimitConfig{RequestsPerMinute: 100, RequestsPerHour: 100, BurstLimit: 1})
	_, _ = validator.ValidateToken(context.Background(), "token", nil)

	if _, err := validator.ValidateToken(context.Background(), "token", nil); err == nil {
		t.Fatal("expected burst limit error")
	} else {
		var rerr *RateLimitError
		if !errors.As(err, &rerr) || rerr.Msg != "Burst limit exceeded: 1/1 requests per 10 seconds" {
			t.Fatalf("unexpected error: %v", err)
		}
	}
}

func TestTokenValidatorCacheStats(t *testing.T) {
	t.Setenv("SUPABASE_URL", "")
	t.Setenv("SUPABASE_ANON_KEY", "")
	validator := NewTokenValidator(nil)
	validator.ClearCache()
	stats := validator.GetCacheStats()
	if v, _ := stats.Get("cached_tokens"); v != 0 {
		t.Fatalf("cached_tokens = %v, want 0", v)
	}
}

// --- keycloak_dependencies -------------------------------------------------

func TestValidateLocalToken(t *testing.T) {
	t.Setenv("JWT_SECRET_KEY", "local-secret")

	claims := taskentities.NewOrderedMap[any]()
	claims.Set("sub", "user-9")
	claims.Set("email", "u9@example.com")
	claims.Set("username", "u9")
	claims.Set("exp", float64(time.Now().Add(time.Hour).UnixNano())/1e9)
	token, err := jwtEncodeHS256(claims, "local-secret", "HS256")
	if err != nil {
		t.Fatalf("jwtEncodeHS256: %v", err)
	}

	user, err := ValidateLocalToken(token)
	if err != nil {
		t.Fatalf("ValidateLocalToken: %v", err)
	}
	if user.ID == nil || *user.ID != "user-9" || user.Email != "u9@example.com" || user.Username != "u9" {
		t.Fatalf("unexpected user: %+v", user)
	}

	t.Setenv("JWT_SECRET_KEY", "")
	if _, err := ValidateLocalToken(token); err == nil {
		t.Fatal("expected configuration error without JWT_SECRET_KEY")
	} else {
		var httpErr *HTTPException
		if !errors.As(err, &httpErr) || httpErr.StatusCode != 500 {
			t.Fatalf("unexpected error: %v", err)
		}
	}
}

func TestValidateLocalTokenInvalid(t *testing.T) {
	t.Setenv("JWT_SECRET_KEY", "local-secret")
	if _, err := ValidateLocalToken("not-a-jwt"); err == nil {
		t.Fatal("expected invalid token error")
	} else {
		var httpErr *HTTPException
		if !errors.As(err, &httpErr) || httpErr.StatusCode != 401 {
			t.Fatalf("unexpected error: %v", err)
		}
	}
}

// --- mcp_keycloak_validator ------------------------------------------------

func TestMCPKeycloakExtractUserInfo(t *testing.T) {
	v := &MCPKeycloakValidator{ClientID: "mcp-backend"}
	claims := map[string]any{
		"sub":                "u1",
		"preferred_username": "bob",
		"email":              "bob@example.com",
		"email_verified":     true,
		"realm_access":       map[string]any{"roles": []any{"admin", "user"}},
		"resource_access":    map[string]any{"mcp-backend": map[string]any{"roles": []any{"viewer"}}},
		"mcp_permissions":    []any{"mcp:custom"},
	}

	info := v.ExtractUserInfo(claims)
	if uid, _ := info.Get("user_id"); uid != "u1" {
		t.Fatalf("user_id = %v", uid)
	}

	rolesVal, _ := info.Get("roles")
	roles := rolesVal.([]string)
	wantRoles := []string{"admin", "user", "viewer"}
	if len(roles) != len(wantRoles) {
		t.Fatalf("roles = %v, want %v", roles, wantRoles)
	}
	for i := range wantRoles {
		if roles[i] != wantRoles[i] {
			t.Fatalf("roles = %v, want %v", roles, wantRoles)
		}
	}

	permsVal, _ := info.Get("mcp_permissions")
	perms := permsVal.([]string)
	wantPerms := []string{"mcp:*", "mcp:read", "mcp:execute", "mcp:custom"}
	if len(perms) != len(wantPerms) {
		t.Fatalf("mcp_permissions = %v, want %v", perms, wantPerms)
	}
	for i := range wantPerms {
		if perms[i] != wantPerms[i] {
			t.Fatalf("mcp_permissions = %v, want %v", perms, wantPerms)
		}
	}
}

func TestMCPKeycloakValidateRequirements(t *testing.T) {
	t.Setenv("KEYCLOAK_VERIFY_TOKEN_AUDIENCE", "true")
	t.Setenv("KEYCLOAK_TOKEN_AUDIENCE", "")

	v := &MCPKeycloakValidator{ClientID: "mcp-backend"}

	valid := map[string]any{
		"sub":             "u1",
		"iat":             float64(time.Now().Unix()),
		"exp":             float64(time.Now().Add(time.Hour).Unix()),
		"aud":             "mcp-backend",
		"mcp_permissions": []any{"mcp:read"},
	}
	if !v.validateMCPRequirements(valid) {
		t.Fatal("expected valid claims to pass")
	}

	expired := map[string]any{
		"sub":             "u1",
		"iat":             float64(time.Now().Add(-2 * time.Hour).Unix()),
		"exp":             float64(time.Now().Add(-time.Hour).Unix()),
		"aud":             "mcp-backend",
		"mcp_permissions": []any{"mcp:read"},
	}
	if v.validateMCPRequirements(expired) {
		t.Fatal("expected expired claims to fail")
	}

	noPermissions := map[string]any{
		"sub": "u1",
		"iat": float64(time.Now().Unix()),
		"exp": float64(time.Now().Add(time.Hour).Unix()),
		"aud": "mcp-backend",
	}
	if v.validateMCPRequirements(noPermissions) {
		t.Fatal("expected missing permissions to fail")
	}

	wrongAudience := map[string]any{
		"sub":             "u1",
		"iat":             float64(time.Now().Unix()),
		"exp":             float64(time.Now().Add(time.Hour).Unix()),
		"aud":             "other",
		"mcp_permissions": []any{"mcp:read"},
	}
	if v.validateMCPRequirements(wrongAudience) {
		t.Fatal("expected wrong audience to fail")
	}
}

// --- shared JWT helpers ----------------------------------------------------

func signRS256(t *testing.T, key *rsa.PrivateKey, kid string, payload map[string]any) string {
	t.Helper()
	header := map[string]any{"alg": "RS256", "typ": "JWT", "kid": kid}
	hb, err := json.Marshal(header)
	if err != nil {
		t.Fatalf("marshal header: %v", err)
	}
	pb, err := json.Marshal(payload)
	if err != nil {
		t.Fatalf("marshal payload: %v", err)
	}
	signingInput := base64.RawURLEncoding.EncodeToString(hb) + "." + base64.RawURLEncoding.EncodeToString(pb)
	digest := sha256.Sum256([]byte(signingInput))
	sig, err := rsa.SignPKCS1v15(rand.Reader, key, crypto.SHA256, digest[:])
	if err != nil {
		t.Fatalf("sign: %v", err)
	}
	return signingInput + "." + base64.RawURLEncoding.EncodeToString(sig)
}

func TestMCPKeycloakValidateMCPTokenRS256(t *testing.T) {
	t.Setenv("KEYCLOAK_VERIFY_TOKEN_AUDIENCE", "true")
	t.Setenv("KEYCLOAK_TOKEN_AUDIENCE", "")

	key, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		t.Fatalf("GenerateKey: %v", err)
	}
	n := base64.RawURLEncoding.EncodeToString(key.N.Bytes())
	e := base64.RawURLEncoding.EncodeToString(big.NewInt(int64(key.E)).Bytes())

	jwks := map[string]any{"keys": []any{map[string]any{
		"kty": "RSA", "kid": "k1", "alg": "RS256", "use": "sig", "n": n, "e": e,
	}}}
	mux := http.NewServeMux()
	mux.HandleFunc("/certs", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(jwks)
	})
	server := httptest.NewServer(mux)
	defer server.Close()

	validator := &MCPKeycloakValidator{
		ClientID:   "mcp-backend",
		Realm:      "",
		RealmURL:   server.URL,
		JWKSURI:    server.URL + "/certs",
		tokenCache: map[string]cachedValidation{},
		cacheTTL:   300,
	}

	now := time.Now()
	claims := map[string]any{
		"sub":             "u1",
		"iat":             float64(now.Unix()),
		"exp":             float64(now.Add(time.Hour).Unix()),
		"aud":             "mcp-backend",
		"iss":             server.URL,
		"mcp_permissions": []any{"mcp:read"},
	}
	token := signRS256(t, key, "k1", claims)

	got := validator.ValidateMCPToken(context.Background(), token)
	if got == nil {
		t.Fatal("expected RS256 token to validate")
	}
	if got["sub"] != "u1" {
		t.Fatalf("sub = %v, want u1", got["sub"])
	}

	// Wrong audience must fail.
	badClaims := map[string]any{
		"sub":             "u1",
		"iat":             float64(now.Unix()),
		"exp":             float64(now.Add(time.Hour).Unix()),
		"aud":             "other",
		"iss":             server.URL,
		"mcp_permissions": []any{"mcp:read"},
	}
	badToken := signRS256(t, key, "k1", badClaims)
	if validator.ValidateMCPToken(context.Background(), badToken) != nil {
		t.Fatal("expected wrong audience to fail")
	}
}

func TestJWTHS256RoundTripAndErrors(t *testing.T) {
	claims := taskentities.NewOrderedMap[any]()
	claims.Set("sub", "u1")
	claims.Set("aud", "mcp-server")
	claims.Set("exp", float64(time.Now().Add(time.Hour).UnixNano())/1e9)

	token, err := jwtEncodeHS256(claims, "secret", "HS256")
	if err != nil {
		t.Fatalf("jwtEncodeHS256: %v", err)
	}

	payload, err := jwtDecodeHS256Claims(token, "secret", "HS256", jwtDecodeOptions{
		VerifyAud: true, Audience: "mcp-server",
		VerifyExp: true, VerifyIat: true, VerifyNbf: true,
	})
	if err != nil {
		t.Fatalf("jwtDecodeHS256Claims: %v", err)
	}
	if payload["sub"] != "u1" {
		t.Fatalf("sub = %v", payload["sub"])
	}

	if _, err := jwtDecodeHS256Claims(token, "wrong", "HS256", jwtDecodeOptions{}); err == nil {
		t.Fatal("expected signature failure")
	}

	header, err := jwtUnverifiedHeader(token)
	if err != nil || header["alg"] != "HS256" {
		t.Fatalf("unexpected header: %v (err %v)", header, err)
	}
}
