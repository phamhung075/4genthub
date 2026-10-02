package value_objects

import tmvo "agenthub/fastmcp/task_management/domain/value_objects"

// UserAgentInstanceId is a value object for a UserAgentInstance ID, represented as a UUID in canonical format.
type UserAgentInstanceId struct{ tmvo.EntityId }

// NewUserAgentInstanceId validates value and normalizes it to canonical UUID format.
func NewUserAgentInstanceId(value string) (UserAgentInstanceId, error) {
	id, err := tmvo.NewTypedEntityId("UserAgentInstanceId", value)
	return UserAgentInstanceId{id}, err
}

// GenerateNewUserAgentInstanceId creates a new unique UserAgentInstanceId using UUIDv4 (Python generate_new).
func GenerateNewUserAgentInstanceId() UserAgentInstanceId {
	return UserAgentInstanceId{tmvo.EntityId{Value: tmvo.NewUUIDv4()}}
}
