package services

import (
	"fmt"
	"sync"
)

// FacadeService ports application/services/facade_service.py.
//
// Python returns untyped facades; the Go facades package imports this services
// package, so to avoid an import cycle the getters return `any` (matching the
// missing Python return annotations). Factory dependencies are the minimal
// interfaces below; callers wire in the existing factories.
type taskFacadeFactory interface {
	CreateTaskFacade(projectID, gitBranchID, userID *string) (any, error)
}

type subtaskFacadeFactory interface {
	CreateFacade(projectID, gitBranchID, userID, taskID *string) (any, error)
}

type projectFacadeFactory interface {
	CreateProjectFacade(userID *string) (any, error)
}

type gitBranchFacadeFactory interface {
	CreateFacade(projectID, userID *string) (any, error)
}

type unifiedContextFacadeFactory interface {
	CreateFacade(userID, projectID, gitBranchID *string) (any, error)
}

type tokenFacadeFactory interface {
	CreateTokenFacade() (any, error)
}

// FacadeService is the single point of contact for the interface layer.
type FacadeService struct {
	taskFactory    taskFacadeFactory
	subtaskFactory subtaskFacadeFactory
	projectFactory projectFacadeFactory
	branchFactory  gitBranchFacadeFactory
	contextFactory unifiedContextFacadeFactory
	tokenFactory   tokenFacadeFactory
	authFactory    func() (any, error)
}

var (
	facadeServiceMu       sync.Mutex
	facadeServiceInstance *FacadeService
)

// SetInstance installs the singleton returned by GetInstance. Python builds a
// default FacadeService lazily from its module-level factory singletons; Go has
// no such singletons, so the composition root must call this once at startup.
func SetInstance(s *FacadeService) {
	facadeServiceMu.Lock()
	defer facadeServiceMu.Unlock()
	facadeServiceInstance = s
}

// GetInstance ports the get_instance classmethod (nil until SetInstance ran).
func GetInstance() *FacadeService {
	facadeServiceMu.Lock()
	defer facadeServiceMu.Unlock()
	return facadeServiceInstance
}

// WithAuthFacadeFactory sets the factory used by GetAuthFacade (Python builds
// AuthApplicationFacade() directly, with no factory).
func (s *FacadeService) WithAuthFacadeFactory(f func() (any, error)) *FacadeService {
	s.authFactory = f
	return s
}

// GetAuthFacade returns an auth facade.
func (s *FacadeService) GetAuthFacade() (any, error) {
	return s.authFactory()
}

// GetUnifiedContextFacade ports the get_unified_context_facade classmethod: a
// shortcut through the singleton instance.
func GetUnifiedContextFacade(userID, projectID, gitBranchID *string) (any, error) {
	return GetInstance().GetContextFacade(userID, projectID, gitBranchID)
}

// NewFacadeService builds a facade service. Dependencies may be nil when the
// corresponding getter is not used, mirroring Python's lazy imports.
func NewFacadeService(
	taskFactory taskFacadeFactory,
	subtaskFactory subtaskFacadeFactory,
	projectFactory projectFacadeFactory,
	branchFactory gitBranchFacadeFactory,
	contextFactory unifiedContextFacadeFactory,
	tokenFactory tokenFacadeFactory,
) *FacadeService {
	return &FacadeService{
		taskFactory:    taskFactory,
		subtaskFactory: subtaskFactory,
		projectFactory: projectFactory,
		branchFactory:  branchFactory,
		contextFactory: contextFactory,
		tokenFactory:   tokenFactory,
	}
}

// GetTaskFacade returns a task facade with the given context.
func (s *FacadeService) GetTaskFacade(projectID, gitBranchID, userID *string) (any, error) {
	if s.taskFactory == nil {
		return nil, errFactoryNotConfigured("task")
	}
	return s.taskFactory.CreateTaskFacade(projectID, gitBranchID, userID)
}

// GetSubtaskFacade returns a subtask facade with the given context.
func (s *FacadeService) GetSubtaskFacade(projectID, gitBranchID, userID, taskID *string) (any, error) {
	if s.subtaskFactory == nil {
		return nil, errFactoryNotConfigured("subtask")
	}
	return s.subtaskFactory.CreateFacade(projectID, gitBranchID, userID, taskID)
}

// GetProjectFacade returns a project facade with the given context.
func (s *FacadeService) GetProjectFacade(userID *string) (any, error) {
	if s.projectFactory == nil {
		return nil, errFactoryNotConfigured("project")
	}
	return s.projectFactory.CreateProjectFacade(userID)
}

// GetBranchFacade returns a git branch facade with the given context.
func (s *FacadeService) GetBranchFacade(projectID, userID *string) (any, error) {
	if s.branchFactory == nil {
		return nil, errFactoryNotConfigured("git branch")
	}
	return s.branchFactory.CreateFacade(projectID, userID)
}

// GetContextFacade returns a unified context facade with the given context.
func (s *FacadeService) GetContextFacade(userID, projectID, gitBranchID *string) (any, error) {
	if s.contextFactory == nil {
		return nil, errFactoryNotConfigured("unified context")
	}
	return s.contextFactory.CreateFacade(userID, projectID, gitBranchID)
}

// GetTokenFacade returns a token facade.
func (s *FacadeService) GetTokenFacade() (any, error) {
	if s.tokenFactory == nil {
		return nil, errFactoryNotConfigured("token")
	}
	return s.tokenFactory.CreateTokenFacade()
}

// errFactoryNotConfigured replaces the nil dereference of a facade factory the
// composition root did not wire.
func errFactoryNotConfigured(name string) error {
	return fmt.Errorf("%s facade factory is not configured", name)
}
