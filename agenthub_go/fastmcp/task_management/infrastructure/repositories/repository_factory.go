package repositories

// Central Repository Factory (Python infrastructure/repositories/repository_factory.py):
// environment-based repository selection. The Go form carries the environment and session
// manager on an instance. Mock construction goes through injectable hooks; when a hook is
// missing the caller gets a ConfigurationException instead. The Python `sys.exit(1)` for an
// unknown database type becomes an error (the supported types are validated before reaching
// it, so the path is unreachable).

import (
	"os"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	domainrepos "agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// RepositoryFactory is Python's RepositoryFactory. The Python classmethods are methods on an
// instance here, since they need the session manager.
type RepositoryFactory struct {
	Sessions *database.SessionManager
	Getenv   func(string) string

	MockTaskRepositoryFactory      func() domainrepos.TaskRepository
	MockProjectRepositoryFactory   func() domainrepos.ProjectRepository
	MockGitBranchRepositoryFactory func() domainrepos.GitBranchRepository
	MockSubtaskRepositoryFactory   func() domainrepos.SubtaskRepository
	MockAgentRepositoryFactory     func() domainrepos.AgentRepository
	MockContextRepositoryFactory   func() any
}

// NewRepositoryFactory builds the factory.
func NewRepositoryFactory(sessions *database.SessionManager, getenv func(string) string) *RepositoryFactory {
	if getenv == nil {
		getenv = os.Getenv
	}
	return &RepositoryFactory{Sessions: sessions, Getenv: getenv}
}

// GetEnvironmentConfig is get_environment_config.
func (f *RepositoryFactory) GetEnvironmentConfig() (*entities.OrderedMap[any], error) {
	return GetRepositoryConfig()
}

func repositoryFactoryConfigString(config *entities.OrderedMap[any], key string) string {
	v, ok := config.Get(key)
	if !ok {
		return ""
	}
	s, _ := v.(string)
	return s
}

// GetTaskRepository creates the task repository for the environment.
func (f *RepositoryFactory) GetTaskRepository(projectID, gitBranchName, userID *string) (domainrepos.TaskRepository, error) {
	config, err := f.GetEnvironmentConfig()
	if err != nil {
		return nil, err
	}
	environment := repositoryFactoryConfigString(config, "environment")
	databaseType := repositoryFactoryConfigString(config, "database_type")

	if environment == "test" {
		if f.MockTaskRepositoryFactory == nil {
			return nil, exceptions.NewConfigurationException("MockTaskRepository is not available", "")
		}
		return f.MockTaskRepositoryFactory(), nil
	}

	var base domainrepos.TaskRepository
	switch databaseType {
	case "sqlite", "supabase", "postgresql":
		base, err = NewORMTaskRepository(f.Sessions, nil, projectID, gitBranchName, userID, false)
		if err != nil {
			return nil, err
		}
	}
	if base == nil {
		return nil, exceptions.NewConfigurationException(
			"Failed to create repository for database type: "+databaseType, "")
	}
	return base, nil
}

// GetProjectRepository creates the project repository for the environment.
func (f *RepositoryFactory) GetProjectRepository() (domainrepos.ProjectRepository, error) {
	config, err := f.GetEnvironmentConfig()
	if err != nil {
		return nil, err
	}
	if repositoryFactoryConfigString(config, "environment") == "test" {
		if f.MockProjectRepositoryFactory == nil {
			return nil, exceptions.NewConfigurationException("MockProjectRepository is not available", "")
		}
		return f.MockProjectRepositoryFactory(), nil
	}
	return NewORMProjectRepository(f.Sessions, nil)
}

// GetGitBranchRepository creates the git branch repository for the environment.
func (f *RepositoryFactory) GetGitBranchRepository(userID *string) (domainrepos.GitBranchRepository, error) {
	config, err := f.GetEnvironmentConfig()
	if err != nil {
		return nil, err
	}
	if repositoryFactoryConfigString(config, "environment") == "test" {
		if f.MockGitBranchRepositoryFactory == nil {
			return nil, exceptions.NewConfigurationException("MockGitBranchRepository is not available", "")
		}
		return f.MockGitBranchRepositoryFactory(), nil
	}
	return NewORMGitBranchRepository(f.Sessions, userID, false)
}

// GetSubtaskRepository creates the subtask repository for the environment.
func (f *RepositoryFactory) GetSubtaskRepository(userID *string) (domainrepos.SubtaskRepository, error) {
	config, err := f.GetEnvironmentConfig()
	if err != nil {
		return nil, err
	}
	if repositoryFactoryConfigString(config, "environment") == "test" {
		if f.MockSubtaskRepositoryFactory == nil {
			return nil, exceptions.NewConfigurationException("MockSubtaskRepository is not available", "")
		}
		return f.MockSubtaskRepositoryFactory(), nil
	}
	return NewORMSubtaskRepository(f.Sessions, userID)
}

// GetAgentRepository creates the agent repository for the environment.
func (f *RepositoryFactory) GetAgentRepository() (domainrepos.AgentRepository, error) {
	config, err := f.GetEnvironmentConfig()
	if err != nil {
		return nil, err
	}
	if repositoryFactoryConfigString(config, "environment") == "test" {
		if f.MockAgentRepositoryFactory == nil {
			return nil, exceptions.NewConfigurationException("MockAgentRepository is not available", "")
		}
		return f.MockAgentRepositoryFactory(), nil
	}
	return NewORMAgentRepository(f.Sessions, nil, nil)
}

// GetContextRepository creates the (task) context repository for the environment.
func (f *RepositoryFactory) GetContextRepository() (any, error) {
	config, err := f.GetEnvironmentConfig()
	if err != nil {
		return nil, err
	}
	if repositoryFactoryConfigString(config, "environment") == "test" {
		if f.MockContextRepositoryFactory != nil {
			return f.MockContextRepositoryFactory(), nil
		}
		return NewMockTaskContextRepository(), nil
	}
	return NewTaskContextRepository(f.Sessions, nil)
}
