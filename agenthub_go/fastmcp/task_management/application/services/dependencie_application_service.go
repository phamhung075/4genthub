package services

import (
	"context"

	"agenthub/fastmcp/task_management/application/dtos/dependency"
	"agenthub/fastmcp/task_management/application/use_cases"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
)

// DependencieApplicationService ports dependencie_application_service.DependencieApplicationService.
type DependencieApplicationService struct {
	taskRepository repositories.TaskRepository
	userID         *string

	addDependencyUseCase     *use_cases.AddDependencyUseCase
	removeDependencyUseCase  *use_cases.RemoveDependencyUseCase
	getDependenciesUseCase   *use_cases.GetDependenciesUseCase
	clearDependenciesUseCase *use_cases.ClearDependenciesUseCase
	getBlockingTasksUseCase  *use_cases.GetBlockingTasksUseCase
}

// NewDependencieApplicationService builds the service. userID nil mirrors Python None.
func NewDependencieApplicationService(taskRepository repositories.TaskRepository, userID *string) *DependencieApplicationService {
	return &DependencieApplicationService{taskRepository: taskRepository, userID: userID}
}

// WithUser mirrors with_user(user_id): a new service sharing the repository.
func (s *DependencieApplicationService) WithUser(userID string) *DependencieApplicationService {
	return NewDependencieApplicationService(s.taskRepository, &userID)
}

// userScopedRepository mirrors _get_user_scoped_repository: the Go repository
// interfaces expose no with_user/user_id/session attributes, so it is unchanged.
func (s *DependencieApplicationService) userScopedRepository() repositories.TaskRepository {
	return s.taskRepository
}

// AddDependency ports add_dependency.
func (s *DependencieApplicationService) AddDependency(ctx context.Context, request *dependency.AddDependencyRequest) (*dependency.DependencyResponse, error) {
	if s.addDependencyUseCase == nil {
		s.addDependencyUseCase = use_cases.NewAddDependencyUseCase(s.userScopedRepository())
	}
	return s.addDependencyUseCase.Execute(ctx, request)
}

// RemoveDependency ports remove_dependency. The existing Go RemoveDependencyUseCase
// returns the use_cases.DependencyResponse shape, so the service does too.
func (s *DependencieApplicationService) RemoveDependency(ctx context.Context, taskID, dependencyID string) (*use_cases.DependencyResponse, error) {
	if s.removeDependencyUseCase == nil {
		s.removeDependencyUseCase = use_cases.NewRemoveDependencyUseCase(s.userScopedRepository())
	}
	return s.removeDependencyUseCase.Execute(ctx, taskID, dependencyID)
}

// GetDependencies ports get_dependencies.
func (s *DependencieApplicationService) GetDependencies(ctx context.Context, taskID string) (*entities.OrderedMap[any], error) {
	if s.getDependenciesUseCase == nil {
		s.getDependenciesUseCase = use_cases.NewGetDependenciesUseCase(s.userScopedRepository())
	}
	return s.getDependenciesUseCase.Execute(ctx, taskID)
}

// ClearDependencies ports clear_dependencies.
func (s *DependencieApplicationService) ClearDependencies(ctx context.Context, taskID string) (*dependency.DependencyResponse, error) {
	if s.clearDependenciesUseCase == nil {
		s.clearDependenciesUseCase = use_cases.NewClearDependenciesUseCase(s.userScopedRepository())
	}
	return s.clearDependenciesUseCase.Execute(ctx, taskID)
}

// GetBlockingTasks ports get_blocking_tasks.
func (s *DependencieApplicationService) GetBlockingTasks(ctx context.Context, taskID string) (*entities.OrderedMap[any], error) {
	if s.getBlockingTasksUseCase == nil {
		s.getBlockingTasksUseCase = use_cases.NewGetBlockingTasksUseCase(s.userScopedRepository())
	}
	return s.getBlockingTasksUseCase.Execute(ctx, taskID)
}
