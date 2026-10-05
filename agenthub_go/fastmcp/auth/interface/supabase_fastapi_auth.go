// This file ports fastmcp/auth/interface/supabase_fastapi_auth.py.
//
// FastAPI's Request/Depends plumbing is replaced by an explicit
// MiddlewareAuthState and a repository interface. The SQLAlchemy
// add/commit/to_domain dance maps onto UserRepository.Save.
package authinterface

import (
	"context"
	"strings"
	"sync"

	authpkg "agenthub/fastmcp/auth"
	authEntities "agenthub/fastmcp/auth/domain/entities"
	authinfra "agenthub/fastmcp/auth/infrastructure"
	"agenthub/fastmcp/task_management/domain/entities"
)

// SupabaseUserRepository is the minimal user repository surface this package
// needs (the Python module uses infrastructure.repositories.UserRepository).
type SupabaseUserRepository interface {
	FindByID(ctx context.Context, userID string) (*authEntities.User, error)
	Save(ctx context.Context, user *authEntities.User) (*authEntities.User, error)
}

// MiddlewareAuthState carries what DualAuthMiddleware puts on request.state.
// AuthInfo is the auth_info dict (nil means absent, like Python's default {}).
type MiddlewareAuthState struct {
	UserID   *string
	AuthInfo *entities.OrderedMap[any]
}

var (
	supabaseAuthOnce sync.Once
	supabaseAuthInst *authinfra.SupabaseAuthService
	supabaseAuthErr  error
)

// GetSupabaseAuth is get_supabase_auth: a lazily created singleton.
func GetSupabaseAuth() (*authinfra.SupabaseAuthService, error) {
	supabaseAuthOnce.Do(func() {
		supabaseAuthInst, supabaseAuthErr = authinfra.NewSupabaseAuthService()
	})
	return supabaseAuthInst, supabaseAuthErr
}

// GetCurrentUserFromMiddleware is get_current_user_from_middleware.
func GetCurrentUserFromMiddleware(ctx context.Context, state *MiddlewareAuthState, repo SupabaseUserRepository) (*authEntities.User, error) {
	if state == nil || state.UserID == nil || *state.UserID == "" {
		return nil, &authpkg.HTTPException{
			StatusCode: 401,
			Detail:     "Authentication required - no user context found",
		}
	}
	userID := *state.UserID

	user, err := repo.FindByID(ctx, userID)
	if err != nil {
		return nil, &authpkg.HTTPException{StatusCode: 500, Detail: "Internal server error while retrieving user"}
	}
	if user != nil {
		return user, nil
	}

	// If user doesn't exist in local DB, create from auth info.
	email := supabaseAuthInfoEmail(state.AuthInfo)
	if email == "" {
		return nil, &authpkg.HTTPException{
			StatusCode: 401,
			Detail:     "User not found in database and no email available for creation",
		}
	}

	domainUser := &authEntities.User{
		ID:           &userID,
		Email:        email,
		Username:     strings.Split(email, "@")[0], // email prefix as username
		PasswordHash: "",                           // empty for JWT-authenticated users
		Status:       authEntities.UserStatusActive,
		Roles:        []authEntities.UserRole{authEntities.UserRoleUser},
	}
	saved, saveErr := repo.Save(ctx, domainUser)
	if saveErr != nil {
		// Race condition: another request created the user first.
		user, err = repo.FindByID(ctx, userID)
		if err != nil || user == nil {
			return nil, &authpkg.HTTPException{StatusCode: 500, Detail: "Failed to create or retrieve user"}
		}
		return user, nil
	}
	return saved, nil
}

// GetCurrentUserSupabase is get_current_user_supabase.
func GetCurrentUserSupabase(ctx context.Context, credentials *string, repo SupabaseUserRepository) (*authEntities.User, error) {
	if authInterfaceToken(credentials) == "" {
		return nil, &authpkg.HTTPException{StatusCode: 401, Detail: "Authentication required"}
	}

	svc, err := GetSupabaseAuth()
	if err != nil {
		return nil, &authpkg.HTTPException{StatusCode: 401, Detail: "Authentication failed"}
	}
	result := svc.VerifyToken(ctx, authInterfaceToken(credentials))
	if !result.Success || result.User == nil {
		detail := "Invalid or expired token"
		if result.ErrorMessage != nil && *result.ErrorMessage != "" {
			detail = *result.ErrorMessage
		}
		return nil, &authpkg.HTTPException{StatusCode: 401, Detail: detail}
	}

	supabaseUser := result.User
	userID := orderedString(supabaseUser, "id")
	if userID == "" {
		return nil, &authpkg.HTTPException{StatusCode: 401, Detail: "Invalid token: missing user ID"}
	}

	user, err := repo.FindByID(ctx, userID)
	if err != nil {
		return nil, &authpkg.HTTPException{StatusCode: 401, Detail: "Authentication failed"}
	}
	if user != nil {
		return user, nil
	}

	// Create user from Supabase data if not exists.
	email := orderedString(supabaseUser, "email")
	var metadata *entities.OrderedMap[any]
	if v, ok := supabaseUser.Get("user_metadata"); ok {
		if m, ok := v.(*entities.OrderedMap[any]); ok {
			metadata = m
		}
	}
	username := orderedString(metadata, "username")
	if username == "" {
		if email != "" {
			username = strings.Split(email, "@")[0]
		} else {
			username = "user"
		}
	}
	fullName := orderedString(metadata, "full_name")

	domainUser := &authEntities.User{
		ID:            &userID,
		Email:         email,
		Username:      username,
		FullName:      &fullName,
		PasswordHash:  "", // no password stored for Supabase users
		Status:        authEntities.UserStatusActive,
		Roles:         []authEntities.UserRole{authEntities.UserRoleUser},
		EmailVerified: true, // Supabase users are verified through Supabase
	}

	saved, saveErr := repo.Save(ctx, domainUser)
	if saveErr != nil {
		// Race condition: another request created the user first.
		user, err = repo.FindByID(ctx, userID)
		if err != nil || user == nil {
			return nil, &authpkg.HTTPException{StatusCode: 500, Detail: "Failed to create or retrieve user from Supabase"}
		}
		return user, nil
	}
	return saved, nil
}

// supabaseAuthInfoEmail reads auth_info["email"] when auth_info is a dict.
func supabaseAuthInfoEmail(authInfo *entities.OrderedMap[any]) string {
	return orderedString(authInfo, "email")
}

// orderedString reads a string value from an ordered map ("" when absent).
func orderedString(m *entities.OrderedMap[any], key string) string {
	if m == nil {
		return ""
	}
	v, ok := m.Get(key)
	if !ok {
		return ""
	}
	s, _ := v.(string)
	return s
}
