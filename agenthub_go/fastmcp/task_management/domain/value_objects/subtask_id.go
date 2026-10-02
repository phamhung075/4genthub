package value_objects

import (
	"fmt"
	"strings"
)

// SubtaskId is a subtask identifier (UUID, hierarchical, integer, or test format).
type SubtaskId struct{ Value string }

// NewSubtaskId validates and normalizes value.
func NewSubtaskId(value string) (SubtaskId, error) {
	trimmed := strings.TrimSpace(value)
	if trimmed == "" {
		return SubtaskId{}, valueErrorf("Subtask ID cannot be empty or whitespace")
	}
	if !isValidTaskLikeID(trimmed) {
		return SubtaskId{}, valueErrorf(
			"Invalid Subtask ID format: '%s'. Expected canonical UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
			trimmed)
	}
	return SubtaskId{normalizeTaskLikeID(trimmed)}, nil
}

// GenerateNewSubtaskId creates a new unique SubtaskId using UUIDv4.
func GenerateNewSubtaskId() SubtaskId { return SubtaskId{NewUUIDv4()} }

func (s SubtaskId) String() string { return s.Value }

// GoString mirrors Python's __repr__.
func (s SubtaskId) GoString() string { return fmt.Sprintf("SubtaskId('%s')", s.Value) }

func (s SubtaskId) ToCanonicalFormat() string { return s.Value }

func (s SubtaskId) ToHexFormat() string { return strings.ReplaceAll(s.Value, "-", "") }
