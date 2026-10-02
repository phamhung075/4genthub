package auth

import (
	"context"
	"crypto"
	"crypto/hmac"
	"crypto/rsa"
	"crypto/sha256"
	"crypto/tls"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"math/big"
	"net/http"
	"os"
	"strings"
	"sync"
	"time"

	authentities "agenthub/fastmcp/auth/domain/entities"
)

// HTTPException mirrors FastAPI/Starlette's HTTPException as a Go error. Its
// Error text matches Starlette's __str__ ("status: detail").
type HTTPException struct {
	StatusCode int
	Detail     string
}

func (e *HTTPException) Error() string { return fmt.Sprintf("%d: %s", e.StatusCode, e.Detail) }

// envOr is os.getenv(key) or default.
func envOr(key, def string) string {
	if v, ok := os.LookupEnv(key); ok && v != "" {
		return v
	}
	return def
}

// insecureHTTPClient is an http.Client that does not verify TLS certificates
// (the unverified urllib opener used by get_keycloak_jwks_client).
func insecureHTTPClient() *http.Client {
	return &http.Client{Transport: &http.Transport{TLSClientConfig: &tls.Config{InsecureSkipVerify: true}}}
}

// Local JWT configuration (module import time), mirroring the Python module
// constants. JWT_SECRET_KEY itself is read dynamically by validate_local_token.
var keycloakDependenciesJWTAlgorithm = envOr("JWT_ALGORITHM", "HS256")

// ---------------------------------------------------------------------------
// Minimal JWT / JWKS implementation (golang-jwt and PyJWT are not available).
// ---------------------------------------------------------------------------

type jwtExpiredError struct{}

func (jwtExpiredError) Error() string { return "Signature has expired" }

type jwtInvalidError struct{ msg string }

func (e *jwtInvalidError) Error() string { return e.msg }

func isJWTExpired(err error) bool {
	var e jwtExpiredError
	return errors.As(err, &e)
}

// b64urlDecodeRaw decodes a base64url JWT segment (padding optional).
func b64urlDecodeRaw(s string) ([]byte, error) {
	s = strings.TrimRight(s, "=")
	return base64.RawURLEncoding.DecodeString(s)
}

// jwtSplitToken splits a compact JWS into signing input and signature.
func jwtSplitToken(token string) (signingInput string, signature []byte, err error) {
	i := strings.LastIndex(token, ".")
	if i < 0 {
		return "", nil, &jwtInvalidError{"Not enough segments"}
	}
	signingInput = token[:i]
	sig, err := b64urlDecodeRaw(token[i+1:])
	if err != nil {
		return "", nil, &jwtInvalidError{err.Error()}
	}
	return signingInput, sig, nil
}

// jwtPartsHeaderPayload returns the decoded header and payload objects.
func jwtPartsHeaderPayload(token string) (header, payload map[string]any, err error) {
	signingInput, _, err := jwtSplitToken(token)
	if err != nil {
		return nil, nil, err
	}
	parts := strings.SplitN(signingInput, ".", 2)
	if len(parts) != 2 {
		return nil, nil, &jwtInvalidError{"Not enough segments"}
	}
	hb, err := b64urlDecodeRaw(parts[0])
	if err != nil {
		return nil, nil, &jwtInvalidError{err.Error()}
	}
	pb, err := b64urlDecodeRaw(parts[1])
	if err != nil {
		return nil, nil, &jwtInvalidError{err.Error()}
	}
	if err := json.Unmarshal(hb, &header); err != nil {
		return nil, nil, &jwtInvalidError{err.Error()}
	}
	if err := json.Unmarshal(pb, &payload); err != nil {
		return nil, nil, &jwtInvalidError{err.Error()}
	}
	return header, payload, nil
}

// jwtUnverifiedHeader is jwt.get_unverified_header.
func jwtUnverifiedHeader(token string) (map[string]any, error) {
	header, _, err := jwtPartsHeaderPayload(token)
	return header, err
}

// jwtUnverifiedClaims is jwt.get_unverified_claims.
func jwtUnverifiedClaims(token string) (map[string]any, error) {
	_, payload, err := jwtPartsHeaderPayload(token)
	return payload, err
}

// jwtClaimInt is int(claim) for claim validation.
func jwtClaimInt(v any) (float64, error) {
	switch n := v.(type) {
	case float64:
		return n, nil
	case int64:
		return float64(n), nil
	case int:
		return float64(n), nil
	case json.Number:
		f, err := n.Float64()
		if err != nil {
			return 0, err
		}
		return f, nil
	case string:
		var f float64
		if _, err := fmt.Sscanf(n, "%g", &f); err != nil {
			return 0, err
		}
		return f, nil
	}
	return 0, fmt.Errorf("not a number")
}

// jwtDecodeOptions mirrors the PyJWT option set used by the ported modules.
type jwtDecodeOptions struct {
	VerifyAud bool
	Audience  string
	VerifyIss bool
	Issuer    string
	VerifyExp bool
	VerifyIat bool
	VerifyNbf bool
	Require   []string
	Leeway    time.Duration
}

// jwtValidateClaims implements PyJWT's time and audience claim validation.
func jwtValidateClaims(payload map[string]any, opts jwtDecodeOptions) error {
	now := float64(time.Now().UnixNano()) / 1e9
	leeway := opts.Leeway.Seconds()

	if opts.VerifyIat {
		if v, ok := payload["iat"]; ok {
			iat, err := jwtClaimInt(v)
			if err != nil {
				return &jwtInvalidError{"Issued At claim (iat) must be an integer."}
			}
			if iat > now+leeway {
				return &jwtInvalidError{"The token is not yet valid (iat)"}
			}
		}
	}
	if opts.VerifyNbf {
		if v, ok := payload["nbf"]; ok {
			nbf, err := jwtClaimInt(v)
			if err != nil {
				return &jwtInvalidError{"Not Before claim (nbf) must be an integer."}
			}
			if nbf > now+leeway {
				return &jwtInvalidError{"The token is not yet valid (nbf)"}
			}
		}
	}
	if opts.VerifyExp {
		if v, ok := payload["exp"]; ok {
			exp, err := jwtClaimInt(v)
			if err != nil {
				return &jwtInvalidError{"Expiration Time claim (exp) must be an integer."}
			}
			if exp <= now-leeway {
				return jwtExpiredError{}
			}
		}
	}
	if opts.VerifyAud {
		aud, present := payload["aud"]
		if !present {
			return &jwtInvalidError{"Token is missing the \"aud\" claim"}
		}
		var audiences []string
		switch a := aud.(type) {
		case string:
			audiences = []string{a}
		case []any:
			for _, e := range a {
				s, ok := e.(string)
				if !ok {
					return &jwtInvalidError{"Invalid claim format in token"}
				}
				audiences = append(audiences, s)
			}
		default:
			return &jwtInvalidError{"Invalid claim format in token"}
		}
		matched := false
		for _, a := range audiences {
			if a == opts.Audience {
				matched = true
			}
		}
		if !matched {
			return &jwtInvalidError{"Audience doesn't match"}
		}
	}
	if opts.VerifyIss {
		iss, _ := payload["iss"].(string)
		if iss != opts.Issuer {
			return &jwtInvalidError{"Invalid issuer"}
		}
	}
	for _, claim := range opts.Require {
		if _, ok := payload[claim]; !ok {
			return &jwtInvalidError{fmt.Sprintf("missing required claim: %s", claim)}
		}
	}
	return nil
}

// jwtDecodeHS256Claims verifies an HS256 token and its claims.
func jwtDecodeHS256Claims(token, secret, algorithm string, opts jwtDecodeOptions) (map[string]any, error) {
	header, payload, err := jwtPartsHeaderPayload(token)
	if err != nil {
		return nil, err
	}
	alg, _ := header["alg"].(string)
	if alg != algorithm {
		return nil, &jwtInvalidError{"The specified alg value is not allowed"}
	}
	signingInput, signature, err := jwtSplitToken(token)
	if err != nil {
		return nil, err
	}
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write([]byte(signingInput))
	if !hmac.Equal(mac.Sum(nil), signature) {
		return nil, &jwtInvalidError{"Signature verification failed"}
	}
	if err := jwtValidateClaims(payload, opts); err != nil {
		return nil, err
	}
	return payload, nil
}

// jwtDecodeRS256Claims verifies an RS256 token and its claims.
func jwtDecodeRS256Claims(token string, pub *rsa.PublicKey, opts jwtDecodeOptions) (map[string]any, error) {
	header, payload, err := jwtPartsHeaderPayload(token)
	if err != nil {
		return nil, err
	}
	alg, _ := header["alg"].(string)
	if alg != "RS256" {
		return nil, &jwtInvalidError{"The specified alg value is not allowed"}
	}
	signingInput, signature, err := jwtSplitToken(token)
	if err != nil {
		return nil, err
	}
	digest := sha256.Sum256([]byte(signingInput))
	if err := rsa.VerifyPKCS1v15(pub, crypto.SHA256, digest[:], signature); err != nil {
		return nil, &jwtInvalidError{"Signature verification failed"}
	}
	if err := jwtValidateClaims(payload, opts); err != nil {
		return nil, err
	}
	return payload, nil
}

// jwksKey is one JSON Web Key from a JWKS document.
type jwksKey struct {
	Kty string `json:"kty"`
	Kid string `json:"kid"`
	Alg string `json:"alg"`
	Use string `json:"use"`
	N   string `json:"n"`
	E   string `json:"e"`
}

// KeycloakJWKSClient fetches and caches RSA public keys from a JWKS endpoint
// (PyJWKClient).
type KeycloakJWKSClient struct {
	JWKSURL    string
	Lifespan   time.Duration
	HTTPClient *http.Client

	mu        sync.Mutex
	keys      map[string]*rsa.PublicKey
	fetchedAt time.Time
}

// NewKeycloakJWKSClient builds a JWKS client; a nil HTTPClient uses the default.
func NewKeycloakJWKSClient(jwksURL string, lifespan time.Duration, client *http.Client) *KeycloakJWKSClient {
	if client == nil {
		client = &http.Client{}
	}
	return &KeycloakJWKSClient{JWKSURL: jwksURL, Lifespan: lifespan, HTTPClient: client, keys: map[string]*rsa.PublicKey{}}
}

func rsaPublicKeyFromJWK(nB64, eB64 string) (*rsa.PublicKey, error) {
	nBytes, err := b64urlDecodeRaw(nB64)
	if err != nil {
		return nil, err
	}
	eBytes, err := b64urlDecodeRaw(eB64)
	if err != nil {
		return nil, err
	}
	e := 0
	for _, b := range eBytes {
		e = e<<8 | int(b)
	}
	return &rsa.PublicKey{N: new(big.Int).SetBytes(nBytes), E: e}, nil
}

// refresh fetches the JWKS document and replaces the key cache.
func (c *KeycloakJWKSClient) refresh() error {
	req, err := http.NewRequest(http.MethodGet, c.JWKSURL, nil)
	if err != nil {
		return err
	}
	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return fmt.Errorf("JWKS request failed: %d", resp.StatusCode)
	}
	var doc struct {
		Keys []jwksKey `json:"keys"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&doc); err != nil {
		return err
	}
	keys := map[string]*rsa.PublicKey{}
	for _, k := range doc.Keys {
		pub, err := rsaPublicKeyFromJWK(k.N, k.E)
		if err != nil {
			continue
		}
		keys[k.Kid] = pub
	}
	c.keys = keys
	c.fetchedAt = time.Now()
	return nil
}

// GetSigningKeyFromJWT finds the RSA key for the token's kid, refreshing the
// cache when it is missing or stale (PyJWKClient.get_signing_key_from_jwt).
func (c *KeycloakJWKSClient) GetSigningKeyFromJWT(token string) (*rsa.PublicKey, error) {
	header, err := jwtUnverifiedHeader(token)
	if err != nil {
		return nil, err
	}
	kid, _ := header["kid"].(string)

	c.mu.Lock()
	defer c.mu.Unlock()

	needRefresh := len(c.keys) == 0 || (c.Lifespan > 0 && time.Since(c.fetchedAt) > c.Lifespan)
	if needRefresh {
		if err := c.refresh(); err != nil {
			return nil, err
		}
	}
	if pub, ok := c.keys[kid]; ok {
		return pub, nil
	}
	// PyJWKClient refetches once when the requested kid is not in the cache.
	if err := c.refresh(); err != nil {
		return nil, err
	}
	if pub, ok := c.keys[kid]; ok {
		return pub, nil
	}
	return nil, fmt.Errorf("Unable to find a signing key that matches: %q", kid)
}

// ---------------------------------------------------------------------------
// keycloak_dependencies.py port (FastAPI dependency wrappers dropped).
// ---------------------------------------------------------------------------

// keycloakJWKSClientInstance is the module-level _keycloak_jwks_client cache.
var keycloakJWKSClientInstance *KeycloakJWKSClient

// GetKeycloakJWKSClient returns the cached JWKS client (Python
// get_keycloak_jwks_client). It returns nil when KEYCLOAK_URL is unset.
func GetKeycloakJWKSClient() *KeycloakJWKSClient {
	keycloakURL := os.Getenv("KEYCLOAK_URL")
	keycloakRealm := envOr("KEYCLOAK_REALM", "mcp")

	if keycloakURL == "" {
		return nil
	}

	if keycloakJWKSClientInstance == nil {
		jwksURL := fmt.Sprintf("%s/realms/%s/protocol/openid-connect/certs", keycloakURL, keycloakRealm)
		keycloakJWKSClientInstance = NewKeycloakJWKSClient(jwksURL, 3600*time.Second, insecureHTTPClient())
	}
	return keycloakJWKSClientInstance
}

func ptrOrEmpty(s *string) string {
	if s == nil {
		return ""
	}
	return *s
}

// ValidateKeycloakToken validates a Keycloak JWT token (Python
// validate_keycloak_token).
func ValidateKeycloakToken(ctx context.Context, token string) (*authentities.User, error) {
	authProvider := envOr("AUTH_PROVIDER", "keycloak")
	keycloakURL := os.Getenv("KEYCLOAK_URL")

	if authProvider != "keycloak" || keycloakURL == "" {
		return nil, &HTTPException{StatusCode: 500, Detail: "Keycloak not configured"}
	}

	jwksClient := GetKeycloakJWKSClient()
	if jwksClient == nil {
		return nil, &HTTPException{StatusCode: 500, Detail: "Keycloak JWKS client not available"}
	}

	signingKey, err := jwksClient.GetSigningKeyFromJWT(token)
	if err != nil {
		// PyJWT's PyJWKClientError is not an InvalidTokenError, so the Python
		// code falls through to the generic exception handler.
		return nil, &HTTPException{StatusCode: 401, Detail: "Token validation failed"}
	}

	payload, err := jwtDecodeRS256Claims(token, signingKey, jwtDecodeOptions{
		VerifyAud: false,
		VerifyExp: true,
		VerifyIat: true,
		VerifyNbf: true,
		Leeway:    30 * time.Second,
	})
	if err != nil {
		if isJWTExpired(err) {
			return nil, &HTTPException{StatusCode: 401, Detail: "Token expired"}
		}
		return nil, &HTTPException{StatusCode: 401, Detail: fmt.Sprintf("Invalid token: %s", err.Error())}
	}

	userID, _ := payload["sub"].(string)
	email, _ := payload["email"].(string)
	username, _ := payload["preferred_username"].(string)
	if username == "" {
		username = email
	}

	if userID == "" {
		return nil, &HTTPException{StatusCode: 401, Detail: "Invalid token: missing user ID"}
	}

	if exp, ok := payload["exp"]; ok {
		if v, err := jwtClaimInt(exp); err == nil && float64(time.Now().UnixNano())/1e9 > v {
			return nil, &HTTPException{StatusCode: 401, Detail: "Token expired"}
		}
	}

	if email == "" {
		email = fmt.Sprintf("%s@keycloak.local", username)
	}
	if username == "" {
		username = userID
	}

	user, err := authentities.NewUser(authentities.User{
		ID:           &userID,
		Email:        email,
		Username:     username,
		PasswordHash: "keycloak-authenticated",
	})
	if err != nil {
		return nil, err
	}
	return user, nil
}

// ValidateLocalToken validates a locally-generated JWT token (Python
// validate_local_token).
func ValidateLocalToken(token string) (*authentities.User, error) {
	jwtSecret := os.Getenv("JWT_SECRET_KEY")
	if jwtSecret == "" {
		return nil, &HTTPException{StatusCode: 500, Detail: "Server configuration error: JWT secret not set"}
	}

	payload, err := jwtDecodeHS256Claims(token, jwtSecret, keycloakDependenciesJWTAlgorithm, jwtDecodeOptions{
		VerifyAud: false,
		VerifyExp: true,
		VerifyIat: true,
		VerifyNbf: true,
		Leeway:    30 * time.Second,
	})
	if err != nil {
		if isJWTExpired(err) {
			return nil, &HTTPException{StatusCode: 401, Detail: "Token expired"}
		}
		return nil, &HTTPException{StatusCode: 401, Detail: "Invalid token"}
	}

	userID, _ := payload["sub"].(string)
	if userID == "" {
		userID, _ = payload["user_id"].(string)
	}
	email, _ := payload["email"].(string)

	if userID == "" {
		return nil, &HTTPException{StatusCode: 401, Detail: "Invalid token: missing user ID"}
	}

	if exp, ok := payload["exp"]; ok {
		if v, err := jwtClaimInt(exp); err == nil && float64(time.Now().UnixNano())/1e9 > v {
			return nil, &HTTPException{StatusCode: 401, Detail: "Token expired"}
		}
	}

	username, _ := payload["username"].(string)
	if email == "" {
		email = fmt.Sprintf("%s@local.dev", userID)
	}
	if username == "" {
		if email != "" {
			username = email
		} else {
			username = userID
		}
	}

	return authentities.NewUser(authentities.User{
		ID:           &userID,
		Email:        email,
		Username:     username,
		PasswordHash: "local-jwt-authenticated",
	})
}

// GetCurrentUserUniversal ports get_current_user_universal: it validates the bearer token
// as a Keycloak token (RS256) when the issuer matches KEYCLOAK_URL, otherwise as a local
// JWT (HS256). AUTH_ENABLED=false returns the default development user.
func GetCurrentUserUniversal(ctx context.Context, token string) (*authentities.User, error) {
	if strings.ToLower(envOr("AUTH_ENABLED", "true")) != "true" {
		id := envOr("DEFAULT_USER_ID", "dev-user-00000000-0000-0000-0000-000000000000")
		return authentities.NewUser(authentities.User{
			ID:           &id,
			Email:        envOr("DEFAULT_USER_EMAIL", "dev@localhost"),
			Username:     envOr("DEFAULT_USERNAME", "developer"),
			PasswordHash: "bypass-no-auth",
		})
	}

	claims, err := jwtUnverifiedClaims(token)
	if err != nil {
		// jwt.DecodeError: try local validation.
		return ValidateLocalToken(token)
	}
	issuer, _ := claims["iss"].(string)
	if keycloakURL := os.Getenv("KEYCLOAK_URL"); keycloakURL != "" && strings.HasPrefix(issuer, keycloakURL) {
		return ValidateKeycloakToken(ctx, token)
	}
	return ValidateLocalToken(token)
}
