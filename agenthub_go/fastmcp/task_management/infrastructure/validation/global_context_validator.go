package validation

import (
	"fmt"
	"reflect"
	"sort"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// migrationImportError reproduces the ModuleNotFoundError raised by the Python
// lazy import of `...infrastructure.migration.global_context_migration`
// (the `migration` package does not exist). Both value-validation paths that use
// the migrator therefore always report this error.
const migrationImportError = "No module named 'fastmcp.task_management.infrastructure.migration'"

// MigrationFieldMapping is the module-level MIGRATION_FIELD_MAPPING (declaration order).
var MigrationFieldMapping = func() *entities.OrderedMap[string] {
	m := entities.NewOrderedMap[string]()
	m.Set("organization_standards", "organization.standards")
	m.Set("organization_policies", "organization.policies")
	m.Set("development_patterns", "development.patterns")
	m.Set("development_tools", "development.tools")
	m.Set("security_authentication", "security.authentication")
	m.Set("security_encryption", "security.encryption")
	m.Set("operations_resources", "operations.resources")
	m.Set("operations_monitoring", "operations.monitoring")
	m.Set("preferences_user_interface", "preferences.user_interface")
	m.Set("preferences_agent_behavior", "preferences.agent_behavior")
	return m
}()

var validationNow = func() time.Time { return time.Now().Truncate(time.Microsecond) }

// GlobalContextValidationError is raised when global context validation fails.
type GlobalContextValidationError struct {
	Message string
	Errors  []string
	Field   *string
}

func (e *GlobalContextValidationError) Error() string { return e.Message }

// NewGlobalContextValidationError applies the Python defaults (errors or []).
func NewGlobalContextValidationError(message string, validationErrors []string, field *string) *GlobalContextValidationError {
	if validationErrors == nil {
		validationErrors = []string{}
	}
	return &GlobalContextValidationError{Message: message, Errors: validationErrors, Field: field}
}

// --- Minimal JSON Schema engine (ports the subset jsonschema.validate uses here) ---

// jsSchema is one draft-07 schema node. keywordOrder keeps the Python dict keyword
// order because jsonschema raises only the first error.
type jsSchema struct {
	keywordOrder         []string
	types                []string
	required             []string
	properties           *entities.OrderedMap[*jsSchema]
	additionalProperties *bool
	enum                 []any
}

// jsErr is a jsonschema.ValidationError (message plus absolute_path).
type jsErr struct {
	message string
	path    []string
}

func isArray(v any) bool {
	k := reflect.ValueOf(v)
	if !k.IsValid() {
		return false
	}
	return k.Kind() == reflect.Slice || k.Kind() == reflect.Array
}

func isInteger(v any) bool {
	k := reflect.ValueOf(v)
	switch k.Kind() {
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64,
		reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64:
		return true
	}
	return false
}

func isNumber(v any) bool {
	k := reflect.ValueOf(v)
	switch k.Kind() {
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64,
		reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64,
		reflect.Float32, reflect.Float64:
		return true
	}
	return false
}

// asObject returns a dict view of map/OrderedMap values; a nil OrderedMap is None.
func asObject(v any) (map[string]any, bool) {
	switch m := v.(type) {
	case map[string]any:
		return m, true
	case *entities.OrderedMap[any]:
		if m == nil {
			return nil, false
		}
		out := map[string]any{}
		for _, k := range m.Keys() {
			x, _ := m.Get(k)
			out[k] = x
		}
		return out, true
	}
	return nil, false
}

func matchesSingleType(instance any, t string) bool {
	switch t {
	case "object":
		_, ok := asObject(instance)
		return ok
	case "string":
		_, ok := instance.(string)
		return ok
	case "array":
		return isArray(instance)
	case "null":
		return instance == nil
	case "integer":
		return isInteger(instance)
	case "number":
		return isNumber(instance)
	case "boolean":
		_, ok := instance.(bool)
		return ok
	}
	return false
}

func matchesType(instance any, types []string) bool {
	for _, t := range types {
		if matchesSingleType(instance, t) {
			return true
		}
	}
	return false
}

func quotedTypes(types []string) string {
	parts := make([]string, len(types))
	for i, t := range types {
		parts[i] = value_objects.PyRepr(t)
	}
	return strings.Join(parts, ", ")
}

// validateSchema returns the first validation error in keyword order, or nil.
func validateSchema(instance any, s *jsSchema, path []string) *jsErr {
	for _, kw := range s.keywordOrder {
		switch kw {
		case "type":
			if !matchesType(instance, s.types) {
				return &jsErr{message: fmt.Sprintf("%s is not of type %s", value_objects.PyRepr(instance), quotedTypes(s.types)), path: path}
			}
		case "enum":
			found := false
			for _, e := range s.enum {
				if value_objects.PyEqual(instance, e) {
					found = true
					break
				}
			}
			if !found {
				return &jsErr{message: fmt.Sprintf("%s is not one of %s", value_objects.PyRepr(instance), value_objects.PyRepr(s.enum)), path: path}
			}
		case "required":
			m, ok := asObject(instance)
			if !ok {
				continue
			}
			for _, req := range s.required {
				if _, present := m[req]; !present {
					return &jsErr{message: fmt.Sprintf("%s is a required property", value_objects.PyRepr(req)), path: path}
				}
			}
		case "properties":
			m, ok := asObject(instance)
			if !ok {
				continue
			}
			for _, name := range s.properties.Keys() {
				if v, present := m[name]; present {
					sub, _ := s.properties.Get(name)
					if e := validateSchema(v, sub, append(append([]string{}, path...), name)); e != nil {
						return e
					}
				}
			}
		case "additionalProperties":
			if s.additionalProperties == nil || *s.additionalProperties {
				continue
			}
			m, ok := asObject(instance)
			if !ok {
				continue
			}
			extras := []string{}
			for k := range m {
				if !s.properties.Has(k) {
					extras = append(extras, k)
				}
			}
			if len(extras) > 0 {
				sort.Strings(extras)
				reprs := make([]string, len(extras))
				for i, e := range extras {
					reprs[i] = value_objects.PyRepr(e)
				}
				verb := "was"
				if len(extras) != 1 {
					verb = "were"
				}
				return &jsErr{message: fmt.Sprintf("Additional properties are not allowed (%s %s unexpected)", strings.Join(reprs, ", "), verb), path: path}
			}
		}
	}
	return nil
}

func pyTypeRepr(v any) string {
	if v == nil {
		return "<class 'NoneType'>"
	}
	switch v.(type) {
	case string:
		return "<class 'str'>"
	case bool:
		return "<class 'bool'>"
	case map[string]any, *entities.OrderedMap[any]:
		return "<class 'dict'>"
	}
	k := reflect.ValueOf(v).Kind()
	switch k {
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64,
		reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64:
		return "<class 'int'>"
	case reflect.Float32, reflect.Float64:
		return "<class 'float'>"
	case reflect.Slice, reflect.Array:
		return "<class 'list'>"
	}
	return "<class 'object'>"
}

// --- Validator ---

type nestedCategoryInfo struct {
	name string
	subs []string
}

// nestedCategoryList derives category → subcategories from the existing
// GlobalContextNestedData.GetAllPaths() (declaration order).
func nestedCategoryList() []nestedCategoryInfo {
	out := []nestedCategoryInfo{}
	for _, p := range (entities.NestedCategorySchema{}).GetAllPaths() {
		if i := strings.IndexByte(p, '.'); i >= 0 {
			if len(out) > 0 {
				out[len(out)-1].subs = append(out[len(out)-1].subs, p[i+1:])
			}
		} else {
			out = append(out, nestedCategoryInfo{name: p})
		}
	}
	return out
}

// GlobalContextValidator validates global context data and operations.
type GlobalContextValidator struct {
	Schema       entities.NestedCategorySchema
	nestedSchema *jsSchema
	flatSchema   *jsSchema
	categories   []nestedCategoryInfo
}

// NewGlobalContextValidator builds the validator and its two JSON schemas.
func NewGlobalContextValidator() *GlobalContextValidator {
	categories := nestedCategoryList()
	return &GlobalContextValidator{
		Schema:       entities.NestedCategorySchema{},
		nestedSchema: createNestedJSONSchema(categories),
		flatSchema:   createFlatJSONSchema(),
		categories:   categories,
	}
}

func objectSchema(keywordOrder []string) *jsSchema {
	return &jsSchema{keywordOrder: keywordOrder, types: []string{"object"}}
}

func createNestedJSONSchema(categories []nestedCategoryInfo) *jsSchema {
	properties := entities.NewOrderedMap[*jsSchema]()
	for _, cat := range categories {
		subProperties := entities.NewOrderedMap[*jsSchema]()
		for _, sub := range cat.subs {
			subProperties.Set(sub, objectSchema([]string{"type"}))
		}
		properties.Set(cat.name, &jsSchema{
			keywordOrder: []string{"type", "properties"},
			types:        []string{"object"},
			properties:   subProperties,
		})
	}
	properties.Set("_schema_version", &jsSchema{
		keywordOrder: []string{"type", "enum"},
		types:        []string{"string"},
		enum:         []any{"2.0"},
	})
	properties.Set("_migrated_from", &jsSchema{keywordOrder: []string{"type"}, types: []string{"string", "null"}})
	properties.Set("_migration_timestamp", &jsSchema{keywordOrder: []string{"type"}, types: []string{"string", "null"}})
	properties.Set("_custom_categories", objectSchema([]string{"type"}))
	additional := false
	return &jsSchema{
		keywordOrder:         []string{"type", "required", "properties", "additionalProperties"},
		types:                []string{"object"},
		required:             []string{"organization", "development", "security", "operations", "preferences"},
		properties:           properties,
		additionalProperties: &additional,
	}
}

func createFlatJSONSchema() *jsSchema {
	globalSettingsProps := entities.NewOrderedMap[*jsSchema]()
	for _, field := range []string{
		"organization_standards", "security_policies", "compliance_requirements",
		"shared_resources", "reusable_patterns", "global_preferences",
		"user_preferences", "delegation_rules",
	} {
		globalSettingsProps.Set(field, objectSchema([]string{"type"}))
	}
	properties := entities.NewOrderedMap[*jsSchema]()
	properties.Set("id", &jsSchema{keywordOrder: []string{"type"}, types: []string{"string"}})
	properties.Set("organization_name", &jsSchema{keywordOrder: []string{"type"}, types: []string{"string"}})
	properties.Set("global_settings", &jsSchema{
		keywordOrder: []string{"type", "properties"},
		types:        []string{"object"},
		properties:   globalSettingsProps,
	})
	properties.Set("metadata", objectSchema([]string{"type"}))
	additional := true
	return &jsSchema{
		keywordOrder:         []string{"type", "properties", "required", "additionalProperties"},
		types:                []string{"object"},
		properties:           properties,
		required:             []string{"id", "global_settings"},
		additionalProperties: &additional,
	}
}

// ValidateNestedStructure validates nested global context data against the schema
// and the semantic checks.
func (v *GlobalContextValidator) ValidateNestedStructure(nestedData map[string]any) (bool, []string) {
	errors := []string{}
	if e := validateSchema(nestedData, v.nestedSchema, nil); e != nil {
		errors = append(errors, "Schema validation failed: "+e.message)
		if len(e.path) > 0 {
			errors = append(errors, "Path: "+strings.Join(e.path, "."))
		}
	}
	errors = append(errors, v.validateNestedSemantics(nestedData)...)
	return len(errors) == 0, errors
}

// ValidateFlatStructure validates flat global context data against the schema and
// the semantic checks.
func (v *GlobalContextValidator) ValidateFlatStructure(flatData map[string]any) (bool, []string) {
	errors := []string{}
	if e := validateSchema(flatData, v.flatSchema, nil); e != nil {
		errors = append(errors, "Schema validation failed: "+e.message)
	}
	errors = append(errors, v.validateFlatSemantics(flatData)...)
	return len(errors) == 0, errors
}

func (v *GlobalContextValidator) validateNestedSemantics(nestedData map[string]any) []string {
	errors := []string{}

	schemaVersion := nestedData["_schema_version"]
	if !value_objects.PyEqual(schemaVersion, "2.0") {
		errors = append(errors, fmt.Sprintf("Invalid schema version: %s, expected '2.0'", value_objects.PyStr(schemaVersion)))
	}

	for _, cat := range v.categories {
		value, present := nestedData[cat.name]
		if !present {
			errors = append(errors, "Missing required category: "+cat.name)
		} else if _, ok := asObject(value); !ok {
			errors = append(errors, "Category "+cat.name+" must be an object")
		}
	}

	for _, cat := range v.categories {
		value, present := nestedData[cat.name]
		if !present {
			continue
		}
		categoryData, ok := asObject(value)
		if !ok {
			continue
		}
		for _, sub := range cat.subs {
			if subData, exists := categoryData[sub]; exists {
				if _, ok := asObject(subData); !ok {
					errors = append(errors, "Subcategory "+cat.name+"."+sub+" must be an object")
				}
			}
		}
	}

	if ts, present := nestedData["_migration_timestamp"]; present && value_objects.PyTruthy(ts) {
		valid := false
		if s, ok := ts.(string); ok {
			if _, err := value_objects.ParseISO(strings.ReplaceAll(s, "Z", "+00:00")); err == nil {
				valid = true
			}
		}
		if !valid {
			errors = append(errors, "Invalid migration timestamp format: "+value_objects.PyStr(ts))
		}
	}

	return errors
}

func (v *GlobalContextValidator) validateFlatSemantics(flatData map[string]any) []string {
	errors := []string{}
	if _, present := flatData["id"]; !present {
		errors = append(errors, "Missing required field: id")
	}
	value, present := flatData["global_settings"]
	if !present {
		errors = append(errors, "Missing required field: global_settings")
		return errors
	}
	globalSettings, ok := asObject(value)
	if !ok {
		errors = append(errors, "global_settings must be an object")
		return errors
	}
	for _, field := range MigrationFieldMapping.Keys() {
		if fieldValue, exists := globalSettings[field]; exists {
			if fieldValue != nil {
				if _, ok := asObject(fieldValue); !ok {
					errors = append(errors, fmt.Sprintf("Field %s must be an object, got %s", field, pyTypeRepr(fieldValue)))
				}
			}
		}
	}
	return errors
}

// ValidateGlobalContextEntity validates a GlobalContext entity comprehensively.
func (v *GlobalContextValidator) ValidateGlobalContextEntity(context *entities.GlobalContext) (bool, []string) {
	errors := []string{}

	if context.ID == "" {
		errors = append(errors, "GlobalContext must have an ID")
	}
	if context.GlobalSettings == nil {
		errors = append(errors, "global_settings must be a dictionary")
	}
	if context.Metadata == nil {
		errors = append(errors, "metadata must be a dictionary")
	}

	nested := context.GetNestedData()
	if nested != nil {
		nestedValid, nestedErrors := v.ValidateNestedStructure(nested.ToDict())
		if !nestedValid {
			for _, err := range nestedErrors {
				errors = append(errors, "Nested structure: "+err)
			}
		}
	}

	flatValid, flatErrors := v.ValidateFlatStructure(context.ToDict())
	if !flatValid {
		for _, err := range flatErrors {
			errors = append(errors, "Flat structure: "+err)
		}
	}

	errors = append(errors, v.validateStructureConsistency(context)...)

	return len(errors) == 0, errors
}

// validateStructureConsistency compares flat and nested structures. The Python
// implementation lazily imports GlobalContextMigrator from a package that does not
// exist, so it always appends the import error.
func (v *GlobalContextValidator) validateStructureConsistency(context *entities.GlobalContext) []string {
	errors := []string{}
	if context.GetNestedData() == nil {
		return errors
	}
	errors = append(errors, "Error validating structure consistency: "+migrationImportError)
	return errors
}

// ValidateMigrationData validates that migration preserved data integrity.
func (v *GlobalContextValidator) ValidateMigrationData(originalFlat map[string]any, migratedNested *entities.GlobalContextNestedData) []string {
	errors := []string{}

	nestedValid, nestedErrors := v.ValidateNestedStructure(migratedNested.ToDict())
	if !nestedValid {
		for _, err := range nestedErrors {
			errors = append(errors, "Migration result validation: "+err)
		}
	}

	// The reverse-migration lazy import always fails, exactly like Python.
	errors = append(errors, "Error validating migration: "+migrationImportError)
	return errors
}

// isAcceptableTransformation checks whether a migration transformation is acceptable.
func (v *GlobalContextValidator) isAcceptableTransformation(key string, original, transformed any) bool {
	if !value_objects.PyTruthy(original) && !value_objects.PyTruthy(transformed) {
		return true
	}
	if key == "global_preferences" || key == "user_preferences" {
		_, originalOK := asObject(original)
		_, transformedOK := asObject(transformed)
		if originalOK && transformedOK {
			return true
		}
	}
	originalMap, originalOK := asObject(original)
	transformedMap, transformedOK := asObject(transformed)
	if originalOK && transformedOK && len(originalMap) == len(transformedMap) {
		return true
	}
	return false
}

// CreateValidationReport builds a comprehensive validation report.
func (v *GlobalContextValidator) CreateValidationReport(context *entities.GlobalContext) *entities.OrderedMap[any] {
	isValid, errors := v.ValidateGlobalContextEntity(context)

	nested := context.GetNestedData()
	hasNested := nested != nil
	hasFlat := len(context.GlobalSettings) > 0
	isMigrated := false // getattr(context, "_is_migrated", False)

	schemaVersion := "1.0"
	if hasNested {
		schemaVersion = nested.SchemaVersion
	}

	nestedCategories := 0
	if hasNested {
		for _, cat := range v.categories {
			if value_objects.PyTruthy(nestedCategoryField(nested, cat.name)) {
				nestedCategories++
			}
		}
	}

	structureInfo := entities.NewOrderedMap[any]()
	structureInfo.Set("has_nested_structure", hasNested)
	structureInfo.Set("has_flat_structure", hasFlat)
	structureInfo.Set("is_migrated", isMigrated)
	structureInfo.Set("schema_version", schemaVersion)

	fieldCounts := entities.NewOrderedMap[any]()
	flatFields := 0
	if hasFlat {
		flatFields = len(context.GlobalSettings)
	}
	fieldCounts.Set("flat_fields", flatFields)
	fieldCounts.Set("nested_categories", nestedCategories)

	report := entities.NewOrderedMap[any]()
	report.Set("validation_timestamp", value_objects.IsoFormatNaive(validationNow()))
	report.Set("is_valid", isValid)
	report.Set("errors", errors)
	report.Set("structure_info", structureInfo)
	report.Set("field_counts", fieldCounts)

	if warnings, present := context.Metadata["migration_warnings"]; present && value_objects.PyTruthy(warnings) {
		report.Set("migration_warnings", warnings)
	}

	return report
}

// nestedCategoryField resolves a category name to the Go field (getattr equivalent).
func nestedCategoryField(n *entities.GlobalContextNestedData, name string) any {
	switch name {
	case "organization":
		return n.Organization
	case "development":
		return n.Development
	case "security":
		return n.Security
	case "operations":
		return n.Operations
	case "preferences":
		return n.Preferences
	}
	return nil
}

// ValidateGlobalContext is the convenience function around the validator.
func ValidateGlobalContext(context *entities.GlobalContext, raiseOnError bool) (bool, []string, error) {
	validator := NewGlobalContextValidator()
	isValid, errors := validator.ValidateGlobalContextEntity(context)

	if !isValid && raiseOnError {
		message := fmt.Sprintf("Global context validation failed with %d errors", len(errors))
		return false, errors, NewGlobalContextValidationError(message, errors, nil)
	}

	return isValid, errors, nil
}
