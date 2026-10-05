package interfaces

// ValidationSeverity is the validation severity enumeration.
type ValidationSeverity string

const (
	ValidationSeverityInfo     ValidationSeverity = "info"
	ValidationSeverityWarning  ValidationSeverity = "warning"
	ValidationSeverityError    ValidationSeverity = "error"
	ValidationSeverityCritical ValidationSeverity = "critical"
)

// ValidationSeverityValues lists the severities in declaration order.
var ValidationSeverityValues = []ValidationSeverity{ValidationSeverityInfo, ValidationSeverityWarning, ValidationSeverityError, ValidationSeverityCritical}

// IValidationResult is a validation outcome (Python properties become methods).
type IValidationResult interface {
	IsValid() bool
	Errors() []string
	Warnings() []string
	Details() map[string]any
}

// IValidator validates arbitrary data.
type IValidator interface {
	Validate(data any) IValidationResult
	ValidationRules() []string
}

// IDocumentValidator validates documents against schemas.
type IDocumentValidator interface {
	ValidateDocument(document map[string]any) IValidationResult
	ValidateSchema(document, schema map[string]any) IValidationResult
	// GetSchema returns the schema for a document type, or nil.
	GetSchema(documentType string) map[string]any
}

// IValidationService routes validation by data type.
type IValidationService interface {
	RegisterValidator(dataType string, validator IValidator)
	UnregisterValidator(dataType string) bool
	Validate(dataType string, data any) IValidationResult
	ValidateAll(data map[string]any) map[string]IValidationResult
	GetValidator(dataType string) IValidator
	ListValidators() []string
}
