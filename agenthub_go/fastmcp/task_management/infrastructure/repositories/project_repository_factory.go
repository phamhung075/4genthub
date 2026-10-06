package repositories

// Project Repository Factory (Python infrastructure/repositories/project_repository_factory.py).
// Python class-level caches and os.environ probing are represented by an injectable factory
// instance; mock construction goes through the MockFactory hook. The per-db_path environment
// juggling is not reproduced (the Go database configuration is process-wide).

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

// RepositoryType is the available repository implementation types.
type RepositoryType string

const (
	RepositoryTypeORM      RepositoryType = "orm"
	RepositoryTypeInMemory RepositoryType = "in_memory"
	RepositoryTypeMock     RepositoryType = "mock"
)

// ProjectRepositoryBuilder builds a concrete repository of a registered type (Python
// repository class constructor).
type ProjectRepositoryBuilder func(userID string, dbPath *string, kwargs Kwargs) (domainrepos.ProjectRepository, error)

// ProjectRepositoryFactory is Python's ProjectRepositoryFactory. The class-level state lives
// on the instance.
type ProjectRepositoryFactory struct {
	Instances         *entities.OrderedMap[domainrepos.ProjectRepository]
	RepositoryTypes   *entities.OrderedMap[ProjectRepositoryBuilder]
	Sessions          *database.SessionManager
	Getenv            func(string) string
	DatabaseAvailable func() bool
	// MockFactory builds the mock repository once mock_repository_factory.py is ported.
	MockFactory func() domainrepos.ProjectRepository
}

// NewProjectRepositoryFactory builds the factory and registers the default types.
func NewProjectRepositoryFactory(sessions *database.SessionManager, getenv func(string) string) *ProjectRepositoryFactory {
	if getenv == nil {
		getenv = os.Getenv
	}
	f := &ProjectRepositoryFactory{
		Instances:       entities.NewOrderedMap[domainrepos.ProjectRepository](),
		RepositoryTypes: entities.NewOrderedMap[ProjectRepositoryBuilder](),
		Sessions:        sessions,
		Getenv:          getenv,
	}
	f.DatabaseAvailable = func() bool { return f.Sessions != nil }
	f.RepositoryTypes.Set(string(RepositoryTypeORM), f.buildORM)
	f.RepositoryTypes.Set(string(RepositoryTypeMock), f.buildMock)
	return f
}

// Create creates (or returns a cached) project repository.
func (f *ProjectRepositoryFactory) Create(repositoryType *RepositoryType, userID *string, dbPath *string, kwargs Kwargs) (domainrepos.ProjectRepository, error) {
	if userID == nil {
		return nil, exceptions.NewUserAuthenticationRequiredError("Project repository creation")
	}
	validated, err := domain.ValidateUserID(userID, "Project repository creation")
	if err != nil {
		return nil, err
	}
	repoType := RepositoryTypeORM
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
		if f.MockFactory == nil {
			return nil, err
		}
		repoType = RepositoryTypeMock
		cacheKey = f.GenerateCacheKey(repoType, validated, dbPath)
		if cached, ok := f.Instances.Get(cacheKey); ok {
			return cached, nil
		}
		if repository, err = f.CreateInstance(repoType, validated, dbPath, kwargs); err != nil {
			return nil, err
		}
	}
	f.Instances.Set(cacheKey, repository)
	return repository, nil
}

// GetDefaultType selects the default repository type from the environment.
func (f *ProjectRepositoryFactory) GetDefaultType() (RepositoryType, error) {
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
		return RepositoryTypeMock, nil
	}
	if f.DatabaseAvailable != nil && f.DatabaseAvailable() {
		return RepositoryTypeORM, nil
	}
	return RepositoryTypeMock, nil
}

// GenerateCacheKey builds the instance cache key.
func (f *ProjectRepositoryFactory) GenerateCacheKey(repositoryType RepositoryType, userID string, dbPath *string) string {
	path := "memory"
	if dbPath != nil && *dbPath != "" {
		path = *dbPath
	}
	return string(repositoryType) + ":" + userID + ":" + path
}

// CreateInstance builds a repository of the given type.
func (f *ProjectRepositoryFactory) CreateInstance(repositoryType RepositoryType, userID string, dbPath *string, kwargs Kwargs) (domainrepos.ProjectRepository, error) {
	builder, ok := f.RepositoryTypes.Get(string(repositoryType))
	if !ok {
		return nil, &tmvo.ValueError{Msg: "Unsupported repository type: " + string(repositoryType)}
	}
	repo, err := builder(userID, dbPath, kwargs)
	if err != nil {
		if repositoryType == RepositoryTypeORM && f.MockFactory != nil {
			return f.MockFactory(), nil
		}
		return nil, err
	}
	return repo, nil
}

func (f *ProjectRepositoryFactory) buildORM(userID string, dbPath *string, kwargs Kwargs) (domainrepos.ProjectRepository, error) {
	if f.Sessions == nil {
		return nil, &tmvo.ValueError{Msg: "Database session manager is not configured"}
	}
	return NewORMProjectRepository(f.Sessions, &userID)
}

func (f *ProjectRepositoryFactory) buildMock(userID string, dbPath *string, kwargs Kwargs) (domainrepos.ProjectRepository, error) {
	if f.MockFactory == nil {
		return nil, &tmvo.ValueError{Msg: "MockProjectRepository is not ported"}
	}
	return f.MockFactory(), nil
}

// RegisterType registers a new repository type.
func (f *ProjectRepositoryFactory) RegisterType(repositoryType RepositoryType, builder ProjectRepositoryBuilder) {
	f.RepositoryTypes.Set(string(repositoryType), builder)
}

// ClearCache clears every cached instance.
func (f *ProjectRepositoryFactory) ClearCache() {
	f.Instances = entities.NewOrderedMap[domainrepos.ProjectRepository]()
}

// GetInfo returns information about the factory.
func (f *ProjectRepositoryFactory) GetInfo() (*entities.OrderedMap[any], error) {
	available := []any{}
	for _, k := range f.RepositoryTypes.Keys() {
		available = append(available, k)
	}
	defaultType, err := f.GetDefaultType()
	if err != nil {
		return nil, err
	}
	environment := entities.NewOrderedMap[any]()
	environment.Set("MCP_PROJECT_REPOSITORY_TYPE", projectRepoFactoryEnvOrNil(f.Getenv, "MCP_PROJECT_REPOSITORY_TYPE"))
	environment.Set("MCP_DB_PATH", projectRepoFactoryEnvOrNil(f.Getenv, "MCP_DB_PATH"))
	out := entities.NewOrderedMap[any]()
	out.Set("available_types", available)
	out.Set("cached_instances", f.Instances.Len())
	out.Set("default_type", string(defaultType))
	out.Set("environment", environment)
	return out, nil
}

// RepositoryConfig is Python's RepositoryConfig.
type RepositoryConfig struct {
	RepositoryType RepositoryType
	UserID         *string
	DBPath         *string
	Kwargs         Kwargs
}

// NewRepositoryConfig validates the repository type and builds a config.
func NewRepositoryConfig(repositoryType *string, userID, dbPath *string, kwargs Kwargs) *RepositoryConfig {
	return &RepositoryConfig{
		RepositoryType: projectRepoConfigValidateType(repositoryType),
		UserID:         userID,
		DBPath:         dbPath,
		Kwargs:         kwargs,
	}
}

func projectRepoConfigValidateType(repositoryType *string) RepositoryType {
	if repositoryType == nil {
		return RepositoryTypeORM
	}
	value := RepositoryType(strings.ToLower(*repositoryType))
	switch value {
	case RepositoryTypeORM, RepositoryTypeInMemory, RepositoryTypeMock:
		return value
	}
	return RepositoryTypeORM
}

// CreateRepository creates the configured repository.
func (c *RepositoryConfig) CreateRepository(factory *ProjectRepositoryFactory) (domainrepos.ProjectRepository, error) {
	return factory.Create(&c.RepositoryType, c.UserID, c.DBPath, c.Kwargs)
}

// RepositoryConfigFromEnvironment builds a config from the environment variables.
func RepositoryConfigFromEnvironment(getenv func(string) string) *RepositoryConfig {
	if getenv == nil {
		getenv = os.Getenv
	}
	var repositoryType, userID, dbPath *string
	if v := getenv("MCP_PROJECT_REPOSITORY_TYPE"); v != "" {
		repositoryType = &v
	}
	if v := getenv("MCP_USER_ID"); v != "" {
		userID = &v
	}
	if v := getenv("MCP_DB_PATH"); v != "" {
		dbPath = &v
	}
	return NewRepositoryConfig(repositoryType, userID, dbPath, nil)
}

// GlobalRepositoryManager is Python's GlobalRepositoryManager.
type GlobalRepositoryManager struct {
	DefaultRepository domainrepos.ProjectRepository
	UserRepositories  *entities.OrderedMap[domainrepos.ProjectRepository]
	Factory           *ProjectRepositoryFactory
}

// NewGlobalRepositoryManager builds the manager.
func NewGlobalRepositoryManager(factory *ProjectRepositoryFactory) *GlobalRepositoryManager {
	return &GlobalRepositoryManager{
		UserRepositories: entities.NewOrderedMap[domainrepos.ProjectRepository](),
		Factory:          factory,
	}
}

func (m *GlobalRepositoryManager) managerFactory() *ProjectRepositoryFactory {
	if m.Factory != nil {
		return m.Factory
	}
	return DefaultProjectRepositoryFactory
}

// GetDefault returns the default repository (user_id=None, which the factory rejects).
func (m *GlobalRepositoryManager) GetDefault() (domainrepos.ProjectRepository, error) {
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
func (m *GlobalRepositoryManager) GetForUser(userID string) (domainrepos.ProjectRepository, error) {
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
func (m *GlobalRepositoryManager) ClearAll() {
	m.DefaultRepository = nil
	m.UserRepositories = entities.NewOrderedMap[domainrepos.ProjectRepository]()
	m.managerFactory().ClearCache()
}

// GetStatus returns the manager status.
func (m *GlobalRepositoryManager) GetStatus() (*entities.OrderedMap[any], error) {
	info, err := m.managerFactory().GetInfo()
	if err != nil {
		return nil, err
	}
	out := entities.NewOrderedMap[any]()
	out.Set("has_default", m.DefaultRepository != nil)
	out.Set("user_count", m.UserRepositories.Len())
	out.Set("factory_info", info)
	return out, nil
}

// DefaultProjectRepositoryFactory is the process-wide factory (Python class-level state).
var DefaultProjectRepositoryFactory = NewProjectRepositoryFactory(nil, os.Getenv)

// DefaultGlobalRepositoryManager is the process-wide manager.
var DefaultGlobalRepositoryManager = NewGlobalRepositoryManager(nil)

// CreateProjectRepository creates a project repository instance.
func CreateProjectRepository(userID *string, repositoryType *string, dbPath *string) (domainrepos.ProjectRepository, error) {
	var repoType *RepositoryType
	if repositoryType != nil {
		value := RepositoryType(*repositoryType)
		switch value {
		case RepositoryTypeORM, RepositoryTypeInMemory, RepositoryTypeMock:
			repoType = &value
		default:
			return nil, &tmvo.ValueError{Msg: "'" + *repositoryType + "' is not a valid RepositoryType"}
		}
	}
	return DefaultProjectRepositoryFactory.Create(repoType, userID, dbPath, nil)
}

// GetSQLiteRepository returns the ORM project repository (legacy compatibility method).
func GetSQLiteRepository(userID *string, dbPath *string) (domainrepos.ProjectRepository, error) {
	repoType := RepositoryTypeORM
	return DefaultProjectRepositoryFactory.Create(&repoType, userID, dbPath, nil)
}

// GetDefaultRepository returns the default global repository.
func GetDefaultRepository() (domainrepos.ProjectRepository, error) {
	return DefaultGlobalRepositoryManager.GetDefault()
}

// GetUserRepository returns the repository for a specific user.
func GetUserRepository(userID string) (domainrepos.ProjectRepository, error) {
	return DefaultGlobalRepositoryManager.GetForUser(userID)
}

func projectRepoFactoryEnvOrNil(getenv func(string) string, key string) any {
	v := getenv(key)
	if v == "" {
		return nil
	}
	return v
}
