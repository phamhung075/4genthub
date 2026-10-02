// Package services ports agent_management/domain/services.
package services

import (
	"context"

	"agenthub/fastmcp/agent_management/domain/entities"
	"agenthub/fastmcp/agent_management/domain/repositories"
	"agenthub/fastmcp/agent_management/domain/value_objects"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// AgentInstantiationService creates user-specific agent instances from templates; each
// user has at most one instance per template.
type AgentInstantiationService struct {
	TemplateRepository repositories.AgentTemplateRepository
	InstanceRepository repositories.UserAgentInstanceRepository
}

func NewAgentInstantiationService(templates repositories.AgentTemplateRepository, instances repositories.UserAgentInstanceRepository) *AgentInstantiationService {
	return &AgentInstantiationService{TemplateRepository: templates, InstanceRepository: instances}
}

// GetOrCreateInstance returns the user's instance of the template (creating it from the
// template defaults when missing), or nil when the template is not found.
func (s *AgentInstantiationService) GetOrCreateInstance(ctx context.Context, userID *value_objects.UserId, templateSlug string) (*entities.UserAgentInstance, error) {
	if userID == nil {
		return nil, tmvo.ValueErrorf("user_id is required")
	}
	if tmvo.PyStrip(templateSlug) == "" {
		return nil, tmvo.ValueErrorf("template_slug cannot be empty")
	}
	template, err := s.TemplateRepository.FindBySlug(ctx, templateSlug)
	if err != nil || template == nil {
		return nil, err
	}
	if template.ID == nil {
		return nil, tmvo.TypeErrorf("template has no id")
	}
	existing, err := s.InstanceRepository.FindByUserAndTemplate(ctx, *userID, *template.ID)
	if err != nil {
		return nil, err
	}
	if existing != nil {
		return existing, nil
	}
	created, err := s.createInstanceFromTemplate(userID, template)
	if err != nil {
		return nil, err
	}
	return s.InstanceRepository.Save(ctx, created)
}

func (s *AgentInstantiationService) createInstanceFromTemplate(userID *value_objects.UserId, template *entities.AgentTemplate) (*entities.UserAgentInstance, error) {
	configuration, err := template.GetConfigurationCopy()
	if err != nil {
		return nil, err
	}
	id := value_objects.GenerateNewUserAgentInstanceId()
	metadata := tmentities.NewOrderedMap[any]()
	metadata.Set("instantiated_from_template", template.ID.String())
	metadata.Set("template_slug", template.Slug)
	metadata.Set("template_version", template.Version)

	instance := entities.DefaultUserAgentInstance()
	instance.ID = &id
	instance.UserID = userID
	instance.TemplateID = template.ID
	instance.AgentName = template.Name
	instance.Configuration = &configuration
	instance.Metadata = metadata
	return entities.NewUserAgentInstance(instance)
}

// GetInstanceByID returns the instance or nil.
func (s *AgentInstantiationService) GetInstanceByID(ctx context.Context, instanceID value_objects.UserAgentInstanceId) (*entities.UserAgentInstance, error) {
	return s.InstanceRepository.FindByID(ctx, instanceID)
}

// GetInstancesForUser returns every instance owned by the user.
func (s *AgentInstantiationService) GetInstancesForUser(ctx context.Context, userID value_objects.UserId) ([]*entities.UserAgentInstance, error) {
	return s.InstanceRepository.FindByUser(ctx, userID)
}
