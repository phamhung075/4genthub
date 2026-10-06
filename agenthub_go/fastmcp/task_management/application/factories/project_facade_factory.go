// Project Facade Factory (Python
// task_management/application/factories/project_facade_factory.py).
//
// Requires validated user authentication; the ProjectApplicationFacade Go constructor has
// different, unexported argument types, so facade construction goes through
// ProjectFacadeBuilder. The singleton pattern uses package-level state.
package factories

import (
	"agenthub/fastmcp/task_management/application/services"
	"agenthub/fastmcp/task_management/domain"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"sync"
)

// projectFacadeFactoryInstance is the class-level `_instance`.
var projectFacadeFactoryInstance *ProjectFacadeFactory

// projectFacadeFactoryInitialized is the class-level `_initialized`.
var projectFacadeFactoryInitialized bool

// ProjectFacadeBuilder builds the ProjectManagementService + facade pair.
var ProjectFacadeBuilder func(projectRepo repositories.ProjectRepository, userID string) (any, error)

// ProjectFacadeFactory mirrors project_facade_factory.ProjectFacadeFactory.
type ProjectFacadeFactory struct {
	repositoryProvider *services.RepositoryProviderService
	cacheMu            sync.Mutex
	facadesCache       map[string]any
}

// GetInstance mirrors the get_instance classmethod.
func (f *ProjectFacadeFactory) GetInstance() *ProjectFacadeFactory {
	return NewProjectFacadeFactory(services.RepositoryProviderService{}.GetInstance())
}

// NewProjectFacadeFactory mirrors __init__ (skips work when already initialized).
func NewProjectFacadeFactory(repositoryProvider *services.RepositoryProviderService) *ProjectFacadeFactory {
	factoriesMu.Lock()
	defer factoriesMu.Unlock()
	if projectFacadeFactoryInitialized {
		return projectFacadeFactoryInstance
	}
	projectFacadeFactoryInitialized = true
	projectFacadeFactoryInstance = &ProjectFacadeFactory{repositoryProvider: repositoryProvider, facadesCache: map[string]any{}}
	return projectFacadeFactoryInstance
}

// CreateProjectFacade mirrors create_project_facade.
func (f *ProjectFacadeFactory) CreateProjectFacade(session any, userID string) (any, error) {
	validated, err := domain.ValidateUserID(&userID, "Project facade creation")
	if err != nil {
		return nil, err
	}
	f.cacheMu.Lock()
	cached, ok := f.facadesCache[validated]
	f.cacheMu.Unlock()
	if ok {
		return cached, nil
	}
	if f.repositoryProvider == nil {
		return nil, &value_objects.ValueError{Msg: "Repository provider is required for project facade creation"}
	}
	projectRepository, err := f.repositoryProvider.GetProjectRepository(&validated, session)
	if err != nil {
		return nil, err
	}
	if ProjectFacadeBuilder == nil {
		return nil, &value_objects.ValueError{Msg: "ProjectApplicationFacade is not ported"}
	}
	facade, err := ProjectFacadeBuilder(projectRepository, validated)
	if err != nil {
		return nil, err
	}
	f.cacheMu.Lock()
	f.facadesCache[validated] = facade
	f.cacheMu.Unlock()
	return facade, nil
}

// ClearCache mirrors clear_cache.
func (f *ProjectFacadeFactory) ClearCache() {
	f.cacheMu.Lock()
	defer f.cacheMu.Unlock()
	f.facadesCache = map[string]any{}
}

// GetCachedFacade mirrors get_cached_facade.
func (f *ProjectFacadeFactory) GetCachedFacade(userID string) (any, error) {
	validated, err := domain.ValidateUserID(&userID, "Get cached facade")
	if err != nil {
		return nil, err
	}
	f.cacheMu.Lock()
	defer f.cacheMu.Unlock()
	facade, _ := f.facadesCache[validated]
	return facade, nil
}
