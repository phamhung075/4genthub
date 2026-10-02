package interfacelayer

// Facade Provider for Interface Layer (Python facade_provider.py).
//
// Python uses FacadeService.get_instance() and class-level caches. The Go
// FacadeService has no singleton accessor, so the service is injected via
// SetFacadeService / the DefaultFacadeService package variable and caches live
// on the provider value. get_auth_facade is omitted: the Go FacadeService has
// no GetAuthFacade method.

import (
	"fmt"

	services "agenthub/fastmcp/task_management/application/services"
)

// DefaultFacadeService is used when a provider is created without an explicit
// service.
var DefaultFacadeService *services.FacadeService

// SetFacadeService replaces the process-wide default facade service.
func SetFacadeService(service *services.FacadeService) {
	DefaultFacadeService = service
}

// FacadeProvider ports FacadeProvider.
type FacadeProvider struct {
	service *services.FacadeService

	taskFacade    any
	subtaskFacade any
	projectFacade any
	branchFacade  any
	agentFacade   any
	contextFacade any
	tokenFacade   any
}

// NewFacadeProvider creates a provider; a nil service falls back to
// DefaultFacadeService.
func NewFacadeProvider(service *services.FacadeService) *FacadeProvider {
	if service == nil {
		service = DefaultFacadeService
	}
	return &FacadeProvider{service: service}
}

func (p *FacadeProvider) requireService() (*services.FacadeService, error) {
	if p.service == nil {
		return nil, fmt.Errorf("facade service not configured")
	}
	return p.service, nil
}

// GetTaskFacade ports get_task_facade(session=None, user_id=None).
func (p *FacadeProvider) GetTaskFacade(userID *string) (any, error) {
	if p.taskFacade == nil {
		service, err := p.requireService()
		if err != nil {
			return nil, err
		}
		v, err := service.GetTaskFacade(nil, nil, userID)
		if err != nil {
			return nil, err
		}
		p.taskFacade = v
	}
	return p.taskFacade, nil
}

// GetSubtaskFacade ports get_subtask_facade(session=None, user_id=None).
func (p *FacadeProvider) GetSubtaskFacade(userID *string) (any, error) {
	if p.subtaskFacade == nil {
		service, err := p.requireService()
		if err != nil {
			return nil, err
		}
		v, err := service.GetSubtaskFacade(nil, nil, userID, nil)
		if err != nil {
			return nil, err
		}
		p.subtaskFacade = v
	}
	return p.subtaskFacade, nil
}

// GetProjectFacade ports get_project_facade(session=None, user_id=None).
func (p *FacadeProvider) GetProjectFacade(userID *string) (any, error) {
	if p.projectFacade == nil {
		service, err := p.requireService()
		if err != nil {
			return nil, err
		}
		v, err := service.GetProjectFacade(userID)
		if err != nil {
			return nil, err
		}
		p.projectFacade = v
	}
	return p.projectFacade, nil
}

// GetBranchFacade ports get_branch_facade(session=None, user_id=None).
func (p *FacadeProvider) GetBranchFacade(userID *string) (any, error) {
	if p.branchFacade == nil {
		service, err := p.requireService()
		if err != nil {
			return nil, err
		}
		v, err := service.GetBranchFacade(nil, userID)
		if err != nil {
			return nil, err
		}
		p.branchFacade = v
	}
	return p.branchFacade, nil
}

// GetAgentFacade ports get_agent_facade(session=None, user_id=None). The Go
// service additionally needs a project id, which Python does not pass here.
func (p *FacadeProvider) GetAgentFacade(userID *string) (any, error) {
	if p.agentFacade == nil {
		service, err := p.requireService()
		if err != nil {
			return nil, err
		}
		v, err := service.GetAgentFacade("", userID)
		if err != nil {
			return nil, err
		}
		p.agentFacade = v
	}
	return p.agentFacade, nil
}

// GetContextFacade ports get_context_facade(session=None, user_id=None).
func (p *FacadeProvider) GetContextFacade(userID *string) (any, error) {
	if p.contextFacade == nil {
		service, err := p.requireService()
		if err != nil {
			return nil, err
		}
		v, err := service.GetContextFacade(userID, nil, nil)
		if err != nil {
			return nil, err
		}
		p.contextFacade = v
	}
	return p.contextFacade, nil
}

// GetTokenFacade ports get_token_facade(session=None, user_id=None).
func (p *FacadeProvider) GetTokenFacade() (any, error) {
	if p.tokenFacade == nil {
		service, err := p.requireService()
		if err != nil {
			return nil, err
		}
		v, err := service.GetTokenFacade()
		if err != nil {
			return nil, err
		}
		p.tokenFacade = v
	}
	return p.tokenFacade, nil
}

// ClearCache ports clear_cache().
func (p *FacadeProvider) ClearCache() {
	p.taskFacade = nil
	p.subtaskFacade = nil
	p.projectFacade = nil
	p.branchFacade = nil
	p.agentFacade = nil
	p.contextFacade = nil
	p.tokenFacade = nil
}
