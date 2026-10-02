package services

import (
	stderrors "errors"
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/utilities"
)

// ContextValidationService ports context_validation_service.ContextValidationService.
type ContextValidationService struct {
	userID      *string
	idValidator *utilities.IDValidator
}

// NewContextValidationService builds the service. userID nil mirrors Python None;
// a nil validator becomes IDValidator() with Python's default strict validation.
func NewContextValidationService(userID *string, idValidator *utilities.IDValidator) *ContextValidationService {
	if idValidator == nil {
		idValidator = utilities.NewIDValidator(true)
	}
	return &ContextValidationService{userID: userID, idValidator: idValidator}
}

// WithUser mirrors with_user(user_id).
func (s *ContextValidationService) WithUser(userID string) *ContextValidationService {
	return NewContextValidationService(&userID, s.idValidator)
}

// ValidateCompletionContext ports validate_completion_context.
func (s *ContextValidationService) ValidateCompletionContext(
	task *entities.Task, context *entities.TaskContext, completionSummary string,
	testingNotes, nextRecommendations *string,
) (bool, []string) {
	_ = testingNotes
	_ = nextRecommendations
	errors := []string{}

	if strings.TrimSpace(completionSummary) == "" {
		errors = append(errors, "completion_summary is required and cannot be empty")
	}

	taskIDStr := "None"
	if task.ID != nil {
		taskIDStr = task.ID.Value
	}
	taskIDResult := s.idValidator.DetectIDType(taskIDStr, "task_id")
	if !taskIDResult.IsValid {
		if taskIDResult.ErrorMessage != nil {
			errors = append(errors, "Invalid task ID format: "+*taskIDResult.ErrorMessage)
		} else {
			errors = append(errors, "Invalid task ID format: ")
		}
	}

	if context.Metadata.TaskID != taskIDStr {
		errors = append(errors, "Context task_id "+context.Metadata.TaskID+" does not match task "+taskIDStr)

		contextIDResult := s.idValidator.DetectIDType(context.Metadata.TaskID, "task_id")
		if !contextIDResult.IsValid {
			if contextIDResult.ErrorMessage != nil {
				errors = append(errors, "Invalid context task_id format: "+*contextIDResult.ErrorMessage)
			} else {
				errors = append(errors, "Invalid context task_id format: ")
			}
		} else if context.Metadata.TaskID == taskIDStr {
			errors = append(errors, "CRITICAL: Context task_id and task ID mismatch may indicate ID confusion")
		}
	}

	if task.IsCompleted() {
		errors = append(errors, "Task is already completed")
	}

	return len(errors) == 0, errors
}

// ValidateContextUpdate ports validate_context_update.
func (s *ContextValidationService) ValidateContextUpdate(context *entities.TaskContext, updateData map[string]any) (bool, []string) {
	_ = context
	errors := []string{}

	if v, ok := updateData["completion_percentage"]; ok {
		if !ctxIsNumber(v) || ctxFloat(v) < 0 || ctxFloat(v) > 100 {
			errors = append(errors, "completion_percentage must be a number between 0 and 100")
		}
	}

	if v, ok := updateData["next_steps"]; ok {
		if !ctxIsList(v) {
			errors = append(errors, "next_steps must be a list")
		}
	}

	if v, ok := updateData["vision_alignment_score"]; ok {
		if !ctxIsNumber(v) || ctxFloat(v) < 0 || ctxFloat(v) > 1 {
			errors = append(errors, "vision_alignment_score must be a number between 0 and 1")
		}
	}

	return len(errors) == 0, errors
}

// EnsureCompletionSummaryInContext ports ensure_completion_summary_in_context.
func (s *ContextValidationService) EnsureCompletionSummaryInContext(
	context *entities.TaskContext, completionSummary string,
	testingNotes, nextRecommendations *string,
) error {
	err := context.UpdateCompletionSummary(completionSummary, testingNotes, nextRecommendations)
	if err != nil {
		var ve *value_objects.ValueError
		if stderrors.As(err, &ve) {
			taskID := context.Metadata.TaskID
			field := "completion_summary"
			return exceptions.NewInvalidContextUpdateError(ve.Msg, &taskID, &field)
		}
		return err
	}
	return nil
}

// ValidateProgressUpdate ports validate_progress_update.
func (s *ContextValidationService) ValidateProgressUpdate(progressType, details string, percentage *float64) (bool, []string) {
	errors := []string{}

	validTypes := []string{
		"analysis", "design", "implementation", "testing",
		"documentation", "review", "deployment", "general",
	}

	valid := false
	for _, t := range validTypes {
		if progressType == t {
			valid = true
			break
		}
	}
	if !valid {
		errors = append(errors, "Invalid progress_type. Must be one of: "+strings.Join(validTypes, ", "))
	}

	if strings.TrimSpace(details) == "" {
		errors = append(errors, "Progress details cannot be empty")
	}

	if percentage != nil {
		if *percentage < 0 || *percentage > 100 {
			errors = append(errors, "Progress percentage must be between 0 and 100")
		}
	}

	return len(errors) == 0, errors
}

// ValidateCheckpoint ports validate_checkpoint.
func (s *ContextValidationService) ValidateCheckpoint(checkpointName string, stateData map[string]any) (bool, []string) {
	errors := []string{}

	if strings.TrimSpace(checkpointName) == "" {
		errors = append(errors, "Checkpoint name cannot be empty")
	}

	if stateData == nil {
		errors = append(errors, "State data must be a dictionary")
	}

	if stateJSON, err := value_objects.PyJSONDumps(stateData, -1); err != nil {
		errors = append(errors, "State data must be JSON serializable")
	} else if len(stateJSON) > 1_000_000 {
		errors = append(errors, "State data too large (max 1MB)")
	}

	return len(errors) == 0, errors
}

// ValidateContextData ports validate_context_data.
func (s *ContextValidationService) ValidateContextData(level value_objects.ContextLevel, data map[string]any) (*entities.OrderedMap[any], error) {
	errors := []string{}

	switch level {
	case value_objects.ContextLevelTask:
		if v, ok := data["title"]; ok {
			empty, err := ctxStripIsEmpty(v)
			if err != nil {
				return nil, err
			}
			if empty {
				errors = append(errors, "Task title cannot be empty")
			}
		}
		if v, ok := data["status"]; ok {
			if !ctxStringIn(v, []string{"todo", "in_progress", "blocked", "review", "testing", "done", "cancelled"}) {
				errors = append(errors, "Invalid task status")
			}
		}
		if v, ok := data["priority"]; ok {
			if !ctxStringIn(v, []string{"low", "medium", "high", "urgent", "critical"}) {
				errors = append(errors, "Invalid task priority")
			}
		}
	case value_objects.ContextLevelProject:
		if v, ok := data["name"]; ok {
			empty, err := ctxStripIsEmpty(v)
			if err != nil {
				return nil, err
			}
			if empty {
				errors = append(errors, "Project name cannot be empty")
			}
		}
	case value_objects.ContextLevelBranch:
		if v, ok := data["name"]; ok {
			empty, err := ctxStripIsEmpty(v)
			if err != nil {
				return nil, err
			}
			if empty {
				errors = append(errors, "Branch name cannot be empty")
			}
		}
	case value_objects.ContextLevelGlobal:
		// Global level requirements (minimal validation).
	}

	if v, ok := data["completion_percentage"]; ok {
		if !ctxIsNumber(v) || ctxFloat(v) < 0 || ctxFloat(v) > 100 {
			errors = append(errors, "completion_percentage must be a number between 0 and 100")
		}
	}

	if v, ok := data["vision_alignment_score"]; ok {
		if !ctxIsNumber(v) || ctxFloat(v) < 0 || ctxFloat(v) > 1 {
			errors = append(errors, "vision_alignment_score must be a number between 0 and 1")
		}
	}

	if v, ok := data["labels"]; ok {
		if !ctxIsList(v) {
			errors = append(errors, "labels must be a list")
		}
	}

	if v, ok := data["assignees"]; ok {
		if !ctxIsList(v) {
			errors = append(errors, "assignees must be a list")
		}
	}

	out := entities.NewOrderedMap[any]()
	out.Set("valid", len(errors) == 0)
	out.Set("errors", errors)
	return out, nil
}

// ctxStripIsEmpty is `not data[key].strip()`: a non-string raises AttributeError in
// Python (the caller reports it as the error response).
func ctxStripIsEmpty(v any) (bool, error) {
	str, ok := v.(string)
	if !ok {
		return false, &value_objects.TypeError{Msg: "'" + ctxPyTypeName(v) + "' object has no attribute 'strip'"}
	}
	return strings.TrimSpace(str) == "", nil
}

func ctxPyTypeName(v any) string {
	switch v.(type) {
	case nil:
		return "NoneType"
	case bool:
		return "bool"
	case float32, float64:
		return "float"
	case []any, []string:
		return "list"
	case *entities.OrderedMap[any], map[string]any:
		return "dict"
	}
	return "int"
}

func ctxIsNumber(v any) bool {
	switch v.(type) {
	case bool, int, int8, int16, int32, int64, uint, uint8, uint16, uint32, uint64, float32, float64:
		return true
	}
	return false
}

func ctxFloat(v any) float64 {
	switch n := v.(type) {
	case bool:
		if n {
			return 1
		}
		return 0
	case int:
		return float64(n)
	case int8:
		return float64(n)
	case int16:
		return float64(n)
	case int32:
		return float64(n)
	case int64:
		return float64(n)
	case uint:
		return float64(n)
	case uint8:
		return float64(n)
	case uint16:
		return float64(n)
	case uint32:
		return float64(n)
	case uint64:
		return float64(n)
	case float32:
		return float64(n)
	case float64:
		return n
	}
	return 0
}

func ctxIsList(v any) bool {
	switch v.(type) {
	case []any, []string:
		return true
	}
	return false
}

func ctxStringIn(v any, allowed []string) bool {
	s, ok := v.(string)
	if !ok {
		return false
	}
	for _, a := range allowed {
		if s == a {
			return true
		}
	}
	return false
}
