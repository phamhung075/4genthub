package value_objects

import tmvo "agenthub/fastmcp/task_management/domain/value_objects"

// AgentTemplateId is a value object for a AgentTemplate ID, represented as a UUID in canonical format.
type AgentTemplateId struct{ tmvo.EntityId }

// NewAgentTemplateId validates value and normalizes it to canonical UUID format.
func NewAgentTemplateId(value string) (AgentTemplateId, error) {
	id, err := tmvo.NewTypedEntityId("AgentTemplateId", value)
	return AgentTemplateId{id}, err
}

// GenerateNewAgentTemplateId creates a new unique AgentTemplateId using UUIDv4 (Python generate_new).
func GenerateNewAgentTemplateId() AgentTemplateId {
	return AgentTemplateId{tmvo.EntityId{Value: tmvo.NewUUIDv4()}}
}
