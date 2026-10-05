package repositories

// Base User-Scoped Repository (Python repositories/base_user_scoped_repository.py): user-based
// data isolation shared by derived repositories. Embed UserScope in a repository.
//
// with_user / create_system_context re-instantiate self.__class__; in Go each concrete
// repository provides its own constructor taking the user id, so they are not ported here.

import (
	"strings"
)

// UserScopedError is raised when a user-scoped operation fails.
type UserScopedError struct{ Msg string }

func (e *UserScopedError) Error() string { return e.Msg }

// InsufficientPermissionsError: the user lacks permissions for an operation.
type InsufficientPermissionsError struct{ UserScopedError }

// CrossUserAccessError: the user attempted to access another user's data.
type CrossUserAccessError struct{ UserScopedError }

// PermissionError mirrors Python's builtin PermissionError.
type PermissionError struct{ Msg string }

func (e *PermissionError) Error() string { return e.Msg }

// ValueError mirrors Python's ValueError for repository-level validation.
type ValueError struct{ Msg string }

func (e *ValueError) Error() string { return e.Msg }

// HasUserID is an entity that carries a user_id attribute.
type HasUserID interface{ GetUserID() string }

// UserScope scopes operations to one user; a nil user id is system mode (no filtering).
type UserScope struct {
	UserID       *string
	isSystemMode bool
}

// NewUserScope builds the scope; nil userID means system mode.
func NewUserScope(userID *string) UserScope {
	return UserScope{UserID: userID, isSystemMode: userID == nil}
}

// GetUserFilter is the filter for user-scoped queries (empty in system mode).
func (u UserScope) GetUserFilter() Kwargs {
	if u.isSystemMode {
		return NewKwargs()
	}
	return NewKwargs("user_id", *u.UserID)
}

// ApplyUserFilter appends the user filter to a raw SQL string (the string branch of
// apply_user_filter; query objects are handled by GetUserFilter in the Go repositories).
func (u UserScope) ApplyUserFilter(query string) string {
	if u.isSystemMode {
		return query
	}
	if strings.Contains(strings.ToUpper(query), "WHERE") {
		return query + " AND user_id = '" + *u.UserID + "'"
	}
	return query + " WHERE user_id = '" + *u.UserID + "'"
}

// EnsureUserOwnership fails when the entity belongs to another user.
func (u UserScope) EnsureUserOwnership(entity HasUserID) error {
	if u.isSystemMode {
		return nil
	}
	if entity != nil && entity.GetUserID() != *u.UserID {
		return &PermissionError{Msg: "Access denied: Entity does not belong to user " + *u.UserID}
	}
	return nil
}

// SetUserID adds user_id to the data for entity creation; system mode is an error
// (authentication is required, no fallbacks).
func (u UserScope) SetUserID(data Kwargs) (Kwargs, error) {
	if u.isSystemMode {
		return nil, &ValueError{Msg: "User authentication required. No user ID provided."}
	}
	data.Set("user_id", *u.UserID)
	return data, nil
}

// ValidateBulkOperation checks every entity's ownership.
func (u UserScope) ValidateBulkOperation(entities []HasUserID) error {
	if u.isSystemMode {
		return nil
	}
	for _, e := range entities {
		if err := u.EnsureUserOwnership(e); err != nil {
			return err
		}
	}
	return nil
}

// IsSystemMode reports whether no user filtering applies.
func (u UserScope) IsSystemMode() bool { return u.isSystemMode }

// GetCurrentUserID returns the scoped user id, or nil in system mode.
func (u UserScope) GetCurrentUserID() *string { return u.UserID }
