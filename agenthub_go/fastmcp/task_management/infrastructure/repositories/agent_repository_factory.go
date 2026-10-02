package repositories

// Agent Repository Factory (Python infrastructure/repositories/agent_repository_factory.py).
// The Python class-level caches and os.environ probing are represented by an injectable
// factory instance, mirroring project_repository_factory.go. The non-ORM branch calls
// repository_factory.RepositoryFactory, which is not ported yet, so it goes through the
// UnportedFactory hook.

import (
	"os"
	"strings"

	"agenthub/fastmcp/task_management/domain"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	domainrepos "agenthub/fastmcp/task_management/domain/repositories"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// AgentRepositoryType is the available agent repository implementation types.
type AgentRepositoryType string

const (
	AgentRepositoryTypeORM      AgentRepositoryType = "orm"
	AgentRepositoryTypeInMemory AgentRepositoryType = "in_memory"
	AgentRepositoryTypeMock     AgentRepositoryType = "mock"
)

// AgentRepositoryBuilder builds a concrete agent repository of a registered type.
type AgentRepositoryBuilder func(userID string, dbPath *string, kwargs Kwargs) (domainrepos.AgentRepository, error)

// AgentRepositoryFactory is Python's AgentRepositoryFactory. The class-level state lives on
// the instance.
type AgentRepositoryFactory struct {
	Instances       *entities.OrderedMap[domainrepos.AgentRepository]
	RepositoryTypes *entities.OrderedMap[AgentRepositoryBuilder]
	Sessions        *database.SessionManager
	Getenv          func(string) string
	// UnportedFactory is repository_factory.RepositoryFactory.get_agent_repository(), used for
	// the non-ORM branch.
	UnportedFactory func() (domainrepos.AgentRepository, error)
}

// NewAgentRepositoryFactory builds the factory and registers the default ORM type.
func NewAgentRepositoryFactory(sessions *database.SessionManager, getenv func(string) string) *AgentRepositoryFactory {
	if getenv == nil {
		getenv = os.Getenv
	}
	f := &AgentRepositoryFactory{
		Instances:       entities.NewOrderedMap[domainrepos.AgentRepository](),
		RepositoryTypes: entities.NewOrderedMap[AgentRepositoryBuilder](),
		Sessions:        sessions,
		Getenv:          getenv,
	}
	f.RepositoryTypes.Set(string(AgentRepositoryTypeORM), f.buildORM)
	return f
}

// Create creates (or returns a cached) agent repository.
func (f *AgentRepositoryFactory) Create(repositoryType *AgentRepositoryType, userID *string, dbPath *string, kwargs Kwargs) (domainrepos.AgentRepository, error) {
	if userID == nil {
		return nil, exceptions.NewUserAuthenticationRequiredError("Agent repository creation")
	}
	validated, err := domain.ValidateUserID(userID, "Agent repository creation")
	if err != nil {
		return nil, err
	}
	repoType := AgentRepositoryTypeORM
	if repositoryType != nil {
		repoType = *repositoryType
	} else {
		repoType, err = f.GetDefaultType()
		if err != nil {
			return nil, err
		}
	}
	cacheKey := f.GenerateCacheKey(repoType, validated, dbPath)
	if cached, ok := f.Instances.Get(cacheKey); ok {
		return cached, nil
	}
	repository, err := f.CreateInstance(repoType, validated, dbPath, kwargs)
	if err != nil {
		return nil, err
	}
	f.Instances.Set(cacheKey, repository)
	return repository, nil
}

// GetDefaultType selects the default repository type from the environment.
func (f *AgentRepositoryFactory) GetDefaultType() (AgentRepositoryType, error) {
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
		return AgentRepositoryTypeMock, nil
	}
	if dbType == "sqlite" || dbType == "supabase" || dbType == "postgresql" {
		return AgentRepositoryTypeORM, nil
	}
	return AgentRepositoryTypeORM, nil
}

// GenerateCacheKey builds the instance cache key.
func (f *AgentRepositoryFactory) GenerateCacheKey(repositoryType AgentRepositoryType, userID string, dbPath *string) string {
	path := "memory"
	if dbPath != nil && *dbPath != "" {
		path = *dbPath
	}
	return "agent:" + string(repositoryType) + ":" + userID + ":" + path
}

// CreateInstance builds a repository of the given type. Like Python, the ORM type is
// hardcoded and the registered-type map is only used by RegisterType/GetInfo.
func (f *AgentRepositoryFactory) CreateInstance(repositoryType AgentRepositoryType, userID string, dbPath *string, kwargs Kwargs) (domainrepos.AgentRepository, error) {
	if repositoryType == AgentRepositoryTypeORM {
		return f.buildORM(userID, dbPath, kwargs)
	}
	if f.UnportedFactory == nil {
		return nil, &tmvo.ValueError{Msg: "repository_factory.RepositoryFactory is not ported"}
	}
	return f.UnportedFactory()
}

func (f *AgentRepositoryFactory) buildORM(userID string, dbPath *string, kwargs Kwargs) (domainrepos.AgentRepository, error) {
	if f.Sessions == nil {
		return nil, &tmvo.ValueError{Msg: "Database session manager is not configured"}
	}
	var projectID *string
	if kwargs != nil {
		if v, ok := kwargs.Get("project_id"); ok {
			switch s := v.(type) {
			case string:
				projectID = &s
			case *string:
				projectID = s
			}
		}
	}
	return NewORMAgentRepository(f.Sessions, &userID, projectID)
}

// RegisterType registers a new repository type.
func (f *AgentRepositoryFactory) RegisterType(repositoryType AgentRepositoryType, builder AgentRepositoryBuilder) {
	f.RepositoryTypes.Set(string(repositoryType), builder)
}

// ClearCache clears every cached instance.
func (f *AgentRepositoryFactory) ClearCache() {
	f.Instances = entities.NewOrderedMap[domainrepos.AgentRepository]()
}

// GetInfo returns information about the factory.
func (f *AgentRepositoryFactory) GetInfo() (*entities.OrderedMap[any], error) {
	available := []any{}
	for _, k := range f.RepositoryTypes.Keys() {
		available = append(available, k)
	}
	defaultType, err := f.GetDefaultType()
	if err != nil {
		return nil, err
	}
	environment := entities.NewOrderedMap[any]()
	environment.Set("MCP_AGENT_REPOSITORY_TYPE", projectRepoFactoryEnvOrNil(f.Getenv, "MCP_AGENT_REPOSITORY_TYPE"))
	environment.Set("MCP_DB_PATH", projectRepoFactoryEnvOrNil(f.Getenv, "MCP_DB_PATH"))
	out := entities.NewOrderedMap[any]()
	out.Set("available_types", available)
	out.Set("cached_instances", f.Instances.Len())
	out.Set("default_type", string(defaultType))
	out.Set("environment", environment)
	return out, nil
}

// AgentRepositoryConfig is Python's AgentRepositoryConfig.
type AgentRepositoryConfig struct {
	RepositoryType AgentRepositoryType
	UserID         *string
	DBPath         *string
	Kwargs         Kwargs
}

// NewAgentRepositoryConfig validates the repository type and builds a config.
func NewAgentRepositoryConfig(repositoryType *string, userID, dbPath *string, kwargs Kwargs) *AgentRepositoryConfig {
	return &AgentRepositoryConfig{
		RepositoryType: agentRepoConfigValidateType(repositoryType),
		UserID:         userID,
		DBPath:         dbPath,
		Kwargs:         kwargs,
	}
}

func agentRepoConfigValidateType(repositoryType *string) AgentRepositoryType {
	if repositoryType == nil {
		return AgentRepositoryTypeORM
	}
	value := AgentRepositoryType(strings.ToLower(*repositoryType))
	switch value {
	case AgentRepositoryTypeORM, AgentRepositoryTypeInMemory, AgentRepositoryTypeMock:
		return value
	}
	return AgentRepositoryTypeORM
}

// CreateRepository creates the configured repository.
func (c *AgentRepositoryConfig) CreateRepository(factory *AgentRepositoryFactory) (domainrepos.AgentRepository, error) {
	return factory.Create(&c.RepositoryType, c.UserID, c.DBPath, c.Kwargs)
}

// AgentRepositoryConfigFromEnvironment builds a config from the environment variables.
func AgentRepositoryConfigFromEnvironment(getenv func(string) string) *AgentRepositoryConfig {
	if getenv == nil {
		getenv = os.Getenv
	}
	var repositoryType, userID, dbPath *string
	if v := getenv("MCP_AGENT_REPOSITORY_TYPE"); v != "" {
		repositoryType = &v
	}
	if v := getenv("MCP_USER_ID"); v != "" {
		userID = &v
	}
	if v := getenv("MCP_DB_PATH"); v != "" {
		dbPath = &v
	}
	return NewAgentRepositoryConfig(repositoryType, userID, dbPath, nil)
}

// GlobalAgentRepositoryManager is Python's GlobalAgentRepositoryManager.
type GlobalAgentRepositoryManager struct {
	DefaultRepository domainrepos.AgentRepository
	UserRepositories  *entities.OrderedMap[domainrepos.AgentRepository]
	Factory           *AgentRepositoryFactory
}

// NewGlobalAgentRepositoryManager builds the manager.
func NewGlobalAgentRepositoryManager(factory *AgentRepositoryFactory) *GlobalAgentRepositoryManager {
	return &GlobalAgentRepositoryManager{
		UserRepositories: entities.NewOrderedMap[domainrepos.AgentRepository](),
		Factory:          factory,
	}
}

func (m *GlobalAgentRepositoryManager) managerFactory() *AgentRepositoryFactory {
	if m.Factory != nil {
		return m.Factory
	}
	return DefaultAgentRepositoryFactory
}

// GetDefault returns the default repository (user_id=None, which the factory rejects).
func (m *GlobalAgentRepositoryManager) GetDefault() (domainrepos.AgentRepository, error) {
	if m.DefaultRepository == nil {
		repo, err := m.managerFactory().Create(nil, nil, nil, nil)
		if err != nil {
			return nil, err
		}
		m.DefaultRepository = repo
	}
	return m.DefaultRepository, nil
}

// GetForUser returns (and caches) the repository for a user.
func (m *GlobalAgentRepositoryManager) GetForUser(userID string) (domainrepos.AgentRepository, error) {
	if repo, ok := m.UserRepositories.Get(userID); ok {
		return repo, nil
	}
	repo, err := m.managerFactory().Create(nil, &userID, nil, nil)
	if err != nil {
		return nil, err
	}
	m.UserRepositories.Set(userID, repo)
	return repo, nil
}

// ClearAll clears every managed repository.
func (m *GlobalAgentRepositoryManager) ClearAll() {
	m.DefaultRepository = nil
	m.UserRepositories = entities.NewOrderedMap[domainrepos.AgentRepository]()
	m.managerFactory().ClearCache()
}

// GetStatus returns the manager status.
func (m *GlobalAgentRepositoryManager) GetStatus() (*entities.OrderedMap[any], error) {
	info, err := m.managerFactory().GetInfo()
	if err != nil {
		return nil, err
	}
	out := entities.NewOrderedMap[any]()
	out.Set("default_repository", m.DefaultRepository != nil)
	out.Set("user_repositories", m.UserRepositories.Len())
	out.Set("cached_users", m.UserRepositories.Keys())
	out.Set("factory_info", info)
	return out, nil
}

// DefaultAgentRepositoryFactory is the process-wide factory (Python class-level state).
var DefaultAgentRepositoryFactory = NewAgentRepositoryFactory(nil, os.Getenv)

// DefaultGlobalAgentRepositoryManager is the process-wide manager.
var DefaultGlobalAgentRepositoryManager = NewGlobalAgentRepositoryManager(nil)

// CreateAgentRepository creates an agent repository instance.
func CreateAgentRepository(userID *string, repositoryType *string, dbPath *string) (domainrepos.AgentRepository, error) {
	var repoType *AgentRepositoryType
	if repositoryType != nil {
		value := AgentRepositoryType(strings.ToLower(*repositoryType))
		switch value {
		case AgentRepositoryTypeORM, AgentRepositoryTypeInMemory, AgentRepositoryTypeMock:
			repoType = &value
		default:
			return nil, &tmvo.ValueError{Msg: "'" + *repositoryType + "' is not a valid AgentRepositoryType"}
		}
	}
	return DefaultAgentRepositoryFactory.Create(repoType, userID, dbPath, nil)
}

// GetSQLiteAgentRepository returns the ORM agent repository (legacy compatibility method).
func GetSQLiteAgentRepository(userID *string, dbPath *string) (domainrepos.AgentRepository, error) {
	repoType := AgentRepositoryTypeORM
	return DefaultAgentRepositoryFactory.Create(&repoType, userID, nil, nil)
}

// GetORMAgentRepository returns the ORM agent repository for a user/project.
func GetORMAgentRepository(userID *string, projectID *string) (domainrepos.AgentRepository, error) {
	repoType := AgentRepositoryTypeORM
	return DefaultAgentRepositoryFactory.Create(&repoType, userID, nil, NewKwargs("project_id", projectID))
}

// GetDefaultAgentRepository returns the default global repository.
func GetDefaultAgentRepository() (domainrepos.AgentRepository, error) {
	return DefaultGlobalAgentRepositoryManager.GetDefault()
}

// GetUserAgentRepository returns the repository for a specific user.
func GetUserAgentRepository(userID string) (domainrepos.AgentRepository, error) {
	return DefaultGlobalAgentRepositoryManager.GetForUser(userID)
}

// CreateAgentRepositoryFactory returns the process-wide factory (Python's fresh instance
// shares the class-level cache; the Go process-wide factory is the equivalent).
func CreateAgentRepositoryFactory() *AgentRepositoryFactory {
	return DefaultAgentRepositoryFactory
}
