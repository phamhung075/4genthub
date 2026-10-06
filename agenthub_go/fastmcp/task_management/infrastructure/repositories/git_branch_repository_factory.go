package repositories

// Git Branch Repository Factory (Python
// infrastructure/repositories/git_branch_repository_factory.py). The Python class-level caches
// and os.environ probing are represented by an injectable factory instance. Creation goes
// through the central RepositoryFactory (repository_factory.py), represented by the
// GitBranchRepositoryFactoryBackend hook and the registered MockGitBranchRepository
// builder.

import (
	"os"

	"agenthub/fastmcp/task_management/domain/entities"
	domainrepos "agenthub/fastmcp/task_management/domain/repositories"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// GitBranchRepositoryType is the available git branch repository types.
type GitBranchRepositoryType string

const (
	GitBranchRepositoryTypeJSON   GitBranchRepositoryType = "json"
	GitBranchRepositoryTypeORM    GitBranchRepositoryType = "orm"
	GitBranchRepositoryTypeMemory GitBranchRepositoryType = "memory"
)

// GitBranchRepositoryBuilder builds a concrete repository of a registered type (Python
// repository class).
type GitBranchRepositoryBuilder func(userID *string, kwargs Kwargs) (domainrepos.GitBranchRepository, error)

// GitBranchRepositoryFactoryBackend is central RepositoryFactory.get_git_branch_repository.
type GitBranchRepositoryFactoryBackend interface {
	GetGitBranchRepository(userID *string) (domainrepos.GitBranchRepository, error)
}

var gitBranchRepoFactoryBackend GitBranchRepositoryFactoryBackend

// SetGitBranchRepositoryFactoryBackend registers the central repository factory.
func SetGitBranchRepositoryFactoryBackend(backend GitBranchRepositoryFactoryBackend) {
	gitBranchRepoFactoryBackend = backend
}

// GitBranchRepositoryFactory is Python's GitBranchRepositoryFactory. The class-level state
// lives on the instance.
type GitBranchRepositoryFactory struct {
	RepositoryTypes *entities.OrderedMap[GitBranchRepositoryBuilder]
	Instances       *entities.OrderedMap[domainrepos.GitBranchRepository]
	Sessions        *database.SessionManager
	Getenv          func(string) string
}

// NewGitBranchRepositoryFactory builds the factory and registers the default types.
func NewGitBranchRepositoryFactory(sessions *database.SessionManager, getenv func(string) string) *GitBranchRepositoryFactory {
	if getenv == nil {
		getenv = os.Getenv
	}
	f := &GitBranchRepositoryFactory{
		RepositoryTypes: entities.NewOrderedMap[GitBranchRepositoryBuilder](),
		Instances:       entities.NewOrderedMap[domainrepos.GitBranchRepository](),
		Sessions:        sessions,
		Getenv:          getenv,
	}
	f.RegisterType(GitBranchRepositoryTypeORM, func(userID *string, kwargs Kwargs) (domainrepos.GitBranchRepository, error) {
		return NewORMGitBranchRepository(f.Sessions, userID, false)
	})
	f.RegisterType(GitBranchRepositoryTypeMemory, func(userID *string, kwargs Kwargs) (domainrepos.GitBranchRepository, error) {
		return nil, &tmvo.ValueError{Msg: "MockGitBranchRepository is not ported"}
	})
	return f
}

// Create creates (or returns a cached) git branch repository.
func (f *GitBranchRepositoryFactory) Create(repositoryType *GitBranchRepositoryType, userID *string, kwargs Kwargs) (domainrepos.GitBranchRepository, error) {
	repoType := GitBranchRepositoryTypeORM
	if repositoryType != nil {
		repoType = *repositoryType
	} else {
		var err error
		repoType, err = f.GetDefaultType()
		if err != nil {
			return nil, err
		}
	}
	cacheKey := string(repoType) + "_" + gitBranchRepoFactoryUserKey(userID)
	if cached, ok := f.Instances.Get(cacheKey); ok {
		return cached, nil
	}
	if gitBranchRepoFactoryBackend == nil {
		return nil, &tmvo.ValueError{Msg: "RepositoryFactory is not registered"}
	}
	repository, err := gitBranchRepoFactoryBackend.GetGitBranchRepository(userID)
	if err != nil {
		return nil, err
	}
	f.Instances.Set(cacheKey, repository)
	return repository, nil
}

// GetDefaultType is _get_default_type.
func (f *GitBranchRepositoryFactory) GetDefaultType() (GitBranchRepositoryType, error) {
	env := f.Getenv("ENVIRONMENT")
	if env == "" {
		env = "production"
	}
	dbType := f.Getenv("DATABASE_TYPE")
	if dbType == "" {
		return "", &tmvo.ValueError{Msg: "DATABASE_TYPE environment variable is not set. " +
			"Please set DATABASE_TYPE to 'postgresql', 'sqlite', or 'supabase'"}
	}
	if env == "test" {
		return GitBranchRepositoryTypeMemory, nil
	}
	switch dbType {
	case "sqlite", "supabase", "postgresql":
		return GitBranchRepositoryTypeORM, nil
	}
	return GitBranchRepositoryTypeORM, nil
}

// RegisterType registers a new repository type.
func (f *GitBranchRepositoryFactory) RegisterType(repositoryType GitBranchRepositoryType, builder GitBranchRepositoryBuilder) {
	f.RepositoryTypes.Set(string(repositoryType), builder)
}

// ClearCache clears every cached instance.
func (f *GitBranchRepositoryFactory) ClearCache() {
	f.Instances = entities.NewOrderedMap[domainrepos.GitBranchRepository]()
}

// GetInfo returns information about the factory.
func (f *GitBranchRepositoryFactory) GetInfo() (*entities.OrderedMap[any], error) {
	available := []any{}
	for _, k := range f.RepositoryTypes.Keys() {
		available = append(available, k)
	}
	defaultType, err := f.GetDefaultType()
	if err != nil {
		return nil, err
	}
	environment := entities.NewOrderedMap[any]()
	environment.Set("MCP_GIT_BRANCH_REPOSITORY_TYPE", gitBranchRepoFactoryEnvOrNil(f.Getenv, "MCP_GIT_BRANCH_REPOSITORY_TYPE"))
	out := entities.NewOrderedMap[any]()
	out.Set("available_types", available)
	out.Set("cached_instances", f.Instances.Len())
	out.Set("default_type", string(defaultType))
	out.Set("environment", environment)
	return out, nil
}

// DefaultGitBranchRepositoryFactory is the process-wide factory (Python class-level state).
var DefaultGitBranchRepositoryFactory = NewGitBranchRepositoryFactory(nil, os.Getenv)

// GetGitBranchDefaultRepository is get_default_repository.
func GetGitBranchDefaultRepository(userID *string) (domainrepos.GitBranchRepository, error) {
	return DefaultGitBranchRepositoryFactory.Create(nil, userID, nil)
}

// GetSQLiteGitBranchRepository is get_sqlite_repository (legacy compatibility method).
func GetSQLiteGitBranchRepository(userID *string, kwargs Kwargs) (domainrepos.GitBranchRepository, error) {
	repoType := GitBranchRepositoryTypeORM
	return DefaultGitBranchRepositoryFactory.Create(&repoType, userID, kwargs)
}

// GetORMGitBranchRepository is get_orm_repository.
func GetORMGitBranchRepository(userID *string, kwargs Kwargs) (domainrepos.GitBranchRepository, error) {
	repoType := GitBranchRepositoryTypeORM
	return DefaultGitBranchRepositoryFactory.Create(&repoType, userID, kwargs)
}

func gitBranchRepoFactoryUserKey(userID *string) string {
	if userID == nil {
		return "None"
	}
	return *userID
}

func gitBranchRepoFactoryEnvOrNil(getenv func(string) string, key string) any {
	v := getenv(key)
	if v == "" {
		return nil
	}
	return v
}
