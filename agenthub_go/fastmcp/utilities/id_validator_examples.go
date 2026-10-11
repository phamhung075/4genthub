// Package utilities ports fastmcp/utilities.
package utilities

import (
	"fmt"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// --- Minimal facade interfaces (the real facade service is ported in
// application/services/facade_service.go) ---------------------------------------------

// FacadeService mirrors the duck-typed facade service used by the examples.
type FacadeService interface {
	GetTaskFacade(userID string) TaskFacade
	GetSubtaskFacade(userID, gitBranchID string) SubtaskFacade
}

// TaskFacade is the task facade returned by FacadeService.GetTaskFacade.
type TaskFacade interface {
	GetTask(taskID string) *entities.OrderedMap[any]
}

// SubtaskFacade is the result of FacadeService.GetSubtaskFacade. The Python example's
// MockSubtaskFacade has no methods, so this is an empty interface.
type SubtaskFacade interface{}

// oaGetSuccess is the truthiness of task_response.get("success").
func oaGetSuccess(m *entities.OrderedMap[any]) bool {
	v, _ := m.Get("success")
	return oaTruthy(v)
}

// oaNestedDict is m.get(k1, {}).get(k2, {}) ... for dict-valued lookups.
func oaNestedDict(m *entities.OrderedMap[any], keys ...string) *entities.OrderedMap[any] {
	current := m
	for _, k := range keys {
		v, ok := current.Get(k)
		if !ok {
			return entities.NewOrderedMap[any]()
		}
		next, ok := v.(*entities.OrderedMap[any])
		if !ok {
			return entities.NewOrderedMap[any]()
		}
		current = next
	}
	return current
}

// oaStrPtr is kwargs.get(key) restricted to strings (missing/None -> nil).
func oaStrPtr(m *entities.OrderedMap[any], key string) *string {
	if m == nil {
		return nil
	}
	return oaOptString(m, key)
}

// --- SubtaskControllerExample --------------------------------------------------------

// SubtaskControllerExample mirrors SubtaskControllerExample.
type SubtaskControllerExample struct {
	facadeService FacadeService
	idValidator   *IDValidator
}

// NewSubtaskControllerExample mirrors SubtaskControllerExample(facade_service).
func NewSubtaskControllerExample(facadeService FacadeService) *SubtaskControllerExample {
	return &SubtaskControllerExample{
		facadeService: facadeService,
		idValidator:   NewIDValidator(true),
	}
}

// getFacadeForRequestWrong mirrors _get_facade_for_request_WRONG: it forwards task_id as
// git_branch_id (the critical bug).
func (c *SubtaskControllerExample) getFacadeForRequestWrong(taskID, userID string) SubtaskFacade {
	return c.facadeService.GetSubtaskFacade(userID, taskID)
}

// getFacadeForRequestFixed mirrors _get_facade_for_request_FIXED. Python's single outer
// try/except wraps every failure inside it as "Facade creation failed: ..."; the two
// steps before that try are not wrapped.
func (c *SubtaskControllerExample) getFacadeForRequestFixed(taskID, userID string) (SubtaskFacade, error) {
	// Step 1: validate parameters using IDValidator.
	if err := PreventIDConfusion(&taskID, nil, nil, &userID); err != nil {
		return nil, &value_objects.ValueError{Msg: "Invalid parameters: " + err.Error()}
	}

	// Step 2: validate task context specifically.
	taskValidation := c.idValidator.ValidateTaskContext(taskID, "")
	if !taskValidation.IsValid {
		return nil, &value_objects.ValueError{Msg: "Task validation failed: " + oaErrorText(taskValidation.ErrorMessage)}
	}

	// Step 3: look up the correct git_branch_id from task.
	taskFacade := c.facadeService.GetTaskFacade(userID)
	taskResponse := taskFacade.GetTask(taskID)

	if taskResponse == nil || !oaGetSuccess(taskResponse) {
		return nil, &value_objects.ValueError{Msg: "Facade creation failed: Task " + taskID + " not found or inaccessible"}
	}

	taskData := oaNestedDict(taskResponse, "data", "task")
	gitBranchID, _ := oaGet(taskData, "git_branch_id").(string)
	if gitBranchID == "" {
		return nil, &value_objects.ValueError{Msg: "Facade creation failed: Task " + taskID + " missing git_branch_id"}
	}

	// Step 4: validate that task_id != git_branch_id (critical check).
	contextValidation := c.idValidator.ValidateTaskContext(taskID, gitBranchID)
	if !contextValidation.IsValid {
		return nil, &value_objects.ValueError{
			Msg: "Facade creation failed: Parameter confusion detected: " + oaErrorText(contextValidation.ErrorMessage),
		}
	}

	// Step 5: final parameter validation before facade creation.
	if err := PreventIDConfusion(&taskID, &gitBranchID, nil, &userID); err != nil {
		return nil, &value_objects.ValueError{Msg: "Facade creation failed: " + err.Error()}
	}

	// Step 6: create facade with CORRECT git_branch_id.
	return c.facadeService.GetSubtaskFacade(userID, gitBranchID), nil
}

// --- FacadeServiceExample ------------------------------------------------------------

// FacadeServiceExample mirrors FacadeServiceExample.
type FacadeServiceExample struct {
	idValidator *IDValidator
}

// NewFacadeServiceExample mirrors FacadeServiceExample().
func NewFacadeServiceExample() *FacadeServiceExample {
	return &FacadeServiceExample{idValidator: NewIDValidator(true)}
}

// GetSubtaskFacadeWithValidation mirrors get_subtask_facade_with_validation. Python logs
// warnings and an info line but returns None.
func (f *FacadeServiceExample) GetSubtaskFacadeWithValidation(userID string, gitBranchID, projectID *string) error {
	validationResult := f.idValidator.ValidateParameterMapping(nil, gitBranchID, projectID, &userID)
	if !validationResult.IsValid {
		return &value_objects.ValueError{Msg: "Invalid facade parameters: " + oaErrorText(validationResult.ErrorMessage)}
	}
	return nil
}

// --- MCPControllerBaseExample --------------------------------------------------------

// MCPControllerBaseExample mirrors MCPControllerBaseExample.
type MCPControllerBaseExample struct {
	idValidator *IDValidator
}

// NewMCPControllerBaseExample mirrors MCPControllerBaseExample().
func NewMCPControllerBaseExample() *MCPControllerBaseExample {
	return &MCPControllerBaseExample{idValidator: NewIDValidator(true)}
}

// ValidateRequestParameters mirrors validate_request_parameters(**kwargs).
func (c *MCPControllerBaseExample) ValidateRequestParameters(kwargs *entities.OrderedMap[any]) ValidationResult {
	taskID := oaStrPtr(kwargs, "task_id")
	gitBranchID := oaStrPtr(kwargs, "git_branch_id")
	projectID := oaStrPtr(kwargs, "project_id")
	userID := oaStrPtr(kwargs, "user_id")
	return c.idValidator.ValidateParameterMapping(taskID, gitBranchID, projectID, userID)
}

// HandleRequestWithValidation mirrors handle_request_with_validation. The failure dict
// keeps key order success, error, message, suggestions.
func (c *MCPControllerBaseExample) HandleRequestWithValidation(action string, kwargs *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	if kwargs == nil {
		kwargs = entities.NewOrderedMap[any]()
	}
	validationResult := c.ValidateRequestParameters(kwargs)

	if !validationResult.IsValid {
		// kwargs.get("task_id", "unknown") with None rendered as "".
		confusedTaskID := "unknown"
		if taskIDVal, has := kwargs.Get("task_id"); has {
			if s, ok := taskIDVal.(string); ok {
				confusedTaskID = s
			} else {
				confusedTaskID = ""
			}
		}

		var message any
		if validationResult.ErrorMessage != nil {
			message = *validationResult.ErrorMessage
		}

		result := entities.NewOrderedMap[any]()
		result.Set("success", false)
		result.Set("error", "PARAMETER_VALIDATION_FAILED")
		result.Set("message", message)
		result.Set("suggestions", c.idValidator.SuggestFixForConfusion(
			confusedTaskID, "MCP controller "+action+" action"))
		return result
	}

	result := entities.NewOrderedMap[any]()
	result.Set("success", true)
	result.Set("message", "Request processed successfully")
	return result
}

// --- DatabaseConstraintExample -------------------------------------------------------

// DatabaseConstraintExample mirrors DatabaseConstraintExample (static-method holder).
type DatabaseConstraintExample struct{}

// CreateIDValidationConstraints mirrors create_id_validation_constraints.
func (DatabaseConstraintExample) CreateIDValidationConstraints() []string {
	return []string{`
            ALTER TABLE tasks
            ADD CONSTRAINT chk_task_id_uuid_format
            CHECK (id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$');
            `, `
            ALTER TABLE task_subtasks
            ADD CONSTRAINT chk_subtask_task_id_uuid_format
            CHECK (task_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$');
            `, `
            ALTER TABLE task_subtasks
            ADD CONSTRAINT fk_subtask_task_id
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE;
            `, `
            ALTER TABLE tasks
            ADD CONSTRAINT fk_task_git_branch_id
            FOREIGN KEY (git_branch_id) REFERENCES git_branches(id) ON DELETE CASCADE;
            `}
}

// ValidateExistingData mirrors validate_existing_data.
func (DatabaseConstraintExample) ValidateExistingData() []string {
	return []string{`
            SELECT ts.id as subtask_id, ts.task_id, t.id as actual_task_id
            FROM task_subtasks ts
            LEFT JOIN tasks t ON ts.task_id = t.id
            WHERE t.id IS NULL;
            `, `
            SELECT t.id as task_id, t.git_branch_id, gb.id as actual_branch_id
            FROM tasks t
            LEFT JOIN git_branches gb ON t.git_branch_id = gb.id
            WHERE gb.id IS NULL;
            `, `
            SELECT 'task_id_as_branch_id' as issue_type, COUNT(*) as count
            FROM tasks t1
            JOIN git_branches gb ON t1.id = gb.id
            UNION ALL
            SELECT 'branch_id_as_task_id' as issue_type, COUNT(*) as count
            FROM git_branches gb
            JOIN tasks t ON gb.id = t.id;
            `}
}

// --- Integration testing example -----------------------------------------------------

// idValidatorExamplesMockFacadeService mirrors the nested MockFacadeService.
type idValidatorExamplesMockFacadeService struct{}

func (idValidatorExamplesMockFacadeService) GetTaskFacade(userID string) TaskFacade {
	return idValidatorExamplesMockTaskFacade{}
}

func (idValidatorExamplesMockFacadeService) GetSubtaskFacade(userID, gitBranchID string) SubtaskFacade {
	return idValidatorExamplesMockSubtaskFacade{}
}

// idValidatorExamplesMockTaskFacade mirrors the nested MockTaskFacade.
type idValidatorExamplesMockTaskFacade struct{}

func (idValidatorExamplesMockTaskFacade) GetTask(taskID string) *entities.OrderedMap[any] {
	response := entities.NewOrderedMap[any]()
	response.Set("success", true)
	data := entities.NewOrderedMap[any]()
	task := entities.NewOrderedMap[any]()
	task.Set("id", taskID)
	task.Set("git_branch_id", "550e8400-e29b-41d4-a716-446655440001")
	data.Set("task", task)
	response.Set("data", data)
	return response
}

// idValidatorExamplesMockSubtaskFacade mirrors the nested MockSubtaskFacade (pass).
type idValidatorExamplesMockSubtaskFacade struct{}

// TestIntegrationExample mirrors test_integration_example. Note the Python example's
// user_id is not a UUID, so this returns false (the Python bug is preserved).
func TestIntegrationExample() bool {
	controller := NewSubtaskControllerExample(idValidatorExamplesMockFacadeService{})

	_, err := controller.getFacadeForRequestFixed(
		"550e8400-e29b-41d4-a716-446655440000",
		"user-550e8400-e29b-41d4-a716-446655440002",
	)
	if err != nil {
		fmt.Printf("❌ IDValidator integration failed: %v\n", err)
		return false
	}
	fmt.Println("✅ IDValidator integration successful - no parameter confusion detected")
	return true
}
