package factories

import (
	"context"
	"testing"

	"agenthub/fastmcp/task_management/application/services"
	"agenthub/fastmcp/task_management/domain/repositories"
)

// providerBackendStub is services.RepositoryProviderBackend with every
// constructor answered, so a facade factory whose builder seam is unwired
// reaches its builder guard instead of failing on a missing repository.
type providerBackendStub struct{}

func (providerBackendStub) NewTaskRepositoryFactory() services.RepositoryProviderTaskFactoryPort {
	return taskRepositoryFactoryStub{}
}

func (providerBackendStub) NewORMTaskRepository(any, *string, *string, string, *string) (repositories.TaskRepository, error) {
	return nil, nil
}

func (providerBackendStub) NewSubtaskRepositoryFactory() services.RepositoryProviderSubtaskFactoryPort {
	return subtaskRepositoryFactoryStub{}
}

func (providerBackendStub) CreateProjectRepository(*string) (repositories.ProjectRepository, error) {
	return nil, nil
}

func (providerBackendStub) NewAgentRepositoryFactory() services.RepositoryProviderAgentFactoryPort {
	return agentRepositoryFactoryStub{}
}

func (providerBackendStub) CreateGitBranchRepository(*string) (repositories.GitBranchRepository, error) {
	return nil, nil
}

func (providerBackendStub) NewGlobalContextRepository(any) (repositories.ContextRepository, error) {
	return nil, nil
}

func (providerBackendStub) NewProjectContextRepository(any) (repositories.ContextRepository, error) {
	return nil, nil
}

func (providerBackendStub) NewBranchContextRepository(any) (repositories.ContextRepository, error) {
	return nil, nil
}

func (providerBackendStub) NewTaskContextRepository(any) (repositories.ContextRepository, error) {
	return nil, nil
}

func (providerBackendStub) NewTokenRepository(any) (repositories.ITokenRepository, error) {
	return nil, nil
}

type taskRepositoryFactoryStub struct{}

func (taskRepositoryFactoryStub) CreateRepository(string, string, *string) (repositories.TaskRepository, error) {
	return nil, nil
}

type subtaskRepositoryFactoryStub struct{}

func (subtaskRepositoryFactoryStub) CreateORMSubtaskRepository(*string) (repositories.SubtaskRepository, error) {
	return nil, nil
}

func (subtaskRepositoryFactoryStub) CreateSubtaskRepository(string, string, *string) (repositories.SubtaskRepository, error) {
	return nil, nil
}

type agentRepositoryFactoryStub struct{}

func (agentRepositoryFactoryStub) CreateRepository(any) (repositories.AgentRepository, error) {
	return nil, nil
}

// TestFacadeBuilderGuardNamesTheMissingWiring pins the message each facade
// factory answers when its builder seam was never wired. The three facades ARE
// ported (project/git_branch/task application facades), so the message must name
// the missing wiring rather than claiming the facade has no Go port.
func TestFacadeBuilderGuardNamesTheMissingWiring(t *testing.T) {
	services.SetRepositoryProviderBackend(func() services.RepositoryProviderBackend {
		return providerBackendStub{}
	})
	defer services.SetRepositoryProviderBackend(nil)
	provider := services.RepositoryProviderService{}.GetInstance()

	user := "user-1"
	project := "project-1"

	t.Run("project facade", func(t *testing.T) {
		factory := &ProjectFacadeFactory{repositoryProvider: provider, facadesCache: map[string]any{}}
		_, err := factory.CreateProjectFacade(context.Background(), user)
		if err == nil || err.Error() != "ProjectFacadeBuilder is not wired: set it at server composition" {
			t.Fatalf("err = %v", err)
		}
	})

	t.Run("git branch facade", func(t *testing.T) {
		factory := &GitBranchFacadeFactory{facadesCache: map[string]any{}}
		_, err := factory.CreateFacade(context.Background(), &project, &user)
		if err == nil || err.Error() != "GitBranchFacadeBuilder is not wired: set it at server composition" {
			t.Fatalf("err = %v", err)
		}
	})

	t.Run("task facade", func(t *testing.T) {
		factory := &TaskFacadeFactory{repositoryProvider: provider}
		_, err := factory.CreateTaskFacade(context.Background(), nil, nil, &user)
		if err == nil || err.Error() != "TaskFacadeBuilder is not wired: set it at server composition" {
			t.Fatalf("err = %v", err)
		}
	})
}
