package value_objects

// TemplateId is a Value object for a Template ID, represented as a UUID in canonical format.
type TemplateId struct{ EntityId }

// NewTemplateId validates value and normalizes it to canonical UUID format.
func NewTemplateId(value string) (TemplateId, error) {
	id, err := newEntityId("TemplateId", value)
	return TemplateId{id}, err
}

// GenerateNewTemplateId creates a new unique TemplateId using UUIDv4 (Python generate_new).
func GenerateNewTemplateId() TemplateId { return TemplateId{EntityId{Value: NewUUIDv4()}} }
