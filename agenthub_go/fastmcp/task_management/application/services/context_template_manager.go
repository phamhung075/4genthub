package services

import (
	"os"
	"path/filepath"

	"gopkg.in/yaml.v3"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// OperationType mirrors the Python OperationType enum.
type OperationType string

const (
	OperationTypeTaskCreate   OperationType = "task.create"
	OperationTypeTaskUpdate   OperationType = "task.update"
	OperationTypeTaskGet      OperationType = "task.get"
	OperationTypeTaskList     OperationType = "task.list"
	OperationTypeTaskDelete   OperationType = "task.delete"
	OperationTypeTaskComplete OperationType = "task.complete"
	OperationTypeTaskSearch   OperationType = "task.search"
	OperationTypeTaskNext     OperationType = "task.next"

	OperationTypeSubtaskCreate   OperationType = "subtask.create"
	OperationTypeSubtaskUpdate   OperationType = "subtask.update"
	OperationTypeSubtaskDelete   OperationType = "subtask.delete"
	OperationTypeSubtaskList     OperationType = "subtask.list"
	OperationTypeSubtaskComplete OperationType = "subtask.complete"

	OperationTypeContextCreate   OperationType = "context.create"
	OperationTypeContextGet      OperationType = "context.get"
	OperationTypeContextUpdate   OperationType = "context.update"
	OperationTypeContextDelete   OperationType = "context.delete"
	OperationTypeContextResolve  OperationType = "context.resolve"
	OperationTypeContextDelegate OperationType = "context.delegate"

	OperationTypeProjectCreate      OperationType = "project.create"
	OperationTypeProjectGet         OperationType = "project.get"
	OperationTypeProjectUpdate      OperationType = "project.update"
	OperationTypeProjectList        OperationType = "project.list"
	OperationTypeProjectHealthCheck OperationType = "project.health_check"

	OperationTypeGitBranchCreate OperationType = "git_branch.create"
	OperationTypeGitBranchGet    OperationType = "git_branch.get"
	OperationTypeGitBranchList   OperationType = "git_branch.list"
	OperationTypeGitBranchUpdate OperationType = "git_branch.update"
	OperationTypeGitBranchDelete OperationType = "git_branch.delete"

	OperationTypeAgentRegister OperationType = "agent.register"
	OperationTypeAgentAssign   OperationType = "agent.assign"
	OperationTypeAgentList     OperationType = "agent.list"
	OperationTypeAgentCall     OperationType = "agent.call"
)

// TemplateValidationError mirrors the Python TemplateValidationError exception.
type TemplateValidationError struct{ Msg string }

func (e *TemplateValidationError) Error() string { return e.Msg }

// TemplateVariable mirrors the Python TemplateVariable dataclass.
type TemplateVariable struct {
	Name        string
	Required    bool
	Default     any
	Description string
}

// NewTemplateVariable mirrors TemplateVariable.__init__ (required defaults to True).
func NewTemplateVariable(name string, required *bool, defaultVal any, description string) *TemplateVariable {
	r := true
	if required != nil {
		r = *required
	}
	return &TemplateVariable{Name: name, Required: r, Default: defaultVal, Description: description}
}

// ContextTemplate mirrors the Python ContextTemplate class.
type ContextTemplate struct {
	Name                string
	OperationType       OperationType
	Variables           []*TemplateVariable
	ContextRequirements []string
	Description         string
}

// NewContextTemplate mirrors ContextTemplate.__init__.
func NewContextTemplate(name string, operationType OperationType, variables []*TemplateVariable, contextRequirements []string, description string) *ContextTemplate {
	if variables == nil {
		variables = []*TemplateVariable{}
	}
	if contextRequirements == nil {
		contextRequirements = []string{}
	}
	return &ContextTemplate{Name: name, OperationType: operationType, Variables: variables, ContextRequirements: contextRequirements, Description: description}
}

// Validate mirrors ContextTemplate.validate.
func (t *ContextTemplate) Validate(context *entities.OrderedMap[any]) error {
	for _, variable := range t.Variables {
		if variable.Required {
			if context == nil || !context.Has(variable.Name) {
				return &TemplateValidationError{Msg: "Required variable '" + variable.Name + "' missing from context"}
			}
		}
	}
	return nil
}

// ContextTemplateManager manages context templates for all MCP operations.
type ContextTemplateManager struct {
	templates       map[OperationType]*entities.OrderedMap[[]string]
	customTemplates map[OperationType]*entities.OrderedMap[[]string]
	TemplateVersion string
	templateCache   map[string]*entities.OrderedMap[[]string]
	inheritanceMap  map[OperationType][]OperationType
	metrics         map[string]int
}

// NewContextTemplateManager mirrors ContextTemplateManager.__init__.
func NewContextTemplateManager(templatesPath *string) *ContextTemplateManager {
	m := &ContextTemplateManager{
		templates:       ctmDefaultTemplates(),
		customTemplates: map[OperationType]*entities.OrderedMap[[]string]{},
		TemplateVersion: "1.0.0",
		templateCache:   map[string]*entities.OrderedMap[[]string]{},
		metrics: map[string]int{
			"templates_used":   0,
			"fields_requested": 0,
			"fields_saved":     0,
			"cache_hits":       0,
		},
	}
	m.inheritanceMap = m.buildInheritanceMap()
	if templatesPath != nil {
		m.LoadCustomTemplates(*templatesPath)
	}
	return m
}

func ctmOM(pairs ...any) *entities.OrderedMap[[]string] {
	m := entities.NewOrderedMap[[]string]()
	for i := 0; i+1 < len(pairs); i += 2 {
		m.Set(pairs[i].(string), ctmStrList(pairs[i+1]))
	}
	return m
}

func ctmStrList(v any) []string {
	switch s := v.(type) {
	case []string:
		return s
	case []any:
		out := make([]string, 0, len(s))
		for _, x := range s {
			out = append(out, value_objects.PyStr(x))
		}
		return out
	}
	return nil
}

func ctmDefaultTemplates() map[OperationType]*entities.OrderedMap[[]string] {
	return map[OperationType]*entities.OrderedMap[[]string]{
		OperationTypeTaskCreate: ctmOM(
			"project", []string{"id", "name", "default_priority", "workflow_rules"},
			"git_branch", []string{"id", "name", "status"},
			"recent_tasks", []string{"title", "status", "assignees"},
			"user", []string{"id", "preferences", "default_assignees"},
			"parent_context", []string{"metadata", "requirements"},
		),
		OperationTypeTaskUpdate: ctmOM(
			"task", []string{"id", "current_status", "dependencies", "assignees", "progress_percentage"},
			"related_tasks", []string{"id", "status", "blocking_status"},
			"project", []string{"id", "workflow_rules", "completion_criteria"},
			"user", []string{"id", "permissions"},
		),
		OperationTypeTaskGet: ctmOM(
			"task", []string{"*"},
			"subtasks", []string{"id", "title", "status", "progress_percentage"},
			"dependencies", []string{"id", "title", "status"},
			"context", []string{"data", "metadata"},
		),
		OperationTypeTaskList: ctmOM(
			"filters", []string{"status", "priority", "assignees", "labels"},
			"pagination", []string{"limit", "offset", "sort_by", "sort_order"},
			"user", []string{"preferences", "saved_filters"},
			"project", []string{"id", "name"},
		),
		OperationTypeTaskDelete: ctmOM(
			"task", []string{"id", "dependencies", "subtasks"},
			"user", []string{"id", "permissions"},
			"cleanup", []string{"cascade_delete", "archive_mode"},
		),
		OperationTypeTaskComplete: ctmOM(
			"task", []string{"id", "title", "dependencies", "subtasks"},
			"subtasks", []string{"id", "status", "completion_percentage"},
			"project", []string{"completion_rules", "notification_settings"},
			"next_tasks", []string{"id", "title", "can_start"},
		),
		OperationTypeTaskSearch: ctmOM(
			"query", []string{"search_terms", "filters"},
			"scope", []string{"project_id", "git_branch_id"},
			"user", []string{"search_history", "preferences"},
		),
		OperationTypeTaskNext: ctmOM(
			"git_branch", []string{"id", "active_tasks"},
			"user", []string{"id", "current_context"},
			"priorities", []string{"urgent_tasks", "blocked_tasks", "ready_tasks"},
			"agent", []string{"capabilities", "current_load"},
		),
		OperationTypeSubtaskCreate: ctmOM(
			"parent_task", []string{"id", "title", "assignees", "progress_percentage"},
			"project", []string{"id", "subtask_rules"},
			"user", []string{"id", "preferences"},
		),
		OperationTypeSubtaskUpdate: ctmOM(
			"subtask", []string{"id", "status", "progress_percentage"},
			"parent_task", []string{"id", "progress_percentage", "status"},
			"user", []string{"id", "permissions"},
		),
		OperationTypeSubtaskComplete: ctmOM(
			"subtask", []string{"id", "title"},
			"parent_task", []string{"id", "subtasks", "progress_percentage"},
			"impact", []string{"parent_progress", "sibling_tasks"},
		),
		OperationTypeContextCreate: ctmOM(
			"level", []string{"hierarchy_level", "parent_context"},
			"data", []string{"initial_data", "metadata"},
			"inheritance", []string{"inherit_from_parent", "override_fields"},
		),
		OperationTypeContextGet: ctmOM(
			"context", []string{"id", "level", "data"},
			"inheritance", []string{"include_inherited", "parent_chain"},
			"cache", []string{"use_cache", "cache_ttl"},
		),
		OperationTypeContextUpdate: ctmOM(
			"context", []string{"id", "current_data"},
			"changes", []string{"data_updates", "metadata_updates"},
			"propagation", []string{"propagate_to_children", "affected_contexts"},
		),
		OperationTypeContextResolve: ctmOM(
			"context", []string{"id", "level"},
			"hierarchy", []string{"full_chain", "inheritance_mode"},
			"optimization", []string{"field_selection", "cache_strategy"},
		),
		OperationTypeProjectCreate: ctmOM(
			"project", []string{"name", "description", "settings"},
			"user", []string{"id", "default_settings"},
			"templates", []string{"project_template", "initial_structure"},
		),
		OperationTypeProjectGet: ctmOM(
			"project", []string{"*"},
			"statistics", []string{"task_count", "completion_rate", "active_branches"},
			"team", []string{"members", "roles"},
		),
		OperationTypeProjectList: ctmOM(
			"filters", []string{"status", "owner", "created_after"},
			"user", []string{"id", "accessible_projects"},
			"summary", []string{"minimal_fields", "include_stats"},
		),
		OperationTypeProjectHealthCheck: ctmOM(
			"project", []string{"id", "status", "last_activity"},
			"metrics", []string{"task_metrics", "branch_metrics", "agent_metrics"},
			"issues", []string{"blocked_tasks", "stale_branches", "overdue_items"},
		),
		OperationTypeGitBranchCreate: ctmOM(
			"project", []string{"id", "branch_naming_convention"},
			"source_branch", []string{"id", "status"},
			"user", []string{"id", "permissions"},
		),
		OperationTypeGitBranchList: ctmOM(
			"project", []string{"id", "name"},
			"filters", []string{"status", "created_by"},
			"statistics", []string{"task_count", "completion_percentage"},
		),
		OperationTypeAgentRegister: ctmOM(
			"project", []string{"id", "agent_registry"},
			"agent", []string{"name", "capabilities", "configuration"},
			"user", []string{"id", "permissions"},
		),
		OperationTypeAgentAssign: ctmOM(
			"agent", []string{"id", "current_load", "capabilities"},
			"target", []string{"task_id", "git_branch_id"},
			"workload", []string{"current_assignments", "capacity"},
		),
		OperationTypeAgentCall: ctmOM(
			"agent", []string{"name", "configuration"},
			"context", []string{"current_task", "current_branch"},
			"parameters", []string{"agent_params", "timeout"},
		),
	}
}

// GetTemplate mirrors ContextTemplateManager.get_template.
func (m *ContextTemplateManager) GetTemplate(operation OperationType, overrideFields *entities.OrderedMap[[]string]) *entities.OrderedMap[[]string] {
	cacheKey := operation.String() + ":"
	if overrideFields != nil {
		s, _ := value_objects.PyJSONDumps(overrideFields, -1)
		cacheKey += s
	}
	if cached, ok := m.templateCache[cacheKey]; ok {
		m.metrics["cache_hits"]++
		return cached
	}

	template := entities.NewOrderedMap[[]string]()
	if base, ok := m.templates[operation]; ok {
		for _, k := range base.Keys() {
			v, _ := base.Get(k)
			template.Set(k, v)
		}
	}
	template = m.applyInheritance(operation, template)

	if overrideFields != nil {
		for _, contextType := range overrideFields.Keys() {
			fields, _ := overrideFields.Get(contextType)
			if ctmIsStar(fields) {
				template.Set(contextType, []string{"*"})
			} else {
				template.Set(contextType, fields)
			}
		}
	}

	m.templateCache[cacheKey] = template
	m.metrics["templates_used"]++
	totalFields := 0
	for _, k := range template.Keys() {
		fields, _ := template.Get(k)
		totalFields += ctmFieldCount(fields)
	}
	m.metrics["fields_requested"] += totalFields
	return template
}

func ctmIsStar(fields []string) bool {
	return len(fields) == 1 && fields[0] == "*"
}

func ctmFieldCount(fields []string) int {
	if ctmIsStar(fields) {
		return 50
	}
	return len(fields)
}

func (m *ContextTemplateManager) buildInheritanceMap() map[OperationType][]OperationType {
	return map[OperationType][]OperationType{
		OperationTypeSubtaskCreate:   {OperationTypeTaskCreate},
		OperationTypeSubtaskUpdate:   {OperationTypeTaskUpdate},
		OperationTypeSubtaskComplete: {OperationTypeTaskComplete},
		OperationTypeTaskSearch:      {OperationTypeTaskList},
		OperationTypeTaskNext:        {OperationTypeTaskList},
		OperationTypeGitBranchUpdate: {OperationTypeGitBranchGet},
		OperationTypeGitBranchDelete: {OperationTypeGitBranchGet},
	}
}

func (m *ContextTemplateManager) applyInheritance(operation OperationType, template *entities.OrderedMap[[]string]) *entities.OrderedMap[[]string] {
	parentOps, ok := m.inheritanceMap[operation]
	if !ok {
		return template
	}
	for _, parentOp := range parentOps {
		parentTemplate, ok := m.templates[parentOp]
		if !ok {
			continue
		}
		for _, contextType := range parentTemplate.Keys() {
			fields, _ := parentTemplate.Get(contextType)
			if existing, has := template.Get(contextType); !has {
				template.Set(contextType, fields)
			} else {
				existingSet := map[string]bool{}
				for _, f := range existing {
					existingSet[f] = true
				}
				for _, field := range fields {
					if !existingSet[field] {
						existing = append(existing, field)
						existingSet[field] = true
					}
				}
				template.Set(contextType, existing)
			}
		}
	}
	return template
}

// LoadCustomTemplates mirrors ContextTemplateManager.load_custom_templates.
func (m *ContextTemplateManager) LoadCustomTemplates(templatesPath string) {
	data, err := os.ReadFile(templatesPath)
	if err != nil {
		return
	}
	loaded, err := entities.LoadYAML(data)
	if err != nil {
		return
	}
	customData, ok := loaded.(*entities.OrderedMap[any])
	if !ok {
		return
	}
	if tv, ok := customData.Get("templates"); ok {
		if templates, ok := tv.(*entities.OrderedMap[any]); ok {
			for _, opName := range templates.Keys() {
				opType, ok := ctmLookupOperation(opName)
				if !ok {
					continue
				}
				tv, _ := templates.Get(opName)
				converted := ctmConvertTemplate(tv)
				if converted == nil {
					continue
				}
				m.templates[opType] = converted
				m.customTemplates[opType] = converted
			}
		}
	}
	if vv, ok := customData.Get("version"); ok {
		m.TemplateVersion = value_objects.PyStr(vv)
	}
}

func ctmLookupOperation(name string) (OperationType, bool) {
	op := OperationType(name)
	for _, existing := range ctmAllOperations() {
		if existing == op {
			return op, true
		}
	}
	return "", false
}

func ctmConvertTemplate(v any) *entities.OrderedMap[[]string] {
	om, ok := v.(*entities.OrderedMap[any])
	if !ok {
		return nil
	}
	out := entities.NewOrderedMap[[]string]()
	for _, k := range om.Keys() {
		raw, _ := om.Get(k)
		out.Set(k, ctmStrList(raw))
	}
	return out
}

// SaveTemplates mirrors ContextTemplateManager.save_templates.
func (m *ContextTemplateManager) SaveTemplates(outputPath string) {
	root := &yaml.Node{Kind: yaml.MappingNode}
	ctmAppendPair(root, "version", ctmScalarNode(m.TemplateVersion))
	templatesNode := &yaml.Node{Kind: yaml.MappingNode}
	for _, op := range ctmAllOperations() {
		template, ok := m.templates[op]
		if !ok {
			continue
		}
		templatesNode.Content = append(templatesNode.Content, ctmScalarNode(op.String()), ctmTemplateNode(template))
	}
	ctmAppendPair(root, "templates", templatesNode)

	out, err := yaml.Marshal(root)
	if err != nil {
		return
	}
	if dir := filepath.Dir(outputPath); dir != "" {
		if err := os.MkdirAll(dir, 0o755); err != nil {
			return
		}
	}
	_ = os.WriteFile(outputPath, out, 0o644)
}

func ctmAppendPair(root *yaml.Node, key string, value *yaml.Node) {
	root.Content = append(root.Content, ctmScalarNode(key), value)
}

func ctmScalarNode(s string) *yaml.Node {
	return &yaml.Node{Kind: yaml.ScalarNode, Tag: "!!str", Value: s}
}

func ctmTemplateNode(template *entities.OrderedMap[[]string]) *yaml.Node {
	n := &yaml.Node{Kind: yaml.MappingNode}
	for _, k := range template.Keys() {
		fields, _ := template.Get(k)
		seq := &yaml.Node{Kind: yaml.SequenceNode, Tag: "!!seq"}
		for _, f := range fields {
			seq.Content = append(seq.Content, ctmScalarNode(f))
		}
		n.Content = append(n.Content, ctmScalarNode(k), seq)
	}
	return n
}

// ValidateTemplate mirrors ContextTemplateManager.validate_template.
func (m *ContextTemplateManager) ValidateTemplate(operation OperationType, requiredContexts []string) bool {
	template := m.GetTemplate(operation, nil)
	for _, contextType := range requiredContexts {
		if !template.Has(contextType) {
			return false
		}
	}
	return true
}

// GetMinimalContext mirrors ContextTemplateManager.get_minimal_context.
func (m *ContextTemplateManager) GetMinimalContext(operation OperationType, availableData *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	template := m.GetTemplate(operation, nil)
	minimalContext := entities.NewOrderedMap[any]()
	for _, contextType := range template.Keys() {
		requiredFields, _ := template.Get(contextType)
		raw, ok := availableData.Get(contextType)
		if !ok {
			continue
		}
		sourceData, isMap := raw.(*entities.OrderedMap[any])
		entryLen := 0
		if ctmIsStar(requiredFields) {
			minimalContext.Set(contextType, sourceData)
			if isMap {
				entryLen = sourceData.Len()
			}
		} else {
			filtered := entities.NewOrderedMap[any]()
			if isMap {
				for _, field := range requiredFields {
					if v, has := sourceData.Get(field); has {
						filtered.Set(field, v)
					}
				}
			}
			minimalContext.Set(contextType, filtered)
			entryLen = filtered.Len()
		}
		if isMap {
			m.metrics["fields_saved"] += sourceData.Len() - entryLen
		}
	}
	return minimalContext
}

// SuggestTemplateImprovements mirrors ContextTemplateManager.suggest_template_improvements.
func (m *ContextTemplateManager) SuggestTemplateImprovements(operation OperationType, actualUsage *entities.OrderedMap[[]string]) *entities.OrderedMap[any] {
	template := m.GetTemplate(operation, nil)
	unusedFields := entities.NewOrderedMap[any]()
	missingFields := entities.NewOrderedMap[any]()
	suggestions := entities.NewOrderedMap[any]()
	suggestions.Set("operation", operation.String())
	suggestions.Set("unused_fields", unusedFields)
	suggestions.Set("missing_fields", missingFields)
	suggestions.Set("optimization_potential", 0)

	for _, contextType := range template.Keys() {
		templateFields, _ := template.Get(contextType)
		used, has := actualUsage.Get(contextType)
		if !has || ctmIsStar(templateFields) {
			continue
		}
		usedSet := map[string]bool{}
		for _, f := range used {
			usedSet[f] = true
		}
		templateSet := map[string]bool{}
		for _, f := range templateFields {
			templateSet[f] = true
		}
		unused := []string{}
		for _, f := range templateFields {
			if !usedSet[f] {
				unused = append(unused, f)
			}
		}
		if len(unused) > 0 {
			unusedFields.Set(contextType, unused)
		}
		missing := []string{}
		for _, f := range used {
			if !templateSet[f] {
				missing = append(missing, f)
			}
		}
		if len(missing) > 0 {
			missingFields.Set(contextType, missing)
		}
	}

	totalUnused := 0
	for _, contextType := range unusedFields.Keys() {
		fields, _ := unusedFields.Get(contextType)
		if list, ok := fields.([]string); ok {
			totalUnused += len(list)
		}
	}
	totalFields := 0
	for _, k := range template.Keys() {
		fields, _ := template.Get(k)
		totalFields += ctmFieldCount(fields)
	}
	if totalFields > 0 {
		suggestions.Set("optimization_potential", (float64(totalUnused)/float64(totalFields))*100)
	}
	return suggestions
}

// GetMetrics mirrors ContextTemplateManager.get_metrics.
func (m *ContextTemplateManager) GetMetrics() *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	for _, k := range []string{"templates_used", "fields_requested", "fields_saved", "cache_hits"} {
		out.Set(k, m.metrics[k])
	}
	return out
}

// ResetMetrics mirrors ContextTemplateManager.reset_metrics.
func (m *ContextTemplateManager) ResetMetrics() {
	m.metrics = map[string]int{"templates_used": 0, "fields_requested": 0, "fields_saved": 0, "cache_hits": 0}
}

// GetAllOperations mirrors ContextTemplateManager.get_all_operations.
func (m *ContextTemplateManager) GetAllOperations() []string {
	out := []string{}
	for _, op := range ctmAllOperations() {
		out = append(out, op.String())
	}
	return out
}

// EstimateSavings mirrors ContextTemplateManager.estimate_savings.
func (m *ContextTemplateManager) EstimateSavings() *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	if m.metrics["fields_requested"] == 0 {
		out.Set("field_reduction_percent", 0)
		out.Set("estimated_time_savings_ms", 0)
		out.Set("estimated_bandwidth_savings_kb", 0)
		return out
	}
	totalPossible := m.metrics["fields_requested"] + m.metrics["fields_saved"]
	fieldReduction := 0.0
	if totalPossible > 0 {
		fieldReduction = (float64(m.metrics["fields_saved"]) / float64(totalPossible)) * 100
	}
	timeSavings := m.metrics["fields_saved"] * 1
	bandwidthSavings := float64(m.metrics["fields_saved"]*100) / 1024
	out.Set("field_reduction_percent", cfsRound1(fieldReduction))
	out.Set("estimated_time_savings_ms", timeSavings)
	out.Set("estimated_bandwidth_savings_kb", cfsRound2(bandwidthSavings))
	cacheHitRate := 0.0
	if m.metrics["templates_used"] > 0 {
		cacheHitRate = (float64(m.metrics["cache_hits"]) / float64(m.metrics["templates_used"])) * 100
	}
	out.Set("cache_hit_rate", cfsRound1(cacheHitRate))
	return out
}

// String returns the enum value, mirroring str(OperationType.X) -> value.
func (o OperationType) String() string { return string(o) }

func ctmAllOperations() []OperationType {
	return []OperationType{
		OperationTypeTaskCreate, OperationTypeTaskUpdate, OperationTypeTaskGet,
		OperationTypeTaskList, OperationTypeTaskDelete, OperationTypeTaskComplete,
		OperationTypeTaskSearch, OperationTypeTaskNext,
		OperationTypeSubtaskCreate, OperationTypeSubtaskUpdate, OperationTypeSubtaskDelete,
		OperationTypeSubtaskList, OperationTypeSubtaskComplete,
		OperationTypeContextCreate, OperationTypeContextGet, OperationTypeContextUpdate,
		OperationTypeContextDelete, OperationTypeContextResolve, OperationTypeContextDelegate,
		OperationTypeProjectCreate, OperationTypeProjectGet, OperationTypeProjectUpdate,
		OperationTypeProjectList, OperationTypeProjectHealthCheck,
		OperationTypeGitBranchCreate, OperationTypeGitBranchGet, OperationTypeGitBranchList,
		OperationTypeGitBranchUpdate, OperationTypeGitBranchDelete,
		OperationTypeAgentRegister, OperationTypeAgentAssign, OperationTypeAgentList,
		OperationTypeAgentCall,
	}
}
