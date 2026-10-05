package use_cases

import (
	"context"
	"fmt"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/services"
)

// DeleteBranchUseCase ports delete_branch.DeleteBranchUseCase.
type DeleteBranchUseCase struct {
	taskRepository   services.CascadeTaskRepository
	branchRepository services.CascadeBranchRepository
	projectRepo      services.CascadeProjectRepository
	cascadeService   *services.CascadeDeletionService
}

// NewDeleteBranchUseCase builds the use case and its cascade deletion service.
// Python's unused db_session_factory and logging_service arguments are dropped.
func NewDeleteBranchUseCase(taskRepository services.CascadeTaskRepository,
	subtaskRepository services.CascadeSubtaskRepository,
	branchRepository services.CascadeBranchRepository,
	projectRepository services.CascadeProjectRepository,
	contextRepository services.CascadeContextRepository) *DeleteBranchUseCase {
	return &DeleteBranchUseCase{
		taskRepository:   taskRepository,
		branchRepository: branchRepository,
		projectRepo:      projectRepository,
		cascadeService: services.NewCascadeDeletionService(taskRepository, subtaskRepository,
			branchRepository, projectRepository, contextRepository),
	}
}

// Execute deletes a branch with cascade deletion.
func (uc *DeleteBranchUseCase) Execute(ctx context.Context, branchID string) (*entities.OrderedMap[any], error) {
	branch, err := uc.branchRepository.FindByID(ctx, branchID)
	if err != nil {
		return nil, err
	}
	if branch == nil {
		out := entities.NewOrderedMap[any]()
		out.Set("success", false)
		out.Set("branch_deleted", false)
		out.Set("message", fmt.Sprintf("Branch %s not found", branchID))
		return out, nil
	}

	projectID := branch.ProjectID

	stats, err := uc.cascadeService.DeleteBranchCascade(ctx, branchID)
	if err != nil {
		return nil, err
	}

	// _send_websocket_notification is dropped: no WebSocketService exists in the Go
	// port.
	if stats["branch_deleted"] == true && projectID != "" {
		// _update_project_statistics computes fresh statistics and then calls
		// ProjectStatisticsUpdatedEvent.create, which does not exist; the
		// AttributeError is caught and swallowed, so no event is ever dispatched and
		// the result is never observed. It is not reproduced.
	}

	out := entities.NewOrderedMap[any]()
	out.Set("success", stats["branch_deleted"])
	out.Set("branch_deleted", stats["branch_deleted"])
	out.Set("tasks_deleted", stats["tasks_deleted"])
	out.Set("subtasks_deleted", stats["subtasks_deleted"])
	out.Set("contexts_deleted", stats["contexts_deleted"])
	out.Set("events_dispatched", stats["events_dispatched"])
	return out, nil
}
