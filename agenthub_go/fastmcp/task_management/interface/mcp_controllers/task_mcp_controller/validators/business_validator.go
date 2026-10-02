// Package validators ports task_mcp_controller/validators/*.py.
package validators

// Business Validator for Task MCP Controller
// (Python validators/business_validator.py).

import (
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
)

// ResponseFormatter is the minimal view of the interface-layer
// StandardResponseFormatter used by the validators. Declared locally (the
// task_mcp_controller/factories package is being ported concurrently).
type ResponseFormatter interface {
	CreateErrorResponse(operation, errorMessage, errorCode string, metadata *entities.OrderedMap[any]) *entities.OrderedMap[any]
}

// Error codes from interface/utils/response_formatter.py.
const (
	errorCodeValidation            = "VALIDATION_ERROR"
	errorCodeBusinessRuleViolation = "BUSINESS_RULE_VIOLATION"
)

// BusinessValidator validates business rules for task operations.
type BusinessValidator struct {
	responseFormatter ResponseFormatter
}

// NewBusinessValidator ports __init__(response_formatter).
func NewBusinessValidator(responseFormatter ResponseFormatter) *BusinessValidator {
	return &BusinessValidator{responseFormatter: responseFormatter}
}

// bvParseISODate mirrors datetime.fromisoformat(s.replace("Z", "+00:00")).
func bvParseISODate(s string) (time.Time, error) {
	s = strings.ReplaceAll(s, "Z", "+00:00")
	layouts := []string{time.RFC3339Nano, "2006-01-02T15:04:05", "2006-01-02 15:04:05", "2006-01-02"}
	var lastErr error
	for _, l := range layouts {
		if t, err := time.Parse(l, s); err == nil {
			return t, nil
		} else {
			lastErr = err
		}
	}
	return time.Time{}, lastErr
}

// ValidateTaskCreationRules ports validate_task_creation_rules.
func (v *BusinessValidator) ValidateTaskCreationRules(title, gitBranchID string, priority, dueDate *string,
	dependencies []string) (bool, *entities.OrderedMap[any]) {

	if len(strings.TrimSpace(title)) < 3 {
		return false, v.createBusinessError(
			"title_length",
			"Task title must be at least 3 characters long",
			"Provide a more descriptive title for the task",
		)
	}

	// Rule: critical tasks should have due dates -- warning only (logging dropped).

	if dueDate != nil {
		if dueDatetime, err := bvParseISODate(*dueDate); err == nil {
			now := time.Now().UTC()
			if dueDatetime.Before(now) && now.Sub(dueDatetime).Seconds() > 3600 {
				return false, v.createBusinessError(
					"due_date_past",
					"Due date cannot be significantly in the past",
					"Set a due date in the future or remove the due date",
				)
			}
		}
	}

	return true, nil
}

// ValidateTaskUpdateRules ports validate_task_update_rules.
func (v *BusinessValidator) ValidateTaskUpdateRules(taskID string, currentTaskData *entities.OrderedMap[any],
	status, priority, dueDate *string, dependencies []string, completionSummary *string) (bool, *entities.OrderedMap[any]) {

	if dependencies != nil {
		for _, d := range dependencies {
			if d == taskID {
				return false, v.createBusinessError(
					"self_dependency",
					"Task cannot depend on itself",
					"Remove the task's own ID from the dependencies list",
				)
			}
		}
	}

	if status != nil && strings.ToLower(*status) == "completed" && currentTaskData != nil {
		currentPriority := "medium"
		if p, ok := currentTaskData.Get("priority"); ok {
			if ps, isStr := p.(string); isStr {
				currentPriority = ps
			}
		}
		// warning only unless summary missing on high/critical (logging dropped)
		_ = currentPriority
	}

	if status != nil && currentTaskData != nil {
		currentStatus := "pending"
		if s, ok := currentTaskData.Get("status"); ok {
			if ss, isStr := s.(string); isStr {
				currentStatus = ss
			}
		}
		if !v.isValidStatusTransition(currentStatus, *status) {
			return false, v.createBusinessError(
				"invalid_status_transition",
				"Cannot transition from '"+currentStatus+"' to '"+*status+"'",
				"Valid transitions from '"+currentStatus+"': "+v.getValidTransitions(currentStatus),
			)
		}
	}

	if dueDate != nil && currentTaskData != nil {
		if s, ok := currentTaskData.Get("status"); ok {
			if ss, isStr := s.(string); isStr && ss == "completed" {
				return false, v.createBusinessError(
					"completed_task_due_date",
					"Cannot change due date of completed task",
					"Reopen the task before changing the due date",
				)
			}
		}
	}

	return true, nil
}

// ValidateTaskDeletionRules ports validate_task_deletion_rules.
func (v *BusinessValidator) ValidateTaskDeletionRules(taskID string, currentTaskData *entities.OrderedMap[any]) (bool, *entities.OrderedMap[any]) {
	if currentTaskData == nil {
		return true, nil
	}
	// status in_progress warning only (logging dropped).
	return true, nil
}

// ValidateCompletionRequirements ports validate_completion_requirements.
func (v *BusinessValidator) ValidateCompletionRequirements(taskData *entities.OrderedMap[any], completionSummary, testingNotes *string) (bool, *entities.OrderedMap[any]) {

	priority := "medium"
	if p, ok := taskData.Get("priority"); ok {
		if ps, isStr := p.(string); isStr {
			priority = ps
		}
	}
	title := "Unknown task"
	if t, ok := taskData.Get("title"); ok {
		if ts, isStr := t.(string); isStr {
			title = ts
		}
	}

	if priority == "high" || priority == "critical" {
		if completionSummary == nil || len(strings.TrimSpace(*completionSummary)) < 10 {
			return false, v.createBusinessError(
				"completion_summary_required",
				"High/critical priority tasks require detailed completion summary (minimum 10 characters)",
				"Add a meaningful completion summary explaining what was accomplished",
			)
		}
	}

	lowerTitle := strings.ToLower(title)
	isTestOrBug := strings.Contains(lowerTitle, "test") || strings.Contains(lowerTitle, "bug") ||
		strings.Contains(lowerTitle, "fix") || strings.Contains(lowerTitle, "issue")
	if isTestOrBug {
		_ = testingNotes // warning only (logging dropped)
	}

	return true, nil
}

func (v *BusinessValidator) isValidStatusTransition(fromStatus, toStatus string) bool {
	validTransitions := map[string][]string{
		"pending":     {"in_progress", "blocked", "cancelled"},
		"in_progress": {"completed", "blocked", "pending", "in_progress"},
		"blocked":     {"pending", "in_progress", "cancelled"},
		"completed":   {"pending", "in_progress"},
		"cancelled":   {"pending"},
	}
	fromLower := strings.ToLower(fromStatus)
	toLower := strings.ToLower(toStatus)
	allowed, ok := validTransitions[fromLower]
	if !ok {
		return true
	}
	for _, a := range allowed {
		if a == toLower {
			return true
		}
	}
	return false
}

func (v *BusinessValidator) getValidTransitions(fromStatus string) string {
	validTransitions := map[string][]string{
		"pending":     {"in_progress", "blocked", "cancelled"},
		"in_progress": {"completed", "blocked", "pending", "in_progress"},
		"blocked":     {"pending", "in_progress", "cancelled"},
		"completed":   {"pending", "in_progress"},
		"cancelled":   {"pending"},
	}
	allowed := validTransitions[strings.ToLower(fromStatus)]
	quoted := make([]string, 0, len(allowed))
	for _, a := range allowed {
		quoted = append(quoted, "'"+a+"'")
	}
	return "[" + strings.Join(quoted, ", ") + "]"
}

func (v *BusinessValidator) createBusinessError(ruleName, message, hint string) *entities.OrderedMap[any] {
	metadata := entities.NewOrderedMap[any]()
	metadata.Set("rule", ruleName)
	metadata.Set("hint", hint)
	return v.responseFormatter.CreateErrorResponse(
		"validate_business_rules",
		"Business rule violation ("+ruleName+"): "+message,
		errorCodeBusinessRuleViolation,
		metadata,
	)
}
