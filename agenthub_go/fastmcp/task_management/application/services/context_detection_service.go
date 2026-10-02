package services

import (
	"context"

	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// ContextDetectionService detects whether an ID is a project, git branch or task ID
// (Python application/services/context_detection_service.py). Python builds the
// repositories from RepositoryFactory; following the application-layer rule the Go
// port receives the three domain repository interfaces in the constructor.
type ContextDetectionService struct {
	projectRepository   repositories.ProjectRepository
	gitBranchRepository repositories.GitBranchRepository
	taskRepository      repositories.TaskRepository
}

// NewContextDetectionService mirrors __init__ with the repository dependencies injected.
func NewContextDetectionService(projectRepository repositories.ProjectRepository, gitBranchRepository repositories.GitBranchRepository, taskRepository repositories.TaskRepository) *ContextDetectionService {
	return &ContextDetectionService{
		projectRepository:   projectRepository,
		gitBranchRepository: gitBranchRepository,
		taskRepository:      taskRepository,
	}
}

// DetectIDType returns ("project"|"git_branch"|"task"|"unknown", projectID). An empty
// id returns ("unknown", nil); repository errors are swallowed like the Python
// try/except pass blocks.
func (s *ContextDetectionService) DetectIDType(ctx context.Context, contextID string) (string, *string) {
	if contextID == "" {
		return "unknown", nil
	}

	if s.projectRepository != nil {
		if project, err := s.projectRepository.FindByID(ctx, contextID); err == nil && project != nil {
			id := contextID
			return "project", &id
		}
	}

	if s.gitBranchRepository != nil {
		if branch, err := s.gitBranchRepository.FindByID(ctx, contextID, nil); err == nil && branch != nil {
			projectID := branch.ProjectID
			return "git_branch", &projectID
		}
	}

	if s.taskRepository != nil {
		if taskID, err := value_objects.NewTaskId(contextID); err == nil {
			if task, err := s.taskRepository.FindByID(ctx, taskID); err == nil && task != nil {
				if task.GitBranchID != nil && s.gitBranchRepository != nil {
					if branch, err := s.gitBranchRepository.FindByID(ctx, *task.GitBranchID, nil); err == nil && branch != nil {
						projectID := branch.ProjectID
						return "task", &projectID
					}
				}
			}
		}
	}

	return "unknown", nil
}

// GetContextLevelForID maps a detected ID type to the context level: project ->
// "project", git_branch/task -> "task", unknown -> "task".
func (s *ContextDetectionService) GetContextLevelForID(ctx context.Context, contextID string) string {
	idType, _ := s.DetectIDType(ctx, contextID)
	if idType == "project" {
		return "project"
	}
	if idType == "git_branch" || idType == "task" {
		return "task"
	}
	return "task"
}
