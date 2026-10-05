package repositories

import (
	"context"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// TemplateListFilter carries list_templates' optional filters; nil means unfiltered.
// Build it with NewTemplateListFilter to get the Python defaults (limit 50, offset 0);
// a literal struct has Limit 0, which Python treats as an explicit limit of 0.
type TemplateListFilter struct {
	TemplateType    *string
	Category        *string
	AgentCompatible *string
	IsActive        *bool
	Limit           int // Python default 50
	Offset          int
}

// NewTemplateListFilter returns an unfiltered filter with the Python defaults.
func NewTemplateListFilter() TemplateListFilter { return TemplateListFilter{Limit: 50} }

// TemplateRepositoryInterface is the repository interface for templates.
type TemplateRepositoryInterface interface {
	Save(ctx context.Context, template *entities.Template) (*entities.Template, error)
	GetByID(ctx context.Context, templateID value_objects.TemplateId) (*entities.Template, error)
	// ListTemplates returns the page of templates and the total count.
	ListTemplates(ctx context.Context, filter TemplateListFilter) ([]*entities.Template, int, error)
	Delete(ctx context.Context, templateID value_objects.TemplateId) (bool, error)
	SaveUsage(ctx context.Context, usage entities.TemplateUsage) (bool, error)
	GetUsageStats(ctx context.Context, templateID value_objects.TemplateId) (map[string]any, error)
	// GetAnalytics: templateID nil means all templates.
	GetAnalytics(ctx context.Context, templateID *string) (map[string]any, error)
}
