package value_objects

import "strings"

// PriorityLevel pairs a priority label with its numeric ordering level.
type PriorityLevel struct {
	Label string
	Level int
}

// PriorityLevels lists all levels in ascending order (Python PriorityLevel enum).
var PriorityLevels = []PriorityLevel{
	{"low", 1}, {"medium", 2}, {"high", 3}, {"urgent", 4}, {"critical", 5},
}

// Priority is a validated task priority with ordering.
type Priority struct{ Value string }

// NewPriority validates value against the known priority labels.
func NewPriority(value string) (Priority, error) {
	if value == "" {
		return Priority{}, valueErrorf("Priority cannot be empty")
	}
	labels := make([]string, len(PriorityLevels))
	for i, p := range PriorityLevels {
		if p.Label == value {
			return Priority{value}, nil
		}
		labels[i] = p.Label
	}
	return Priority{}, valueErrorf("Invalid priority: %s. Valid priorities: %s", value, strings.Join(labels, ", "))
}

func mustPriority(v string) Priority { return Priority{v} }

func PriorityLow() Priority      { return mustPriority("low") }
func PriorityMedium() Priority   { return mustPriority("medium") }
func PriorityHigh() Priority     { return mustPriority("high") }
func PriorityUrgent() Priority   { return mustPriority("urgent") }
func PriorityCritical() Priority { return mustPriority("critical") }

// PriorityFromString trims value and defaults empty input to "medium".
func PriorityFromString(value string) (Priority, error) {
	if value == "" {
		return NewPriority("medium")
	}
	return NewPriority(strings.TrimSpace(value))
}

func (p Priority) String() string { return p.Value }

// Order returns the numeric level (0 for unknown values).
func (p Priority) Order() int {
	for _, l := range PriorityLevels {
		if l.Label == p.Value {
			return l.Level
		}
	}
	return 0
}

func (p Priority) Lt(o Priority) bool { return p.Order() < o.Order() }
func (p Priority) Le(o Priority) bool { return p.Order() <= o.Order() }
func (p Priority) Gt(o Priority) bool { return p.Order() > o.Order() }
func (p Priority) Ge(o Priority) bool { return p.Order() >= o.Order() }

func (p Priority) IsCritical() bool { return p.Value == "critical" }

// IsHighOrCritical mirrors Python: only "high" and "critical" (not "urgent").
func (p Priority) IsHighOrCritical() bool { return p.Value == "high" || p.Value == "critical" }
