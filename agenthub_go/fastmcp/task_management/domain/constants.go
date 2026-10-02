// Package domain ports task_management/domain/constants.py.
package domain

import (
	"errors"

	"agenthub/fastmcp/task_management/domain/value_objects"
)

// UserIDNormalizer is validate_user_id's lazy import of
// infrastructure.database.uuid_column_type.normalize_user_id_to_uuid. The domain
// cannot import infrastructure in Go (import cycle), so the infrastructure
// package registers the function in its init(). When unset (or when it fails)
// the original value is returned, exactly like Python's except-branch.
var UserIDNormalizer func(userID string) (string, error)

// AssertUserIDNormalizerRegistered lets server startup fail fast when the
// infrastructure package that registers UserIDNormalizer was not linked in.
// Python always attempts the normalization (the import is inside the function); Go
// would silently skip it.
func AssertUserIDNormalizerRegistered() error {
	if UserIDNormalizer == nil {
		return errors.New("domain.UserIDNormalizer is not registered: import the infrastructure uuid_column_type package")
	}
	return nil
}

// ValidateUserID validates that a user ID is present and normalizes it to UUID
// format. operation describes the operation requiring authentication (Python
// default "This operation"); nil userID means None.
func ValidateUserID(userID *string, operation string) (string, error) {
	if operation == "" {
		operation = "This operation"
	}
	if userID == nil {
		return "", value_objects.ValueErrorf("%s requires user authentication. No user ID was provided.", operation)
	}
	trimmed := value_objects.PyStrip(*userID)
	if trimmed == "" {
		return "", value_objects.ValueErrorf("%s requires user authentication. No user ID was provided.", operation)
	}
	if UserIDNormalizer != nil {
		if normalized, err := UserIDNormalizer(trimmed); err == nil {
			return normalized, nil
		}
	}
	return trimmed, nil
}

// RequireAuthenticatedUser is an alias for ValidateUserID with clearer intent.
func RequireAuthenticatedUser(userID *string, operation string) (string, error) {
	return ValidateUserID(userID, operation)
}
