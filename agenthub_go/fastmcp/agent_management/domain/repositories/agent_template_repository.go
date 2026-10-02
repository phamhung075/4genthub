// Package repositories ports agent_management/domain/repositories (interfaces only; the
// implementations live in the infrastructure layer).
package repositories

import (
	"context"

	"agenthub/fastmcp/agent_management/domain/entities"
	"agenthub/fastmcp/agent_management/domain/value_objects"
)

// AgentTemplateRepository is the repository interface for agent templates. The Find*
// methods return nil when nothing is found.
type AgentTemplateRepository interface {
	// Save returns the saved template with updated timestamps.
	Save(ctx context.Context, template *entities.AgentTemplate) (*entities.AgentTemplate, error)
	FindByID(ctx context.Context, templateID value_objects.AgentTemplateId) (*entities.AgentTemplate, error)
	FindBySlug(ctx context.Context, slug string) (*entities.AgentTemplate, error)
	FindAll(ctx context.Context) ([]*entities.AgentTemplate, error)
	FindByCategory(ctx context.Context, category string) ([]*entities.AgentTemplate, error)
	ExistsBySlug(ctx context.Context, slug string) (bool, error)
	Delete(ctx context.Context, templateID value_objects.AgentTemplateId) error
}
