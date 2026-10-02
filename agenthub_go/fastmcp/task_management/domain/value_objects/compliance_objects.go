package value_objects

import "time"

// DocumentType: document types for compliance.
type DocumentType string

const (
	DocumentTypeConfig   DocumentType = "config"
	DocumentTypeTemplate DocumentType = "template"
	DocumentTypeDocument DocumentType = "document"
	DocumentTypeAudit    DocumentType = "audit"
	DocumentTypeReport   DocumentType = "report"
)

// DocumentInfo is a document information value object.
type DocumentInfo struct {
	Path      string
	Type      DocumentType
	Content   string
	Metadata  map[string]any
	CreatedAt time.Time
	UpdatedAt *time.Time
	Hash      *string
}

// NewDocumentInfo validates that path and content are non-empty.
func NewDocumentInfo(path string, typ DocumentType, content string, metadata map[string]any, createdAt time.Time) (DocumentInfo, error) {
	if path == "" {
		return DocumentInfo{}, valueErrorf("Document path cannot be empty")
	}
	if content == "" {
		return DocumentInfo{}, valueErrorf("Document content cannot be empty")
	}
	return DocumentInfo{Path: path, Type: typ, Content: content, Metadata: metadata, CreatedAt: createdAt}, nil
}

// ComplianceObjectsComplianceStatus is compliance_objects.ComplianceStatus (the
// dataclass); compliance_enums.ComplianceStatus owns the plain name.
type ComplianceObjectsComplianceStatus struct {
	IsCompliant    bool
	ValidationDate time.Time
	Validator      string
	Issues         []string
	Metadata       map[string]any
}

// ComplianceObjectsValidationResult is compliance_objects.ValidationResult (the
// dataclass); compliance_enums.ValidationResult owns the plain name.
type ComplianceObjectsValidationResult struct {
	IsValid  bool
	Errors   []string
	Warnings []string
	Metadata map[string]any
}

// ValidationReport is a comprehensive validation report.
type ValidationReport struct {
	ValidationID        string
	EntityID            string
	EntityType          string
	ValidationTimestamp time.Time
	Results             []ComplianceObjectsValidationResult
	OverallStatus       bool
	Summary             string
	Recommendations     []string
	Metadata            map[string]any
}

// TotalErrors sums errors across all results.
func (r ValidationReport) TotalErrors() int {
	n := 0
	for _, res := range r.Results {
		n += len(res.Errors)
	}
	return n
}

// TotalWarnings sums warnings across all results.
func (r ValidationReport) TotalWarnings() int {
	n := 0
	for _, res := range r.Results {
		n += len(res.Warnings)
	}
	return n
}

// HasIssues: any error or warning.
func (r ValidationReport) HasIssues() bool { return r.TotalErrors() > 0 || r.TotalWarnings() > 0 }
