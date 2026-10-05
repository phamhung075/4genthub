// Package authinterface ports fastmcp/auth/interface/*.py.
//
// The FastAPI plumbing (Depends, HTTPBearer, get_db session generator) has no Go
// meaning, so the dependencies are exposed as ordinary functions that receive the
// bearer token and the user repository explicitly.
package authinterface

import (
	"context"
	"os"

	authpkg "agenthub/fastmcp/auth"
	authEntities "agenthub/fastmcp/auth/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// authInterfaceEnvOr is os.getenv(key) or default.
func authInterfaceEnvOr(key, def string) string {
	if v, ok := os.LookupEnv(key); ok {
		return v
	}
	return def
}

// authProvider is AUTH_PROVIDER, read once at import time like the Python module.
var authProvider = value_objects.PyLower(authInterfaceEnvOr("AUTH_PROVIDER", "keycloak"))

// GetCurrentUserUniversal is the Go port of
// fastmcp.auth.keycloak_dependencies.get_current_user_universal, which has no Go
// port yet. It is the minimal interface this package depends on; callers set it,
// and a nil value is reported as the "not configured" error.
var GetCurrentUserUniversal func(ctx context.Context, token string) (*authEntities.User, error)

// getCurrentUserUniversalError mirrors the exception raised when the universal
// dependency is unavailable.
type getCurrentUserUniversalError struct{}

func (getCurrentUserUniversalError) Error() string {
	return "get_current_user_universal is not configured"
}

// GetCurrentUser is fastapi_auth.get_current_user.
func GetCurrentUser(ctx context.Context, credentials *string, repo SupabaseUserRepository) (*authEntities.User, error) {
	switch authProvider {
	case "keycloak":
		// Development fallback when Keycloak is not accessible.
		user, err := getCurrentUserUniversal(ctx, credentials)
		if err != nil {
			env := value_objects.PyLower(authInterfaceEnvOr("ENV", "production"))
			if env == "local" || env == "development" || env == "dev" {
				id := "dev-user-001"
				return &authEntities.User{
					ID:           &id,
					Email:        "dev@example.com",
					Username:     "dev-user",
					PasswordHash: "dev-hash",
				}, nil
			}
			return nil, err
		}
		return user, nil
	case "supabase":
		return GetCurrentUserSupabase(ctx, credentials, repo)
	default:
		// Fallback for local/testing - should not be used in production.
		id := "test-user-001"
		return &authEntities.User{
			ID:           &id,
			Email:        "test@example.com",
			Username:     "test-user",
			PasswordHash: "test-hash",
		}, nil
	}
}

// getCurrentUserUniversal invokes the hook, returning a stable error when unset.
func getCurrentUserUniversal(ctx context.Context, credentials *string) (*authEntities.User, error) {
	if GetCurrentUserUniversal == nil {
		return nil, getCurrentUserUniversalError{}
	}
	return GetCurrentUserUniversal(ctx, authInterfaceToken(credentials))
}

// authInterfaceToken returns the bearer token string (empty when absent).
func authInterfaceToken(credentials *string) string {
	if credentials == nil {
		return ""
	}
	return *credentials
}

// GetCurrentActiveUser is fastapi_auth.get_current_active_user.
func GetCurrentActiveUser(ctx context.Context, credentials *string, repo SupabaseUserRepository) (*authEntities.User, error) {
	return GetCurrentUser(ctx, credentials, repo)
}

// RequireAdmin is fastapi_auth.require_admin.
func RequireAdmin(ctx context.Context, credentials *string, repo SupabaseUserRepository) (*authEntities.User, error) {
	return GetCurrentUser(ctx, credentials, repo)
}

// RequireRoles is fastapi_auth.require_roles. The Python roles argument is
// accepted but unused, exactly as in the Python implementation.
func RequireRoles(ctx context.Context, roles []string, credentials *string, repo SupabaseUserRepository) (*authEntities.User, error) {
	_ = roles
	return GetCurrentUser(ctx, credentials, repo)
}

// GetOptionalUser is fastapi_auth.get_optional_user.
func GetOptionalUser(ctx context.Context, credentials *string, repo SupabaseUserRepository) *authEntities.User {
	if authInterfaceToken(credentials) == "" {
		return nil
	}
	user, err := GetCurrentUser(ctx, credentials, repo)
	if err != nil {
		return nil
	}
	return user
}

// httpExceptionStatusCode returns the status code carried by an auth HTTPException.
func httpExceptionStatusCode(err error) (int, bool) {
	if he, ok := err.(*authpkg.HTTPException); ok {
		return he.StatusCode, true
	}
	return 0, false
}
