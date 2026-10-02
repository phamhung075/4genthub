package services

import (
	"sync"

	domainrepos "agenthub/fastmcp/task_management/domain/repositories"
)

// This file ports RepositoryProviderService: the application-layer boundary that
// creates repository instances without exposing infrastructure details. The
// infrastructure factories the Python code imports lazily have no Go port with the
// same shape yet, so they are described by the consumer-side interfaces below and
// supplied through repoProviderFactoryBackendProvider (logging is dropped).

// repoProviderTaskRepositoryFactory is the consumer-side view of TaskRepositoryFactory.
type repoProviderTaskRepositoryFactory interface {
	CreateRepository(projectID, gitBranchName string, userID *string) (domainrepos.TaskRepository, error)
}

// repoProviderSubtaskRepositoryFactory is the consumer-side view of SubtaskRepositoryFactory.
type repoProviderSubtaskRepositoryFactory interface {
	CreateORMSubtaskRepository(userID *string) (domainrepos.SubtaskRepository, error)
	CreateSubtaskRepository(projectID, gitBranchName string, userID *string) (domainrepos.SubtaskRepository, error)
}

// repoProviderAgentRepositoryFactory is the consumer-side view of AgentRepositoryFactory
// (the provider caches the factory, then calls create_repository).
type repoProviderAgentRepositoryFactory interface {
	CreateRepository(session any) (domainrepos.AgentRepository, error)
}

// repoProviderFactoryBackend is the consumer-side boundary to the infrastructure
// repository factories and concrete repository constructors. It bundles the lazy
// imports performed inside each RepositoryProviderService method.
type repoProviderFactoryBackend interface {
	NewTaskRepositoryFactory() repoProviderTaskRepositoryFactory
	NewORMTaskRepository(session any, gitBranchID *string, projectID *string, gitBranchName string, userID *string) (domainrepos.TaskRepository, error)
	NewSubtaskRepositoryFactory() repoProviderSubtaskRepositoryFactory
	CreateProjectRepository(userID *string) (domainrepos.ProjectRepository, error)
	NewAgentRepositoryFactory() repoProviderAgentRepositoryFactory
	CreateGitBranchRepository(userID *string) (domainrepos.GitBranchRepository, error)
	NewGlobalContextRepository(session any) (domainrepos.ContextRepository, error)
	NewProjectContextRepository(session any) (domainrepos.ContextRepository, error)
	NewBranchContextRepository(session any) (domainrepos.ContextRepository, error)
	NewTaskContextRepository(session any) (domainrepos.ContextRepository, error)
	NewTokenRepository(session any) (domainrepos.ITokenRepository, error)
}

// repoProviderFactoryBackendProvider supplies the backend during wiring. Python
// imports the factories lazily; the Go application layer must not import
// infrastructure, so the concrete backend is injected here.
var repoProviderFactoryBackendProvider func() repoProviderFactoryBackend

// RepositoryProviderService provides repository instances to the application layer
// (Python application/services/repository_provider_service.py).
type RepositoryProviderService struct {
	// mu guards repoProviderRepositories: the singleton is shared by HTTP goroutines.
	mu                       *sync.Mutex
	repoProviderRepositories map[string]any
	repoProviderFactories    repoProviderFactoryBackend
}

// repoProviderInstance is the class-level singleton (Python _instance).
var (
	repoProviderInstance   *RepositoryProviderService
	repoProviderInstanceMu sync.Mutex
)

// GetInstance mirrors the get_instance classmethod.
func (RepositoryProviderService) GetInstance() *RepositoryProviderService {
	repoProviderInstanceMu.Lock()
	defer repoProviderInstanceMu.Unlock()
	if repoProviderInstance == nil {
		repoProviderInstance = &RepositoryProviderService{mu: &sync.Mutex{}, repoProviderRepositories: map[string]any{}}
		if repoProviderFactoryBackendProvider != nil {
			repoProviderInstance.repoProviderFactories = repoProviderFactoryBackendProvider()
		}
	}
	return repoProviderInstance
}

// GetTaskRepository gets a task repository instance. git_branch_name defaults to "main".
func (s *RepositoryProviderService) GetTaskRepository(projectID *string, gitBranchName *string, userID *string, session any) (domainrepos.TaskRepository, error) {
	branchName := "main"
	if gitBranchName != nil && *gitBranchName != "" {
		branchName = *gitBranchName
	}
	if projectID == nil {
		return s.repoProviderFactories.NewORMTaskRepository(session, nil, nil, branchName, userID)
	}
	return s.repoProviderFactories.NewTaskRepositoryFactory().CreateRepository(*projectID, branchName, userID)
}

// GetSubtaskRepository gets a subtask repository instance.
func (s *RepositoryProviderService) GetSubtaskRepository(projectID *string, gitBranchName *string, userID *string, session any) (domainrepos.SubtaskRepository, error) {
	branchName := "main"
	if gitBranchName != nil && *gitBranchName != "" {
		branchName = *gitBranchName
	}
	factory := s.repoProviderFactories.NewSubtaskRepositoryFactory()
	if projectID == nil {
		return factory.CreateORMSubtaskRepository(userID)
	}
	return factory.CreateSubtaskRepository(*projectID, branchName, userID)
}

// GetProjectRepository gets a project repository instance.
func (s *RepositoryProviderService) GetProjectRepository(userID *string, session any) (domainrepos.ProjectRepository, error) {
	return s.repoProviderFactories.CreateProjectRepository(userID)
}

// GetAgentRepository gets an agent repository instance. The factory is cached under
// "agent" and create_repository is called each time, as in Python.
func (s *RepositoryProviderService) GetAgentRepository(session any) (domainrepos.AgentRepository, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if _, ok := s.repoProviderRepositories["agent"]; !ok {
		s.repoProviderRepositories["agent"] = s.repoProviderFactories.NewAgentRepositoryFactory()
	}
	factory := s.repoProviderRepositories["agent"].(repoProviderAgentRepositoryFactory)
	return factory.CreateRepository(session)
}

// GetGitBranchRepository gets a git branch repository instance.
func (s *RepositoryProviderService) GetGitBranchRepository(session any, userID *string) (domainrepos.GitBranchRepository, error) {
	return s.repoProviderFactories.CreateGitBranchRepository(userID)
}

// GetGlobalContextRepository gets a global context repository instance (cached).
func (s *RepositoryProviderService) GetGlobalContextRepository(session any) (domainrepos.ContextRepository, error) {
	return s.contextRepository("global_context", session, s.repoProviderFactories.NewGlobalContextRepository)
}

// GetProjectContextRepository gets a project context repository instance (cached).
func (s *RepositoryProviderService) GetProjectContextRepository(session any) (domainrepos.ContextRepository, error) {
	return s.contextRepository("project_context", session, s.repoProviderFactories.NewProjectContextRepository)
}

// GetBranchContextRepository gets a branch context repository instance (cached).
func (s *RepositoryProviderService) GetBranchContextRepository(session any) (domainrepos.ContextRepository, error) {
	return s.contextRepository("branch_context", session, s.repoProviderFactories.NewBranchContextRepository)
}

// GetTaskContextRepository gets a task context repository instance (cached).
func (s *RepositoryProviderService) GetTaskContextRepository(session any) (domainrepos.ContextRepository, error) {
	return s.contextRepository("task_context", session, s.repoProviderFactories.NewTaskContextRepository)
}

// contextRepository implements the shared cache-then-construct pattern for the four
// context repositories.
func (s *RepositoryProviderService) contextRepository(cacheKey string, session any, construct func(any) (domainrepos.ContextRepository, error)) (domainrepos.ContextRepository, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if _, ok := s.repoProviderRepositories[cacheKey]; !ok {
		repository, err := construct(session)
		if err != nil {
			return nil, err
		}
		s.repoProviderRepositories[cacheKey] = repository
	}
	return s.repoProviderRepositories[cacheKey].(domainrepos.ContextRepository), nil
}

// GetTokenRepository gets a token repository instance (cached).
func (s *RepositoryProviderService) GetTokenRepository(session any) (domainrepos.ITokenRepository, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if _, ok := s.repoProviderRepositories["token"]; !ok {
		repository, err := s.repoProviderFactories.NewTokenRepository(session)
		if err != nil {
			return nil, err
		}
		s.repoProviderRepositories["token"] = repository
	}
	return s.repoProviderRepositories["token"].(domainrepos.ITokenRepository), nil
}

// ClearCache clears all cached repository instances.
func (s *RepositoryProviderService) ClearCache() {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.repoProviderRepositories = map[string]any{}
}

// Exported names for the factory backend, for the composition root.
type (
	RepositoryProviderBackend            = repoProviderFactoryBackend
	RepositoryProviderTaskFactoryPort    = repoProviderTaskRepositoryFactory
	RepositoryProviderSubtaskFactoryPort = repoProviderSubtaskRepositoryFactory
	RepositoryProviderAgentFactoryPort   = repoProviderAgentRepositoryFactory
)

// SetRepositoryProviderBackend wires the infrastructure factories used by
// RepositoryProviderService.GetInstance.
func SetRepositoryProviderBackend(provider func() RepositoryProviderBackend) {
	repoProviderFactoryBackendProvider = provider
}
