package services

import (
	"context"

	"agenthub/fastmcp/task_management/domain/value_objects"
)

// zpATokenUsageRepository is the minimal storage dependency of TrackTokenOperation:
// the Python function builds TokenRepository(session) and calls
// update_token_usage(token_id, operation). The existing repositories.ITokenRepository
// does not carry the operation argument, so this application-layer interface is used.
type zpATokenUsageRepository interface {
	UpdateTokenUsage(ctx context.Context, tokenID string, operation string) (bool, error)
}

// TrackTokenOperation tracks a specific operation for a token
// (Python application/services/token_usage_tracking_service.py). A falsy token_id or
// any error returns false.
func TrackTokenOperation(ctx context.Context, tokenID *string, operation string, repository zpATokenUsageRepository) bool {
	if tokenID == nil || *tokenID == "" {
		return false
	}
	if repository == nil {
		return false
	}

	success, err := repository.UpdateTokenUsage(ctx, *tokenID, operation)
	if err != nil {
		return false
	}
	return success
}

// GetOperationName generates a standardized operation name from entity and action
// using Python str.lower.
func GetOperationName(entity string, action string) string {
	return value_objects.PyLower(entity) + "_" + value_objects.PyLower(action)
}

// OperationNames are the standard operation names for token usage tracking.
type OperationNames string

const (
	// Task operations
	OperationNamesTaskCreate   OperationNames = "task_create"
	OperationNamesTaskUpdate   OperationNames = "task_update"
	OperationNamesTaskDelete   OperationNames = "task_delete"
	OperationNamesTaskComplete OperationNames = "task_complete"
	OperationNamesTaskList     OperationNames = "task_list"
	OperationNamesTaskGet      OperationNames = "task_get"

	// Subtask operations
	OperationNamesSubtaskCreate   OperationNames = "subtask_create"
	OperationNamesSubtaskUpdate   OperationNames = "subtask_update"
	OperationNamesSubtaskDelete   OperationNames = "subtask_delete"
	OperationNamesSubtaskComplete OperationNames = "subtask_complete"
	OperationNamesSubtaskList     OperationNames = "subtask_list"
	OperationNamesSubtaskGet      OperationNames = "subtask_get"

	// Project operations
	OperationNamesProjectCreate OperationNames = "project_create"
	OperationNamesProjectUpdate OperationNames = "project_update"
	OperationNamesProjectDelete OperationNames = "project_delete"
	OperationNamesProjectGet    OperationNames = "project_get"
	OperationNamesProjectList   OperationNames = "project_list"

	// Branch operations
	OperationNamesBranchCreate OperationNames = "branch_create"
	OperationNamesBranchUpdate OperationNames = "branch_update"
	OperationNamesBranchDelete OperationNames = "branch_delete"
	OperationNamesBranchGet    OperationNames = "branch_get"
	OperationNamesBranchList   OperationNames = "branch_list"

	// Agent operations
	OperationNamesAgentRegister OperationNames = "agent_register"
	OperationNamesAgentUpdate   OperationNames = "agent_update"
	OperationNamesAgentDelete   OperationNames = "agent_delete"
	OperationNamesAgentAssign   OperationNames = "agent_assign"
	OperationNamesAgentUnassign OperationNames = "agent_unassign"
	OperationNamesAgentCall     OperationNames = "agent_call"

	// Context operations
	OperationNamesContextCreate OperationNames = "context_create"
	OperationNamesContextUpdate OperationNames = "context_update"
	OperationNamesContextDelete OperationNames = "context_delete"
	OperationNamesContextGet    OperationNames = "context_get"
)
