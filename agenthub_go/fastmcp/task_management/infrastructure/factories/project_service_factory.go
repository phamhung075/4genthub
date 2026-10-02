package factories

import (
	"os"

	"agenthub/fastmcp/task_management/application/services"
	domainrepositories "agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/infrastructure/repositories"
	"agenthub/fastmcp/task_management/infrastructure/utilities"
)

// ProjectServiceFactory mirrors ProjectServiceFactory.
type ProjectServiceFactory struct {
	pathResolver      *utilities.PathResolver
	projectRepository domainrepositories.ProjectRepository
}

// NewProjectServiceFactory mirrors ProjectServiceFactory.__init__.
func NewProjectServiceFactory(pathResolver *utilities.PathResolver, projectRepository domainrepositories.ProjectRepository) *ProjectServiceFactory {
	return &ProjectServiceFactory{pathResolver: pathResolver, projectRepository: projectRepository}
}

// CreateProjectApplicationService mirrors create_project_application_service.
func (f *ProjectServiceFactory) CreateProjectApplicationService(userID *string) (*services.ProjectApplicationService, error) {
	repository, err := f.repositoryForUser(userID)
	if err != nil {
		return nil, err
	}
	return services.NewProjectApplicationService(repository, userID), nil
}

func (f *ProjectServiceFactory) defaultRepository() (domainrepositories.ProjectRepository, error) {
	if f.projectRepository != nil {
		return f.projectRepository, nil
	}
	return repositories.GetDefaultRepository()
}

func (f *ProjectServiceFactory) repositoryForUser(userID *string) (domainrepositories.ProjectRepository, error) {
	if f.projectRepository != nil {
		return f.projectRepository, nil
	}
	return repositories.CreateProjectRepository(userID, nil, nil)
}

// CreateSQLiteService mirrors create_sqlite_service.
func (f *ProjectServiceFactory) CreateSQLiteService(userID *string, dbPath *string) (*services.ProjectApplicationService, error) {
	repository, err := repositories.GetSQLiteRepository(userID, dbPath)
	if err != nil {
		return nil, err
	}
	return services.NewProjectApplicationService(repository, userID), nil
}

// CreateServiceFromConfig mirrors create_service_from_config.
func (f *ProjectServiceFactory) CreateServiceFromConfig(config *repositories.RepositoryConfig) (*services.ProjectApplicationService, error) {
	repository, err := config.CreateRepository(repositories.DefaultProjectRepositoryFactory)
	if err != nil {
		return nil, err
	}
	return services.NewProjectApplicationService(repository, config.UserID), nil
}

// CreateServiceFromEnvironment mirrors create_service_from_environment.
func (f *ProjectServiceFactory) CreateServiceFromEnvironment(userID *string) (*services.ProjectApplicationService, error) {
	config := repositories.RepositoryConfigFromEnvironment(os.Getenv)
	config.UserID = userID
	return f.CreateServiceFromConfig(config)
}

// SetProjectRepository mirrors set_project_repository.
func (f *ProjectServiceFactory) SetProjectRepository(repository domainrepositories.ProjectRepository) {
	f.projectRepository = repository
}

// GetProjectRepository mirrors get_project_repository.
func (f *ProjectServiceFactory) GetProjectRepository() domainrepositories.ProjectRepository {
	return f.projectRepository
}

// CreateProjectServiceFactory mirrors create_project_service_factory.
func CreateProjectServiceFactory(pathResolver *utilities.PathResolver, projectRepository domainrepositories.ProjectRepository) *ProjectServiceFactory {
	if pathResolver == nil {
		pathResolver, _ = utilities.NewPathResolver()
	}
	return NewProjectServiceFactory(pathResolver, projectRepository)
}

// CreateDefaultProjectService mirrors create_default_project_service.
func CreateDefaultProjectService() (*services.ProjectApplicationService, error) {
	return CreateProjectServiceFactory(nil, nil).CreateProjectApplicationService(nil)
}

// CreateProjectServiceForUser mirrors create_project_service_for_user.
func CreateProjectServiceForUser(userID string) (*services.ProjectApplicationService, error) {
	return CreateProjectServiceFactory(nil, nil).CreateProjectApplicationService(&userID)
}

// CreateSQLiteProjectService mirrors create_sqlite_project_service.
func CreateSQLiteProjectService(userID *string, dbPath *string) (*services.ProjectApplicationService, error) {
	return CreateProjectServiceFactory(nil, nil).CreateSQLiteService(userID, dbPath)
}
