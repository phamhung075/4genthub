package services

import (
	"context"

	subtaskdto "agenthub/fastmcp/task_management/application/dtos/subtask"
	usecases "agenthub/fastmcp/task_management/application/use_cases"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// SubtaskApplicationService ports
// application/services/subtask_application_service.SubtaskApplicationService.
type SubtaskApplicationService struct {
	taskRepository    repositories.TaskRepository
	subtaskRepository repositories.SubtaskRepository
	userID            *string

	addSubtaskUseCase      *usecases.AddSubtaskUseCase
	updateSubtaskUseCase   *usecases.UpdateSubtaskUseCase
	removeSubtaskUseCase   *usecases.RemoveSubtaskUseCase
	completeSubtaskUseCase *usecases.CompleteSubtaskUseCase
	getSubtasksUseCase     *usecases.GetSubtasksUseCase
	getSubtaskUseCase      *usecases.GetSubtaskUseCase
}

// NewSubtaskApplicationService mirrors __init__. Go repositories do not expose
// with_user/user_id/session attributes, so _get_user_scoped_repository returns the
// repository unchanged (same as the other ported application services).
func NewSubtaskApplicationService(taskRepository repositories.TaskRepository,
	subtaskRepository repositories.SubtaskRepository, userID *string) *SubtaskApplicationService {
	s := &SubtaskApplicationService{
		taskRepository:    taskRepository,
		subtaskRepository: subtaskRepository,
		userID:            userID,
	}
	s.addSubtaskUseCase = usecases.NewAddSubtaskUseCase(taskRepository, subtaskRepository)
	s.updateSubtaskUseCase = usecases.NewUpdateSubtaskUseCase(taskRepository, subtaskRepository)
	s.removeSubtaskUseCase = usecases.NewRemoveSubtaskUseCase(taskRepository, subtaskRepository)
	s.completeSubtaskUseCase = usecases.NewCompleteSubtaskUseCase(taskRepository, subtaskRepository)
	s.getSubtasksUseCase = usecases.NewGetSubtasksUseCase(taskRepository, subtaskRepository)
	s.getSubtaskUseCase = usecases.NewGetSubtaskUseCase(taskRepository, subtaskRepository)
	return s
}

// WithUser mirrors with_user.
func (s *SubtaskApplicationService) WithUser(userID string) *SubtaskApplicationService {
	return NewSubtaskApplicationService(s.taskRepository, s.subtaskRepository, &userID)
}

// AddSubtask mirrors add_subtask.
func (s *SubtaskApplicationService) AddSubtask(ctx context.Context, request *subtaskdto.AddSubtaskRequest) (*subtaskdto.SubtaskResponse, error) {
	return s.addSubtaskUseCase.Execute(ctx, request)
}

// RemoveSubtask mirrors remove_subtask.
func (s *SubtaskApplicationService) RemoveSubtask(ctx context.Context, taskID string, id string) (*entities.OrderedMap[any], error) {
	return s.removeSubtaskUseCase.Execute(ctx, taskID, id, nil)
}

// UpdateSubtask mirrors update_subtask.
func (s *SubtaskApplicationService) UpdateSubtask(ctx context.Context, request *subtaskdto.UpdateSubtaskRequest) (*subtaskdto.SubtaskResponse, error) {
	return s.updateSubtaskUseCase.Execute(ctx, request)
}

// CompleteSubtask mirrors complete_subtask.
func (s *SubtaskApplicationService) CompleteSubtask(ctx context.Context, taskID string, id string) (*entities.OrderedMap[any], error) {
	return s.completeSubtaskUseCase.Execute(ctx, taskID, id, nil, nil, nil, nil)
}

// GetSubtasks mirrors get_subtasks.
func (s *SubtaskApplicationService) GetSubtasks(ctx context.Context, taskID string) (*entities.OrderedMap[any], error) {
	return s.getSubtasksUseCase.Execute(ctx, taskID)
}

// GetSubtask mirrors get_subtask.
func (s *SubtaskApplicationService) GetSubtask(ctx context.Context, taskID string, id string) (*entities.OrderedMap[any], error) {
	return s.getSubtaskUseCase.Execute(ctx, taskID, id)
}

// zpSubtaskAppResponseDict mirrors Python `SubtaskResponse.__dict__`: all dataclass
// fields in declaration order.
func zpSubtaskAppResponseDict(r *subtaskdto.SubtaskResponse) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("task_id", r.TaskID)
	m.Set("subtask", r.Subtask)
	m.Set("progress", r.Progress)
	m.Set("agent_inheritance_applied", r.AgentInheritanceApplied)
	m.Set("inherited_assignees", r.InheritedAssignees)
	return m
}

// zpSubtaskAppStringSlice mirrors the list-vs-single assignee normalization.
func zpSubtaskAppStringSlice(v any) []string {
	if v == nil {
		return []string{}
	}
	if list, ok := v.([]any); ok {
		out := make([]string, 0, len(list))
		for _, e := range list {
			out = append(out, value_objects.PyStr(e))
		}
		return out
	}
	if list, ok := v.([]string); ok {
		return list
	}
	return []string{value_objects.PyStr(v)}
}

// zpSubtaskAppAnySlice mirrors the list-vs-single assignee normalization for
// UpdateSubtaskRequest, whose assignees field is untyped.
func zpSubtaskAppAnySlice(v any) []any {
	if v == nil {
		return nil
	}
	if list, ok := v.([]any); ok {
		return list
	}
	return []any{v}
}

// zpSubtaskAppStringPtr returns a *string when v is a string, else nil.
func zpSubtaskAppStringPtr(v any) *string {
	if s, ok := v.(string); ok {
		return &s
	}
	return nil
}

// zpSubtaskAppIntPtr mirrors int coercion of a JSON-decoded value.
func zpSubtaskAppIntPtr(v any) *int {
	switch n := v.(type) {
	case int:
		return &n
	case int64:
		i := int(n)
		return &i
	case float64:
		i := int(n)
		return &i
	}
	return nil
}

// ManageSubtasks mirrors manage_subtasks with enhanced DDD support.
func (s *SubtaskApplicationService) ManageSubtasks(ctx context.Context, taskID string, action string, subtaskData *entities.OrderedMap[any]) (*entities.OrderedMap[any], error) {
	get := func(key string) (any, bool) {
		if subtaskData == nil {
			return nil, false
		}
		return subtaskData.Get(key)
	}

	switch action {
	case "add_subtask", "add":
		assignees := []string{}
		if v, ok := get("assignees"); ok {
			assignees = zpSubtaskAppStringSlice(v)
		} else if v, ok := get("assignee"); ok && value_objects.PyTruthy(v) {
			assignees = []string{value_objects.PyStr(v)}
		}

		title, _ := get("title")
		description, _ := get("description")
		request, err := subtaskdto.NewAddSubtaskRequest(subtaskdto.AddSubtaskRequest{
			TaskID:      taskID,
			Title:       value_objects.PyStr(title),
			Description: value_objects.PyStr(description),
			Assignees:   assignees,
		})
		if err != nil {
			return nil, err
		}
		response, err := s.AddSubtask(ctx, request)
		if err != nil {
			return nil, err
		}
		return zpSubtaskAppResponseDict(response), nil

	case "complete_subtask", "complete":
		id, ok := get("id")
		if !ok || id == nil {
			return nil, &value_objects.ValueError{Msg: "id is required for completing a subtask"}
		}
		return s.CompleteSubtask(ctx, taskID, value_objects.PyStr(id))

	case "update_subtask", "update":
		var assignees []any
		if v, ok := get("assignees"); ok {
			assignees = zpSubtaskAppAnySlice(v)
		} else if v, ok := get("assignee"); ok && value_objects.PyTruthy(v) {
			assignees = []any{v}
		}

		statusValue, _ := get("status")
		status := zpSubtaskAppStringPtr(statusValue)
		if v, ok := get("completed"); ok && value_objects.PyTruthy(v) {
			completed := "completed"
			status = &completed
		}

		id, _ := get("id")
		title, _ := get("title")
		description, _ := get("description")
		priority, _ := get("priority")
		progress, _ := get("progress_percentage")

		request := &subtaskdto.UpdateSubtaskRequest{
			TaskID:             taskID,
			ID:                 id,
			Title:              zpSubtaskAppStringPtr(title),
			Description:        zpSubtaskAppStringPtr(description),
			Status:             status,
			Assignees:          assignees,
			Priority:           zpSubtaskAppStringPtr(priority),
			ProgressPercentage: zpSubtaskAppIntPtr(progress),
		}
		response, err := s.UpdateSubtask(ctx, request)
		if err != nil {
			return nil, err
		}
		return zpSubtaskAppResponseDict(response), nil

	case "remove_subtask", "remove":
		id, ok := get("id")
		if !ok || id == nil {
			return nil, &value_objects.ValueError{Msg: "id is required for removing a subtask"}
		}
		return s.RemoveSubtask(ctx, taskID, value_objects.PyStr(id))

	case "get_subtask", "get":
		id, ok := get("id")
		if !ok || id == nil {
			return nil, &value_objects.ValueError{Msg: "id is required for getting a subtask"}
		}
		return s.GetSubtask(ctx, taskID, value_objects.PyStr(id))

	case "list_subtasks", "list":
		return s.GetSubtasks(ctx, taskID)

	default:
		return nil, &value_objects.ValueError{Msg: "Unknown subtask action: " + action}
	}
}
