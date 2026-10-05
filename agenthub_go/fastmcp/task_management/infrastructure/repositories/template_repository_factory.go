package repositories

import (
	"os"
	"strings"

	"agenthub/fastmcp/task_management/infrastructure/database"
)

// TemplateRepositoryFactory ports template_repository_factory.TemplateRepositoryFactory.
//
// Python's constructor takes no session; the Go ORMTemplateRepository needs a
// SessionManager, so it is carried on the factory. The Python mock-template
// repository import (test environment) and the Redis cache wrapper import
// (CachedTemplateRepository) have no Go port yet, so both ImportError branches
// fall through to the ORM repository, exactly as Python does on ImportError.
type TemplateRepositoryFactory struct {
	ProjectRoot string
	Sessions    *database.SessionManager
}

// NewTemplateRepositoryFactory mirrors the constructor (project_root or _find_project_root()).
func NewTemplateRepositoryFactory(projectRoot *string, sessions *database.SessionManager) *TemplateRepositoryFactory {
	root := FindProjectRoot()
	if projectRoot != nil && *projectRoot != "" {
		root = *projectRoot
	}
	return &TemplateRepositoryFactory{ProjectRoot: root, Sessions: sessions}
}

// CreateRepository ports create_repository (db_path is ignored for the ORM).
//
// Python's declared return type is TemplateRepositoryInterface, but the Go
// domain interface (domain/repositories.TemplateRepositoryInterface) is stale and
// not satisfied by ORMTemplateRepository (GetAnalytics arity differs), so the
// concrete repository is returned instead.
func (f *TemplateRepositoryFactory) CreateRepository(dbPath *string) (*ORMTemplateRepository, error) {
	_ = dbPath
	env := templateRepoFactoryGetenv("ENVIRONMENT", "production")
	dbType := os.Getenv("DATABASE_TYPE")
	redisEnabled := strings.ToLower(templateRepoFactoryGetenv("REDIS_ENABLED", "false")) == "true"

	if dbType == "" {
		return nil, &ValueError{Msg: "DATABASE_TYPE environment variable is not set. " +
			"Please set DATABASE_TYPE to 'postgresql', 'sqlite', or 'supabase'"}
	}

	// env == "test" would return MockTemplateRepository; that Go port is absent,
	// so (like Python's ImportError) control falls through to the ORM repository.
	_ = env

	baseRepo, err := NewORMTemplateRepository(f.Sessions)
	if err != nil {
		return nil, err
	}

	// redisEnabled && env != "test" would wrap with CachedTemplateRepository; that
	// Go port is absent, so (like Python's ImportError) the base repository is used.
	_ = redisEnabled
	return baseRepo, nil
}

// CreateSQLiteRepository ports create_sqlite_repository (delegates to create_repository).
func (f *TemplateRepositoryFactory) CreateSQLiteRepository(dbPath *string) (*ORMTemplateRepository, error) {
	return f.CreateRepository(dbPath)
}

// CreateORMRepository ports create_orm_repository (delegates to create_repository).
func (f *TemplateRepositoryFactory) CreateORMRepository() (*ORMTemplateRepository, error) {
	return f.CreateRepository(nil)
}

func templateRepoFactoryGetenv(key, fallback string) string {
	if v, ok := os.LookupEnv(key); ok {
		return v
	}
	return fallback
}
