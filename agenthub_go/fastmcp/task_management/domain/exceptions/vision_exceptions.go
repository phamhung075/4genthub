package exceptions

import "fmt"

// VisionSystemError is the base exception for all vision system errors.
type VisionSystemError struct{ Msg string }

func (e *VisionSystemError) Error() string { return e.Msg }

// ContextEnforcementError: context enforcement rules were violated.
type ContextEnforcementError struct {
	VisionSystemError
	TaskID *string
}

func (e *ContextEnforcementError) Unwrap() error { return &e.VisionSystemError }

func NewContextEnforcementError(message string, taskID *string) *ContextEnforcementError {
	return &ContextEnforcementError{VisionSystemError{message}, taskID}
}

// MissingCompletionSummaryError: completing a task without a completion summary.
type MissingCompletionSummaryError struct{ ContextEnforcementError }

func (e *MissingCompletionSummaryError) Unwrap() error { return &e.ContextEnforcementError }

func NewMissingCompletionSummaryError(taskID string) *MissingCompletionSummaryError {
	msg := fmt.Sprintf("Task '%s' cannot be completed without a completion_summary. "+
		"The Vision System requires a summary of what was accomplished.", taskID)
	return &MissingCompletionSummaryError{*NewContextEnforcementError(msg, &taskID)}
}

// InvalidContextUpdateError: context update validation failed.
type InvalidContextUpdateError struct {
	ContextEnforcementError
	Field *string
}

func (e *InvalidContextUpdateError) Unwrap() error { return &e.ContextEnforcementError }

func NewInvalidContextUpdateError(message string, taskID, field *string) *InvalidContextUpdateError {
	return &InvalidContextUpdateError{*NewContextEnforcementError(message, taskID), field}
}

// WorkflowStateError: workflow state transition is invalid.
type WorkflowStateError struct {
	VisionSystemError
	CurrentState   string
	AttemptedState string
}

func (e *WorkflowStateError) Unwrap() error { return &e.VisionSystemError }

func NewWorkflowStateError(message, currentState, attemptedState string) *WorkflowStateError {
	return &WorkflowStateError{VisionSystemError{message}, currentState, attemptedState}
}

// VisionDataIntegrityError: vision data integrity checks failed.
type VisionDataIntegrityError struct{ VisionSystemError }

func (e *VisionDataIntegrityError) Unwrap() error { return &e.VisionSystemError }

func NewVisionDataIntegrityError(message string) *VisionDataIntegrityError {
	return &VisionDataIntegrityError{VisionSystemError{message}}
}

// ProgressTrackingError: progress tracking operations failed.
type ProgressTrackingError struct {
	VisionSystemError
	TaskID *string
}

func (e *ProgressTrackingError) Unwrap() error { return &e.VisionSystemError }

func NewProgressTrackingError(message string, taskID *string) *ProgressTrackingError {
	return &ProgressTrackingError{VisionSystemError{message}, taskID}
}
