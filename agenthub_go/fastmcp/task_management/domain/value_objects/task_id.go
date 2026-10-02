package value_objects

import (
	"fmt"
	"regexp"
	"strconv"
	"strings"
)

var (
	uuidPattern         = regexp.MustCompile(`^[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}$`)
	hierarchicalPattern = regexp.MustCompile(`^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.[0-9]{3}$`)
	integerPattern      = regexp.MustCompile(`^[0-9]+$`)
	testIDPattern       = regexp.MustCompile(`^[a-zA-Z]+(?:-[a-zA-Z]+)*-[0-9]+$`)
	simpleTestPattern   = regexp.MustCompile(`^[a-zA-Z]+(?:-[a-zA-Z]+)*$`)
)

// isValidTaskLikeID reports whether value is a UUID (32-hex or canonical), a
// hierarchical subtask ID (uuid.NNN), an integer ID, or a test-style ID.
// Shared by TaskId and SubtaskId, whose Python validators are identical.
func isValidTaskLikeID(value string) bool {
	lower := strings.ToLower(value)
	return uuidPattern.MatchString(lower) ||
		hierarchicalPattern.MatchString(lower) ||
		integerPattern.MatchString(value) ||
		testIDPattern.MatchString(value) ||
		simpleTestPattern.MatchString(value)
}

// normalizeTaskLikeID converts 32-char hex to canonical UUID, keeps integer and
// hierarchical IDs as-is, and lowercases everything else.
func normalizeTaskLikeID(value string) string {
	if !strings.Contains(value, "-") && len(value) == 32 {
		h := strings.ToLower(value)
		return h[:8] + "-" + h[8:12] + "-" + h[12:16] + "-" + h[16:20] + "-" + h[20:]
	}
	if integerPattern.MatchString(value) || strings.Contains(value, ".") {
		return value
	}
	return strings.ToLower(value)
}

// TaskId is a task identifier: a UUID, a hierarchical subtask ID (uuid.NNN),
// or one of the integer/test formats accepted by the Python implementation.
type TaskId struct{ EntityId }

// NewTaskId validates and normalizes value.
func NewTaskId(value string) (TaskId, error) {
	trimmed := strings.TrimSpace(value)
	if trimmed == "" {
		return TaskId{}, valueErrorf("TaskId cannot be empty or whitespace")
	}
	if !isValidTaskLikeID(trimmed) {
		return TaskId{}, valueErrorf(
			"Invalid TaskId format: '%s'. Expected canonical UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
			trimmed)
	}
	return TaskId{EntityId{Value: normalizeTaskLikeID(trimmed)}}, nil
}

// TaskIdFromInt creates a TaskId from an integer value.
func TaskIdFromInt(value int) (TaskId, error) { return NewTaskId(strconv.Itoa(value)) }

// GenerateNewTaskId creates a new unique TaskId using UUIDv4.
func GenerateNewTaskId() TaskId { return TaskId{EntityId{Value: NewUUIDv4()}} }

// GenerateSubtaskId builds the next hierarchical ID "parent.NNN", skipping
// numbers already used by existingSubtaskIDs. Validation is bypassed, as in Python.
func GenerateSubtaskId(parent TaskId, existingSubtaskIDs []string) TaskId {
	parentStr := parent.String()
	prefix := parentStr + "."
	maxNum := 0
	for _, existing := range existingSubtaskIDs {
		if !strings.HasPrefix(existing, prefix) {
			continue
		}
		suffix := existing[len(prefix):]
		if n, err := strconv.Atoi(suffix); err == nil && integerPattern.MatchString(suffix) && n > maxNum {
			maxNum = n
		}
	}
	return TaskId{EntityId{Value: fmt.Sprintf("%s.%03d", parentStr, maxNum+1)}}
}
