// Git Branch Facade Factory (Python
// task_management/application/factories/git_branch_facade_factory.py).
//
// The Python factory obtains user-scoped project / git-branch repositories from
// RepositoryProviderService, builds a GitBranchService and a GitBranchApplicationFacade.
// The Go service constructor (zpGitBranchNewService) is unexported and the facade
// constructor has different argument types, so that pair is built through
// GitBranchFacadeBuilder. It implements the Python singleton pattern.
package factories

import (
	"agenthub/fastmcp/task_management/application/services"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"sync"
)

// gitBranchFacadeFactoryInstance is the class-level `_instance`.
var gitBranchFacadeFactoryInstance *GitBranchFacadeFactory

// gitBranchFacadeFactoryInitialized is the class-level `_initialized`.
var gitBranchFacadeFactoryInitialized bool

// GitBranchFacadeBuilder builds the GitBranchService + facade pair.
var GitBranchFacadeBuilder func(projectRepo repositories.ProjectRepository, gitBranchRepo repositories.GitBranchRepository, projectID, userID *string) (any, error)

// GitBranchFacadeFactory mirrors git_branch_facade_factory.GitBranchFacadeFactory.
type GitBranchFacadeFactory struct {
	gitBranchRepositoryFactory any
	cacheMu                    sync.Mutex
	facadesCache               map[string]any
}

// GetInstance mirrors the get_instance classmethod.
func (f *GitBranchFacadeFactory) GetInstance() *GitBranchFacadeFactory {
	return NewGitBranchFacadeFactory(nil)
}

// NewGitBranchFacadeFactory mirrors __init__ (skips work when already initialized).
func NewGitBranchFacadeFactory(gitBranchRepositoryFactory any) *GitBranchFacadeFactory {
	factoriesMu.Lock()
	defer factoriesMu.Unlock()
	if gitBranchFacadeFactoryInitialized {
		return gitBranchFacadeFactoryInstance
	}
	gitBranchFacadeFactoryInitialized = true
	gitBranchFacadeFactoryInstance = &GitBranchFacadeFactory{gitBranchRepositoryFactory: gitBranchRepositoryFactory, facadesCache: map[string]any{}}
	return gitBranchFacadeFactoryInstance
}

// CreateFacade mirrors create_facade.
func (f *GitBranchFacadeFactory) CreateFacade(session any, projectID *string, userID *string) (any, error) {
	if projectID == nil {
		return nil, &value_objects.ValueError{Msg: "project_id is required for git branch facade creation (no fallback allowed for DDD compliance)"}
	}
	return f.CreateGitBranchFacade(session, *projectID, userID)
}

// CreateGitBranchFacade mirrors create_git_branch_facade.
func (f *GitBranchFacadeFactory) CreateGitBranchFacade(session any, projectID string, userID *string) (any, error) {
	userSuffix := "no_user"
	if userID != nil && *userID != "" {
		userSuffix = *userID
	}
	cacheKey := projectID + ":" + userSuffix
	f.cacheMu.Lock()
	cached, ok := f.facadesCache[cacheKey]
	f.cacheMu.Unlock()
	if ok {
		return cached, nil
	}

	if GitBranchFacadeBuilder == nil {
		return nil, &value_objects.ValueError{Msg: "GitBranchFacadeBuilder is not wired: set it at server composition"}
	}

	repoProvider := services.RepositoryProviderService{}.GetInstance()
	projectRepo, err := repoProvider.GetProjectRepository(userID, session)
	if err != nil {
		return nil, err
	}
	gitBranchRepo, err := repoProvider.GetGitBranchRepository(session, userID)
	if err != nil {
		return nil, err
	}
	projectIDCopy := projectID
	facade, err := GitBranchFacadeBuilder(projectRepo, gitBranchRepo, &projectIDCopy, userID)
	if err != nil {
		return nil, err
	}
	f.cacheMu.Lock()
	f.facadesCache[cacheKey] = facade
	f.cacheMu.Unlock()
	return facade, nil
}

// GetBranchFacade mirrors get_branch_facade.
func (f *GitBranchFacadeFactory) GetBranchFacade(session any, projectID string, userID *string) (any, error) {
	return f.CreateFacade(session, &projectID, userID)
}

// ClearCache mirrors clear_cache.
func (f *GitBranchFacadeFactory) ClearCache() {
	f.cacheMu.Lock()
	defer f.cacheMu.Unlock()
	f.facadesCache = map[string]any{}
}

// GetCachedFacade mirrors get_cached_facade.
func (f *GitBranchFacadeFactory) GetCachedFacade(projectID string, userID *string) any {
	userSuffix := "no_user"
	if userID != nil && *userID != "" {
		userSuffix = *userID
	}
	f.cacheMu.Lock()
	defer f.cacheMu.Unlock()
	facade, _ := f.facadesCache[projectID+":"+userSuffix]
	return facade
}
