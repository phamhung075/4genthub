package entities

import (
	"strings"

	"agenthub/fastmcp/task_management/domain/value_objects"
)

// Core organizational categories (NestedCategorySchema class constants).
const (
	CategoryOrganization = "organization"
	CategoryDevelopment  = "development"
	CategorySecurity     = "security"
	CategoryOperations   = "operations"
	CategoryPreferences  = "preferences"
)

type schemaSubcategory struct {
	Name        string
	Description string
	Fields      []string
}

type schemaCategory struct {
	Name          string
	Subcategories []schemaSubcategory
}

// nestedStructure is NestedCategorySchema.NESTED_STRUCTURE in declaration order.
var nestedStructure = []schemaCategory{
	{"organization", []schemaSubcategory{
		{"standards", "Coding style, git workflow, testing requirements", []string{"coding_standards", "git_workflow", "testing_requirements", "documentation_standards"}},
		{"compliance", "Regulatory and compliance requirements", []string{"gdpr", "hipaa", "soc2", "iso27001", "custom_compliance"}},
		{"policies", "Organizational policies and procedures", []string{"code_review_policy", "deployment_policy", "incident_response", "data_retention"}},
	}},
	{"development", []schemaSubcategory{
		{"patterns", "Reusable design patterns and code templates", []string{"design_patterns", "code_templates", "architecture_patterns", "api_patterns"}},
		{"tools", "Development tools and configurations", []string{"ide_settings", "linters", "formatters", "build_tools", "testing_frameworks"}},
		{"workflows", "Development workflows and automation", []string{"ci_cd_workflows", "deployment_workflows", "testing_workflows", "review_workflows"}},
	}},
	{"security", []schemaSubcategory{
		{"authentication", "Authentication and authorization settings", []string{"auth_providers", "token_management", "session_config", "multi_factor_auth"}},
		{"encryption", "Encryption and cryptographic settings", []string{"encryption_algorithms", "key_management", "certificate_management", "secure_communication"}},
		{"access_control", "Access control and permissions", []string{"role_definitions", "permission_matrix", "resource_access", "api_security"}},
	}},
	{"operations", []schemaSubcategory{
		{"resources", "Shared operational resources", []string{"api_keys", "service_accounts", "shared_credentials", "external_services"}},
		{"monitoring", "Monitoring and observability", []string{"logging_config", "metrics_collection", "alerting_rules", "dashboard_config"}},
		{"deployment", "Deployment and infrastructure settings", []string{"environment_config", "container_settings", "cloud_resources", "backup_strategies"}},
	}},
	{"preferences", []schemaSubcategory{
		{"user_interface", "User interface preferences and settings", []string{"theme", "layout", "notifications", "dashboard_widgets"}},
		{"agent_behavior", "AI agent behavior and interaction preferences", []string{"response_style", "automation_level", "context_awareness", "learning_preferences"}},
		{"workflow", "Personal workflow preferences", []string{"task_organization", "priority_handling", "time_management", "collaboration_style"}},
	}},
}

// NestedCategorySchema is the schema definition for nested global context categories.
type NestedCategorySchema struct{}

// GetCategoryPath joins category and optional subcategory with a dot.
func (NestedCategorySchema) GetCategoryPath(category, subcategory string) string {
	if subcategory != "" {
		return category + "." + subcategory
	}
	return category
}

func findCategory(name string) *schemaCategory {
	for i := range nestedStructure {
		if nestedStructure[i].Name == name {
			return &nestedStructure[i]
		}
	}
	return nil
}

// ValidateCategoryPath checks that "category" or "category.subcategory" exists in the schema.
func (NestedCategorySchema) ValidateCategoryPath(path string) bool {
	parts := strings.Split(path, ".")
	switch len(parts) {
	case 1:
		return findCategory(parts[0]) != nil
	case 2:
		c := findCategory(parts[0])
		if c == nil {
			return false
		}
		for _, s := range c.Subcategories {
			if s.Name == parts[1] {
				return true
			}
		}
	}
	return false
}

// GetAllPaths lists every category followed by its subcategories.
func (NestedCategorySchema) GetAllPaths() []string {
	paths := []string{}
	for _, c := range nestedStructure {
		paths = append(paths, c.Name)
		for _, s := range c.Subcategories {
			paths = append(paths, c.Name+"."+s.Name)
		}
	}
	return paths
}

// GetFieldCategory finds the "category.subcategory" that lists fieldName.
func (NestedCategorySchema) GetFieldCategory(fieldName string) (string, bool) {
	for _, c := range nestedStructure {
		for _, s := range c.Subcategories {
			if indexOf(s.Fields, fieldName) >= 0 {
				return c.Name + "." + s.Name, true
			}
		}
	}
	return "", false
}

// GlobalContextNestedData is the nested data structure for global context.
// Each category maps subcategory → value (a map[string]any in normal use).
type GlobalContextNestedData struct {
	Organization     map[string]any
	Development      map[string]any
	Security         map[string]any
	Operations       map[string]any
	Preferences      map[string]any
	SchemaVersion    string
	CustomCategories map[string]any
}

func emptySubs(names ...string) map[string]any {
	m := map[string]any{}
	for _, n := range names {
		m[n] = map[string]any{}
	}
	return m
}

// NewGlobalContextNestedData returns the default (empty subcategories, version "2.0").
func NewGlobalContextNestedData() *GlobalContextNestedData {
	return &GlobalContextNestedData{
		Organization:     emptySubs("standards", "compliance", "policies"),
		Development:      emptySubs("patterns", "tools", "workflows"),
		Security:         emptySubs("authentication", "encryption", "access_control"),
		Operations:       emptySubs("resources", "monitoring", "deployment"),
		Preferences:      emptySubs("user_interface", "agent_behavior", "workflow"),
		SchemaVersion:    "2.0",
		CustomCategories: map[string]any{},
	}
}

// category resolves an attribute name to its dict. Python's hasattr() also
// accepts "_custom_categories"; other attributes (methods, _schema_version)
// would raise TypeError on item access and are treated as absent here.
func (g *GlobalContextNestedData) category(name string) (map[string]any, bool) {
	switch name {
	case CategoryOrganization:
		return g.Organization, true
	case CategoryDevelopment:
		return g.Development, true
	case CategorySecurity:
		return g.Security, true
	case CategoryOperations:
		return g.Operations, true
	case CategoryPreferences:
		return g.Preferences, true
	case "_custom_categories":
		return g.CustomCategories, true
	}
	return nil, false
}

// SetNestedValue sets "category.subcategory" or "category.subcategory.field".
func (g *GlobalContextNestedData) SetNestedValue(path string, value any) error {
	parts := strings.Split(path, ".")
	switch len(parts) {
	case 2:
		if data, ok := g.category(parts[0]); ok {
			data[parts[1]] = value
		}
	case 3:
		if data, ok := g.category(parts[0]); ok {
			sub, exists := data[parts[1]]
			if !exists {
				sub = map[string]any{}
				data[parts[1]] = sub
			}
			m, ok := sub.(map[string]any)
			if !ok {
				return value_objects.TypeErrorf("'%s' object does not support item assignment", pyTypeName(sub))
			}
			m[parts[2]] = value
		}
	}
	return nil
}

func pyTypeName(v any) string {
	switch v.(type) {
	case string:
		return "str"
	case int, int64:
		return "int"
	case float64:
		return "float"
	case bool:
		return "bool"
	case nil:
		return "NoneType"
	case []any, []string:
		return "list"
	}
	return "object"
}

// GetNestedValue reads "category.subcategory[.field]", returning def when absent.
func (g *GlobalContextNestedData) GetNestedValue(path string, def any) any {
	parts := strings.Split(path, ".")
	switch len(parts) {
	case 2:
		if data, ok := g.category(parts[0]); ok {
			if v, ok := data[parts[1]]; ok {
				return v
			}
			return def
		}
	case 3:
		if data, ok := g.category(parts[0]); ok {
			if m, ok := data[parts[1]].(map[string]any); ok {
				if v, ok := m[parts[2]]; ok {
					return v
				}
			}
			return def
		}
	}
	return def
}

func (g *GlobalContextNestedData) ToDict() map[string]any {
	return map[string]any{
		"organization": g.Organization, "development": g.Development, "security": g.Security,
		"operations": g.Operations, "preferences": g.Preferences,
		"_schema_version": g.SchemaVersion, "_custom_categories": g.CustomCategories,
	}
}

// GlobalContextNestedDataFromDict keeps defaults for absent keys.
func GlobalContextNestedDataFromDict(data map[string]any) *GlobalContextNestedData {
	g := NewGlobalContextNestedData()
	pick := func(key string, dst *map[string]any) {
		if m, ok := data[key].(map[string]any); ok {
			*dst = m
		}
	}
	pick("organization", &g.Organization)
	pick("development", &g.Development)
	pick("security", &g.Security)
	pick("operations", &g.Operations)
	pick("preferences", &g.Preferences)
	g.SchemaVersion = "2.0"
	if v, ok := data["_schema_version"].(string); ok {
		g.SchemaVersion = v
	}
	g.CustomCategories = map[string]any{}
	pick("_custom_categories", &g.CustomCategories)
	return g
}
