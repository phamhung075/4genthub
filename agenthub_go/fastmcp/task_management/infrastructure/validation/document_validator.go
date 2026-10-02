// Package validation ports task_management/infrastructure/validation.
package validation

import "errors"

// DocumentType is the simplified document type enum.
type DocumentType string

const (
	DocumentTypeConfig   DocumentType = "config"
	DocumentTypeTemplate DocumentType = "template"
	DocumentTypeDocument DocumentType = "document"
)

// DocumentTypeValues lists all members in declaration order.
var DocumentTypeValues = []DocumentType{DocumentTypeConfig, DocumentTypeTemplate, DocumentTypeDocument}

func (e DocumentType) String() string { return string(e) }

// DocumentValidator is the infrastructure service for document validation.
// PYTHON DEFECT (preserved): DocumentValidator.__init__ builds validation_patterns
// with DocumentType.AI_GENERATED and DocumentType.SYSTEM_CONFIG, which the
// simplified DocumentType enum no longer defines, so DocumentValidator() always
// raises AttributeError and no instance (hence none of its methods) is reachable.
type DocumentValidator struct{}

// NewDocumentValidator always fails like the Python constructor.
func NewDocumentValidator() (*DocumentValidator, error) {
	return nil, errors.New("type object 'DocumentType' has no attribute 'AI_GENERATED'")
}
