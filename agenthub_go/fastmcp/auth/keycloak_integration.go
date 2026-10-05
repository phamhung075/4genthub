package auth

import (
	"context"
	"crypto/rand"
	"crypto/sha256"
	"crypto/tls"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"

	taskentities "agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// KeycloakAuthProvider is the clean Keycloak authentication provider for MCP.
type KeycloakAuthProvider struct {
	KeycloakURL  string
	Realm        string
	ClientID     string
	ClientSecret string

	VerifyAudience    bool
	SSLVerify         bool
	TokenCacheTTL     int
	PublicKeyCacheTTL int

	RealmURL     string
	WellKnownURL string
	TokenURL     string
	UserinfoURL  string
	JWKSURL      string

	httpClient      *http.Client
	jwksClient      *KeycloakJWKSClient
	oidcConfig      map[string]any
	lastConfigFetch *time.Time
}

// NewKeycloakAuthProvider initializes the Keycloak authentication provider.
func NewKeycloakAuthProvider(
	keycloakURL, realm, clientID, clientSecret string,
	verifyAudience, sslVerify bool,
	tokenCacheTTL, publicKeyCacheTTL int,
) (*KeycloakAuthProvider, error) {
	if keycloakURL == "" {
		keycloakURL = os.Getenv("KEYCLOAK_URL")
	}
	if realm == "" {
		realm = envOr("KEYCLOAK_REALM", "agenthub")
	}
	if clientID == "" {
		clientID = envOr("KEYCLOAK_CLIENT_ID", "mcp-backend")
	}
	if clientSecret == "" {
		clientSecret = os.Getenv("KEYCLOAK_CLIENT_SECRET")
	}

	if keycloakURL == "" {
		return nil, &value_objects.ValueError{Msg: "KEYCLOAK_URL is required"}
	}

	p := &KeycloakAuthProvider{
		KeycloakURL:       keycloakURL,
		Realm:             realm,
		ClientID:          clientID,
		ClientSecret:      clientSecret,
		VerifyAudience:    verifyAudience,
		SSLVerify:         sslVerify,
		TokenCacheTTL:     tokenCacheTTL,
		PublicKeyCacheTTL: publicKeyCacheTTL,
		httpClient: &http.Client{
			Timeout:   5 * time.Second,
			Transport: &http.Transport{TLSClientConfig: &tls.Config{InsecureSkipVerify: !sslVerify}},
		},
	}

	p.RealmURL = keycloakURL + "/realms/" + realm
	p.WellKnownURL = p.RealmURL + "/.well-known/openid-configuration"
	p.TokenURL = p.RealmURL + "/protocol/openid-connect/token"
	p.UserinfoURL = p.RealmURL + "/protocol/openid-connect/userinfo"
	p.JWKSURL = p.RealmURL + "/protocol/openid-connect/certs"
	return p, nil
}

// JWKSClient returns the lazy JWKS client for token validation.
func (p *KeycloakAuthProvider) JWKSClient() *KeycloakJWKSClient {
	if p.jwksClient == nil {
		p.jwksClient = NewKeycloakJWKSClient(p.JWKSURL, time.Duration(p.PublicKeyCacheTTL)*time.Second, nil)
	}
	return p.jwksClient
}

// GetOIDCConfiguration gets the OpenID Connect configuration from Keycloak.
func (p *KeycloakAuthProvider) GetOIDCConfiguration(ctx context.Context) (map[string]any, error) {
	now := time.Now().UTC()

	if p.oidcConfig != nil && p.lastConfigFetch != nil {
		if int(now.Sub(*p.lastConfigFetch).Seconds()) < p.PublicKeyCacheTTL {
			return p.oidcConfig, nil
		}
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, p.WellKnownURL, nil)
	if err != nil {
		if p.oidcConfig != nil {
			return p.oidcConfig, nil
		}
		return nil, err
	}
	resp, err := p.httpClient.Do(req)
	if err != nil {
		if p.oidcConfig != nil {
			return p.oidcConfig, nil
		}
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		if p.oidcConfig != nil {
			return p.oidcConfig, nil
		}
		return nil, fmt.Errorf("HTTP %d", resp.StatusCode)
	}

	var config map[string]any
	if err := json.NewDecoder(resp.Body).Decode(&config); err != nil {
		if p.oidcConfig != nil {
			return p.oidcConfig, nil
		}
		return nil, err
	}
	p.oidcConfig = config
	nowCopy := now
	p.lastConfigFetch = &nowCopy
	return p.oidcConfig, nil
}

// ValidateToken validates a Keycloak JWT token.
func (p *KeycloakAuthProvider) ValidateToken(ctx context.Context, token string) map[string]any {
	config, err := p.GetOIDCConfiguration(ctx)
	if err != nil {
		return nil
	}
	issuer, _ := config["issuer"].(string)

	signingKey, err := p.JWKSClient().GetSigningKeyFromJWT(token)
	if err != nil {
		return nil
	}

	opts := jwtDecodeOptions{
		VerifyAud: p.VerifyAudience,
		Audience:  p.ClientID,
		VerifyIss: true,
		Issuer:    issuer,
		VerifyExp: true,
		VerifyIat: true,
		VerifyNbf: true,
		Require:   []string{"exp", "iat", "sub"},
	}
	if !p.VerifyAudience {
		opts.Audience = ""
	}

	payload, err := jwtDecodeRS256Claims(token, signingKey, opts)
	if err != nil {
		return nil
	}

	if !value_objects.PyTruthy(payload["sub"]) {
		return nil
	}

	if exp, ok := payload["exp"]; ok {
		if v, err := jwtClaimInt(exp); err == nil && v < float64(time.Now().UTC().UnixNano())/1e9 {
			return nil
		}
	}
	return payload
}

// GetUserInfo fetches user information from the Keycloak userinfo endpoint.
func (p *KeycloakAuthProvider) GetUserInfo(ctx context.Context, accessToken string) map[string]any {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, p.UserinfoURL, nil)
	if err != nil {
		return nil
	}
	req.Header.Set("Authorization", "Bearer "+accessToken)
	resp, err := p.httpClient.Do(req)
	if err != nil {
		return nil
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return nil
	}
	var userInfo map[string]any
	if err := json.NewDecoder(resp.Body).Decode(&userInfo); err != nil {
		return nil
	}
	return userInfo
}

// ExchangeToken exchanges credentials for tokens using the Keycloak token endpoint.
func (p *KeycloakAuthProvider) ExchangeToken(
	ctx context.Context,
	username, password, refreshToken, authorizationCode, redirectURI *string,
) map[string]any {
	data := url.Values{}
	data.Set("client_id", p.ClientID)

	if p.ClientSecret != "" {
		data.Set("client_secret", p.ClientSecret)
	}

	switch {
	case username != nil && password != nil:
		data.Set("grant_type", "password")
		data.Set("username", *username)
		data.Set("password", *password)
		data.Set("scope", "openid profile email")
	case refreshToken != nil:
		data.Set("grant_type", "refresh_token")
		data.Set("refresh_token", *refreshToken)
	case authorizationCode != nil && redirectURI != nil:
		data.Set("grant_type", "authorization_code")
		data.Set("code", *authorizationCode)
		data.Set("redirect_uri", *redirectURI)
	default:
		return nil
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, p.TokenURL, strings.NewReader(data.Encode()))
	if err != nil {
		return nil
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	resp, err := p.httpClient.Do(req)
	if err != nil {
		return nil
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return nil
	}

	var tokenResponse map[string]any
	if err := json.NewDecoder(resp.Body).Decode(&tokenResponse); err != nil {
		return nil
	}
	return tokenResponse
}

// Logout logs out a user by revoking the refresh token.
func (p *KeycloakAuthProvider) Logout(ctx context.Context, refreshToken string) bool {
	logoutURL := p.RealmURL + "/protocol/openid-connect/logout"

	data := url.Values{}
	data.Set("client_id", p.ClientID)
	data.Set("refresh_token", refreshToken)
	if p.ClientSecret != "" {
		data.Set("client_secret", p.ClientSecret)
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, logoutURL, strings.NewReader(data.Encode()))
	if err != nil {
		return false
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	resp, err := p.httpClient.Do(req)
	if err != nil {
		return false
	}
	defer resp.Body.Close()
	return resp.StatusCode >= 200 && resp.StatusCode < 300
}

// Close closes HTTP client connections.
func (p *KeycloakAuthProvider) Close() {}

// KeycloakMCPAuth is the MCP-specific Keycloak authentication handler.
type KeycloakMCPAuth struct {
	Keycloak *KeycloakAuthProvider
}

// NewKeycloakMCPAuth initializes the MCP Keycloak authentication handler.
func NewKeycloakMCPAuth(keycloakProvider *KeycloakAuthProvider) (*KeycloakMCPAuth, error) {
	if keycloakProvider == nil {
		provider, err := NewKeycloakAuthProvider("", "", "", "", true, true, 300, 3600)
		if err != nil {
			return nil, err
		}
		keycloakProvider = provider
	}
	return &KeycloakMCPAuth{Keycloak: keycloakProvider}, nil
}

// AuthenticateMCPRequest authenticates an MCP request using a Keycloak token.
func (a *KeycloakMCPAuth) AuthenticateMCPRequest(ctx context.Context, authorizationHeader *string) *taskentities.OrderedMap[any] {
	if authorizationHeader == nil || *authorizationHeader == "" {
		return nil
	}

	parts := value_objects.PySplit(*authorizationHeader)
	if len(parts) != 2 || value_objects.PyLower(parts[0]) != "bearer" {
		return nil
	}
	token := parts[1]

	payload := a.Keycloak.ValidateToken(ctx, token)
	if payload == nil {
		return nil
	}

	roles := payloadRealmRoles(payload)
	username := payloadValue(payload, "preferred_username", payload["email"])
	scope, _ := payload["scope"].(string)

	userContext := taskentities.NewOrderedMap[any]()
	userContext.Set("user_id", payload["sub"])
	userContext.Set("username", username)
	userContext.Set("email", payload["email"])
	userContext.Set("roles", roles)
	userContext.Set("scopes", value_objects.PySplit(scope))
	userContext.Set("authenticated", true)
	userContext.Set("auth_provider", "keycloak")
	userContext.Set("token_exp", payload["exp"])
	userContext.Set("session_id", payload["sid"])

	mcpPermissions := []string{}
	switch {
	case containsString(roles, "admin"):
		mcpPermissions = []string{"mcp:*"}
	case containsString(roles, "developer"):
		mcpPermissions = []string{"mcp:read", "mcp:write", "mcp:execute"}
	case containsString(roles, "user"):
		mcpPermissions = []string{"mcp:read", "mcp:execute"}
	default:
		mcpPermissions = []string{"mcp:read"}
	}
	userContext.Set("mcp_permissions", mcpPermissions)

	return userContext
}

// CreateMCPToken creates an MCP-specific token from a Keycloak token.
func (a *KeycloakMCPAuth) CreateMCPToken(ctx context.Context, keycloakToken, name string, scopes *[]string) *taskentities.OrderedMap[any] {
	payload := a.Keycloak.ValidateToken(ctx, keycloakToken)
	if payload == nil {
		return nil
	}

	mcpToken := "mcp_" + tokenURLSafe(32)
	sum := sha256.Sum256([]byte(mcpToken))
	tokenHash := hex.EncodeToString(sum[:])

	tokenScopes := []string{"mcp:read", "mcp:execute"}
	if scopes != nil {
		tokenScopes = *scopes
	}

	tokenInfo := taskentities.NewOrderedMap[any]()
	tokenInfo.Set("token", mcpToken)
	tokenInfo.Set("token_hash", tokenHash)
	tokenInfo.Set("name", name)
	tokenInfo.Set("user_id", payload["sub"])
	tokenInfo.Set("username", payload["preferred_username"])
	tokenInfo.Set("scopes", tokenScopes)
	tokenInfo.Set("created_at", value_objects.IsoFormat(time.Now().UTC().Truncate(time.Microsecond)))
	tokenInfo.Set("expires_at", value_objects.IsoFormat(time.Now().UTC().Add(30*24*time.Hour).Truncate(time.Microsecond)))
	tokenInfo.Set("keycloak_session", payload["sid"])
	tokenInfo.Set("active", true)
	return tokenInfo
}

func payloadValue(payload map[string]any, key string, def any) any {
	if v, ok := payload[key]; ok {
		return v
	}
	return def
}

func payloadRealmRoles(payload map[string]any) []string {
	realmAccess, ok := payload["realm_access"].(map[string]any)
	if !ok {
		return []string{}
	}
	return stringList(realmAccess["roles"])
}

// tokenURLSafe is secrets.token_urlsafe(n): base64url without padding.
func tokenURLSafe(n int) string {
	b := make([]byte, n)
	if _, err := rand.Read(b); err != nil {
		panic(err)
	}
	return base64.RawURLEncoding.EncodeToString(b)
}

// Singleton instance for easy import.
var defaultKeycloakProvider *KeycloakAuthProvider

// GetKeycloakProvider gets or creates the default Keycloak provider.
func GetKeycloakProvider() (*KeycloakAuthProvider, error) {
	if defaultKeycloakProvider == nil {
		provider, err := NewKeycloakAuthProvider("", "", "", "", true, true, 300, 3600)
		if err != nil {
			return nil, err
		}
		defaultKeycloakProvider = provider
	}
	return defaultKeycloakProvider, nil
}

// GetKeycloakMCPAuth gets or creates the default Keycloak MCP auth handler.
func GetKeycloakMCPAuth() (*KeycloakMCPAuth, error) {
	provider, err := GetKeycloakProvider()
	if err != nil {
		return nil, err
	}
	return NewKeycloakMCPAuth(provider)
}
