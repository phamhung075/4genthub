package value_objects

// ProjectId is a Value object for a Project ID, represented as a UUID in canonical format.
type ProjectId struct{ EntityId }

// NewProjectId validates value and normalizes it to canonical UUID format.
func NewProjectId(value string) (ProjectId, error) {
	id, err := newEntityId("ProjectId", value)
	return ProjectId{id}, err
}

// GenerateNewProjectId creates a new unique ProjectId using UUIDv4 (Python generate_new).
func GenerateNewProjectId() ProjectId { return ProjectId{EntityId{Value: NewUUIDv4()}} }
