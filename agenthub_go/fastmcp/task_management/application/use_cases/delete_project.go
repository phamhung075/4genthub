package use_cases

import (
	"context"
	"errors"
	"fmt"
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/services"
)

// DeleteProjectUseCase ports delete_project.DeleteProjectUseCase.
type DeleteProjectUseCase struct {
	projectRepo    services.CascadeProjectRepository
	gitBranchRepo  services.CascadeBranchRepository
	taskRepo       services.CascadeTaskRepository
	contextRepo    services.CascadeContextRepository
	cascadeService *services.CascadeDeletionService
}

// NewDeleteProjectUseCase builds the use case; repositories are required.
func NewDeleteProjectUseCase(projectRepo services.CascadeProjectRepository,
	gitBranchRepo services.CascadeBranchRepository,
	taskRepo services.CascadeTaskRepository,
	contextRepo services.CascadeContextRepository) *DeleteProjectUseCase {
	return &DeleteProjectUseCase{
		projectRepo:   projectRepo,
		gitBranchRepo: gitBranchRepo,
		taskRepo:      taskRepo,
		contextRepo:   contextRepo,
		cascadeService: services.NewCascadeDeletionService(taskRepo, nil, gitBranchRepo,
			projectRepo, contextRepo),
	}
}

// Execute deletes a project with cascade deletion.
func (uc *DeleteProjectUseCase) Execute(ctx context.Context, projectID string,
	force bool) (*entities.OrderedMap[any], error) {

	project, err := uc.projectRepo.FindByID(ctx, projectID)
	if err != nil {
		return nil, deleteProjectWrapError(err)
	}
	if project == nil {
		return nil, exceptions.NewResourceNotFoundException("Project", projectID,
			fmt.Sprintf("Project %s not found", projectID))
	}

	projectName := project.Name

	if !force {
		if err := uc.validateDeletionSafety(ctx, project); err != nil {
			return nil, err
		}
	}

	stats, err := uc.cascadeService.DeleteProjectCascade(ctx, projectID)
	if err != nil {
		return nil, deleteProjectWrapError(err)
	}

	// _send_websocket_notification is dropped: no WebSocketService exists in the Go
	// port.
	_ = stats

	out := entities.NewOrderedMap[any]()
	out.Set("success", stats["project_deleted"])
	out.Set("message", fmt.Sprintf("Project '%s' and all related data deleted successfully", projectName))
	out.Set("statistics", useCaseOrderedFromMap(stats, []string{
		"project_deleted", "branches_deleted", "tasks_deleted", "subtasks_deleted",
		"contexts_deleted", "events_dispatched",
	}))
	return out, nil
}

// validateDeletionSafety raises a ValidationException when the project still has
// more than the empty main branch.
func (uc *DeleteProjectUseCase) validateDeletionSafety(ctx context.Context, project *entities.Project) error {
	branches, err := uc.gitBranchRepo.FindByProjectID(ctx, projectIDString(project))
	if err != nil {
		// Python logs a warning and lets validation pass.
		return nil
	}

	if len(branches) > 1 {
		names := make([]string, 0, len(branches))
		for _, b := range branches {
			names = append(names, b.Name)
		}
		message := fmt.Sprintf(
			"Cannot delete project with multiple branches (%d branches: %s). Delete other branches first, or use force=True",
			len(branches), strings.Join(names, ", "))
		return exceptions.NewValidationException(message, "project", project.ID)
	}

	if len(branches) == 1 {
		mainBranch := branches[0]
		if mainBranch.Name != "main" {
			message := fmt.Sprintf(
				"Cannot delete project with non-main branch '%s'. Project must have only 'main' branch, or use force=True",
				mainBranch.Name)
			return exceptions.NewValidationException(message, "project", project.ID)
		}
		mainBranchID := ""
		if mainBranch.ID != nil {
			mainBranchID = mainBranch.ID.Value
		}
		tasks, err := uc.taskRepo.FindByGitBranchID(ctx, mainBranchID)
		if err != nil {
			return nil
		}
		if len(tasks) > 0 {
			message := fmt.Sprintf(
				"Cannot delete project with %d tasks in main branch. Delete all tasks first, or use force=True",
				len(tasks))
			return exceptions.NewValidationException(message, "project", project.ID)
		}
	}

	return nil
}

// deleteProjectWrapError re-raises domain exceptions and wraps everything else in
// a DatabaseException, mirroring delete_project.execute's except clause.
func deleteProjectWrapError(err error) error {
	var notFound *exceptions.ResourceNotFoundException
	var validation *exceptions.ValidationException
	var database *exceptions.DatabaseException
	if errors.As(err, &notFound) || errors.As(err, &validation) || errors.As(err, &database) {
		return err
	}
	return exceptions.NewDatabaseException("Failed to delete project: "+err.Error(), "delete", "projects")
}

func projectIDString(project *entities.Project) string {
	if project.ID == nil {
		return "None"
	}
	return project.ID.Value
}
