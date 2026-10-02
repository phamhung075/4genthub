package value_objects

import tmvo "agenthub/fastmcp/task_management/domain/value_objects"

// UserId is a value object for a User ID, represented as a UUID in canonical format.
type UserId struct{ tmvo.EntityId }

// NewUserId validates value and normalizes it to canonical UUID format.
func NewUserId(value string) (UserId, error) {
	id, err := tmvo.NewTypedEntityId("UserId", value)
	return UserId{id}, err
}

// GenerateNewUserId creates a new unique UserId using UUIDv4 (Python generate_new).
func GenerateNewUserId() UserId { return UserId{tmvo.EntityId{Value: tmvo.NewUUIDv4()}} }
