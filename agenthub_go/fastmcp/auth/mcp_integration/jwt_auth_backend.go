// JWT Authentication Backend for MCP integration, ported from
// agenthub_main/src/fastmcp/auth/mcp_integration/jwt_auth_backend.py.
//
// Port notes:
//   - The Python `mcp.server.auth.provider.TokenVerifier` base class and its
//     `AccessToken` dataclass have no Go dependency available, so AccessToken is
//     reproduced here with the same fields.
//   - The database_session_factory argument of create_jwt_auth_backend maps to a
//     minimal MCPUserLookup interface instead of constructing a DB repository
//     (the application/integration layer must not touch the database package).
package mcp_integration

import (
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"

	appServices "agenthub/fastmcp/auth/application/services"
	"agenthub/fastmcp/auth/domain"
	authEntities "agenthub/fastmcp/auth/domain/entities"
	domServices "agenthub/fastmcp/auth/domain/services"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// MCPUserContext is the user context for MCP operations.
type MCPUserContext struct {
	UserID   string
	Email    string
	Username string
	Roles    []string
	Scopes   []string
}

// AccessToken mirrors mcp.server.auth.provider.AccessToken.
type AccessToken struct {
	Token     string
	ClientID  string
	Scopes    []string
	ExpiresAt *int64
}

// MCPUserLookup is the minimal user_repository.find_by_id dependency. The Python
// infrastructure UserRepository satisfies it with FindByID.
type MCPUserLookup interface {
	FindByID(ctx context.Context, userID string) (*authEntities.User, error)
}

// JWTAuthBackend integrates the authentication system with MCP.
type JWTAuthBackend struct {
	jwtService     *domServices.JWTService
	authService    *appServices.AuthService
	userRepository MCPUserLookup

	requiredScopes []string

	mu               sync.Mutex
	userContextCache map[string]*MCPUserContext
	cacheTimestamps  map[string]float64
	cacheTTL         float64
}

// mcpBackendInvalidError mirrors jwt exceptions used by the Supabase branch.
type mcpBackendInvalidError struct{ msg string }

func (e *mcpBackendInvalidError) Error() string { return e.msg }

// NewJWTAuthBackend mirrors JWTAuthBackend.__init__.
func NewJWTAuthBackend(jwtService *domServices.JWTService, authService *appServices.AuthService, userRepository MCPUserLookup, requiredScopes []string) (*JWTAuthBackend, error) {
	jwtSecret := os.Getenv("JWT_SECRET_KEY")
	if jwtSecret == "" {
		return nil, &value_objects.ValueError{Msg: "JWT_SECRET_KEY environment variable not set"}
	}

	if jwtService == nil {
		svc, err := domServices.NewJWTService(jwtSecret, domServices.DefaultIssuer)
		if err != nil {
			return nil, err
		}
		jwtService = svc
	}
	if requiredScopes == nil {
		requiredScopes = []string{"mcp:access"}
	}

	return &JWTAuthBackend{
		jwtService:       jwtService,
		authService:      authService,
		userRepository:   userRepository,
		requiredScopes:   requiredScopes,
		userContextCache: map[string]*MCPUserContext{},
		cacheTimestamps:  map[string]float64{},
		cacheTTL:         300, // 5 minutes
	}, nil
}

// SecretKey is the secret_key property.
func (b *JWTAuthBackend) SecretKey() string { return b.jwtService.SecretKey }

// Algorithm is the algorithm property (the Python JWTService.ALGORITHM constant).
func (b *JWTAuthBackend) Algorithm() string { return domServices.JWTAlgorithm }

// RequiredScopes is the required_scopes property.
func (b *JWTAuthBackend) RequiredScopes() []string { return b.requiredScopes }

// ValidateTokenDualAuth tries local JWT and then Supabase validation.
func (b *JWTAuthBackend) ValidateTokenDualAuth(token string) map[string]any {
	// Try local JWT service first.
	for _, tokenType := range []string{"access", "api_token"} {
		if payload := b.jwtService.VerifyToken(token, tokenType, "mcp-server"); payload != nil {
			return payload
		}
	}

	// Try Supabase JWT secret.
	supabaseSecret := os.Getenv("SUPABASE_JWT_SECRET")
	if supabaseSecret == "" {
		return nil
	}

	payload, err := decodeMCPHS256Audience(token, supabaseSecret, "authenticated")
	if err != nil {
		return nil
	}
	if payload != nil {
		if _, ok := payload["type"]; !ok {
			payload["type"] = "supabase_access"
		}
		return payload
	}
	return nil
}

// VerifyToken validates a JWT token and returns an AccessToken for MCP, or nil.
func (b *JWTAuthBackend) VerifyToken(ctx context.Context, token string) *AccessToken {
	payload := b.ValidateTokenDualAuth(token)
	if payload == nil {
		return nil
	}

	userID := mcpStringClaim(payload["sub"])
	if userID == "" {
		userID = mcpStringClaim(payload["user_id"])
	}
	if userID == "" {
		return nil
	}

	userContext := b.getUserContext(ctx, userID, payload)
	if userContext == nil {
		return nil
	}

	scopes := mcpScopesFromPayload(payload["scopes"])
	mcpScopes := b.MapRolesToScopes(userContext.Roles)
	allScopes := mcpUniqueStrings(append(append([]string{}, scopes...), mcpScopes...))

	var expiresAt *int64
	if exp, ok := payload["exp"]; ok && exp != nil {
		if v, err := strconv.ParseFloat(mcpNumberString(exp), 64); err == nil {
			n := int64(v)
			expiresAt = &n
		}
	}

	return &AccessToken{
		Token:     token,
		ClientID:  userID,
		Scopes:    allScopes,
		ExpiresAt: expiresAt,
	}
}

// getUserContext mirrors _get_user_context.
func (b *JWTAuthBackend) getUserContext(ctx context.Context, userID string, payload map[string]any) *MCPUserContext {
	now := float64(time.Now().UnixNano()) / 1e9

	b.mu.Lock()
	if ctxVal, ok := b.userContextCache[userID]; ok {
		cacheTime := b.cacheTimestamps[userID]
		if now-cacheTime < b.cacheTTL {
			b.mu.Unlock()
			return ctxVal
		}
	}
	b.mu.Unlock()

	if b.userRepository != nil {
		user, err := b.userRepository.FindByID(ctx, userID)
		if err != nil {
			// Python logs the error and falls through to the token fallback.
			user = nil
		}
		if user != nil {
			roleNames := []string{}
			for _, role := range user.Roles {
				roleNames = append(roleNames, strings.ToLower(string(role)))
			}
			idValue := ""
			if user.ID != nil {
				idValue = *user.ID
			}
			contextVal := &MCPUserContext{
				UserID:   idValue,
				Email:    user.Email,
				Username: user.Username,
				Roles:    roleNames,
				Scopes:   []string{},
			}
			b.mu.Lock()
			b.userContextCache[userID] = contextVal
			b.cacheTimestamps[userID] = now
			b.mu.Unlock()
			return contextVal
		}
	}

	fallbackRoles := []string{"user"}
	fallbackEmail := ""
	if payload != nil {
		if v, ok := payload["roles"]; ok {
			fallbackRoles = mcpStringList(v)
		}
		fallbackEmail = mcpStringClaim(payload["email"])
	}

	return &MCPUserContext{
		UserID:   userID,
		Email:    fallbackEmail,
		Username: userID,
		Roles:    fallbackRoles,
		Scopes:   []string{},
	}
}

type mcpRolePermission struct {
	resource domain.ResourceType
	actions  []domain.PermissionAction
}

// MapRolesToScopes maps user roles to resource-specific CRUD scopes.
func (b *JWTAuthBackend) MapRolesToScopes(roles []string) []string {
	rolePermissions := map[string][]mcpRolePermission{
		"admin": {
			{domain.ResourceProjects, []domain.PermissionAction{domain.ActionCreate, domain.ActionRead, domain.ActionUpdate, domain.ActionDelete, domain.ActionExecute}},
			{domain.ResourceTasks, []domain.PermissionAction{domain.ActionCreate, domain.ActionRead, domain.ActionUpdate, domain.ActionDelete, domain.ActionExecute}},
			{domain.ResourceSubtasks, []domain.PermissionAction{domain.ActionCreate, domain.ActionRead, domain.ActionUpdate, domain.ActionDelete}},
			{domain.ResourceContexts, []domain.PermissionAction{domain.ActionCreate, domain.ActionRead, domain.ActionUpdate, domain.ActionDelete, domain.ActionDelegate}},
			{domain.ResourceAgents, []domain.PermissionAction{domain.ActionCreate, domain.ActionRead, domain.ActionUpdate, domain.ActionDelete, domain.ActionExecute}},
			{domain.ResourceBranches, []domain.PermissionAction{domain.ActionCreate, domain.ActionRead, domain.ActionUpdate, domain.ActionDelete}},
			{domain.ResourceMCP, []domain.PermissionAction{domain.ActionCreate, domain.ActionRead, domain.ActionUpdate, domain.ActionDelete, domain.ActionExecute}},
		},
		"developer": {
			{domain.ResourceProjects, []domain.PermissionAction{domain.ActionRead, domain.ActionUpdate}},
			{domain.ResourceTasks, []domain.PermissionAction{domain.ActionCreate, domain.ActionRead, domain.ActionUpdate, domain.ActionDelete, domain.ActionExecute}},
			{domain.ResourceSubtasks, []domain.PermissionAction{domain.ActionCreate, domain.ActionRead, domain.ActionUpdate, domain.ActionDelete}},
			{domain.ResourceContexts, []domain.PermissionAction{domain.ActionCreate, domain.ActionRead, domain.ActionUpdate, domain.ActionDelegate}},
			{domain.ResourceAgents, []domain.PermissionAction{domain.ActionRead, domain.ActionUpdate, domain.ActionExecute}},
			{domain.ResourceBranches, []domain.PermissionAction{domain.ActionCreate, domain.ActionRead, domain.ActionUpdate, domain.ActionDelete}},
			{domain.ResourceMCP, []domain.PermissionAction{domain.ActionRead, domain.ActionExecute}},
		},
		"user": {
			{domain.ResourceProjects, []domain.PermissionAction{domain.ActionRead}},
			{domain.ResourceTasks, []domain.PermissionAction{domain.ActionCreate, domain.ActionRead, domain.ActionUpdate}},
			{domain.ResourceSubtasks, []domain.PermissionAction{domain.ActionCreate, domain.ActionRead, domain.ActionUpdate}},
			{domain.ResourceContexts, []domain.PermissionAction{domain.ActionRead, domain.ActionUpdate}},
			{domain.ResourceAgents, []domain.PermissionAction{domain.ActionRead}},
			{domain.ResourceBranches, []domain.PermissionAction{domain.ActionRead}},
			{domain.ResourceMCP, []domain.PermissionAction{domain.ActionRead}},
		},
	}

	scopes := []string{"mcp:access"}

	for _, role := range roles {
		roleLower := strings.ToLower(role)

		if roleLower == "admin" {
			scopes = append(scopes, "mcp:admin", "mcp:write")
		}
		if roleLower == "admin" || roleLower == "developer" {
			scopes = append(scopes, "mcp:write")
		}

		permissions, ok := rolePermissions[roleLower]
		if !ok {
			continue
		}
		for _, entry := range permissions {
			for _, action := range entry.actions {
				scopes = append(scopes, string(entry.resource)+":"+string(action))
			}
		}
	}

	return mcpUniqueStrings(scopes)
}

// GetCurrentUserID extracts the user id without validating the signature.
func (b *JWTAuthBackend) GetCurrentUserID(token string) *string {
	payload, err := mcpDecodeUnverified(token)
	if err != nil {
		return nil
	}
	sub := mcpStringClaim(payload["sub"])
	if sub == "" {
		return nil
	}
	return &sub
}

// CreateJWTAuthBackend mirrors create_jwt_auth_backend.
func CreateJWTAuthBackend(userRepository MCPUserLookup, requiredScopes []string) (*JWTAuthBackend, error) {
	jwtSecret := os.Getenv("JWT_SECRET_KEY")
	if jwtSecret == "" {
		return nil, &value_objects.ValueError{Msg: "JWT_SECRET_KEY environment variable not set"}
	}

	jwtService, err := domServices.NewJWTService(jwtSecret, domServices.DefaultIssuer)
	if err != nil {
		return nil, err
	}

	return NewJWTAuthBackend(jwtService, nil, userRepository, requiredScopes)
}

// ---------------------------------------------------------------------------
// Minimal HS256 helpers (PyJWT is not available in Go). Kept local to this
// package with mcp-prefixed names to avoid collisions.
// ---------------------------------------------------------------------------

func mcpB64URLDecode(s string) ([]byte, error) {
	if pad := len(s) % 4; pad != 0 {
		s += strings.Repeat("=", 4-pad)
	}
	return base64.URLEncoding.DecodeString(s)
}

// decodeMCPHS256Audience decodes and verifies an HS256 token with an audience.
func decodeMCPHS256Audience(token, secret, audience string) (map[string]any, error) {
	parts := strings.Split(token, ".")
	if len(parts) != 3 {
		return nil, &mcpBackendInvalidError{msg: "Not enough segments"}
	}
	headerBytes, err := mcpB64URLDecode(parts[0])
	if err != nil {
		return nil, &mcpBackendInvalidError{msg: err.Error()}
	}
	var header map[string]any
	if err := json.Unmarshal(headerBytes, &header); err != nil {
		return nil, &mcpBackendInvalidError{msg: err.Error()}
	}
	if alg, _ := header["alg"].(string); alg != "HS256" {
		return nil, &mcpBackendInvalidError{msg: "The specified alg value is not allowed"}
	}

	signature, err := mcpB64URLDecode(parts[2])
	if err != nil {
		return nil, &mcpBackendInvalidError{msg: err.Error()}
	}
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write([]byte(parts[0] + "." + parts[1]))
	if !hmac.Equal(signature, mac.Sum(nil)) {
		return nil, &mcpBackendInvalidError{msg: "Signature verification failed"}
	}

	payloadBytes, err := mcpB64URLDecode(parts[1])
	if err != nil {
		return nil, &mcpBackendInvalidError{msg: err.Error()}
	}
	var payload map[string]any
	if err := json.Unmarshal(payloadBytes, &payload); err != nil {
		return nil, &mcpBackendInvalidError{msg: err.Error()}
	}

	now := float64(time.Now().UnixNano()) / 1e9
	if exp, ok := payload["exp"]; ok {
		v, err := mcpClaimInt(exp)
		if err != nil {
			return nil, &mcpBackendInvalidError{msg: "Expiration Time claim (exp) must be an integer."}
		}
		if now > v {
			return nil, &mcpBackendInvalidError{msg: "Signature has expired"}
		}
	}
	if iat, ok := payload["iat"]; ok {
		v, err := mcpClaimInt(iat)
		if err != nil {
			return nil, &mcpBackendInvalidError{msg: "Issued At claim (iat) must be an integer."}
		}
		if v > now {
			return nil, &mcpBackendInvalidError{msg: "The token is not yet valid (iat)"}
		}
	}
	if nbf, ok := payload["nbf"]; ok {
		v, err := mcpClaimInt(nbf)
		if err != nil {
			return nil, &mcpBackendInvalidError{msg: "Not Before claim (nbf) must be an integer."}
		}
		if v > now {
			return nil, &mcpBackendInvalidError{msg: "The token is not yet valid (nbf)"}
		}
	}
	if audience != "" {
		if !mcpAudienceMatches(payload["aud"], audience) {
			return nil, &mcpBackendInvalidError{msg: "Invalid audience"}
		}
	}
	return payload, nil
}

func mcpDecodeUnverified(token string) (map[string]any, error) {
	parts := strings.Split(token, ".")
	if len(parts) < 2 {
		return nil, &mcpBackendInvalidError{msg: "Not enough segments"}
	}
	payloadBytes, err := mcpB64URLDecode(parts[1])
	if err != nil {
		return nil, &mcpBackendInvalidError{msg: err.Error()}
	}
	var payload map[string]any
	if err := json.Unmarshal(payloadBytes, &payload); err != nil {
		return nil, &mcpBackendInvalidError{msg: err.Error()}
	}
	return payload, nil
}

func mcpAudienceMatches(raw any, want string) bool {
	switch v := raw.(type) {
	case string:
		return v == want
	case []any:
		for _, item := range v {
			if s, _ := item.(string); s == want {
				return true
			}
		}
	}
	return false
}

func mcpClaimInt(v any) (float64, error) {
	switch n := v.(type) {
	case float64:
		return n, nil
	case json.Number:
		return n.Float64()
	case int64:
		return float64(n), nil
	case int:
		return float64(n), nil
	}
	return 0, fmt.Errorf("not a number")
}

func mcpNumberString(v any) string {
	switch n := v.(type) {
	case float64:
		return strconv.FormatFloat(n, 'f', -1, 64)
	case int64:
		return strconv.FormatInt(n, 10)
	case int:
		return strconv.Itoa(n)
	case json.Number:
		return n.String()
	case string:
		return n
	}
	return ""
}

func mcpStringClaim(v any) string {
	if s, ok := v.(string); ok {
		return s
	}
	return ""
}

func mcpScopesFromPayload(v any) []string {
	switch s := v.(type) {
	case string:
		return strings.Fields(s)
	case []any:
		return mcpStringList(s)
	case []string:
		return append([]string{}, s...)
	}
	return []string{}
}

func mcpStringList(v any) []string {
	switch list := v.(type) {
	case []string:
		return append([]string{}, list...)
	case []any:
		out := make([]string, 0, len(list))
		for _, item := range list {
			if s, ok := item.(string); ok {
				out = append(out, s)
			}
		}
		return out
	case string:
		return []string{list}
	}
	return []string{}
}

func mcpUniqueStrings(in []string) []string {
	seen := map[string]struct{}{}
	out := []string{}
	for _, s := range in {
		if _, ok := seen[s]; ok {
			continue
		}
		seen[s] = struct{}{}
		out = append(out, s)
	}
	return out
}
