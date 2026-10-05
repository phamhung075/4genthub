package value_objects

// AgentId is a Value object for a Agent ID, represented as a UUID in canonical format.
type AgentId struct{ EntityId }

// NewAgentId validates value and normalizes it to canonical UUID format.
func NewAgentId(value string) (AgentId, error) {
	id, err := newEntityId("AgentId", value)
	return AgentId{id}, err
}

// GenerateNewAgentId creates a new unique AgentId using UUIDv4 (Python generate_new).
func GenerateNewAgentId() AgentId { return AgentId{EntityId{Value: NewUUIDv4()}} }
