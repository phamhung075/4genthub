// Subtask Facade Factory (Python
// task_management/application/factories/subtask_facade_factory.py).
//
// CRITICAL FIX preserved: GitHub branch context is NOT derived here; task_id is accepted
// by create_facade and ignored when creating the repositories, exactly as in Python.
package factories

import (
	"agenthub/fastmcp/task_management/application/facades"
	"agenthub/fastmcp/task_management/application/services"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// subtaskFacadeFactoryInstance is the class-level `_instance`.
var subtaskFacadeFactoryInstance *SubtaskFacadeFactory

// SubtaskFacadeFactory mirrors subtask_facade_factory.SubtaskFacadeFactory.
type SubtaskFacadeFactory struct {
	repositoryProvider *services.RepositoryProviderService
}

// GetInstance mirrors the get_instance classmethod.
func (f *SubtaskFacadeFactory) GetInstance() *SubtaskFacadeFactory {
	factoriesMu.Lock()
	defer factoriesMu.Unlock()
	if subtaskFacadeFactoryInstance == nil {
		subtaskFacadeFactoryInstance = &SubtaskFacadeFactory{repositoryProvider: services.RepositoryProviderService{}.GetInstance()}
	}
	return subtaskFacadeFactoryInstance
}

// NewSubtaskFacadeFactory mirrors __init__.
func NewSubtaskFacadeFactory(repositoryProvider *services.RepositoryProviderService) *SubtaskFacadeFactory {
	return &SubtaskFacadeFactory{repositoryProvider: repositoryProvider}
}

// CreateFacade mirrors create_facade (the git_branch_id argument is ignored, as in Python).
func (f *SubtaskFacadeFactory) CreateFacade(session any, projectID, gitBranchID, userID, taskID *string) (*facades.SubtaskApplicationFacade, error) {
	return f.CreateSubtaskFacade(session, projectID, userID, taskID)
}

// CreateSubtaskFacade mirrors create_subtask_facade.
func (f *SubtaskFacadeFactory) CreateSubtaskFacade(session any, projectID, userID, taskID *string) (*facades.SubtaskApplicationFacade, error) {
	taskRepository, err := f.repositoryProvider.GetTaskRepository(projectID, nil, userID, session)
	if err != nil {
		return nil, err
	}
	subtaskRepository, err := f.repositoryProvider.GetSubtaskRepository(projectID, nil, userID, session)
	if err != nil {
		return nil, err
	}
	facadeTaskRepository, ok := taskRepository.(facades.FacadeTaskRepository)
	if !ok {
		return nil, &value_objects.ValueError{Msg: "task repository does not satisfy FacadeTaskRepository"}
	}
	return facades.NewSubtaskApplicationFacade(facadeTaskRepository, subtaskRepository, nil, nil, userID), nil
}
