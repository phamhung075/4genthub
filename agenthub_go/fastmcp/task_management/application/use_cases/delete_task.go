package use_cases

import (
	"context"
	"fmt"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/services"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// DeleteTaskUseCase ports delete_task.DeleteTaskUseCase.
type DeleteTaskUseCase struct {
	taskRepository services.CascadeTaskRepository
	cascadeService *services.CascadeDeletionService
}

// NewDeleteTaskUseCase builds the use case and its cascade deletion service.
// Python's unused db_session_factory and logging_service arguments are dropped
// (logging calls are dropped and the session factory is never used).
func NewDeleteTaskUseCase(taskRepository services.CascadeTaskRepository,
	subtaskRepository services.CascadeSubtaskRepository,
	branchRepository services.CascadeBranchRepository,
	projectRepository services.CascadeProjectRepository,
	contextRepository services.CascadeContextRepository) *DeleteTaskUseCase {
	return &DeleteTaskUseCase{
		taskRepository: taskRepository,
		cascadeService: services.NewCascadeDeletionService(taskRepository, subtaskRepository,
			branchRepository, projectRepository, contextRepository),
	}
}

// Execute deletes a task with cascade deletion.
func (uc *DeleteTaskUseCase) Execute(ctx context.Context, taskID any, cascade bool,
	userID *string) (*entities.OrderedMap[any], error) {

	taskIDStr := value_objects.PyStr(taskID)
	domainTaskID, err := useCaseTaskID(taskID)
	if err != nil {
		return nil, err
	}

	task, err := uc.taskRepository.FindByID(ctx, domainTaskID)
	if err != nil {
		return nil, err
	}
	if task == nil {
		out := entities.NewOrderedMap[any]()
		out.Set("success", false)
		out.Set("task_deleted", false)
		out.Set("message", fmt.Sprintf("Task %s not found", taskIDStr))
		return out, nil
	}

	taskTitle := task.Title
	gitBranchID := task.GitBranchID

	scope := services.DeleteScopeTaskOnly
	if cascade {
		scope = services.DeleteScopeTaskFull
	}
	stats, err := uc.cascadeService.DeleteTaskCascade(ctx, taskIDStr, scope)
	if err != nil {
		return nil, err
	}

	if stats["task_deleted"] == true {
		// delete_task.py calls dispatch_domain_event(event) with a single argument
		// while the function requires (event_type, event_data); it raises TypeError,
		// which the surrounding except swallows. No event is ever dispatched.
		_ = gitBranchID
	}

	out := entities.NewOrderedMap[any]()
	out.Set("success", stats["task_deleted"])
	out.Set("title", taskTitle)
	out.Set("task_deleted", stats["task_deleted"])
	out.Set("subtasks_deleted", stats["subtasks_deleted"])
	out.Set("contexts_deleted", stats["contexts_deleted"])
	out.Set("events_dispatched", stats["events_dispatched"])
	return out, nil
}
