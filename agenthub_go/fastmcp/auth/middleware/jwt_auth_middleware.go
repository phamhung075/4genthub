// Package middleware ports agenthub_main/src/fastmcp/auth/middleware.
package middleware

import (
	"strings"

	domainservices "agenthub/fastmcp/auth/domain/services"
	entities "agenthub/fastmcp/task_management/domain/entities"
)

// DefaultJWTSecret is the Python fallback secret compared against in
// get_auth_status.
const DefaultJWTSecret = "default-secret-key-change-in-production"

// JWTAuthMiddleware ports auth/middleware/jwt_auth_middleware.py:JWTAuthMiddleware.
//
// create_user_scoped_repository / create_user_scoped_service inspect Python
// __init__ signatures and set attributes, and UserContextManager caches by
// id(session); both are Python reflection/introspection with no Go meaning.
// require_auth is a FastAPI route decorator and is also not ported.
type JWTAuthMiddleware struct {
	SecretKey string
	Algorithm string
	Enabled   bool
}

// NewJWTAuthMiddleware mirrors JWTAuthMiddleware.__init__.
func NewJWTAuthMiddleware(secretKey, algorithm string, enabled bool) *JWTAuthMiddleware {
	return &JWTAuthMiddleware{SecretKey: secretKey, Algorithm: algorithm, Enabled: enabled}
}

// ExtractUserFromToken ports extract_user_from_token.
func (m *JWTAuthMiddleware) ExtractUserFromToken(token string) *string {
	token = strings.TrimPrefix(token, "Bearer ")

	jwtService, err := domainservices.NewJWTService(m.SecretKey, domainservices.DefaultIssuer)
	if err != nil {
		return nil
	}

	// First try with the Supabase "authenticated" audience, then without an
	// audience check (local tokens).
	payload := jwtService.VerifyAccessToken(token, "authenticated")
	if payload == nil {
		payload = jwtService.VerifyAccessToken(token, "")
	}
	if payload == nil {
		return nil
	}

	userID, _ := payload["sub"].(string)
	if userID == "" {
		userID, _ = payload["user_id"].(string)
	}
	if userID == "" {
		return nil
	}
	return &userID
}

// GetAuthStatus ports get_auth_status.
func (m *JWTAuthMiddleware) GetAuthStatus() *entities.OrderedMap[any] {
	features := entities.NewOrderedMap[any]()
	features.Set("jwt_validation", true)
	features.Set("supabase_tokens", true)
	features.Set("local_tokens", true)
	features.Set("audience_validation", true)

	d := entities.NewOrderedMap[any]()
	d.Set("enabled", m.Enabled)
	d.Set("algorithm", m.Algorithm)
	d.Set("secret_configured", m.SecretKey != DefaultJWTSecret)
	d.Set("middleware", "JWTAuthMiddleware")
	d.Set("features", features)
	return d
}

// CreateAuthMiddleware ports create_auth_middleware.
func CreateAuthMiddleware(secretKey, algorithm string) *JWTAuthMiddleware {
	return NewJWTAuthMiddleware(secretKey, algorithm, true)
}
