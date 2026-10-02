package validators

// Context Validator for Task MCP Controller
// (Python validators/context_validator.py).

import (
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
)

// ContextValidator validates context-related operations for tasks.
type ContextValidator struct {
	responseFormatter ResponseFormatter
}

// NewContextValidator ports __init__(response_formatter).
func NewContextValidator(responseFormatter ResponseFormatter) *ContextValidator {
	return &ContextValidator{responseFormatter: responseFormatter}
}

// ValidateContextRequirements ports validate_context_requirements.
func (v *ContextValidator) ValidateContextRequirements(operation string, taskID, gitBranchID *string, includeContext *bool) (bool, *entities.OrderedMap[any]) {

	gitBranchRequiredOperations := map[string]struct{}{"create": {}, "next": {}}
	if _, required := gitBranchRequiredOperations[operation]; required {
		if gitBranchID == nil {
			capitalized := strings.ToUpper(operation[:1]) + operation[1:]
			return false, v.createContextError(
				"git_branch_id",
				capitalized+" operation requires git_branch_id",
				"Include git_branch_id to specify the branch context",
			)
		}
	}

	if includeContext != nil && *includeContext {
		if taskID == nil {
			return false, v.createContextError(
				"task_id",
				"Context inclusion requires task_id",
				"Provide task_id when requesting context inclusion",
			)
		}
	}

	return true, nil
}

// ValidateContextData ports validate_context_data. The Python isinstance(dict)
// guard cannot be expressed once the parameter is typed as *OrderedMap; the
// reserved-field checks are kept.
func (v *ContextValidator) ValidateContextData(contextData *entities.OrderedMap[any]) (bool, *entities.OrderedMap[any]) {
	if contextData == nil {
		return true, nil
	}

	reservedFields := []string{"id", "created_at", "updated_at", "level", "context_id"}
	for _, field := range reservedFields {
		if contextData.Has(field) {
			return false, v.createContextError(
				"context_data."+field,
				"Field '"+field+"' is reserved and cannot be set directly",
				"Remove '"+field+"' from context data",
			)
		}
	}

	return true, nil
}

// ValidateContextInheritance ports validate_context_inheritance.
func (v *ContextValidator) ValidateContextInheritance(parentContextID, childContextID *string) (bool, *entities.OrderedMap[any]) {
	if parentContextID != nil && childContextID != nil && *parentContextID == *childContextID {
		return false, v.createContextError(
			"context_inheritance",
			"Context cannot inherit from itself",
			"Use different IDs for parent and child contexts",
		)
	}
	return true, nil
}

func (v *ContextValidator) createContextError(field, message, hint string) *entities.OrderedMap[any] {
	metadata := entities.NewOrderedMap[any]()
	metadata.Set("field", field)
	metadata.Set("hint", hint)

	d := entities.NewOrderedMap[any]()
	d.Set("status", "error")
	d.Set("error", "Context validation failed: "+message)
	d.Set("error_code", "VALIDATION_ERROR")
	d.Set("operation", "validate_context")
	d.Set("metadata", metadata)
	return d
}
