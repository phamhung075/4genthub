package auth

import (
	"context"
	"encoding/json"
	"net/http"
	"net/url"
	"os"
	"strconv"
	"strings"
	"time"

	taskentities "agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

type cachedValidation struct {
	cacheTime time.Time
	claims    map[string]any
}

// MCPKeycloakValidator validates Keycloak tokens specifically for MCP connections.
type MCPKeycloakValidator struct {
	KeycloakURL  string
	Realm        string
	ClientID     string
	ClientSecret string

	RealmURL           string
	JWKSURI            string
	IntrospectEndpoint string

	jwksCache     map[string]any
	jwksCacheTime *time.Time
	tokenCache    map[string]cachedValidation
	cacheTTL      int
}

// NewMCPKeycloakValidator initializes the MCP Keycloak validator.
func NewMCPKeycloakValidator() *MCPKeycloakValidator {
	keycloakURL := os.Getenv("KEYCLOAK_URL")
	realm := envOr("KEYCLOAK_REALM", "agenthub")
	clientID := envOr("KEYCLOAK_CLIENT_ID", "mcp-backend")
	clientSecret := os.Getenv("KEYCLOAK_CLIENT_SECRET")

	cacheTTL, err := strconv.Atoi(envOr("KEYCLOAK_TOKEN_CACHE_TTL", "300"))
	if err != nil {
		cacheTTL = 300
	}

	v := &MCPKeycloakValidator{
		KeycloakURL:  keycloakURL,
		Realm:        realm,
		ClientID:     clientID,
		ClientSecret: clientSecret,
		tokenCache:   map[string]cachedValidation{},
		cacheTTL:     cacheTTL,
	}
	v.RealmURL = keycloakURL + "/realms/" + realm
	v.JWKSURI = v.RealmURL + "/protocol/openid-connect/certs"
	v.IntrospectEndpoint = v.RealmURL + "/protocol/openid-connect/token/introspect"
	return v
}

// ValidateMCPToken validates a token for MCP access.
func (v *MCPKeycloakValidator) ValidateMCPToken(ctx context.Context, token string) map[string]any {
	cached := v.getCachedValidation(token)
	if cached != nil {
		return cached
	}

	jwks := v.getJWKS(ctx)
	if jwks == nil {
		return nil
	}

	claims := v.decodeToken(token, jwks)
	if claims == nil {
		return nil
	}

	if !v.validateMCPRequirements(claims) {
		return nil
	}

	v.cacheValidation(token, claims)
	return claims
}

// IntrospectToken introspects a token with the Keycloak server.
func (v *MCPKeycloakValidator) IntrospectToken(ctx context.Context, token string) map[string]any {
	data := url.Values{}
	data.Set("token", token)
	data.Set("client_id", v.ClientID)
	data.Set("client_secret", v.ClientSecret)

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, v.IntrospectEndpoint, strings.NewReader(data.Encode()))
	if err != nil {
		return nil
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil
	}
	defer resp.Body.Close()

	if resp.StatusCode == 200 {
		var result map[string]any
		if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
			return nil
		}
		if value_objects.PyTruthy(result["active"]) {
			return result
		}
	}
	return nil
}

// ExtractUserInfo extracts user information from token claims.
func (v *MCPKeycloakValidator) ExtractUserInfo(claims map[string]any) *taskentities.OrderedMap[any] {
	emailVerified := false
	if b, ok := claims["email_verified"].(bool); ok {
		emailVerified = b
	}
	d := taskentities.NewOrderedMap[any]()
	d.Set("user_id", claims["sub"])
	d.Set("username", claims["preferred_username"])
	d.Set("email", claims["email"])
	d.Set("name", claims["name"])
	d.Set("given_name", claims["given_name"])
	d.Set("family_name", claims["family_name"])
	d.Set("email_verified", emailVerified)
	d.Set("roles", v.extractRoles(claims))
	d.Set("mcp_permissions", v.extractMCPPermissions(claims))
	return d
}

// extractRoles extracts (deduplicated) user roles from token claims.
func (v *MCPKeycloakValidator) extractRoles(claims map[string]any) []string {
	var set taskentities.StringSet

	realmAccess, _ := claims["realm_access"].(map[string]any)
	for _, role := range stringList(realmAccess["roles"]) {
		set.Add(role)
	}

	resourceAccess, _ := claims["resource_access"].(map[string]any)
	if clientRoles, ok := resourceAccess[v.ClientID].(map[string]any); ok {
		for _, role := range stringList(clientRoles["roles"]) {
			set.Add(role)
		}
	}
	return set.Items()
}

// extractMCPPermissions extracts (deduplicated) MCP permissions from claims.
func (v *MCPKeycloakValidator) extractMCPPermissions(claims map[string]any) []string {
	var set taskentities.StringSet
	roles := v.extractRoles(claims)

	rolePermissions := map[string][]string{
		"admin":     {"mcp:*"},
		"developer": {"mcp:read", "mcp:write", "mcp:execute"},
		"user":      {"mcp:read", "mcp:execute"},
		"viewer":    {"mcp:read"},
	}
	for _, role := range roles {
		if perms, ok := rolePermissions[role]; ok {
			for _, p := range perms {
				set.Add(p)
			}
		}
	}

	customPermissions, ok := claims["mcp_permissions"].([]any)
	if ok {
		for _, p := range stringList(customPermissions) {
			set.Add(p)
		}
	}
	return set.Items()
}

// validateMCPRequirements validates that the token meets MCP-specific requirements.
func (v *MCPKeycloakValidator) validateMCPRequirements(claims map[string]any) bool {
	if exp, ok := claims["exp"]; ok {
		if expSeconds, err := jwtClaimInt(exp); err == nil {
			if time.Unix(int64(expSeconds), 0).Before(time.Now()) {
				return false
			}
		}
	}

	if value_objects.PyLower(envOr("KEYCLOAK_VERIFY_TOKEN_AUDIENCE", "true")) == "true" {
		audience := claims["aud"]
		expectedAudience := envOr("KEYCLOAK_TOKEN_AUDIENCE", v.ClientID)

		switch aud := audience.(type) {
		case []any:
			found := false
			for _, a := range aud {
				if s, ok := a.(string); ok && s == expectedAudience {
					found = true
				}
			}
			if !found {
				return false
			}
		case []string:
			if !containsString(aud, expectedAudience) {
				return false
			}
		default:
			if s, ok := audience.(string); !ok || s != expectedAudience {
				return false
			}
		}
	}

	for _, claim := range []string{"sub", "iat", "exp"} {
		if _, ok := claims[claim]; !ok {
			return false
		}
	}

	if len(v.extractMCPPermissions(claims)) == 0 {
		return false
	}
	return true
}

// getJWKS gets the JSON Web Key Set from Keycloak.
func (v *MCPKeycloakValidator) getJWKS(ctx context.Context) map[string]any {
	if v.jwksCache != nil && v.jwksCacheTime != nil {
		cacheAge := int(time.Since(*v.jwksCacheTime).Seconds())
		if cacheAge < 3600 {
			return v.jwksCache
		}
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, v.JWKSURI, nil)
	if err != nil {
		return nil
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil
	}
	defer resp.Body.Close()
	if resp.StatusCode == 200 {
		var jwks map[string]any
		if err := json.NewDecoder(resp.Body).Decode(&jwks); err != nil {
			return nil
		}
		v.jwksCache = jwks
		now := time.Now()
		v.jwksCacheTime = &now
		return v.jwksCache
	}
	return nil
}

// decodeToken decodes and validates a JWT token against the JWKS.
func (v *MCPKeycloakValidator) decodeToken(token string, jwks map[string]any) map[string]any {
	header, err := jwtUnverifiedHeader(token)
	if err != nil {
		return nil
	}
	kid, _ := header["kid"].(string)

	var key map[string]any
	keys, _ := jwks["keys"].([]any)
	for _, k := range keys {
		jwk, ok := k.(map[string]any)
		if !ok {
			continue
		}
		if jwkKid, _ := jwk["kid"].(string); jwkKid == kid {
			key = jwk
			break
		}
	}
	if key == nil {
		return nil
	}

	n, _ := key["n"].(string)
	e, _ := key["e"].(string)
	pub, err := rsaPublicKeyFromJWK(n, e)
	if err != nil {
		return nil
	}

	audience := envOr("KEYCLOAK_TOKEN_AUDIENCE", v.ClientID)
	claims, err := jwtDecodeRS256Claims(token, pub, jwtDecodeOptions{
		VerifyAud: true,
		Audience:  audience,
		VerifyIss: true,
		Issuer:    v.RealmURL,
		VerifyExp: true,
		VerifyIat: true,
		VerifyNbf: true,
	})
	if err != nil {
		return nil
	}
	return claims
}

// getCachedValidation gets a cached validation result.
func (v *MCPKeycloakValidator) getCachedValidation(token string) map[string]any {
	cached, ok := v.tokenCache[token]
	if !ok {
		return nil
	}
	if int(time.Since(cached.cacheTime).Seconds()) < v.cacheTTL {
		return cached.claims
	}
	delete(v.tokenCache, token)
	return nil
}

// cacheValidation caches a validation result.
func (v *MCPKeycloakValidator) cacheValidation(token string, claims map[string]any) {
	v.tokenCache[token] = cachedValidation{cacheTime: time.Now(), claims: claims}
	v.cleanCache()
}

// cleanCache removes expired cache entries.
func (v *MCPKeycloakValidator) cleanCache() {
	now := time.Now()
	var expired []string
	for token, cached := range v.tokenCache {
		if int(now.Sub(cached.cacheTime).Seconds()) > v.cacheTTL {
			expired = append(expired, token)
		}
	}
	for _, token := range expired {
		delete(v.tokenCache, token)
	}
}

// Global validator instance.
var mcpKeycloakValidatorInstance *MCPKeycloakValidator

// GetMCPValidator gets the global MCP Keycloak validator instance.
func GetMCPValidator() *MCPKeycloakValidator {
	if mcpKeycloakValidatorInstance == nil {
		mcpKeycloakValidatorInstance = NewMCPKeycloakValidator()
	}
	return mcpKeycloakValidatorInstance
}

// ValidateMCPRequest validates an MCP request authorization header.
func ValidateMCPRequest(ctx context.Context, authorization string) *taskentities.OrderedMap[any] {
	if authorization == "" {
		return nil
	}

	parts := value_objects.PySplit(authorization)
	if len(parts) != 2 || value_objects.PyLower(parts[0]) != "bearer" {
		return nil
	}
	token := parts[1]

	validator := GetMCPValidator()
	claims := validator.ValidateMCPToken(ctx, token)
	if claims != nil {
		return validator.ExtractUserInfo(claims)
	}
	return nil
}
