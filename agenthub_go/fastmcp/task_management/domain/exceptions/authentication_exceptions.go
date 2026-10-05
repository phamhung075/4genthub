package exceptions

import "fmt"

// AuthenticationError is the base exception for authentication-related errors.
type AuthenticationError struct{ Msg string }

func (e *AuthenticationError) Error() string { return e.Msg }

// UserAuthenticationRequiredError: an operation requires user authentication but none was provided.
type UserAuthenticationRequiredError struct {
	AuthenticationError
	Operation string
}

func (e *UserAuthenticationRequiredError) Unwrap() error { return &e.AuthenticationError }

// NewUserAuthenticationRequiredError defaults an empty operation to "This operation"
// (Python default arg; an explicit "" cannot be distinguished from omitted).
func NewUserAuthenticationRequiredError(operation string) *UserAuthenticationRequiredError {
	if operation == "" {
		operation = "This operation"
	}
	return &UserAuthenticationRequiredError{
		AuthenticationError{fmt.Sprintf("%s requires user authentication. No user ID was provided.", operation)},
		operation,
	}
}

// InvalidUserIdError: an invalid user ID (malformed UUID, empty string, ...) was provided.
type InvalidUserIdError struct {
	AuthenticationError
	UserID string
}

func (e *InvalidUserIdError) Unwrap() error { return &e.AuthenticationError }

func NewInvalidUserIdError(userID string) *InvalidUserIdError {
	return &InvalidUserIdError{
		AuthenticationError{fmt.Sprintf("Invalid user ID provided: %s. User authentication is required.", userID)},
		userID,
	}
}

// DefaultUserProhibitedError: a default user ID was used instead of proper authentication.
type DefaultUserProhibitedError struct{ AuthenticationError }

func (e *DefaultUserProhibitedError) Unwrap() error { return &e.AuthenticationError }

func NewDefaultUserProhibitedError() *DefaultUserProhibitedError {
	return &DefaultUserProhibitedError{AuthenticationError{
		"Use of default user ID is prohibited. All operations must be performed with authenticated user credentials."}}
}
