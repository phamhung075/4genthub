package services

import (
	"context"
	"os"
	"strings"

	"agenthub/fastmcp/task_management/domain"
	"agenthub/fastmcp/task_management/domain/exceptions"
)

// RequestContextUserIDProvider is the minimal surface the Python
// `fastmcp.auth.middleware.request_context_middleware.get_current_user_id` import
// provides. It is ported in fastmcp/auth/middleware/request_context_middleware.go;
// callers may wire a real implementation. When
// nil, _get_user_id_from_context returns nil, matching the Python ImportError path.
var RequestContextUserIDProvider func(ctx context.Context) *string

// AuthenticationService is the Go port of the Keycloak-only MCP authentication service.
type AuthenticationService struct {
	TokenService *TokenExtractionService
}

// NewAuthenticationService mirrors AuthenticationService().
func NewAuthenticationService() *AuthenticationService {
	return &AuthenticationService{TokenService: NewTokenExtractionService()}
}

// AuthEnabled mirrors the auth_enabled property (read from the environment each call).
func (s *AuthenticationService) AuthEnabled() bool {
	value := strings.ToLower(envOr("AUTH_ENABLED", "true"))
	return value == "true" || value == "1" || value == "yes"
}

// AuthMode mirrors the auth_mode property.
func (s *AuthenticationService) AuthMode() string {
	return strings.ToLower(envOr("MCP_AUTH_MODE", "production"))
}

// TestUserID mirrors the test_user_id property.
func (s *AuthenticationService) TestUserID() string {
	return envOr("TEST_USER_ID", "test-user-001")
}

// GetAuthenticatedUserID mirrors get_authenticated_user_id. The returned error is
// a *value_objects.ValueError from ValidateUserID or the Python
// UserAuthenticationRequiredError.
func (s *AuthenticationService) GetAuthenticatedUserID(ctx context.Context, providedUserID *string, operationName string) (string, error) {
	if providedUserID != nil && *providedUserID != "" {
		return domain.ValidateUserID(providedUserID, operationName)
	}

	userID := s.getUserIDFromContext(ctx)
	if userID != nil && *userID != "" {
		return domain.ValidateUserID(userID, operationName)
	}

	if !s.AuthEnabled() || s.AuthMode() == "testing" {
		testUserID := s.TestUserID()
		return domain.ValidateUserID(&testUserID, operationName)
	}

	msg := operationName + " requires valid JWT authentication. " +
		"Please ensure you are authenticated and the JWT token is properly configured."
	return "", &exceptions.UserAuthenticationRequiredError{
		AuthenticationError: exceptions.AuthenticationError{Msg: msg},
	}
}

// getUserIDFromContext mirrors _get_user_id_from_context. The Python except
// Exception branch returns None; recover keeps that behaviour for the hook.
func (s *AuthenticationService) getUserIDFromContext(ctx context.Context) (result *string) {
	defer func() {
		if recover() != nil {
			result = nil
		}
	}()
	if RequestContextUserIDProvider == nil {
		return nil
	}
	return RequestContextUserIDProvider(ctx)
}

func envOr(key, fallback string) string {
	if value, ok := os.LookupEnv(key); ok {
		return value
	}
	return fallback
}
