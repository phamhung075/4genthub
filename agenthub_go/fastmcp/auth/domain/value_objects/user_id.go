package value_objects

import (
	"fmt"

	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// UserId is the validated user id value object. The value is kept as given (Python
// only checks that uuid.UUID() accepts it).
type UserId struct{ Value string }

// NewUserId validates value (dataclass __post_init__).
func NewUserId(value string) (UserId, error) {
	if value == "" {
		return UserId{}, &tmvo.ValueError{Msg: "User ID cannot be empty"}
	}
	if _, ok := tmvo.PyParseUUID(value); !ok {
		return UserId{}, &tmvo.ValueError{Msg: fmt.Sprintf("Invalid user ID format: %s", value)}
	}
	return UserId{value}, nil
}

// GenerateUserId is UserId.generate: a new random UUID.
func GenerateUserId() UserId { return UserId{tmvo.NewUUIDv4()} }

// UserIdFromString is UserId.from_string.
func UserIdFromString(userID string) (UserId, error) { return NewUserId(userID) }

func (u UserId) String() string { return u.Value }
