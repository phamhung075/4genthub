package auth

import (
	"context"
	"encoding/json"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"

	taskentities "agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// KeycloakAuthResult is the KeycloakAuth authentication result data class.
type KeycloakAuthResult struct {
	Success        bool
	AccessToken    *string
	RefreshToken   *string
	ExpiresIn      *int
	User           *taskentities.OrderedMap[any]
	Roles          []string
	MCPPermissions []string
	Error          *string
}

// TokenValidation is the token validation result.
type TokenValidation struct {
	Valid          bool
	UserID         *string
	Email          *string
	Roles          []string
	MCPPermissions []string
	Error          *string
}

// KeycloakAuth is the Keycloak authentication service for MCP.
type KeycloakAuth struct {
	KeycloakURL  string
	Realm        string
	ClientID     string
	ClientSecret string

	TokenEndpoint      string
	UserinfoEndpoint   string
	IntrospectEndpoint string
	LogoutEndpoint     string
	JWKSEndpoint       string

	Client *http.Client

	JWKSCache     any
	JWKSCacheTime *time.Time
	JWKSCacheTTL  int
}

// NewKeycloakAuth initializes the Keycloak authentication service.
func NewKeycloakAuth() (*KeycloakAuth, error) {
	keycloakURL := os.Getenv("KEYCLOAK_URL")
	realm := os.Getenv("KEYCLOAK_REALM")
	clientID := os.Getenv("KEYCLOAK_CLIENT_ID")
	clientSecret := os.Getenv("KEYCLOAK_CLIENT_SECRET")

	if keycloakURL == "" || realm == "" || clientID == "" || clientSecret == "" {
		return nil, &value_objects.ValueError{
			Msg: "Missing Keycloak configuration. " +
				"Please set KEYCLOAK_URL, KEYCLOAK_REALM, " +
				"KEYCLOAK_CLIENT_ID, and KEYCLOAK_CLIENT_SECRET",
		}
	}

	keycloakURL = strings.TrimRight(keycloakURL, "/")

	a := &KeycloakAuth{
		KeycloakURL:  keycloakURL,
		Realm:        realm,
		ClientID:     clientID,
		ClientSecret: clientSecret,
		Client:       &http.Client{Timeout: 30 * time.Second},
		JWKSCacheTTL: 3600,
	}
	a.TokenEndpoint = keycloakURL + "/realms/" + realm + "/protocol/openid-connect/token"
	a.UserinfoEndpoint = keycloakURL + "/realms/" + realm + "/protocol/openid-connect/userinfo"
	a.IntrospectEndpoint = keycloakURL + "/realms/" + realm + "/protocol/openid-connect/token/introspect"
	a.LogoutEndpoint = keycloakURL + "/realms/" + realm + "/protocol/openid-connect/logout"
	a.JWKSEndpoint = keycloakURL + "/realms/" + realm + "/protocol/openid-connect/certs"
	return a, nil
}

func (a *KeycloakAuth) formPost(ctx context.Context, endpoint string, form url.Values) (*http.Response, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, endpoint, strings.NewReader(form.Encode()))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	return a.Client.Do(req)
}

// Login authenticates a user with Keycloak.
func (a *KeycloakAuth) Login(ctx context.Context, username, password string) KeycloakAuthResult {
	form := url.Values{}
	form.Set("grant_type", "password")
	form.Set("client_id", a.ClientID)
	form.Set("client_secret", a.ClientSecret)
	form.Set("username", username)
	form.Set("password", password)
	form.Set("scope", "openid profile email")

	resp, err := a.formPost(ctx, a.TokenEndpoint, form)
	if err != nil {
		return KeycloakAuthResult{Success: false, Error: strPtr(err.Error())}
	}
	defer resp.Body.Close()

	if resp.StatusCode == 200 {
		var tokenData map[string]any
		if err := json.NewDecoder(resp.Body).Decode(&tokenData); err != nil {
			return KeycloakAuthResult{Success: false, Error: strPtr(err.Error())}
		}
		userInfo := a.parseIDToken(optMapString(tokenData, "id_token"))
		accessTokenData := a.parseAccessToken(optMapString(tokenData, "access_token"))
		return KeycloakAuthResult{
			Success:        true,
			AccessToken:    optMapStringPtr(tokenData, "access_token"),
			RefreshToken:   optMapStringPtr(tokenData, "refresh_token"),
			ExpiresIn:      optMapIntPtr(tokenData, "expires_in"),
			User:           userInfo,
			Roles:          orderedStringList(accessTokenData, "roles"),
			MCPPermissions: orderedStringList(accessTokenData, "mcp_permissions"),
		}
	}

	var errorData map[string]any
	if err := json.NewDecoder(resp.Body).Decode(&errorData); err != nil {
		return KeycloakAuthResult{Success: false, Error: strPtr(err.Error())}
	}
	return KeycloakAuthResult{Success: false, Error: strPtr(optMapStringDefault(errorData, "error_description", "Authentication failed"))}
}

// ValidateToken validates an access token with Keycloak.
func (a *KeycloakAuth) ValidateToken(ctx context.Context, token string) TokenValidation {
	form := url.Values{}
	form.Set("token", token)
	form.Set("client_id", a.ClientID)
	form.Set("client_secret", a.ClientSecret)

	resp, err := a.formPost(ctx, a.IntrospectEndpoint, form)
	if err != nil {
		return TokenValidation{Valid: false, Error: strPtr(err.Error())}
	}
	defer resp.Body.Close()

	if resp.StatusCode == 200 {
		var introspection map[string]any
		if err := json.NewDecoder(resp.Body).Decode(&introspection); err != nil {
			return TokenValidation{Valid: false, Error: strPtr(err.Error())}
		}
		if value_objects.PyTruthy(introspection["active"]) {
			accessTokenData := a.parseAccessToken(token)
			return TokenValidation{
				Valid:          true,
				UserID:         optMapStringPtr(introspection, "sub"),
				Email:          optMapStringPtr(introspection, "email"),
				Roles:          orderedStringList(accessTokenData, "roles"),
				MCPPermissions: orderedStringList(accessTokenData, "mcp_permissions"),
			}
		}
		return TokenValidation{Valid: false, Error: strPtr("Token is not active")}
	}

	return TokenValidation{Valid: false, Error: strPtr("Failed to introspect token")}
}

// RefreshToken refreshes an access token using a refresh token.
func (a *KeycloakAuth) RefreshToken(ctx context.Context, refreshToken string) KeycloakAuthResult {
	form := url.Values{}
	form.Set("grant_type", "refresh_token")
	form.Set("refresh_token", refreshToken)
	form.Set("client_id", a.ClientID)
	form.Set("client_secret", a.ClientSecret)

	resp, err := a.formPost(ctx, a.TokenEndpoint, form)
	if err != nil {
		return KeycloakAuthResult{Success: false, Error: strPtr(err.Error())}
	}
	defer resp.Body.Close()

	if resp.StatusCode == 200 {
		var tokenData map[string]any
		if err := json.NewDecoder(resp.Body).Decode(&tokenData); err != nil {
			return KeycloakAuthResult{Success: false, Error: strPtr(err.Error())}
		}
		userInfo := a.parseIDToken(optMapString(tokenData, "id_token"))
		accessTokenData := a.parseAccessToken(optMapString(tokenData, "access_token"))
		return KeycloakAuthResult{
			Success:        true,
			AccessToken:    optMapStringPtr(tokenData, "access_token"),
			RefreshToken:   optMapStringPtr(tokenData, "refresh_token"),
			ExpiresIn:      optMapIntPtr(tokenData, "expires_in"),
			User:           userInfo,
			Roles:          orderedStringList(accessTokenData, "roles"),
			MCPPermissions: orderedStringList(accessTokenData, "mcp_permissions"),
		}
	}

	var errorData map[string]any
	if err := json.NewDecoder(resp.Body).Decode(&errorData); err != nil {
		return KeycloakAuthResult{Success: false, Error: strPtr(err.Error())}
	}
	return KeycloakAuthResult{Success: false, Error: strPtr(optMapStringDefault(errorData, "error_description", "Token refresh failed"))}
}

// Logout logs a user out from Keycloak.
func (a *KeycloakAuth) Logout(ctx context.Context, refreshToken string) bool {
	form := url.Values{}
	form.Set("refresh_token", refreshToken)
	form.Set("client_id", a.ClientID)
	form.Set("client_secret", a.ClientSecret)

	resp, err := a.formPost(ctx, a.LogoutEndpoint, form)
	if err != nil {
		return false
	}
	defer resp.Body.Close()
	return resp.StatusCode == 200 || resp.StatusCode == 204
}

// parseIDToken parses user info from an ID token.
func (a *KeycloakAuth) parseIDToken(idToken string) *taskentities.OrderedMap[any] {
	decoded, err := jwtUnverifiedClaims(idToken)
	if err != nil {
		return taskentities.NewOrderedMap[any]()
	}
	emailVerified := false
	if v, ok := decoded["email_verified"].(bool); ok {
		emailVerified = v
	}
	d := taskentities.NewOrderedMap[any]()
	d.Set("id", decoded["sub"])
	d.Set("email", decoded["email"])
	d.Set("username", decoded["preferred_username"])
	d.Set("name", decoded["name"])
	d.Set("given_name", decoded["given_name"])
	d.Set("family_name", decoded["family_name"])
	d.Set("email_verified", emailVerified)
	return d
}

// parseAccessToken parses roles and permissions from an access token.
func (a *KeycloakAuth) parseAccessToken(accessToken string) *taskentities.OrderedMap[any] {
	decoded, err := jwtUnverifiedClaims(accessToken)
	if err != nil {
		d := taskentities.NewOrderedMap[any]()
		d.Set("roles", []string{})
		d.Set("mcp_permissions", []string{})
		return d
	}

	roles := []string{}
	if realmAccess, ok := decoded["realm_access"].(map[string]any); ok {
		roles = append(roles, stringList(realmAccess["roles"])...)
	}
	if resourceAccess, ok := decoded["resource_access"].(map[string]any); ok {
		if clientAccess, ok := resourceAccess[a.ClientID].(map[string]any); ok {
			roles = append(roles, stringList(clientAccess["roles"])...)
		}
	}

	mcpPermissions := []string{}
	if containsString(roles, "mcp-admin") {
		mcpPermissions = []string{"*"}
	} else if custom, ok := decoded["mcp_permissions"]; ok {
		mcpPermissions = stringList(custom)
	} else if perms, ok := decoded["permissions"]; ok {
		allPermissions := stringList(perms)
		for _, p := range allPermissions {
			if strings.HasPrefix(p, "mcp:") {
				mcpPermissions = append(mcpPermissions, p)
			}
		}
	}

	scope := []string{}
	if s, ok := decoded["scope"].(string); ok && s != "" {
		scope = value_objects.PySplit(s)
	}

	d := taskentities.NewOrderedMap[any]()
	d.Set("roles", roles)
	d.Set("mcp_permissions", mcpPermissions)
	d.Set("scope", scope)
	return d
}

// GetUserInfo gets user info from the Keycloak userinfo endpoint.
func (a *KeycloakAuth) GetUserInfo(ctx context.Context, accessToken string) map[string]any {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, a.UserinfoEndpoint, nil)
	if err != nil {
		return nil
	}
	req.Header.Set("Authorization", "Bearer "+accessToken)
	resp, err := a.Client.Do(req)
	if err != nil {
		return nil
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		return nil
	}
	var result map[string]any
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil
	}
	return result
}

// Close closes HTTP client connections (httpx.AsyncClient.aclose).
func (a *KeycloakAuth) Close() {}

func optMapString(m map[string]any, key string) string {
	if s, ok := m[key].(string); ok {
		return s
	}
	return ""
}

func optMapStringPtr(m map[string]any, key string) *string {
	if s, ok := m[key].(string); ok {
		return &s
	}
	return nil
}

func optMapStringDefault(m map[string]any, key, def string) string {
	if s, ok := m[key].(string); ok {
		return s
	}
	return def
}

func optMapIntPtr(m map[string]any, key string) *int {
	switch v := m[key].(type) {
	case float64:
		n := int(v)
		return &n
	case int:
		n := v
		return &n
	case int64:
		n := int(v)
		return &n
	}
	return nil
}

// stringList converts a decoded JSON list to []string.
func stringList(v any) []string {
	switch x := v.(type) {
	case []any:
		out := []string{}
		for _, e := range x {
			if s, ok := e.(string); ok {
				out = append(out, s)
			} else {
				out = append(out, value_objects.PyStr(e))
			}
		}
		return out
	case []string:
		return append([]string{}, x...)
	}
	return []string{}
}

func containsString(list []string, target string) bool {
	for _, s := range list {
		if s == target {
			return true
		}
	}
	return false
}

// orderedStringList reads a []string value from an OrderedMap.
func orderedStringList(m *taskentities.OrderedMap[any], key string) []string {
	if m == nil {
		return nil
	}
	v, ok := m.Get(key)
	if !ok {
		return nil
	}
	return stringList(v)
}
