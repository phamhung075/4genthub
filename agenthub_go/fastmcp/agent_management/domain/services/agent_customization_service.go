package services

import (
	"context"

	"agenthub/fastmcp/agent_management/domain/entities"
	"agenthub/fastmcp/agent_management/domain/repositories"
	"agenthub/fastmcp/agent_management/domain/value_objects"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// AgentCustomizationService updates agent configurations (system prompt, rules,
// capabilities, output format, tools) of an instance the user owns. Every method returns
// nil (and no error) when the instance is not found or not owned by the user.
type AgentCustomizationService struct {
	InstanceRepository repositories.UserAgentInstanceRepository
}

func NewAgentCustomizationService(instances repositories.UserAgentInstanceRepository) *AgentCustomizationService {
	return &AgentCustomizationService{InstanceRepository: instances}
}

// apply customizes the owned instance with the configuration derived from its current one
// and saves it.
func (s *AgentCustomizationService) apply(ctx context.Context, instanceID value_objects.UserAgentInstanceId, userID value_objects.UserId, notes *string, build func(cur value_objects.AgentConfiguration) (value_objects.AgentConfiguration, error)) (*entities.UserAgentInstance, error) {
	instance, err := getAndVerifyOwnership(ctx, s.InstanceRepository, instanceID, userID)
	if err != nil || instance == nil {
		return nil, err
	}
	next, err := build(*instance.Configuration)
	if err != nil {
		return nil, err
	}
	if err := instance.CustomizeConfiguration(next, notes); err != nil {
		return nil, err
	}
	return s.InstanceRepository.Save(ctx, instance)
}

// UpdateSystemPrompt replaces the system prompt (not empty or whitespace).
func (s *AgentCustomizationService) UpdateSystemPrompt(ctx context.Context, instanceID value_objects.UserAgentInstanceId, userID value_objects.UserId, newSystemPrompt string, notes *string) (*entities.UserAgentInstance, error) {
	if tmvo.PyStrip(newSystemPrompt) == "" {
		return nil, tmvo.ValueErrorf("System prompt cannot be empty")
	}
	return s.apply(ctx, instanceID, userID, notes, func(c value_objects.AgentConfiguration) (value_objects.AgentConfiguration, error) {
		return c.WithSystemPrompt(newSystemPrompt)
	})
}

// UpdateRules replaces the rules.
func (s *AgentCustomizationService) UpdateRules(ctx context.Context, instanceID value_objects.UserAgentInstanceId, userID value_objects.UserId, newRules []string, notes *string) (*entities.UserAgentInstance, error) {
	return s.apply(ctx, instanceID, userID, notes, func(c value_objects.AgentConfiguration) (value_objects.AgentConfiguration, error) {
		return value_objects.NewAgentConfiguration(c.SystemPrompt, c.Tools, c.Capabilities, newRules, c.OutputFormat, c.Metadata)
	})
}

// UpdateCapabilities replaces the capabilities.
func (s *AgentCustomizationService) UpdateCapabilities(ctx context.Context, instanceID value_objects.UserAgentInstanceId, userID value_objects.UserId, newCapabilities *tmentities.OrderedMap[any], notes *string) (*entities.UserAgentInstance, error) {
	return s.apply(ctx, instanceID, userID, notes, func(c value_objects.AgentConfiguration) (value_objects.AgentConfiguration, error) {
		return value_objects.NewAgentConfiguration(c.SystemPrompt, c.Tools, newCapabilities, c.Rules, c.OutputFormat, c.Metadata)
	})
}

// UpdateOutputFormat replaces the output format.
func (s *AgentCustomizationService) UpdateOutputFormat(ctx context.Context, instanceID value_objects.UserAgentInstanceId, userID value_objects.UserId, newOutputFormat *tmentities.OrderedMap[any], notes *string) (*entities.UserAgentInstance, error) {
	return s.apply(ctx, instanceID, userID, notes, func(c value_objects.AgentConfiguration) (value_objects.AgentConfiguration, error) {
		return value_objects.NewAgentConfiguration(c.SystemPrompt, c.Tools, c.Capabilities, c.Rules, newOutputFormat, c.Metadata)
	})
}

// UpdateFullConfiguration replaces the whole configuration.
func (s *AgentCustomizationService) UpdateFullConfiguration(ctx context.Context, instanceID value_objects.UserAgentInstanceId, userID value_objects.UserId, newConfiguration value_objects.AgentConfiguration, notes *string) (*entities.UserAgentInstance, error) {
	return s.apply(ctx, instanceID, userID, notes, func(value_objects.AgentConfiguration) (value_objects.AgentConfiguration, error) {
		return newConfiguration, nil
	})
}

// ResetToTemplateDefaults restores the template configuration, clears the customized flag
// and removes the "last_customization" metadata.
func (s *AgentCustomizationService) ResetToTemplateDefaults(ctx context.Context, instanceID value_objects.UserAgentInstanceId, userID value_objects.UserId, templateConfiguration value_objects.AgentConfiguration) (*entities.UserAgentInstance, error) {
	instance, err := getAndVerifyOwnership(ctx, s.InstanceRepository, instanceID, userID)
	if err != nil || instance == nil {
		return nil, err
	}
	if instance.Metadata == nil {
		return nil, tmvo.TypeErrorf("'NoneType' object has no attribute 'copy'")
	}
	instance.Configuration = &templateConfiguration
	instance.IsCustomized = false
	metadata := instance.Metadata.Copy()
	metadata.Delete("last_customization")
	instance.Metadata = metadata
	return s.InstanceRepository.Save(ctx, instance)
}

// getAndVerifyOwnership returns the instance when it exists and belongs to userID.
func getAndVerifyOwnership(ctx context.Context, repo repositories.UserAgentInstanceRepository, instanceID value_objects.UserAgentInstanceId, userID value_objects.UserId) (*entities.UserAgentInstance, error) {
	instance, err := repo.FindByID(ctx, instanceID)
	if err != nil || instance == nil {
		return nil, err
	}
	if instance.UserID == nil || *instance.UserID != userID {
		return nil, nil
	}
	return instance, nil
}
