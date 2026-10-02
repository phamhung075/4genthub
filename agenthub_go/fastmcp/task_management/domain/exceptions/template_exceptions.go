package exceptions

import "fmt"

// TemplateError is the base template exception.
type TemplateError struct {
	Msg        string
	TemplateID *string
}

func (e *TemplateError) Error() string { return e.Msg }

func newTemplateError(message string, templateID *string) TemplateError {
	return TemplateError{message, templateID}
}

// TemplateNotFoundError: template not found.
type TemplateNotFoundError struct{ TemplateError }

func (e *TemplateNotFoundError) Unwrap() error { return &e.TemplateError }

func NewTemplateNotFoundError(templateID string) *TemplateNotFoundError {
	return &TemplateNotFoundError{newTemplateError(fmt.Sprintf("Template not found: %s", templateID), &templateID)}
}

func nonNilStrings(s []string) []string {
	if s == nil {
		return []string{}
	}
	return s
}

func nonNilMap(m map[string]any) map[string]any {
	if m == nil {
		return map[string]any{}
	}
	return m
}

// TemplateValidationError: template validation failed.
type TemplateValidationError struct {
	TemplateError
	ValidationErrors []string
}

func (e *TemplateValidationError) Unwrap() error { return &e.TemplateError }

func NewTemplateValidationError(message string, templateID *string, validationErrors []string) *TemplateValidationError {
	return &TemplateValidationError{newTemplateError(message, templateID), nonNilStrings(validationErrors)}
}

// TemplateRenderError: template rendering failed.
type TemplateRenderError struct {
	TemplateError
	RenderContext map[string]any
}

func (e *TemplateRenderError) Unwrap() error { return &e.TemplateError }

func NewTemplateRenderError(message string, templateID *string, renderContext map[string]any) *TemplateRenderError {
	return &TemplateRenderError{newTemplateError(message, templateID), nonNilMap(renderContext)}
}

// TemplateCompilationError: template compilation failed.
type TemplateCompilationError struct {
	TemplateError
	CompilationErrors []string
}

func (e *TemplateCompilationError) Unwrap() error { return &e.TemplateError }

func NewTemplateCompilationError(message string, templateID *string, compilationErrors []string) *TemplateCompilationError {
	return &TemplateCompilationError{newTemplateError(message, templateID), nonNilStrings(compilationErrors)}
}

// TemplateVariableError: template variable problem.
type TemplateVariableError struct {
	TemplateError
	VariableName *string
}

func (e *TemplateVariableError) Unwrap() error { return &e.TemplateError }

func NewTemplateVariableError(message string, templateID, variableName *string) *TemplateVariableError {
	return &TemplateVariableError{newTemplateError(message, templateID), variableName}
}

// TemplatePermissionError: template permission problem.
type TemplatePermissionError struct {
	TemplateError
	RequiredPermission *string
}

func (e *TemplatePermissionError) Unwrap() error { return &e.TemplateError }

func NewTemplatePermissionError(message string, templateID, requiredPermission *string) *TemplatePermissionError {
	return &TemplatePermissionError{newTemplateError(message, templateID), requiredPermission}
}

// TemplateVersionError: template version problem.
type TemplateVersionError struct {
	TemplateError
	Version *int
}

func (e *TemplateVersionError) Unwrap() error { return &e.TemplateError }

func NewTemplateVersionError(message string, templateID *string, version *int) *TemplateVersionError {
	return &TemplateVersionError{newTemplateError(message, templateID), version}
}

// TemplateCacheError: template cache problem.
type TemplateCacheError struct {
	TemplateError
	CacheKey *string
}

func (e *TemplateCacheError) Unwrap() error { return &e.TemplateError }

func NewTemplateCacheError(message string, templateID, cacheKey *string) *TemplateCacheError {
	return &TemplateCacheError{newTemplateError(message, templateID), cacheKey}
}

// TemplateCompatibilityError: template compatibility problem.
type TemplateCompatibilityError struct {
	TemplateError
	AgentName *string
}

func (e *TemplateCompatibilityError) Unwrap() error { return &e.TemplateError }

func NewTemplateCompatibilityError(message string, templateID, agentName *string) *TemplateCompatibilityError {
	return &TemplateCompatibilityError{newTemplateError(message, templateID), agentName}
}

// TemplateRegistrationError: template registration failed.
type TemplateRegistrationError struct {
	TemplateError
	RegistrationErrors []string
}

func (e *TemplateRegistrationError) Unwrap() error { return &e.TemplateError }

func NewTemplateRegistrationError(message string, templateID *string, registrationErrors []string) *TemplateRegistrationError {
	return &TemplateRegistrationError{newTemplateError(message, templateID), nonNilStrings(registrationErrors)}
}

// TemplateUsageError: template usage tracking failed.
type TemplateUsageError struct {
	TemplateError
	UsageData map[string]any
}

func (e *TemplateUsageError) Unwrap() error { return &e.TemplateError }

func NewTemplateUsageError(message string, templateID *string, usageData map[string]any) *TemplateUsageError {
	return &TemplateUsageError{newTemplateError(message, templateID), nonNilMap(usageData)}
}
