// Task Facade Factory (Python task_management/application/factories/task_facade_factory.py).
//
// Requires validated user authentication and obtains repositories from
// RepositoryProviderService. The context service factory (unified_context_facade_factory.py)
// and the TaskApplicationFacade constructor differ from the Python call shapes, so both are
// injectable hooks. The Python singleton pattern and its "context factory unavailable"
// fallback are preserved.
package factories

import (
	"agenthub/fastmcp/task_management/application/services"
	"agenthub/fastmcp/task_management/domain"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"errors"
)

// TaskContextFacadeFactory is the consumer-side port of the
// UnifiedContextFacadeFactory.create_facade.
type TaskContextFacadeFactory interface {
	CreateFacade(userID, projectID, gitBranchID *string) any
}

// TaskContextFacadeFactoryProvider constructs the context facade factory; an error is
// treated like the Python except branch and disables context integration.
var TaskContextFacadeFactoryProvider func() (TaskContextFacadeFactory, error)

// TaskFacadeBuilder builds the TaskApplicationFacade.
var TaskFacadeBuilder func(taskRepo repositories.TaskRepository, subtaskRepo repositories.SubtaskRepository,
	contextService any, gitBranchRepo repositories.GitBranchRepository, projectRepo repositories.ProjectRepository) (any, error)

// taskFacadeFactoryInstance is the class-level `_instance`.
var taskFacadeFactoryInstance *TaskFacadeFactory

// taskFacadeFactoryInitialized is the class-level `_initialized`.
var taskFacadeFactoryInitialized bool

// TaskFacadeFactory mirrors task_facade_factory.TaskFacadeFactory.
type TaskFacadeFactory struct {
	repositoryProvider    *services.RepositoryProviderService
	contextServiceFactory TaskContextFacadeFactory
}

// GetInstance mirrors the get_instance classmethod.
func (f *TaskFacadeFactory) GetInstance() *TaskFacadeFactory {
	return NewTaskFacadeFactory(services.RepositoryProviderService{}.GetInstance())
}

// NewTaskFacadeFactory mirrors __init__ (skips work when already initialized).
func NewTaskFacadeFactory(repositoryProvider *services.RepositoryProviderService) *TaskFacadeFactory {
	factoriesMu.Lock()
	defer factoriesMu.Unlock()
	if taskFacadeFactoryInitialized {
		return taskFacadeFactoryInstance
	}
	factory := &TaskFacadeFactory{repositoryProvider: repositoryProvider}
	if TaskContextFacadeFactoryProvider != nil {
		contextFactory, err := TaskContextFacadeFactoryProvider()
		if err == nil {
			factory.contextServiceFactory = contextFactory
		}
	}
	taskFacadeFactoryInitialized = true
	taskFacadeFactoryInstance = factory
	return factory
}

// CreateTaskFacade mirrors create_task_facade.
func (f *TaskFacadeFactory) CreateTaskFacade(session any, projectID, gitBranchID, userID *string) (any, error) {
	validated, err := domain.ValidateUserID(userID, "Task facade creation")
	if err != nil {
		return nil, err
	}

	var taskRepository repositories.TaskRepository
	if projectID == nil {
		taskRepository, err = f.repositoryProvider.GetTaskRepository(nil, nil, &validated, session)
	} else {
		taskRepository, err = f.repositoryProvider.GetTaskRepository(projectID, nil, &validated, session)
	}
	if err != nil {
		return nil, err
	}

	subtaskRepository, err := f.repositoryProvider.GetSubtaskRepository(projectID, nil, &validated, session)
	if err != nil {
		return nil, err
	}

	var contextService any
	if f.contextServiceFactory != nil {
		contextService = f.contextServiceFactory.CreateFacade(&validated, projectID, gitBranchID)
	}

	gitBranchRepository, err := f.repositoryProvider.GetGitBranchRepository(session, &validated)
	if err != nil {
		return nil, err
	}
	projectRepository, err := f.repositoryProvider.GetProjectRepository(&validated, session)
	if err != nil {
		return nil, err
	}

	if TaskFacadeBuilder == nil {
		return nil, &value_objects.ValueError{Msg: "TaskApplicationFacade is not ported"}
	}
	return TaskFacadeBuilder(taskRepository, subtaskRepository, contextService, gitBranchRepository, projectRepository)
}

// CreateTaskFacadeWithGitBranchID mirrors create_task_facade_with_git_branch_id.
func (f *TaskFacadeFactory) CreateTaskFacadeWithGitBranchID(session any, projectID, gitBranchName string, userID, gitBranchID *string) (any, error) {
	validated, err := domain.ValidateUserID(userID, "Task facade with git_branch_id creation")
	if err != nil {
		return nil, err
	}

	taskRepository, err := f.repositoryProvider.GetTaskRepository(&projectID, &gitBranchName, &validated, session)
	if err != nil {
		return nil, err
	}

	var subtaskRepository repositories.SubtaskRepository
	if projectID != "" {
		subtaskRepository, err = f.repositoryProvider.GetSubtaskRepository(&projectID, nil, &validated, session)
		if err != nil {
			return nil, err
		}
	}

	var contextService any
	if f.contextServiceFactory != nil {
		contextService = f.contextServiceFactory.CreateFacade(&validated, &projectID, gitBranchID)
	}

	gitBranchRepository, err := f.repositoryProvider.GetGitBranchRepository(session, &validated)
	if err != nil {
		return nil, err
	}
	projectRepository, err := f.repositoryProvider.GetProjectRepository(&validated, session)
	if err != nil {
		return nil, err
	}

	if TaskFacadeBuilder == nil {
		return nil, errors.New("TaskFacadeBuilder is not wired: set it at server composition")
	}
	return TaskFacadeBuilder(taskRepository, subtaskRepository, contextService, gitBranchRepository, projectRepository)
}
