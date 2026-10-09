// Package providers ports fastmcp/server/auth/providers — JWT Bearer provider.
package providers

import (
	"context"
	"os"
)

// AccessToken mirrors the MCP AccessToken returned by the provider.
type AccessToken struct {
	Token     string
	ClientID  string
	Scopes    []string
	ExpiresAt *int
}

// JWTBackend is the minimal interface needed from
// fastmcp.auth.mcp_integration.jwt_auth_backend.create_jwt_auth_backend. That port
// EXISTS - NewJWTAuthBackend in fastmcp/auth/mcp_integration/jwt_auth_backend.go -
// and this provider is constructed whenever JWT auth is configured
// (mcp_auth_config.go:32 calls NewJWTBearerAuthProvider).
type JWTBackend interface {
	VerifyToken(ctx context.Context, token string) (*AccessToken, error)
}

// NewJWTBackendFunc builds the JWT backend. NOTHING IN THE TREE ASSIGNS IT: a search
// for the name returns this declaration and the read in the constructor, no writer,
// so p.JWTBackend stays nil and VerifyToken answers (nil, nil) - no token and no
// error. The reference does the opposite at construction: jwt_bearer.py:65 calls
// create_jwt_auth_backend(...) unconditionally. This is the injected-global defect
// class that 67af511f fixed for routes.Ownership - an assignment no production code
// made - recorded here rather than silently repaired, because wiring it decides how
// MCP requests authenticate.
var NewJWTBackendFunc func(requiredScopes []string) JWTBackend

// JWTBearerAuthProvider validates JWT tokens from the token management system.
type JWTBearerAuthProvider struct {
	SecretKey      string
	Issuer         string
	Audience       []string
	RequiredScopes []string
	CheckDatabase  bool
	JWTBackend     JWTBackend
}

// NewJWTBearerAuthProvider mirrors JWTBearerAuthProvider.__init__.
func NewJWTBearerAuthProvider(
	secretKey *string,
	issuer string,
	audience []string,
	requiredScopes []string,
	checkDatabase bool,
) (*JWTBearerAuthProvider, error) {
	key := ""
	if secretKey != nil {
		key = *secretKey
	} else {
		key = os.Getenv("JWT_SECRET_KEY")
	}
	if key == "" {
		return nil, &missingSecretError{}
	}
	if requiredScopes == nil {
		requiredScopes = []string{"mcp:access"}
	}
	p := &JWTBearerAuthProvider{
		SecretKey:      key,
		Issuer:         issuer,
		Audience:       audience,
		RequiredScopes: requiredScopes,
		CheckDatabase:  checkDatabase,
	}
	if NewJWTBackendFunc != nil {
		p.JWTBackend = NewJWTBackendFunc(requiredScopes)
	}
	return p, nil
}

type missingSecretError struct{}

func (e *missingSecretError) Error() string {
	return "JWT_SECRET_KEY must be provided or set in environment"
}

// VerifyToken verifies the provided JWT bearer token.
func (p *JWTBearerAuthProvider) VerifyToken(ctx context.Context, token string) (*AccessToken, error) {
	if p.JWTBackend == nil {
		return nil, nil
	}
	return p.JWTBackend.VerifyToken(ctx, token)
}

// LoadAccessToken delegates to VerifyToken for consistency.
func (p *JWTBearerAuthProvider) LoadAccessToken(ctx context.Context, token string) (*AccessToken, error) {
	return p.VerifyToken(ctx, token)
}

// ValidateUserToken validates a regular user JWT token (not API token).
func (p *JWTBearerAuthProvider) ValidateUserToken(token string, payload map[string]any) *AccessToken {
	if payload["token_type"] != "access" {
		return nil
	}
	var userID string
	if v, ok := payload["sub"].(string); ok && v != "" {
		userID = v
	} else if v, ok := payload["user_id"].(string); ok && v != "" {
		userID = v
	}
	roles := stringSlice(payload["roles"])

	if userID == "" {
		return nil
	}

	mcpScopes := []string{"mcp:access"}
	if contains(roles, "admin") {
		mcpScopes = append(mcpScopes, "mcp:admin", "mcp:write", "mcp:read")
	} else if contains(roles, "developer") {
		mcpScopes = append(mcpScopes, "mcp:write", "mcp:read")
	} else if contains(roles, "user") {
		mcpScopes = append(mcpScopes, "mcp:read")
	}

	var expiresAt *int
	if v, ok := payload["exp"]; ok {
		if n, ok := v.(int); ok {
			expiresAt = &n
		}
	}

	return &AccessToken{
		Token:     token,
		ClientID:  userID,
		Scopes:    mcpScopes,
		ExpiresAt: expiresAt,
	}
}

// MapScopesToMCP maps API token scopes to MCP permissions.
func MapScopesToMCP(scopes []string) []string {
	mcpScopes := []string{}
	scopeMappings := map[string]string{
		"read:tasks":    "mcp:read",
		"write:tasks":   "mcp:write",
		"read:context":  "mcp:read",
		"write:context": "mcp:write",
		"read:agents":   "mcp:read",
		"write:agents":  "mcp:write",
		"execute:mcp":   "mcp:execute",
	}
	for _, scope := range scopes {
		if mcpScope, ok := scopeMappings[scope]; ok {
			if !contains(mcpScopes, mcpScope) {
				mcpScopes = append(mcpScopes, mcpScope)
			}
		}
	}
	return mcpScopes
}

func contains(xs []string, v string) bool {
	for _, x := range xs {
		if x == v {
			return true
		}
	}
	return false
}

func stringSlice(v any) []string {
	switch t := v.(type) {
	case []string:
		return t
	case []any:
		out := make([]string, 0, len(t))
		for _, e := range t {
			if s, ok := e.(string); ok {
				out = append(out, s)
			}
		}
		return out
	}
	return nil
}
