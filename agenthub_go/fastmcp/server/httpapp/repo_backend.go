package httpapp

import (
	"errors"

	"agenthub/fastmcp/task_management/application/services"
	domainrepos "agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/infrastructure/database"
	infrarepos "agenthub/fastmcp/task_management/infrastructure/repositories"
)

// repoBackend is the infrastructure side of RepositoryProviderService.
type repoBackend struct{ sessions *database.SessionManager }

var _ services.RepositoryProviderBackend = repoBackend{}

// errContextRepositoryPort: the Go context repositories do not implement the legacy
// domain ContextRepository interface (AddInsight etc.); contexts are reached through the
// unified context service instead.
var errContextRepositoryPort = errors.New("context repositories are not available through RepositoryProviderService; use the unified context service")

type taskFactoryAdapter struct {
	f *infrarepos.TaskRepositoryFactory
}

func (a taskFactoryAdapter) CreateRepository(projectID, gitBranchName string, userID *string) (domainrepos.TaskRepository, error) {
	return a.f.CreateRepository(projectID, gitBranchName, userID)
}

func (b repoBackend) NewTaskRepositoryFactory() services.RepositoryProviderTaskFactoryPort {
	f, err := infrarepos.NewTaskRepositoryFactory(nil, nil, nil, b.sessions)
	if err != nil {
		panic(err)
	}
	return taskFactoryAdapter{f}
}

func (b repoBackend) NewORMTaskRepository(_ any, gitBranchID, projectID *string, gitBranchName string, userID *string) (domainrepos.TaskRepository, error) {
	return infrarepos.NewORMTaskRepository(b.sessions, gitBranchID, projectID, &gitBranchName, userID, false)
}

type subtaskFactoryAdapter struct {
	f *infrarepos.SubtaskRepositoryFactory
}

func (a subtaskFactoryAdapter) CreateORMSubtaskRepository(userID *string) (domainrepos.SubtaskRepository, error) {
	return a.f.CreateORMSubtaskRepository(userID)
}

func (a subtaskFactoryAdapter) CreateSubtaskRepository(projectID, gitBranchName string, userID *string) (domainrepos.SubtaskRepository, error) {
	return a.f.CreateSubtaskRepository(projectID, gitBranchName, userID)
}

func (b repoBackend) NewSubtaskRepositoryFactory() services.RepositoryProviderSubtaskFactoryPort {
	return subtaskFactoryAdapter{infrarepos.NewSubtaskRepositoryFactory(nil, nil, nil, b.sessions)}
}

func (b repoBackend) CreateProjectRepository(userID *string) (domainrepos.ProjectRepository, error) {
	return infrarepos.NewORMProjectRepository(b.sessions, userID)
}

type agentFactoryAdapter struct{ sessions *database.SessionManager }

func (a agentFactoryAdapter) CreateRepository(any) (domainrepos.AgentRepository, error) {
	return infrarepos.NewORMAgentRepository(a.sessions, nil, nil)
}

func (b repoBackend) NewAgentRepositoryFactory() services.RepositoryProviderAgentFactoryPort {
	return agentFactoryAdapter{b.sessions}
}

func (b repoBackend) CreateGitBranchRepository(userID *string) (domainrepos.GitBranchRepository, error) {
	return newGitBranchRepo(b.sessions, userID)
}

func (b repoBackend) NewGlobalContextRepository(any) (domainrepos.ContextRepository, error) {
	return nil, errContextRepositoryPort
}

func (b repoBackend) NewProjectContextRepository(any) (domainrepos.ContextRepository, error) {
	return nil, errContextRepositoryPort
}

func (b repoBackend) NewBranchContextRepository(any) (domainrepos.ContextRepository, error) {
	return nil, errContextRepositoryPort
}

func (b repoBackend) NewTaskContextRepository(any) (domainrepos.ContextRepository, error) {
	return nil, errContextRepositoryPort
}

func (b repoBackend) NewTokenRepository(any) (domainrepos.ITokenRepository, error) {
	return infrarepos.NewTokenRepository(b.sessions)
}
