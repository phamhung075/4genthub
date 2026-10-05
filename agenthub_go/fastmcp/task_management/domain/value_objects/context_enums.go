package value_objects

import "strings"

// ContextLevel: Enumeration of context hierarchy levels.
type ContextLevel string

const (
	ContextLevelGlobal  ContextLevel = "global"
	ContextLevelProject ContextLevel = "project"
	ContextLevelBranch  ContextLevel = "branch"
	ContextLevelTask    ContextLevel = "task"
)

// ContextLevelValues lists all members in declaration order.
var ContextLevelValues = []ContextLevel{ContextLevelGlobal, ContextLevelProject, ContextLevelBranch, ContextLevelTask}

func (e ContextLevel) String() string { return string(e) }

// ContextLevelFromString parses a level case-insensitively.
func ContextLevelFromString(value string) (ContextLevel, error) {
	lower := strings.ToLower(value)
	names := make([]string, len(ContextLevelValues))
	for i, l := range ContextLevelValues {
		if string(l) == lower {
			return l, nil
		}
		names[i] = string(l)
	}
	return "", valueErrorf("Invalid context level: %s. Valid levels are: %s", value, strings.Join(names, ", "))
}

// ContextLevelFromEnumValue is the Python enum constructor ContextLevel(value): an exact,
// case-sensitive match on the member value, with the enum's ValueError text.
func ContextLevelFromEnumValue(value string) (ContextLevel, error) {
	for _, l := range ContextLevelValues {
		if string(l) == value {
			return l, nil
		}
	}
	return "", valueErrorf("'%s' is not a valid ContextLevel", value)
}

// GetParentLevel returns the parent in Global → Project → Branch → Task, and
// false for GLOBAL (Python returns None).
func (e ContextLevel) GetParentLevel() (ContextLevel, bool) {
	switch e {
	case ContextLevelTask:
		return ContextLevelBranch, true
	case ContextLevelBranch:
		return ContextLevelProject, true
	case ContextLevelProject:
		return ContextLevelGlobal, true
	}
	return "", false
}
