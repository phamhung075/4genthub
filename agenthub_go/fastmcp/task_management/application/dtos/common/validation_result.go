package common

// ValidationResult is the result of input validation.
type ValidationResult struct {
	IsValid  bool
	Errors   []string
	Warnings []string
}

// AddError mirrors add_error: it appends the error and marks the result invalid.
func (r *ValidationResult) AddError(err string) {
	r.Errors = append(r.Errors, err)
	r.IsValid = false
}

// AddWarning mirrors add_warning.
func (r *ValidationResult) AddWarning(warning string) {
	r.Warnings = append(r.Warnings, warning)
}
