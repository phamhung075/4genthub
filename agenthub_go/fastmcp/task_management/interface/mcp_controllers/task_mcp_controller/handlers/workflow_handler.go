package handlers

// Workflow Handler for Task MCP Controller
// (Python handlers/workflow_handler.py).
//
// The StandardResponseFormatter is ported as MCPResponseFormatter
// (interface/utils/response_formatter.go); it is declared as ResponseFormatter in
// search_handler.go. The context facade/factory are declared here as the minimal
// interfaces needed.

import (
	"context"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// ContextFacade is the subset of UnifiedContextFacade used by the workflow
// handler (Python UnifiedContextFacade.create_context).
type ContextFacade interface {
	CreateContext(ctx context.Context, level, contextID string, data *entities.OrderedMap[any], userID *string) (*entities.OrderedMap[any], error)
}

// ContextFacadeFactory is the minimal view of the context facade factory used by
// the tasks workflow handler (Python ContextFacadeFactory.create_facade).
type ContextFacadeFactory interface {
	CreateFacade(ctx context.Context, gitBranchID string) (ContextFacade, error)
}

// WorkflowHandler ports WorkflowHandler.
type WorkflowHandler struct {
	responseFormatter    ResponseFormatter
	contextFacadeFactory ContextFacadeFactory
}

// NewWorkflowHandler ports __init__(response_formatter, context_facade_factory=None).
func NewWorkflowHandler(responseFormatter ResponseFormatter, contextFacadeFactory ContextFacadeFactory) *WorkflowHandler {
	return &WorkflowHandler{
		responseFormatter:    responseFormatter,
		contextFacadeFactory: contextFacadeFactory,
	}
}

// CreateTaskContext ports create_task_context(task_id, task_data, git_branch_id).
func (h *WorkflowHandler) CreateTaskContext(ctx context.Context, taskID string, taskData *entities.OrderedMap[any], gitBranchID string) *entities.OrderedMap[any] {
	if h.contextFacadeFactory == nil {
		return errorMap("Context creation not available")
	}

	contextFacade, err := h.contextFacadeFactory.CreateFacade(ctx, gitBranchID)
	if err != nil {
		return errorMap("Failed to create task context: " + err.Error())
	}

	data := entities.NewOrderedMap[any]()
	data.Set("title", omGetOr(taskData, "title", nil))
	data.Set("description", omGetOr(taskData, "description", nil))
	data.Set("status", omGetOr(taskData, "status", nil))
	data.Set("priority", omGetOr(taskData, "priority", nil))
	data.Set("assignees", omGetOr(taskData, "assignees", []any{}))
	data.Set("labels", omGetOr(taskData, "labels", []any{}))
	data.Set("estimated_effort", omGetOr(taskData, "estimated_effort", nil))
	data.Set("due_date", omGetOr(taskData, "due_date", nil))

	result, err := contextFacade.CreateContext(ctx, "task", taskID, data, nil)
	if err != nil {
		return errorMap("Failed to create task context: " + err.Error())
	}
	return result
}

// EnrichTaskResponse ports enrich_task_response(response, action, task_data=None).
func (h *WorkflowHandler) EnrichTaskResponse(response *entities.OrderedMap[any], action string, taskData *entities.OrderedMap[any]) (out *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			out = response
		}
	}()

	successVal, _ := response.Get("success")
	if !value_objects.PyTruthy(successVal) || taskData == nil {
		return response
	}

	statusAny, ok := taskData.Get("status")
	status := "pending"
	if ok && statusAny != nil {
		if s, isStr := statusAny.(string); isStr {
			status = s
		}
	}
	priorityAny, ok := taskData.Get("priority")
	priority := "medium"
	if ok && priorityAny != nil {
		if s, isStr := priorityAny.(string); isStr {
			priority = s
		}
	}

	workflowGuidance := h.generateWorkflowGuidance(status, priority, action)
	if workflowGuidance != nil {
		response.Set("workflow_guidance", workflowGuidance)
	}
	return response
}

// generateWorkflowGuidance ports _generate_workflow_guidance.
func (h *WorkflowHandler) generateWorkflowGuidance(status, priority, action string) *entities.OrderedMap[any] {
	statusGuidance := getStatusGuidance(status)
	priorityGuidance := getPriorityGuidance(priority)
	nextActions := getNextActions(status, action)

	guidance := entities.NewOrderedMap[any]()
	guidance.Set("status_guidance", strOrNil(statusGuidance))
	guidance.Set("priority_guidance", strOrNil(priorityGuidance))
	guidance.Set("next_actions", nextActions)

	if statusGuidance != nil || priorityGuidance != nil || len(nextActions) > 0 {
		return guidance
	}
	return nil
}

// getStatusGuidance ports _get_status_guidance.
func getStatusGuidance(status string) *string {
	statusGuidance := map[string]string{
		"pending":     "Task is ready to be worked on. Consider updating to 'in_progress' when starting work.",
		"in_progress": "Task is actively being worked on. Update progress regularly.",
		"completed":   "Task has been completed. Consider reviewing and archiving.",
		"blocked":     "Task is blocked. Identify and resolve blocking issues.",
		"cancelled":   "Task has been cancelled. Review if it should be reactivated.",
	}
	if v, ok := statusGuidance[value_objects.PyLower(status)]; ok {
		return &v
	}
	return nil
}

// getPriorityGuidance ports _get_priority_guidance.
func getPriorityGuidance(priority string) *string {
	priorityGuidance := map[string]string{
		"high":     "High priority task - consider working on this soon.",
		"critical": "Critical priority task - immediate attention required.",
		"medium":   "Medium priority task - normal workflow applies.",
		"low":      "Low priority task - can be deferred if higher priority work exists.",
	}
	if v, ok := priorityGuidance[value_objects.PyLower(priority)]; ok {
		return &v
	}
	return nil
}

// getNextActions ports _get_next_actions.
func getNextActions(status, action string) []string {
	var nextActions []string
	if action == "create" && status == "pending" {
		nextActions = append(nextActions,
			"Update task status to 'in_progress' when starting work",
			"Add more details or subtasks if needed",
			"Set assignees if working in a team",
		)
	} else if status == "in_progress" {
		nextActions = append(nextActions,
			"Update task progress regularly",
			"Add completion notes when finishing",
			"Mark as 'completed' when done",
		)
	} else if status == "completed" {
		nextActions = append(nextActions,
			"Review task completion",
			"Add testing notes if applicable",
			"Consider archiving the task",
		)
	}
	if nextActions == nil {
		nextActions = []string{}
	}
	return nextActions
}

// strOrNil stores an untyped nil for a nil *string so the ordered map holds
// Python None rather than a typed-nil pointer.
func strOrNil(s *string) any {
	if s == nil {
		return nil
	}
	return s
}

func errorMap(message string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	m.Set("error", message)
	return m
}

// omGetOr mirrors dict.get(key, default).
func omGetOr(m *entities.OrderedMap[any], key string, def any) any {
	if m == nil {
		return def
	}
	if v, ok := m.Get(key); ok {
		return v
	}
	return def
}
