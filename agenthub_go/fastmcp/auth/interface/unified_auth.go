// Package authinterface ports fastmcp/auth/interface/unified_auth.py.
package authinterface

import (
	"context"

	authEntities "agenthub/fastmcp/auth/domain/entities"
)

// GetUnifiedCurrentUser retrieves current user using the configured auth provider.
func GetUnifiedCurrentUser(ctx context.Context, credentials *string, repo SupabaseUserRepository) (*authEntities.User, error) {
	return GetCurrentUser(ctx, credentials, repo)
}

// GetUnifiedCurrentActiveUser retrieves current active user.
func GetUnifiedCurrentActiveUser(ctx context.Context, credentials *string, repo SupabaseUserRepository) (*authEntities.User, error) {
	return GetCurrentActiveUser(ctx, credentials, repo)
}

// GetUnifiedOptionalUser retrieves optional user if authenticated.
func GetUnifiedOptionalUser(ctx context.Context, credentials *string, repo SupabaseUserRepository) *authEntities.User {
	return GetOptionalUser(ctx, credentials, repo)
}

// RequireUnifiedAdmin requires admin role for access.
func RequireUnifiedAdmin(ctx context.Context, credentials *string, repo SupabaseUserRepository) (*authEntities.User, error) {
	return RequireAdmin(ctx, credentials, repo)
}

// RequireUnifiedRoles requires specific roles for access.
func RequireUnifiedRoles(ctx context.Context, roles []string, credentials *string, repo SupabaseUserRepository) (*authEntities.User, error) {
	return RequireRoles(ctx, roles, credentials, repo)
}
