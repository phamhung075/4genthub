// Package services ports task_management/infrastructure/services.
package services

import "errors"

// TemplateRegistryService manages templates using PostgreSQL.
//
// PYTHON DEFECT (preserved): TemplateRegistryService.__init__ unconditionally
// raises RuntimeError ("Template Registry Service requires refactoring..."), so no
// instance is reachable and none of its methods (all PostgreSQL-backed, and its
// _get_connection also raises) can run. The pure pattern helpers
// (_patterns_match/_extract_pattern_components) are only callable as unbound
// methods and are not ported.
type TemplateRegistryService struct{}

// NewTemplateRegistryService always fails like the Python constructor.
func NewTemplateRegistryService(dbPath *string) (*TemplateRegistryService, error) {
	return nil, errors.New("Template Registry Service requires refactoring\n" +
		"PostgreSQL implementation is in progress.\n" +
		"✅ SOLUTION: Use PostgreSQL with SQLAlchemy ORM\n" +
		"🔧 Template data should be stored in PostgreSQL tables")
}
