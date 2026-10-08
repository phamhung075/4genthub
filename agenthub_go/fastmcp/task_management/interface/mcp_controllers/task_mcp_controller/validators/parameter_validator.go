package validators

// Parameter Validator for Task MCP Controller
// (Python validators/parameter_validator.py).

import (
	"regexp"
	"strconv"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
)

// ParameterValidator validates parameters for task operations.
type ParameterValidator struct {
	responseFormatter ResponseFormatter
}

// NewParameterValidator ports __init__(response_formatter).
func NewParameterValidator(responseFormatter ResponseFormatter) *ParameterValidator {
	return &ParameterValidator{responseFormatter: responseFormatter}
}

// ValidateCreateTaskParams ports validate_create_task_params.
func (v *ParameterValidator) ValidateCreateTaskParams(title, gitBranchID, description, status, priority, dueDate *string,
	assignees, labels, dependencies []string) (bool, *entities.OrderedMap[any]) {

	if title == nil || strings.TrimSpace(*title) == "" {
		return false, v.createValidationError(
			"title", "A non-empty title string", "Include 'title' in your request")
	}

	if gitBranchID == nil {
		return false, v.createValidationError(
			"git_branch_id", "A valid git_branch_id string", "Include 'git_branch_id' in your request")
	}

	if !v.isValidUUID(*gitBranchID) {
		return false, v.createValidationError(
			"git_branch_id", "A valid UUID format", "git_branch_id should be a valid UUID")
	}

	if status != nil && !v.isValidStatus(*status) {
		return false, v.createValidationError(
			"status",
			"One of: todo, in_progress, blocked, review, testing, done, cancelled, archived",
			"Use a valid task status")
	}

	if priority != nil && !v.isValidPriority(*priority) {
		return false, v.createValidationError(
			"priority", "One of: low, medium, high, urgent, critical", "Use a valid priority level")
	}

	if dueDate != nil && !v.isValidDateFormat(*dueDate) {
		return false, v.createValidationError(
			"due_date", "ISO format date string (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)", "Use ISO date format")
	}

	if assignees != nil && !v.isValidAssigneesList(assignees) {
		return false, v.createValidationError(
			"assignees", "A list of valid agent identifiers or user IDs",
			"Assignees should be agent identifiers (e.g., 'coding-agent') or user IDs (e.g., 'user123')")
	}

	if labels != nil && !v.isValidLabelsList(labels) {
		return false, v.createValidationError(
			"labels", "A list of valid label strings", "Labels should be a list of strings")
	}

	if dependencies != nil && !v.isValidDependenciesList(dependencies) {
		return false, v.createValidationError(
			"dependencies", "A list of valid task IDs", "Dependencies should be a list of valid UUIDs")
	}

	return true, nil
}

// ValidateUpdateTaskParams ports validate_update_task_params(task_id, **kwargs).
func (v *ParameterValidator) ValidateUpdateTaskParams(taskID *string, kwargs map[string]any) (bool, *entities.OrderedMap[any]) {
	if taskID == nil {
		return false, v.createValidationError(
			"task_id", "A valid task_id string", "Include 'task_id' in your request")
	}
	if !v.isValidUUID(*taskID) {
		return false, v.createValidationError(
			"task_id", "A valid UUID format", "task_id should be a valid UUID")
	}

	if val, ok := kwargs["status"]; ok && val != nil {
		if s, isStr := val.(string); isStr && !v.isValidStatus(s) {
			return false, v.createValidationError(
				"status",
				"One of: todo, in_progress, blocked, review, testing, done, cancelled, archived",
				"Use a valid task status")
		}
	}

	if val, ok := kwargs["priority"]; ok && val != nil {
		if s, isStr := val.(string); isStr && !v.isValidPriority(s) {
			return false, v.createValidationError(
				"priority", "One of: low, medium, high, urgent, critical", "Use a valid priority level")
		}
	}

	if val, ok := kwargs["due_date"]; ok && val != nil {
		if s, isStr := val.(string); isStr && !v.isValidDateFormat(s) {
			return false, v.createValidationError(
				"due_date", "ISO format date string", "Use ISO date format")
		}
	}

	if val, ok := kwargs["progress_percentage"]; ok && val != nil {
		progressValue, converted := v.coerceInt(val)
		if !converted {
			return false, v.createValidationError(
				"progress_percentage", "An integer between 0 and 100",
				"Provide progress_percentage as an integer between 0 and 100")
		}
		if progressValue < 0 || progressValue > 100 {
			return false, v.createValidationError(
				"progress_percentage", "An integer between 0 and 100",
				"Provide progress_percentage within the 0-100 range")
		}
		kwargs["progress_percentage"] = progressValue
	}

	return true, nil
}

// ValidateSearchParams ports validate_search_params.
func (v *ParameterValidator) ValidateSearchParams(query *string, filters map[string]any) (bool, *entities.OrderedMap[any]) {
	if query != nil && strings.TrimSpace(*query) == "" {
		return false, v.createValidationError(
			"query", "A non-empty search query string", "Include a valid 'query' in your request")
	}

	if val, ok := filters["status"]; ok && val != nil {
		if s, isStr := val.(string); isStr && !v.isValidStatus(s) {
			return false, v.createValidationError(
				"status",
				"One of: todo, in_progress, blocked, review, testing, done, cancelled, archived",
				"Use a valid task status for filtering")
		}
	}

	if val, ok := filters["priority"]; ok && val != nil {
		if s, isStr := val.(string); isStr && !v.isValidPriority(s) {
			return false, v.createValidationError(
				"priority", "One of: low, medium, high, urgent, critical", "Use a valid priority level for filtering")
		}
	}

	if val, ok := filters["limit"]; ok && val != nil {
		// coerceInt, not a type assertion: a caller's integer arrives as float64 through
		// encoding/json (or as digits in a string), so `val.(int)` refused every value that came
		// over the wire. Same conversion the progress_percentage block above uses.
		limit, converted := v.coerceInt(val)
		if !converted || limit < 0 || limit > 1000 {
			return false, v.createValidationError(
				"limit", "An integer between 0 and 1000", "Use a reasonable limit for results")
		}
		filters["limit"] = limit
	}

	if val, ok := filters["offset"]; ok && val != nil {
		offset, converted := v.coerceInt(val)
		if !converted || offset < 0 {
			return false, v.createValidationError(
				"offset", "A non-negative integer", "Offset should be 0 or greater")
		}
		filters["offset"] = offset
	}

	return true, nil
}

// coerceInt mirrors int(value) with TypeError/ValueError -> not converted.
func (v *ParameterValidator) coerceInt(value any) (int, bool) {
	switch t := value.(type) {
	case int:
		return t, true
	case int64:
		return int(t), true
	case float64:
		return int(t), true
	case string:
		s := strings.TrimSpace(t)
		out, err := strconv.Atoi(s)
		if err != nil {
			return 0, false
		}
		return out, true
	case bool:
		if t {
			return 1, true
		}
		return 0, true
	default:
		return 0, false
	}
}

var (
	parameterValidatorUUIDPattern = regexp.MustCompile(`^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$`)
	parameterValidatorAssigneesRe = regexp.MustCompile(`^@?[a-zA-Z0-9_-]+$`)
	parameterValidatorLabelsRe    = regexp.MustCompile(`^[a-zA-Z0-9_-]+$`)
)

// isValidUUID ports uuid.UUID(value) acceptance.
func (v *ParameterValidator) isValidUUID(value string) bool {
	return parameterValidatorUUIDPattern.MatchString(value)
}

func (v *ParameterValidator) isValidStatus(status string) bool {
	validStatuses := map[string]struct{}{
		"todo": {}, "in_progress": {}, "blocked": {}, "review": {},
		"testing": {}, "done": {}, "cancelled": {}, "archived": {},
	}
	_, ok := validStatuses[strings.ToLower(status)]
	return ok
}

func (v *ParameterValidator) isValidPriority(priority string) bool {
	validPriorities := map[string]struct{}{
		"low": {}, "medium": {}, "high": {}, "urgent": {}, "critical": {},
	}
	_, ok := validPriorities[strings.ToLower(priority)]
	return ok
}

func (v *ParameterValidator) isValidDateFormat(dateStr string) bool {
	if _, ok := parseISOOrDate(dateStr); ok {
		return true
	}
	_, err := time.Parse("2006-01-02", dateStr)
	return err == nil
}

// parseISOOrDate mirrors datetime.fromisoformat(date_str.replace("Z","+00:00")).
func parseISOOrDate(s string) (time.Time, bool) {
	s = strings.ReplaceAll(s, "Z", "+00:00")
	for _, l := range []string{time.RFC3339Nano, "2006-01-02T15:04:05", "2006-01-02 15:04:05", "2006-01-02"} {
		if t, err := time.Parse(l, s); err == nil {
			return t, true
		}
	}
	return time.Time{}, false
}

func (v *ParameterValidator) isValidAssigneesList(assignees []string) bool {
	for _, assignee := range assignees {
		clean := strings.TrimSpace(assignee)
		if clean == "" {
			return false
		}
		if !parameterValidatorAssigneesRe.MatchString(clean) {
			return false
		}
	}
	return true
}

func (v *ParameterValidator) isValidLabelsList(labels []string) bool {
	for _, label := range labels {
		clean := strings.TrimSpace(label)
		if clean == "" {
			return false
		}
		if !parameterValidatorLabelsRe.MatchString(clean) {
			return false
		}
	}
	return true
}

func (v *ParameterValidator) isValidDependenciesList(dependencies []string) bool {
	for _, depID := range dependencies {
		if !v.isValidUUID(depID) {
			return false
		}
	}
	return true
}

func (v *ParameterValidator) createValidationError(field, expected, hint string) *entities.OrderedMap[any] {
	metadata := entities.NewOrderedMap[any]()
	metadata.Set("field", field)
	metadata.Set("hint", hint)
	return v.responseFormatter.CreateErrorResponse(
		"validate_parameters",
		"Invalid field: "+field+". Expected: "+expected,
		errorCodeValidation,
		metadata,
	)
}
