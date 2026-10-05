// Package auth_helper ports
// task_management/interface/mcp_controllers/auth_helper/auth_helper.py.
package auth_helper

import (
	"context"

	"agenthub/fastmcp/task_management/interface/mcp_controllers/auth_helper/services"
)

// authService mirrors the module singleton `_auth_service`.
var authService *services.AuthenticationService

// getAuthService mirrors _get_auth_service.
func getAuthService() *services.AuthenticationService {
	if authService == nil {
		authService = services.NewAuthenticationService()
	}
	return authService
}

// GetAuthenticatedUserID mirrors get_authenticated_user_id (returning the error
// the Python function raises instead of panicking).
func GetAuthenticatedUserID(ctx context.Context, providedUserID *string, operationName string) (string, error) {
	return getAuthService().GetAuthenticatedUserID(ctx, providedUserID, operationName)
}

// LogAuthenticationDetails mirrors log_authentication_details. Python only logs,
// so the Go port is a no-op kept for API parity.
func LogAuthenticationDetails(userID *string, operation *string) {
	_ = userID
	_ = operation
}
