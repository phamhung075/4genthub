// Package services ports
// task_management/interface/mcp_controllers/auth_helper/services.
package services

import (
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// JWTDecode is the minimal PyJWT `jwt.decode` surface this service needs. The
// Python module imports `jwt` (PyJWT); the Go module does not vendor a JWT
// library yet, so a real implementation (e.g. github.com/golang-jwt/jwt/v5) must
// assign this hook. When nil every decode returns an error, like an invalid token.
var JWTDecode func(token string, verifyExp bool, verifySignature bool) (map[string]any, error)

// TokenExtractionService extracts user information from JWT tokens.
type TokenExtractionService struct{}

// NewTokenExtractionService mirrors TokenExtractionService().
func NewTokenExtractionService() *TokenExtractionService { return &TokenExtractionService{} }

// ExtractUserIDFromToken mirrors extract_user_id_from_token. decode_options
// (verify_signature/verify_exp/verify_aud=false/verify_iss=false) are passed to JWTDecode.
func (s *TokenExtractionService) ExtractUserIDFromToken(token string, verifyExp bool, verifySignature bool) *string {
	if token == "" {
		return nil
	}
	if JWTDecode == nil {
		return nil
	}
	decoded, err := JWTDecode(token, verifyExp, verifySignature)
	if err != nil {
		return nil
	}
	userID, ok := decoded["sub"]
	if !ok || userID == nil {
		return nil
	}
	userIDStr := value_objects.PyStr(userID)
	return &userIDStr
}

// ExtractUserInfoFromToken mirrors extract_user_info_from_token; keys stay in
// Python insertion order and None values are dropped.
func (s *TokenExtractionService) ExtractUserInfoFromToken(token string, verifyExp bool, verifySignature bool) *entities.OrderedMap[any] {
	if token == "" {
		return nil
	}
	if JWTDecode == nil {
		return nil
	}
	decoded, err := JWTDecode(token, verifyExp, verifySignature)
	if err != nil {
		return nil
	}

	info := entities.NewOrderedMap[any]()
	info.Set("email_verified", pyGet(decoded, "email_verified", false))
	realmRoles := []any{}
	if realmAccess, ok := decoded["realm_access"].(map[string]any); ok {
		if roles, ok := realmAccess["roles"].([]any); ok {
			realmRoles = roles
		}
	}
	clientRoles := any(map[string]any{})
	if resourceAccess, ok := decoded["resource_access"].(map[string]any); ok {
		clientRoles = resourceAccess
	}

	// Build in Python key order then drop None values.
	ordered := []struct {
		key   string
		value any
	}{
		{"user_id", decoded["sub"]},
		{"email", decoded["email"]},
		{"email_verified", pyGet(decoded, "email_verified", false)},
		{"name", decoded["name"]},
		{"given_name", decoded["given_name"]},
		{"family_name", decoded["family_name"]},
		{"preferred_username", decoded["preferred_username"]},
		{"realm_roles", realmRoles},
		{"client_roles", clientRoles},
	}
	for _, kv := range ordered {
		if kv.value != nil {
			info.Set(kv.key, kv.value)
		}
	}
	return info
}

// ExtractTokenFromHeader mirrors extract_token_from_header.
func (s *TokenExtractionService) ExtractTokenFromHeader(authorizationHeader string) *string {
	if authorizationHeader == "" {
		return nil
	}
	if strings.HasPrefix(authorizationHeader, "Bearer ") {
		token := strings.TrimSpace(authorizationHeader[7:])
		return &token
	}
	return nil
}

// ExtractUserIDFromRequest mirrors extract_user_id_from_request. Python accepts a
// request object and reads request.headers.get("Authorization"); Go takes the
// header map directly.
func (s *TokenExtractionService) ExtractUserIDFromRequest(headers map[string]string) *string {
	if headers == nil {
		return nil
	}
	authHeader := headers["Authorization"]
	if authHeader == "" {
		return nil
	}
	token := s.ExtractTokenFromHeader(authHeader)
	if token == nil {
		return nil
	}
	return s.ExtractUserIDFromToken(*token, true, false)
}

func pyGet(m map[string]any, key string, fallback any) any {
	if v, ok := m[key]; ok {
		return v
	}
	return fallback
}

// tokenExtractionService is the module singleton (`_token_extraction_service`).
var tokenExtractionService *TokenExtractionService

// GetTokenExtractionService mirrors get_token_extraction_service.
func GetTokenExtractionService() *TokenExtractionService {
	if tokenExtractionService == nil {
		tokenExtractionService = NewTokenExtractionService()
	}
	return tokenExtractionService
}

// ExtractUserIDFromToken mirrors the module-level convenience function.
func ExtractUserIDFromToken(token string, verifyExp bool, verifySignature bool) *string {
	return GetTokenExtractionService().ExtractUserIDFromToken(token, verifyExp, verifySignature)
}

// ExtractUserIDFromRequest mirrors the module-level convenience function.
func ExtractUserIDFromRequest(headers map[string]string) *string {
	return GetTokenExtractionService().ExtractUserIDFromRequest(headers)
}
