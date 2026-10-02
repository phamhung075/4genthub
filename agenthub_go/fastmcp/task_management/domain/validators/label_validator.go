// Package validators ports task_management/domain/validators.
package validators

import (
	"fmt"
	"time"
	"unicode/utf8"

	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// LabelValidationError is a validation error with field context; like the Python class it
// is a ValueError.
type LabelValidationError struct {
	Field   string
	Message string
	Hint    string // "" = no hint
}

func (e *LabelValidationError) Error() string {
	msg := fmt.Sprintf("Label validation error (%s): %s", e.Field, e.Message)
	if e.Hint != "" {
		msg += "\nHint: " + e.Hint
	}
	return msg
}

// Unwrap exposes the ValueError base class.
func (e *LabelValidationError) Unwrap() error { return &tmvo.ValueError{Msg: e.Error()} }

func fail(field, message, hint string) error {
	return &LabelValidationError{Field: field, Message: message, Hint: hint}
}

// Validation constraints (single source of truth).
const (
	MaxNameLength        = 50
	MinNameLength        = 1
	MaxDescriptionLength = 2000
)

// ValidateTimestamp requires a non-nil timestamp with a zero UTC offset. Go cannot carry
// a naive datetime, so the "timezone-aware" check has no failing input.
func ValidateTimestamp(ts *time.Time, fieldName string) error {
	if ts == nil {
		return fail(fieldName, fieldName+" cannot be None", "Use datetime.now(UTC) to create UTC timestamps")
	}
	if _, off := ts.Zone(); off != 0 {
		return fail(fieldName, "Timestamp must be in UTC timezone", "Convert to UTC using: "+fieldName+".astimezone(UTC)")
	}
	return nil
}

func isNameRune(r rune) bool {
	return r >= 'a' && r <= 'z' || r >= 'A' && r <= 'Z' || r >= '0' && r <= '9' || r == '-' || r == '_' || tmvo.PyIsSpace(r)
}

// ValidateName validates label name format and constraints.
func ValidateName(name string) error {
	if name == "" || tmvo.PyStrip(name) == "" {
		return fail("name", "Label name cannot be empty or whitespace",
			"Provide a meaningful label name (e.g., 'backend', 'frontend', 'api')")
	}
	n := utf8.RuneCountInString(name)
	if n < MinNameLength {
		return fail("name", fmt.Sprintf("Label name must be at least %d character(s)", MinNameLength), fmt.Sprintf("Current length: %d", n))
	}
	if n > MaxNameLength {
		return fail("name", fmt.Sprintf("Label name cannot exceed %d characters", MaxNameLength),
			fmt.Sprintf("Current length: %d. Consider abbreviating the name.", n))
	}
	for _, r := range name {
		if !isNameRune(r) {
			return fail("name", "Label name contains invalid characters",
				"Only alphanumeric characters, spaces, hyphens (-), and underscores (_) are allowed")
		}
	}
	return nil
}

func isHex(b byte) bool {
	return b >= '0' && b <= '9' || b >= 'a' && b <= 'f' || b >= 'A' && b <= 'F'
}

// validHexColor is `^#[0-9A-Fa-f]{3}$|^#[0-9A-Fa-f]{6}$` with Python's `$`, which also
// matches before one trailing newline.
func validHexColor(c string) bool {
	if len(c) > 0 && c[len(c)-1] == '\n' {
		c = c[:len(c)-1]
	}
	if (len(c) != 4 && len(c) != 7) || c[0] != '#' {
		return false
	}
	for i := 1; i < len(c); i++ {
		if !isHex(c[i]) {
			return false
		}
	}
	return true
}

// ValidateColor validates a hex color (#RGB or #RRGGBB); nil is allowed.
func ValidateColor(color *string) error {
	if color == nil {
		return nil
	}
	c := *color
	if len(c) == 0 || c[0] != '#' {
		return fail("color", "Color must start with '#'", fmt.Sprintf("Did you mean '#%s'? Use hex color format (e.g., '#ff0000')", c))
	}
	if !validHexColor(c) {
		return fail("color", "Invalid hex color format: "+c, "Use format #RGB (e.g., '#f00') or #RRGGBB (e.g., '#ff0000')")
	}
	return nil
}

// ValidateDescription validates the optional description length.
func ValidateDescription(description *string) error {
	if description == nil || *description == "" {
		return nil
	}
	if n := utf8.RuneCountInString(*description); n > MaxDescriptionLength {
		return fail("description", fmt.Sprintf("Description cannot exceed %d characters", MaxDescriptionLength),
			fmt.Sprintf("Current length: %d. Consider shortening the description.", n))
	}
	return nil
}

// result is Python's (success, error_message) tuple.
func result(err error) (bool, *string) {
	if err == nil {
		return true, nil
	}
	s := err.Error()
	return false, &s
}

// ValidateLabelCreation validates every field required for label creation.
func ValidateLabelCreation(name string, color, description *string, createdAt, updatedAt *time.Time) (bool, *string) {
	return result(func() error {
		if err := ValidateName(name); err != nil {
			return err
		}
		if err := ValidateColor(color); err != nil {
			return err
		}
		if err := ValidateDescription(description); err != nil {
			return err
		}
		if createdAt != nil {
			if err := ValidateTimestamp(createdAt, "created_at"); err != nil {
				return err
			}
		}
		if updatedAt != nil {
			if err := ValidateTimestamp(updatedAt, "updated_at"); err != nil {
				return err
			}
		}
		if createdAt != nil && updatedAt != nil && updatedAt.Before(*createdAt) {
			return fail("updated_at", "updated_at cannot be earlier than created_at", "Ensure updated_at >= created_at")
		}
		return nil
	}())
}

// ValidateLabelUpdate validates only the fields being updated.
func ValidateLabelUpdate(name, color, description *string) (bool, *string) {
	return result(func() error {
		if name != nil {
			if err := ValidateName(*name); err != nil {
				return err
			}
		}
		if err := ValidateColor(color); err != nil {
			return err
		}
		return ValidateDescription(description)
	}())
}

// ValidateTimestampsConsistency checks both timestamps are UTC and ordered.
func ValidateTimestampsConsistency(createdAt, updatedAt time.Time) error {
	if err := ValidateTimestamp(&createdAt, "created_at"); err != nil {
		return err
	}
	if err := ValidateTimestamp(&updatedAt, "updated_at"); err != nil {
		return err
	}
	if updatedAt.Before(createdAt) {
		return fail("updated_at", "updated_at cannot be earlier than created_at",
			fmt.Sprintf("created_at: %s, updated_at: %s", tmvo.IsoFormat(createdAt), tmvo.IsoFormat(updatedAt)))
	}
	return nil
}
