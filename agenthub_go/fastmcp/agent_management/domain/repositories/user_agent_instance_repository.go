package repositories

import (
	"context"

	"agenthub/fastmcp/agent_management/domain/entities"
	"agenthub/fastmcp/agent_management/domain/enums"
	"agenthub/fastmcp/agent_management/domain/value_objects"
)

// UserAgentInstanceRepository is the repository interface for user agent instances. The
// Find* methods that return one instance return nil when nothing is found.
type UserAgentInstanceRepository interface {
	Save(ctx context.Context, instance *entities.UserAgentInstance) (*entities.UserAgentInstance, error)
	FindByID(ctx context.Context, instanceID value_objects.UserAgentInstanceId) (*entities.UserAgentInstance, error)
	// FindByUserAndTemplate enforces UNIQUE(user_id, template_id).
	FindByUserAndTemplate(ctx context.Context, userID value_objects.UserId, templateID value_objects.AgentTemplateId) (*entities.UserAgentInstance, error)
	FindByUser(ctx context.Context, userID value_objects.UserId) ([]*entities.UserAgentInstance, error)
	FindEnabledByUser(ctx context.Context, userID value_objects.UserId) ([]*entities.UserAgentInstance, error)
	FindByShareToken(ctx context.Context, shareToken string) (*entities.UserAgentInstance, error)
	// FindPublicInstances: Python defaults are limit 50, offset 0, CREATED_DESC.
	FindPublicInstances(ctx context.Context, limit, offset int, orderBy enums.InstanceOrdering) ([]*entities.UserAgentInstance, error)
	ExistsByUserAndTemplate(ctx context.Context, userID value_objects.UserId, templateID value_objects.AgentTemplateId) (bool, error)
	CountByAgentNameForUser(ctx context.Context, userID value_objects.UserId, agentName string) (int, error)
	Delete(ctx context.Context, instanceID value_objects.UserAgentInstanceId) error
}
