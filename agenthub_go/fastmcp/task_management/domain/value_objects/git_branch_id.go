package value_objects

// GitBranchId is a Value object for a Git Branch ID, represented as a UUID in canonical format.
type GitBranchId struct{ EntityId }

// NewGitBranchId validates value and normalizes it to canonical UUID format.
func NewGitBranchId(value string) (GitBranchId, error) {
	id, err := newEntityId("GitBranchId", value)
	return GitBranchId{id}, err
}

// GenerateNewGitBranchId creates a new unique GitBranchId using UUIDv4 (Python generate_new).
func GenerateNewGitBranchId() GitBranchId { return GitBranchId{EntityId{Value: NewUUIDv4()}} }
