package use_cases

import (
	"context"
	"fmt"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// TemplateCategory: template categories.
type TemplateCategory string

const (
	TemplateCategoryWebApp       TemplateCategory = "web_app"
	TemplateCategoryAPIService   TemplateCategory = "api_service"
	TemplateCategoryMobileApp    TemplateCategory = "mobile_app"
	TemplateCategoryMicroservice TemplateCategory = "microservice"
	TemplateCategoryDataPipeline TemplateCategory = "data_pipeline"
	TemplateCategoryMLModel      TemplateCategory = "ml_model"
	TemplateCategoryCLITool      TemplateCategory = "cli_tool"
	TemplateCategoryLibrary      TemplateCategory = "library"
	TemplateCategoryCustom       TemplateCategory = "custom"
)

func (e TemplateCategory) String() string { return string(e) }

// TemplateVariable is a variable that can be customized in a template.
type TemplateVariable struct {
	Name            string
	Description     string
	DefaultValue    any
	Required        bool
	ValidationRegex *string
}

// ContextTemplate is a reusable context template.
type ContextTemplate struct {
	ID           string
	Name         string
	Description  string
	Category     TemplateCategory
	Level        value_objects.ContextLevel
	DataTemplate *entities.OrderedMap[any]
	Author       string

	Variables []*TemplateVariable

	Version    string
	Tags       []string
	CreatedAt  time.Time
	UsageCount int
	LastUsedAt *time.Time
}

// newContextTemplate applies the dataclass defaults and __post_init__ timestamp.
func newContextTemplate(t *ContextTemplate) *ContextTemplate {
	if t.Variables == nil {
		t.Variables = []*TemplateVariable{}
	}
	if t.Version == "" {
		t.Version = "1.0.0"
	}
	if t.Tags == nil {
		t.Tags = []string{}
	}
	if t.CreatedAt.IsZero() {
		t.CreatedAt = time.Now().UTC().Truncate(time.Microsecond)
	}
	return t
}

// TemplateRegistry is a registry of available context templates.
type TemplateRegistry struct {
	templates *entities.OrderedMap[*ContextTemplate]
}

// NewTemplateRegistry builds a registry with the built-in templates.
func NewTemplateRegistry() *TemplateRegistry {
	r := &TemplateRegistry{templates: entities.NewOrderedMap[*ContextTemplate]()}
	r.loadBuiltinTemplates()
	return r
}

// Register registers a template (an existing id keeps its position).
func (r *TemplateRegistry) Register(t *ContextTemplate) { r.templates.Set(t.ID, t) }

// Get returns a template by id, or nil.
func (r *TemplateRegistry) Get(templateID string) *ContextTemplate {
	t, _ := r.templates.Get(templateID)
	return t
}

// ListByCategory lists templates in a category.
func (r *TemplateRegistry) ListByCategory(category TemplateCategory) []*ContextTemplate {
	out := []*ContextTemplate{}
	for _, t := range r.templates.Values() {
		if t.Category == category {
			out = append(out, t)
		}
	}
	return out
}

// ListByLevel lists templates at a context level.
func (r *TemplateRegistry) ListByLevel(level value_objects.ContextLevel) []*ContextTemplate {
	out := []*ContextTemplate{}
	for _, t := range r.templates.Values() {
		if t.Level == level {
			out = append(out, t)
		}
	}
	return out
}

// SearchByTags returns templates sharing any tag.
func (r *TemplateRegistry) SearchByTags(tags []string) []*ContextTemplate {
	out := []*ContextTemplate{}
	for _, t := range r.templates.Values() {
		for _, tag := range tags {
			if ucContainsStr(t.Tags, tag) {
				out = append(out, t)
				break
			}
		}
	}
	return out
}

// TemplateContextService is the UnifiedContextService surface used when applying
// templates.
type TemplateContextService interface {
	CreateContext(ctx context.Context, contextLevel value_objects.ContextLevel, contextID string, data *entities.OrderedMap[any], userID string, projectID, gitBranchID *string) (map[string]any, error)
}

// ContextTemplateService manages and applies context templates.
type ContextTemplateService struct {
	contextService TemplateContextService
	registry       *TemplateRegistry
}

// NewContextTemplateService builds the service with the built-in registry.
func NewContextTemplateService(contextService TemplateContextService) *ContextTemplateService {
	return &ContextTemplateService{contextService: contextService, registry: NewTemplateRegistry()}
}

// ListTemplates lists available templates with the Python filters.
func (s *ContextTemplateService) ListTemplates(category *TemplateCategory, level *value_objects.ContextLevel, tags []string) []*entities.OrderedMap[any] {
	templates := s.registry.templates.Values()
	if category != nil {
		filtered := []*ContextTemplate{}
		for _, t := range templates {
			if t.Category == *category {
				filtered = append(filtered, t)
			}
		}
		templates = filtered
	}
	if level != nil {
		filtered := []*ContextTemplate{}
		for _, t := range templates {
			if t.Level == *level {
				filtered = append(filtered, t)
			}
		}
		templates = filtered
	}
	if len(tags) > 0 {
		filtered := []*ContextTemplate{}
		for _, t := range templates {
			for _, tag := range tags {
				if ucContainsStr(t.Tags, tag) {
					filtered = append(filtered, t)
					break
				}
			}
		}
		templates = filtered
	}

	out := make([]*entities.OrderedMap[any], 0, len(templates))
	for _, t := range templates {
		out = append(out, s.templateToDict(t))
	}
	return out
}

// templateToDict ports _template_to_dict (dataclasses.asdict order).
func (s *ContextTemplateService) templateToDict(t *ContextTemplate) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("id", t.ID)
	m.Set("name", t.Name)
	m.Set("description", t.Description)
	m.Set("category", t.Category.String())
	m.Set("level", t.Level.String())
	m.Set("data_template", t.DataTemplate)
	m.Set("author", t.Author)
	m.Set("variables", variableDicts(t.Variables))
	m.Set("version", t.Version)
	m.Set("tags", t.Tags)
	m.Set("created_at", t.CreatedAt)
	m.Set("usage_count", t.UsageCount)
	var lastUsed any
	if t.LastUsedAt != nil {
		lastUsed = *t.LastUsedAt
	}
	m.Set("last_used_at", lastUsed)
	return m
}

func variableDicts(vars []*TemplateVariable) []any {
	out := make([]any, 0, len(vars))
	for _, v := range vars {
		vm := entities.NewOrderedMap[any]()
		vm.Set("name", v.Name)
		vm.Set("description", v.Description)
		vm.Set("default_value", v.DefaultValue)
		vm.Set("required", v.Required)
		vm.Set("validation_regex", v.ValidationRegex)
		out = append(out, vm)
	}
	return out
}

// ApplyTemplate ports apply_template.
func (s *ContextTemplateService) ApplyTemplate(ctx context.Context, templateID, contextID, userID string, variables *entities.OrderedMap[any], projectID, gitBranchID *string) (map[string]any, error) {
	template := s.registry.Get(templateID)
	if template == nil {
		return nil, &value_objects.ValueError{Msg: "Template not found: " + templateID}
	}

	contextData, err := s.applyVariables(template, variables)
	if err != nil {
		return nil, err
	}

	appliedAt := time.Now().UTC().Truncate(time.Microsecond)
	templateMeta := entities.NewOrderedMap[any]()
	templateMeta.Set("id", template.ID)
	templateMeta.Set("name", template.Name)
	templateMeta.Set("version", template.Version)
	templateMeta.Set("applied_at", value_objects.IsoFormat(appliedAt))
	contextData.Set("_template", templateMeta)

	result, err := s.contextService.CreateContext(ctx, template.Level, contextID, contextData, userID, projectID, gitBranchID)
	if err != nil {
		return nil, err
	}

	currentTime := time.Now().UTC().Truncate(time.Microsecond)
	template.UsageCount++
	template.LastUsedAt = &currentTime
	return result, nil
}

// applyVariables ports _apply_variables (JSON string replace then decode).
func (s *ContextTemplateService) applyVariables(template *ContextTemplate, variables *entities.OrderedMap[any]) (*entities.OrderedMap[any], error) {
	if variables == nil {
		variables = entities.NewOrderedMap[any]()
	}
	templateStr, err := value_objects.PyJSONDumps(template.DataTemplate, -1)
	if err != nil {
		return nil, err
	}

	for _, variable := range template.Variables {
		value := variable.DefaultValue
		if got, ok := variables.Get(variable.Name); ok {
			value = got
		}
		if variable.Required && !variables.Has(variable.Name) && variable.DefaultValue == nil {
			return nil, &value_objects.ValueError{Msg: "Required variable not provided: " + variable.Name}
		}
		placeholder := "{{" + variable.Name + "}}"
		if str, ok := value.(string); ok {
			templateStr = strings.ReplaceAll(templateStr, placeholder, str)
		} else {
			jsonValue, err := value_objects.PyJSONDumps(value, -1)
			if err != nil {
				return nil, err
			}
			templateStr = strings.ReplaceAll(templateStr, `"`+placeholder+`"`, jsonValue)
		}
	}

	decoded, err := entities.DecodeJSON([]byte(templateStr))
	if err != nil {
		return nil, err
	}
	om, ok := decoded.(*entities.OrderedMap[any])
	if !ok {
		return nil, &value_objects.TypeError{Msg: "template data did not decode to an object"}
	}
	return om, nil
}

// CreateCustomTemplate ports create_custom_template.
func (s *ContextTemplateService) CreateCustomTemplate(name, description string, level value_objects.ContextLevel, dataTemplate *entities.OrderedMap[any], variables []*TemplateVariable, tags []string) *ContextTemplate {
	hex := strings.ReplaceAll(value_objects.NewUUIDv4(), "-", "")
	if variables == nil {
		variables = []*TemplateVariable{}
	}
	if tags == nil {
		tags = []string{}
	}
	template := newContextTemplate(&ContextTemplate{
		ID:           "custom_" + hex[:8],
		Name:         name,
		Description:  description,
		Category:     TemplateCategoryCustom,
		Level:        level,
		DataTemplate: dataTemplate,
		Variables:    variables,
		Tags:         tags,
		Author:       "user",
	})
	s.registry.Register(template)
	return template
}

// ExportTemplate ports export_template (json.dumps indent=2).
func (s *ContextTemplateService) ExportTemplate(templateID string) (string, error) {
	template := s.registry.Get(templateID)
	if template == nil {
		return "", &value_objects.ValueError{Msg: "Template not found: " + templateID}
	}
	exportData := entities.NewOrderedMap[any]()
	exportData.Set("id", template.ID)
	exportData.Set("name", template.Name)
	exportData.Set("description", template.Description)
	exportData.Set("category", template.Category.String())
	exportData.Set("level", template.Level.String())
	exportData.Set("data_template", template.DataTemplate)
	exportData.Set("variables", variableDicts(template.Variables))
	exportData.Set("tags", template.Tags)
	exportData.Set("version", template.Version)
	exportData.Set("author", template.Author)
	return value_objects.PyJSONDumps(exportData, 2)
}

// ImportTemplate ports import_template.
//
// Accepted deviations (documented in MIGRATION.md): JSON syntax errors other than
// "Expecting value" at the start keep the Go decoder text (Python's JSONDecodeError
// position/message families are not ported), and non-string version/author/tags and
// non-bool variable "required" values are normalised instead of kept raw because the
// ContextTemplate fields are typed.
func (s *ContextTemplateService) ImportTemplate(jsonStr string) (*ContextTemplate, error) {
	decoded, err := entities.DecodeJSON([]byte(jsonStr))
	if err != nil {
		return nil, templateJSONError(jsonStr, err)
	}
	data, ok := decoded.(*entities.OrderedMap[any])
	if !ok {
		// data["id"] on a non-dict.
		return nil, &value_objects.TypeError{Msg: pySubscriptError(decoded)}
	}

	idAny, ok := data.Get("id")
	if !ok {
		return nil, &entities.KeyError{Key: "id"}
	}
	nameAny, ok := data.Get("name")
	if !ok {
		return nil, &entities.KeyError{Key: "name"}
	}
	descriptionAny, ok := data.Get("description")
	if !ok {
		return nil, &entities.KeyError{Key: "description"}
	}
	categoryAny, ok := data.Get("category")
	if !ok {
		return nil, &entities.KeyError{Key: "category"}
	}
	levelAny, ok := data.Get("level")
	if !ok {
		return nil, &entities.KeyError{Key: "level"}
	}
	dataTemplateAny, ok := data.Get("data_template")
	if !ok {
		return nil, &entities.KeyError{Key: "data_template"}
	}
	// Python evaluates the ContextTemplate(...) arguments in order: category and
	// level are validated before the variables list is built.
	category, err := templateUseCasesEnum("TemplateCategory", pyStringValue(categoryAny), templateCategoryValues)
	if err != nil {
		return nil, err
	}
	level, err := templateUseCasesEnum("ContextLevel", pyStringValue(levelAny), value_objects.ContextLevelValues)
	if err != nil {
		return nil, err
	}

	variables := []*TemplateVariable{}
	if rawVars, ok := data.Get("variables"); ok {
		if list, ok := rawVars.([]any); ok {
			for _, entry := range list {
				vm, ok := entry.(*entities.OrderedMap[any])
				if !ok {
					return nil, &value_objects.TypeError{Msg: pySubscriptError(entry)}
				}
				// v["name"], v["description"], v["default_value"] raise KeyError in order.
				name, ok := vm.Get("name")
				if !ok {
					return nil, &entities.KeyError{Key: "name"}
				}
				description, ok := vm.Get("description")
				if !ok {
					return nil, &entities.KeyError{Key: "description"}
				}
				defaultValue, ok := vm.Get("default_value")
				if !ok {
					return nil, &entities.KeyError{Key: "default_value"}
				}
				required, _ := vm.Get("required")
				var regex *string
				if r, ok := vm.Get("validation_regex"); ok {
					if s, ok := r.(string); ok {
						regex = &s
					}
				}
				variables = append(variables, &TemplateVariable{
					Name:            pyStringValue(name),
					Description:     pyStringValue(description),
					DefaultValue:    defaultValue,
					Required:        value_objects.PyTruthy(required),
					ValidationRegex: regex,
				})
			}
		}
	}

	tags := []string{}
	if rawTags, ok := data.Get("tags"); ok {
		tags, _ = anyToStringSlice(rawTags)
		if tags == nil {
			tags = []string{}
		}
	}
	version := "1.0.0"
	if v, ok := data.Get("version"); ok {
		if s, ok := v.(string); ok {
			version = s
		}
	}
	author := "imported"
	if v, ok := data.Get("author"); ok {
		if s, ok := v.(string); ok {
			author = s
		}
	}

	dataTemplate, _ := dataTemplateAny.(*entities.OrderedMap[any])
	template := newContextTemplate(&ContextTemplate{
		ID:           pyStringValue(idAny),
		Name:         pyStringValue(nameAny),
		Description:  pyStringValue(descriptionAny),
		Category:     category,
		Level:        level,
		DataTemplate: dataTemplate,
		Variables:    variables,
		Tags:         tags,
		Version:      version,
		Author:       author,
	})
	s.registry.Register(template)
	return template, nil
}

func pyStringValue(v any) string {
	if s, ok := v.(string); ok {
		return s
	}
	return ""
}

// tmplOM builds an OrderedMap from alternating key/value arguments.
func tmplOM(pairs ...any) *entities.OrderedMap[any] {
	o := entities.NewOrderedMap[any]()
	for i := 0; i+1 < len(pairs); i += 2 {
		o.Set(pairs[i].(string), pairs[i+1])
	}
	return o
}

// tmplList builds a []any from its arguments.
func tmplList(items ...any) []any { return append([]any{}, items...) }

// loadBuiltinTemplates ports _load_builtin_templates.
func (r *TemplateRegistry) loadBuiltinTemplates() {
	r.Register(newContextTemplate(&ContextTemplate{
		ID:          "web_app_react",
		Name:        "React Web Application",
		Description: "Standard React application with TypeScript",
		Category:    TemplateCategoryWebApp,
		Level:       value_objects.ContextLevelProject,
		DataTemplate: tmplOM(
			"project_type", "web_application",
			"framework", "React",
			"language", "TypeScript",
			"build_tool", "Vite",
			"testing", tmplOM(
				"unit", "Vitest",
				"e2e", "Playwright",
				"coverage_threshold", "{{coverage_threshold}}",
			),
			"dependencies", tmplOM(
				"ui_library", "{{ui_library}}",
				"state_management", "{{state_management}}",
				"routing", "React Router",
				"styling", "{{styling_solution}}",
			),
			"structure", tmplOM(
				"src/", "Source code",
				"src/components/", "React components",
				"src/hooks/", "Custom hooks",
				"src/services/", "API services",
				"src/utils/", "Utilities",
				"src/types/", "TypeScript types",
				"tests/", "Test files",
			),
			"conventions", tmplOM(
				"naming", "PascalCase for components, camelCase for functions",
				"file_structure", "Feature-based organization",
				"state_management", "{{state_pattern}}",
			),
			"ci_cd", tmplOM(
				"pipeline", "GitHub Actions",
				"deployment", "{{deployment_platform}}",
			),
		),
		Variables: []*TemplateVariable{
			{Name: "coverage_threshold", Description: "Minimum test coverage percentage", DefaultValue: 80, Required: false},
			{Name: "ui_library", Description: "UI component library", DefaultValue: "shadcn/ui", Required: false},
			{Name: "state_management", Description: "State management solution", DefaultValue: "Zustand", Required: false},
			{Name: "styling_solution", Description: "CSS solution", DefaultValue: "Tailwind CSS", Required: false},
			{Name: "state_pattern", Description: "State management pattern", DefaultValue: "Context + Hooks", Required: false},
			{Name: "deployment_platform", Description: "Deployment platform", DefaultValue: "Vercel", Required: false},
		},
		Tags:   []string{"frontend", "react", "typescript", "spa"},
		Author: "system",
	}))

	r.Register(newContextTemplate(&ContextTemplate{
		ID:          "api_fastapi",
		Name:        "FastAPI Service",
		Description: "RESTful API service with FastAPI",
		Category:    TemplateCategoryAPIService,
		Level:       value_objects.ContextLevelProject,
		DataTemplate: tmplOM(
			"project_type", "api_service",
			"framework", "FastAPI",
			"language", "Python",
			"database", tmplOM(
				"type", "{{database_type}}",
				"orm", "SQLAlchemy",
				"migrations", "Alembic",
			),
			"authentication", tmplOM(
				"type", "{{auth_type}}",
				"token_type", "JWT",
				"provider", "{{auth_provider}}",
			),
			"structure", tmplOM(
				"src/", "Source code",
				"src/api/", "API endpoints",
				"src/models/", "Database models",
				"src/services/", "Business logic",
				"src/schemas/", "Pydantic schemas",
				"src/utils/", "Utilities",
				"tests/", "Test files",
			),
			"testing", tmplOM(
				"framework", "pytest",
				"coverage", "{{coverage_threshold}}%",
			),
			"documentation", tmplOM("openapi", "Auto-generated", "redoc", "Enabled"),
			"deployment", tmplOM(
				"containerization", "Docker",
				"orchestration", "{{orchestration}}",
				"monitoring", "{{monitoring_solution}}",
			),
		),
		Variables: []*TemplateVariable{
			{Name: "database_type", Description: "Database system", DefaultValue: "PostgreSQL", Required: true},
			{Name: "auth_type", Description: "Authentication type", DefaultValue: "OAuth2", Required: false},
			{Name: "auth_provider", Description: "Auth provider", DefaultValue: "Internal", Required: false},
			{Name: "coverage_threshold", Description: "Test coverage threshold", DefaultValue: 85, Required: false},
			{Name: "orchestration", Description: "Container orchestration", DefaultValue: "Kubernetes", Required: false},
			{Name: "monitoring_solution", Description: "Monitoring solution", DefaultValue: "Prometheus + Grafana", Required: false},
		},
		Tags:   []string{"backend", "api", "python", "fastapi"},
		Author: "system",
	}))

	r.Register(newContextTemplate(&ContextTemplate{
		ID:          "ml_model_training",
		Name:        "ML Model Training Pipeline",
		Description: "Machine learning model training and deployment",
		Category:    TemplateCategoryMLModel,
		Level:       value_objects.ContextLevelProject,
		DataTemplate: tmplOM(
			"project_type", "ml_model",
			"framework", "{{ml_framework}}",
			"language", "Python",
			"model_type", "{{model_type}}",
			"data", tmplOM(
				"source", "{{data_source}}",
				"preprocessing", "{{preprocessing_pipeline}}",
				"validation_split", 0.2,
				"test_split", 0.1,
			),
			"training", tmplOM(
				"epochs", "{{epochs}}",
				"batch_size", "{{batch_size}}",
				"optimizer", "{{optimizer}}",
				"loss_function", "{{loss_function}}",
				"metrics", tmplList("accuracy", "precision", "recall"),
			),
			"experiment_tracking", tmplOM(
				"tool", "{{tracking_tool}}",
				"artifacts", tmplList("model", "metrics", "plots"),
			),
			"deployment", tmplOM(
				"serving", "{{serving_platform}}",
				"api", "REST",
				"monitoring", "Model performance tracking",
			),
			"structure", tmplOM(
				"data/", "Dataset storage",
				"notebooks/", "Exploration notebooks",
				"src/", "Training code",
				"models/", "Saved models",
				"configs/", "Configuration files",
				"tests/", "Model tests",
			),
		),
		Variables: []*TemplateVariable{
			{Name: "ml_framework", Description: "ML framework", DefaultValue: "PyTorch", Required: true},
			{Name: "model_type", Description: "Type of model", DefaultValue: "Classification", Required: true},
			{Name: "data_source", Description: "Data source location", DefaultValue: "S3", Required: false},
			{Name: "preprocessing_pipeline", Description: "Data preprocessing", DefaultValue: "StandardScaler + PCA", Required: false},
			{Name: "epochs", Description: "Training epochs", DefaultValue: 100, Required: false},
			{Name: "batch_size", Description: "Batch size", DefaultValue: 32, Required: false},
			{Name: "optimizer", Description: "Optimizer", DefaultValue: "Adam", Required: false},
			{Name: "loss_function", Description: "Loss function", DefaultValue: "CrossEntropy", Required: false},
			{Name: "tracking_tool", Description: "Experiment tracking tool", DefaultValue: "MLflow", Required: false},
			{Name: "serving_platform", Description: "Model serving platform", DefaultValue: "TorchServe", Required: false},
		},
		Tags:   []string{"ml", "ai", "pytorch", "training"},
		Author: "system",
	}))

	r.Register(newContextTemplate(&ContextTemplate{
		ID:          "task_feature_impl",
		Name:        "Feature Implementation Task",
		Description: "Standard template for implementing a new feature",
		Category:    TemplateCategoryCustom,
		Level:       value_objects.ContextLevelTask,
		DataTemplate: tmplOM(
			"task_type", "feature_implementation",
			"requirements", tmplOM(
				"functional", "{{functional_requirements}}",
				"non_functional", "{{non_functional_requirements}}",
				"acceptance_criteria", tmplList(),
			),
			"technical_approach", tmplOM(
				"architecture", "{{architecture_pattern}}",
				"technologies", tmplList(),
				"dependencies", tmplList(),
			),
			"implementation_plan", tmplOM(
				"phases", tmplList("Design", "Implementation", "Testing", "Documentation", "Review"),
				"estimated_effort", "{{effort_estimate}}",
			),
			"testing_strategy", tmplOM(
				"unit_tests", true,
				"integration_tests", true,
				"e2e_tests", "{{e2e_required}}",
				"performance_tests", "{{perf_required}}",
			),
			"documentation", tmplOM(
				"api_docs", true,
				"user_guide", "{{user_guide_required}}",
				"technical_docs", true,
			),
			"review_checklist", tmplList("Code quality", "Test coverage", "Documentation", "Security review", "Performance impact"),
		),
		Variables: []*TemplateVariable{
			{Name: "functional_requirements", Description: "Functional requirements", DefaultValue: "To be defined", Required: true},
			{Name: "non_functional_requirements", Description: "Non-functional requirements", DefaultValue: "Performance, Security, Scalability", Required: false},
			{Name: "architecture_pattern", Description: "Architecture pattern", DefaultValue: "MVC", Required: false},
			{Name: "effort_estimate", Description: "Effort estimate", DefaultValue: "3 days", Required: false},
			{Name: "e2e_required", Description: "E2E tests required", DefaultValue: true, Required: false},
			{Name: "perf_required", Description: "Performance tests required", DefaultValue: false, Required: false},
			{Name: "user_guide_required", Description: "User guide required", DefaultValue: true, Required: false},
		},
		Tags:   []string{"task", "feature", "planning"},
		Author: "system",
	}))
}

var templateCategoryValues = []TemplateCategory{
	TemplateCategoryWebApp, TemplateCategoryAPIService, TemplateCategoryMobileApp, TemplateCategoryMicroservice,
	TemplateCategoryDataPipeline, TemplateCategoryMLModel, TemplateCategoryCLITool, TemplateCategoryLibrary, TemplateCategoryCustom,
}

// pySubscriptError is the TypeError text of `v["key"]` for a non-dict v.
func pySubscriptError(v any) string {
	switch v.(type) {
	case string:
		return "string indices must be integers, not 'str'"
	case []any:
		return "list indices must be integers or slices, not str"
	case nil:
		return "'NoneType' object is not subscriptable"
	case bool:
		return "'bool' object is not subscriptable"
	case float64:
		return "'float' object is not subscriptable"
	}
	return "'int' object is not subscriptable"
}

// templateJSONError maps a decode failure to json.JSONDecodeError text where the
// position is determinable (empty input / no JSON value at the start); other
// syntax errors keep the decoder text.
func templateJSONError(src string, err error) error {
	if err.Error() == "Extra data" {
		return err
	}
	trimmed := strings.TrimLeft(src, " \t\n\r")
	if trimmed == "" || !strings.ContainsRune("{[\"-0123456789tfn", rune(trimmed[0])) {
		pos := len(src) - len(trimmed)
		line := 1 + strings.Count(src[:pos], "\n")
		col := pos + 1
		if i := strings.LastIndex(src[:pos], "\n"); i >= 0 {
			col = pos - i
		}
		return fmt.Errorf("Expecting value: line %d column %d (char %d)", line, col, pos)
	}
	return err
}
