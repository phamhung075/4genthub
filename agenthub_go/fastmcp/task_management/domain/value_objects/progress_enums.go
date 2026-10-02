package value_objects

import "strings"

// ProgressState: Progress state enum for stepper visualization
type ProgressState string

const (
	ProgressStateInitial    ProgressState = "INITIAL"
	ProgressStateInProgress ProgressState = "IN_PROGRESS"
	ProgressStateComplete   ProgressState = "COMPLETE"
)

// ProgressStateValues lists all members in declaration order.
var ProgressStateValues = []ProgressState{ProgressStateInitial, ProgressStateInProgress, ProgressStateComplete}

func (e ProgressState) String() string { return string(e) }

// GetAllProgressStates lists all progress states.
func GetAllProgressStates() []string { return stringValues(ProgressStateValues) }

// IsValidProgressState checks a state string case-insensitively against the upper-case values.
func IsValidProgressState(state string) bool {
	return containsString(GetAllProgressStates(), strings.ToUpper(state))
}

// ProgressStateFromProgressPercentage maps 0 → INITIAL, 100 → COMPLETE, else IN_PROGRESS.
func ProgressStateFromProgressPercentage(percentage int) ProgressState {
	switch percentage {
	case 0:
		return ProgressStateInitial
	case 100:
		return ProgressStateComplete
	}
	return ProgressStateInProgress
}

// ProgressStateFromTaskStatus maps a task status string to a progress state.
func ProgressStateFromTaskStatus(status string) ProgressState {
	switch strings.ToLower(status) {
	case "todo", "pending":
		return ProgressStateInitial
	case "done", "completed", "finished":
		return ProgressStateComplete
	}
	return ProgressStateInProgress
}

// GetVisualIndicator returns the stepper glyph for the state.
func (p ProgressState) GetVisualIndicator() string {
	switch p {
	case ProgressStateInitial:
		return "○"
	case ProgressStateInProgress:
		return "◐"
	}
	return "●"
}

// GetStepNumber returns the 1-based stepper position.
func (p ProgressState) GetStepNumber() int {
	switch p {
	case ProgressStateInitial:
		return 1
	case ProgressStateInProgress:
		return 2
	}
	return 3
}

func (p ProgressState) IsTerminal() bool { return p == ProgressStateComplete }
func (p ProgressState) IsActive() bool   { return p == ProgressStateInProgress }
