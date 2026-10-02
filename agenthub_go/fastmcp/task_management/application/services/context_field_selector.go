package services

import (
	"math"
	"reflect"
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// FieldSet mirrors the Python FieldSet enum.
type FieldSet string

const (
	FieldSetMinimal FieldSet = "minimal"
	FieldSetSummary FieldSet = "summary"
	FieldSetDetail  FieldSet = "detail"
	FieldSetFull    FieldSet = "full"
)

// SelectionProfile mirrors the Python SelectionProfile enum.
type SelectionProfile string

const (
	SelectionProfileMinimal  SelectionProfile = "minimal"
	SelectionProfileStandard SelectionProfile = "summary"
	SelectionProfileDetailed SelectionProfile = "detail"
	SelectionProfileComplete SelectionProfile = "full"
)

// FieldSelectionConfig mirrors the Python mock configuration class.
type FieldSelectionConfig struct {
	IncludeFields   []string
	ExcludePatterns []string
	MaxDepth        int
}

// NewFieldSelectionConfig mirrors FieldSelectionConfig.__init__.
func NewFieldSelectionConfig(includeFields, excludePatterns []string, maxDepth *int) *FieldSelectionConfig {
	d := 3
	if maxDepth != nil && *maxDepth != 0 {
		d = *maxDepth
	}
	return &FieldSelectionConfig{IncludeFields: includeFields, ExcludePatterns: excludePatterns, MaxDepth: d}
}

// ContextFieldSelector provides selective field queries for context entities.
type ContextFieldSelector struct {
	taskFieldSets     map[FieldSet][]string
	projectFieldSets  map[FieldSet][]string
	contextFieldSets  map[FieldSet][]string
	fieldDependencies map[string][]string
	cache             map[string]any
	metrics           map[string]int
}

// NewContextFieldSelector mirrors ContextFieldSelector.__init__.
func NewContextFieldSelector() *ContextFieldSelector {
	return &ContextFieldSelector{
		taskFieldSets: map[FieldSet][]string{
			FieldSetMinimal: {"id", "title", "status", "priority"},
			FieldSetSummary: {"id", "title", "description", "status", "priority", "assignees", "labels"},
			FieldSetDetail:  {"id", "title", "description", "details", "status", "priority", "assignees", "labels", "estimated_effort", "progress_percentage", "dependencies", "subtasks"},
			FieldSetFull:    nil,
		},
		projectFieldSets: map[FieldSet][]string{
			FieldSetMinimal: {"id", "name", "status"},
			FieldSetSummary: {"id", "name", "status", "description", "created_at"},
			FieldSetDetail:  {"id", "name", "description", "status", "created_at", "updated_at", "owner", "team_members"},
			FieldSetFull:    nil,
		},
		contextFieldSets: map[FieldSet][]string{
			FieldSetMinimal: {"id", "level", "data"},
			FieldSetSummary: {"id", "level", "data", "created_at", "updated_at"},
			FieldSetDetail:  {"id", "level", "data", "metadata", "created_at", "updated_at", "parent_id", "children_ids"},
			FieldSetFull:    nil,
		},
		fieldDependencies: map[string][]string{
			"assignees":           {"assignee_ids"},
			"labels":              {"label_ids"},
			"progress_percentage": {"subtasks", "completed_subtasks"},
			"team_members":        {"team_member_ids"},
		},
		cache: map[string]any{},
		metrics: map[string]int{
			"queries_optimized": 0,
			"fields_reduced":    0,
			"cache_hits":        0,
			"cache_misses":      0,
		},
	}
}

// GetTaskFields mirrors ContextFieldSelector.get_task_fields.
func (s *ContextFieldSelector) GetTaskFields(taskID string, fields any) *entities.OrderedMap[any] {
	fieldList, hasFields, _ := s.resolveFields(fields, s.taskFieldSets)
	s.recordOptimization(hasFields, len(fieldList))
	return cfsSpec("task", taskID, "", fieldList, hasFields, false)
}

// GetProjectFields mirrors ContextFieldSelector.get_project_fields.
func (s *ContextFieldSelector) GetProjectFields(projectID string, fields any) *entities.OrderedMap[any] {
	fieldList, hasFields, _ := s.resolveFields(fields, s.projectFieldSets)
	s.recordOptimization(hasFields, len(fieldList))
	return cfsSpec("project", projectID, "", fieldList, hasFields, false)
}

// GetContextFields mirrors ContextFieldSelector.get_context_fields.
func (s *ContextFieldSelector) GetContextFields(contextID, level string, fields any) *entities.OrderedMap[any] {
	fieldList, hasFields, _ := s.resolveFields(fields, s.contextFieldSets)
	s.recordOptimization(hasFields, len(fieldList))
	return cfsSpec("context", contextID, level, fieldList, hasFields, true)
}

func (s *ContextFieldSelector) resolveFields(fields any, sets map[FieldSet][]string) ([]string, bool, bool) {
	requestingFull := false
	if fs, ok := fields.(FieldSet); ok {
		if fs == FieldSetFull {
			requestingFull = true
		}
		fields = fieldSetLookup(sets, fs)
	}
	var fieldList []string
	hasFields := fields != nil
	if fields != nil {
		if l, ok := fields.([]string); ok {
			fieldList = l
		}
	}
	if !hasFields && !requestingFull {
		fieldList = sets[FieldSetSummary]
		hasFields = true
	}
	if hasFields && len(fieldList) > 0 {
		fieldList = s.ExpandFieldDependencies_public(fieldList)
	}
	return fieldList, hasFields, requestingFull
}

func (s *ContextFieldSelector) recordOptimization(hasFields bool, n int) {
	s.metrics["queries_optimized"]++
	if hasFields && n > 0 {
		full := 50
		s.metrics["fields_reduced"] += full - n
	}
}

func fieldSetLookup(sets map[FieldSet][]string, fs FieldSet) any {
	v, ok := sets[fs]
	if !ok || v == nil {
		return nil
	}
	return v
}

func cfsSpec(entityType, entityID, level string, fieldList []string, hasFields, withLevel bool) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("entity_type", entityType)
	m.Set("entity_id", entityID)
	if withLevel {
		m.Set("level", level)
	}
	if hasFields {
		m.Set("fields", fieldList)
	} else {
		m.Set("fields", nil)
	}
	m.Set("optimized", hasFields)
	return m
}

// BuildOptimizedQuery mirrors ContextFieldSelector.build_optimized_query.
func (s *ContextFieldSelector) BuildOptimizedQuery(entityClass any, fields []string) any {
	if fields == nil {
		return entityClass
	}
	var attrs []any
	t := reflect.TypeOf(entityClass)
	if t != nil && t.Kind() == reflect.Ptr {
		t = t.Elem()
	}
	for _, field := range fields {
		if t != nil && t.Kind() == reflect.Struct {
			if _, ok := t.FieldByName(cfsExported(field)); ok {
				attrs = append(attrs, field)
			}
		}
	}
	return attrs
}

func cfsExported(field string) string {
	if field == "" {
		return field
	}
	return strings.ToUpper(field[:1]) + field[1:]
}

// ExpandFieldDependencies_public mirrors _expand_field_dependencies (deterministic
// insertion order is used instead of Python's unordered set iteration).
func (s *ContextFieldSelector) ExpandFieldDependencies_public(fields []string) []string {
	seen := map[string]bool{}
	out := []string{}
	add := func(f string) {
		if !seen[f] {
			seen[f] = true
			out = append(out, f)
		}
	}
	for _, f := range fields {
		add(f)
	}
	for _, f := range fields {
		if deps, ok := s.fieldDependencies[f]; ok {
			for _, d := range deps {
				add(d)
			}
		}
	}
	return out
}

// GetOptimalFieldSet mirrors ContextFieldSelector.get_optimal_field_set.
func (s *ContextFieldSelector) GetOptimalFieldSet(operation, entityType string) FieldSet {
	switch operation {
	case "list", "status", "count", "exists":
		return FieldSetMinimal
	case "get", "search", "filter":
		return FieldSetSummary
	case "update", "create", "workflow":
		return FieldSetDetail
	case "debug", "audit", "export":
		return FieldSetFull
	}
	return FieldSetSummary
}

// CacheFieldMapping mirrors ContextFieldSelector.cache_field_mapping.
func (s *ContextFieldSelector) CacheFieldMapping(entityID string, fields []string, data *entities.OrderedMap[any]) {
	s.cache[cfsCacheKey(entityID, fields)] = data
}

// GetCachedFields mirrors ContextFieldSelector.get_cached_fields.
func (s *ContextFieldSelector) GetCachedFields(entityID string, fields []string) *entities.OrderedMap[any] {
	key := cfsCacheKey(entityID, fields)
	if v, ok := s.cache[key]; ok {
		s.metrics["cache_hits"]++
		if m, ok := v.(*entities.OrderedMap[any]); ok {
			return m
		}
		return nil
	}
	s.metrics["cache_misses"]++
	return nil
}

func cfsCacheKey(entityID string, fields []string) string {
	sorted := append([]string{}, fields...)
	// sorted() in Python
	for i := 1; i < len(sorted); i++ {
		for j := i; j > 0 && sorted[j] < sorted[j-1]; j-- {
			sorted[j], sorted[j-1] = sorted[j-1], sorted[j]
		}
	}
	return entityID + ":" + strings.Join(sorted, ",")
}

// GetMetrics mirrors ContextFieldSelector.get_metrics.
func (s *ContextFieldSelector) GetMetrics() *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	for _, k := range []string{"queries_optimized", "fields_reduced", "cache_hits", "cache_misses"} {
		m.Set(k, s.metrics[k])
	}
	return m
}

// ResetMetrics mirrors ContextFieldSelector.reset_metrics.
func (s *ContextFieldSelector) ResetMetrics() {
	s.metrics = map[string]int{"queries_optimized": 0, "fields_reduced": 0, "cache_hits": 0, "cache_misses": 0}
}

// EstimateSavings mirrors ContextFieldSelector.estimate_savings.
func (s *ContextFieldSelector) EstimateSavings(entityType string, fieldSet FieldSet) *entities.OrderedMap[any] {
	var fullFields int
	var fieldSets map[FieldSet][]string
	switch entityType {
	case "task":
		fullFields = 50
		fieldSets = s.taskFieldSets
	case "project":
		fullFields = 30
		fieldSets = s.projectFieldSets
	case "context":
		fullFields = 20
		fieldSets = s.contextFieldSets
	default:
		m := entities.NewOrderedMap[any]()
		m.Set("error", "Unknown entity type")
		return m
	}

	var selectedFields int
	if fieldSet == FieldSetFull || fieldSets[fieldSet] == nil {
		selectedFields = fullFields
	} else {
		selectedFields = len(fieldSets[fieldSet])
	}

	fieldReduction := (float64(fullFields-selectedFields) / float64(fullFields)) * 100
	queryTime := fieldReduction * 0.7
	bandwidth := fieldReduction * 0.9
	var cache any
	if fieldReduction*1.2 < 95 {
		cache = cfsRound1(fieldReduction * 1.2)
	} else {
		cache = 95
	}

	m := entities.NewOrderedMap[any]()
	m.Set("field_reduction_percent", cfsRound1(fieldReduction))
	m.Set("query_time_savings_percent", cfsRound1(queryTime))
	m.Set("bandwidth_savings_percent", cfsRound1(bandwidth))
	m.Set("cache_efficiency_percent", cache)
	m.Set("selected_fields", selectedFields)
	m.Set("full_fields", fullFields)
	return m
}

func cfsRound1(x float64) float64 { return math.Round(x*10) / 10 }
func cfsRound2(x float64) float64 { return math.Round(x*100) / 100 }

// ExcludeFields mirrors ContextFieldSelector.exclude_fields.
func (s *ContextFieldSelector) ExcludeFields(context *entities.OrderedMap[any], fields []string) *entities.OrderedMap[any] {
	result := context.Copy()
	for _, f := range fields {
		result.Delete(f)
	}
	return result
}

// SelectForAction mirrors ContextFieldSelector.select_for_action.
func (s *ContextFieldSelector) SelectForAction(context *entities.OrderedMap[any], action string) *entities.OrderedMap[any] {
	fieldSet := s.DetermineFieldSetForOperation(action)
	return s.SelectFields(context, fieldSet, nil, nil, nil, nil, nil, nil, nil)
}

// SelectNestedFields mirrors ContextFieldSelector.select_nested_fields.
func (s *ContextFieldSelector) SelectNestedFields(context *entities.OrderedMap[any], fieldPaths []string) *entities.OrderedMap[any] {
	result := entities.NewOrderedMap[any]()
	for _, path := range fieldPaths {
		parts := strings.Split(path, ".")
		source := context
		target := result
		ok := true
		for _, part := range parts[:len(parts)-1] {
			srcVal, has := source.Get(part)
			if !has {
				ok = false
				break
			}
			child, isMap := srcVal.(*entities.OrderedMap[any])
			if !isMap {
				ok = false
				break
			}
			next, hasTarget := target.Get(part)
			if !hasTarget {
				next = entities.NewOrderedMap[any]()
				target.Set(part, next)
			}
			source = child
			target, _ = next.(*entities.OrderedMap[any])
		}
		_ = ok
		if ok {
			if v, has := source.Get(parts[len(parts)-1]); has {
				target.Set(parts[len(parts)-1], v)
			}
		}
	}
	return result
}

// HandleArrayFields mirrors ContextFieldSelector.handle_array_fields.
func (s *ContextFieldSelector) HandleArrayFields(context *entities.OrderedMap[any], arrayConfig map[string]int) *entities.OrderedMap[any] {
	result := context.Copy()
	for field, limit := range arrayConfig {
		if v, ok := result.Get(field); ok {
			if list, ok := v.([]any); ok {
				if len(list) > limit {
					result.Set(field, list[:limit])
				}
			}
		}
	}
	return result
}

// ApplyFieldSizeLimits mirrors ContextFieldSelector.apply_field_size_limits.
func (s *ContextFieldSelector) ApplyFieldSizeLimits(context *entities.OrderedMap[any], limits map[string]int) *entities.OrderedMap[any] {
	result := context.Copy()
	for field, limit := range limits {
		v, ok := result.Get(field)
		if !ok {
			continue
		}
		if str, ok := v.(string); ok && len(str) > limit {
			result.Set(field, str[:limit]+"...")
		} else if list, ok := v.([]any); ok && len(list) > limit {
			result.Set(field, list[:limit])
		}
	}
	return result
}

// ApplySizeLimit mirrors ContextFieldSelector._apply_size_limit.
func (s *ContextFieldSelector) ApplySizeLimit(data *entities.OrderedMap[any], sizeLimit int) *entities.OrderedMap[any] {
	currentSize := len(value_objects.PyJSONDumpsDefaultStr(data, -1))
	if currentSize <= sizeLimit {
		return data
	}
	result := data.Copy()
	removalOrder := []string{"metadata", "attachments", "comments", "details", "description", "subtasks", "dependencies"}
	for _, field := range removalOrder {
		if result.Has(field) {
			result.Delete(field)
			if len(value_objects.PyJSONDumpsDefaultStr(result, -1)) <= sizeLimit {
				break
			}
		}
	}
	return result
}

// GetProfileConfiguration mirrors ContextFieldSelector.get_profile_configuration.
func (s *ContextFieldSelector) GetProfileConfiguration(profile any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	switch p := profile.(type) {
	case FieldSet:
		m.Set("profile", p)
	case SelectionProfile:
		m.Set("profile", p)
	default:
		m.Set("profile", value_objects.PyStr(profile))
	}
	m.Set("task_fields", cfsFieldSetValue(s.taskFieldSets, profile))
	m.Set("project_fields", cfsFieldSetValue(s.projectFieldSets, profile))
	m.Set("context_fields", cfsFieldSetValue(s.contextFieldSets, profile))
	return m
}

func cfsFieldSetValue(m map[FieldSet][]string, p any) any {
	fs, ok := p.(FieldSet)
	if !ok {
		return []string{}
	}
	v, present := m[fs]
	if !present {
		return []string{}
	}
	if v == nil {
		return nil
	}
	return v
}

// DiscoverFields mirrors ContextFieldSelector.discover_fields.
func (s *ContextFieldSelector) DiscoverFields(context *entities.OrderedMap[any], maxDepth int) *entities.OrderedMap[any] {
	return cfsDiscover(context, 0, maxDepth)
}

func cfsDiscover(obj any, depth, maxDepth int) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	if depth >= maxDepth {
		out.Set("type", "object")
		out.Set("truncated", true)
		return out
	}
	switch v := obj.(type) {
	case *entities.OrderedMap[any]:
		out.Set("type", "dict")
		fields := entities.NewOrderedMap[any]()
		for _, k := range v.Keys() {
			val, _ := v.Get(k)
			fields.Set(k, cfsDiscover(val, depth+1, maxDepth))
		}
		out.Set("fields", fields)
	case []any:
		if len(v) > 0 {
			out.Set("type", "list")
			out.Set("length", len(v))
			out.Set("sample", cfsDiscover(v[0], depth+1, maxDepth))
		} else {
			out.Set("type", "list")
			out.Set("length", 0)
		}
	default:
		out.Set("type", cfsPyTypeName(obj))
		if str, ok := obj.(string); ok {
			if len(str) > 50 {
				out.Set("value", str[:50])
			} else {
				out.Set("value", str)
			}
		} else {
			out.Set("value", nil)
		}
	}
	return out
}

func cfsPyTypeName(obj any) string {
	switch obj.(type) {
	case nil:
		return "NoneType"
	case string:
		return "str"
	case bool:
		return "bool"
	case int, int8, int16, int32, int64:
		return "int"
	case float32, float64:
		return "float"
	case []any:
		return "list"
	case *entities.OrderedMap[any]:
		return "dict"
	}
	return reflect.TypeOf(obj).String()
}

// ApplyConditionalInclusion mirrors ContextFieldSelector.apply_conditional_inclusion.
func (s *ContextFieldSelector) ApplyConditionalInclusion(context *entities.OrderedMap[any], conditions *entities.OrderedMap[func(any) bool]) *entities.OrderedMap[any] {
	result := entities.NewOrderedMap[any]()
	for _, field := range conditions.Keys() {
		cond, _ := conditions.Get(field)
		if v, ok := context.Get(field); ok && cond(v) {
			result.Set(field, v)
		}
	}
	return result
}

// TransformFields mirrors ContextFieldSelector.transform_fields.
func (s *ContextFieldSelector) TransformFields(context *entities.OrderedMap[any], transformations *entities.OrderedMap[func(any) any]) *entities.OrderedMap[any] {
	result := context.Copy()
	for _, field := range transformations.Keys() {
		if v, ok := result.Get(field); ok {
			fn, _ := transformations.Get(field)
			result.Set(field, fn(v))
		}
	}
	return result
}

// OptimizeForPerformance mirrors ContextFieldSelector.optimize_for_performance.
func (s *ContextFieldSelector) OptimizeForPerformance(contexts []*entities.OrderedMap[any], profile any) []*entities.OrderedMap[any] {
	out := make([]*entities.OrderedMap[any], 0, len(contexts))
	for _, ctx := range contexts {
		out = append(out, s.SelectFields(ctx, profile, nil, nil, nil, nil, nil, nil, nil))
	}
	return out
}

// CacheFieldConfiguration mirrors ContextFieldSelector.cache_field_configuration.
func (s *ContextFieldSelector) CacheFieldConfiguration(configID string, configuration *entities.OrderedMap[any]) {
	s.cache["config:"+configID] = configuration
}

// MergeFieldSelections mirrors ContextFieldSelector.merge_field_selections.
func (s *ContextFieldSelector) MergeFieldSelections(selections ...[]string) []string {
	seen := map[string]bool{}
	out := []string{}
	for _, sel := range selections {
		for _, f := range sel {
			if !seen[f] {
				seen[f] = true
				out = append(out, f)
			}
		}
	}
	return out
}

// SelectFieldsForAction mirrors ContextFieldSelector.select_fields_for_action.
func (s *ContextFieldSelector) SelectFieldsForAction(context *entities.OrderedMap[any], action string) *entities.OrderedMap[any] {
	return s.SelectForAction(context, action)
}

// ConfigureProfile mirrors ContextFieldSelector.configure_profile.
func (s *ContextFieldSelector) ConfigureProfile(profileName string, config any) {
	s.cache["profile:"+profileName] = config
}

// DiscoverCommonFields mirrors ContextFieldSelector.discover_common_fields.
func (s *ContextFieldSelector) DiscoverCommonFields(contexts []*entities.OrderedMap[any]) map[string]struct{} {
	if len(contexts) == 0 {
		return map[string]struct{}{}
	}
	common := map[string]struct{}{}
	for _, k := range contexts[0].Keys() {
		common[k] = struct{}{}
	}
	for _, ctx := range contexts[1:] {
		for k := range common {
			if !ctx.Has(k) {
				delete(common, k)
			}
		}
	}
	return common
}

// DiscoverAllFields mirrors ContextFieldSelector.discover_all_fields.
func (s *ContextFieldSelector) DiscoverAllFields(contexts []*entities.OrderedMap[any]) map[string]struct{} {
	all := map[string]struct{}{}
	for _, ctx := range contexts {
		for _, k := range ctx.Keys() {
			all[k] = struct{}{}
		}
	}
	return all
}

// ScoreFieldImportance mirrors ContextFieldSelector.score_field_importance.
func (s *ContextFieldSelector) ScoreFieldImportance(context *entities.OrderedMap[any]) *entities.OrderedMap[float64] {
	scores := entities.NewOrderedMap[float64]()
	for _, field := range context.Keys() {
		scores.Set(field, s.ScoreSingleFieldImportance(field, context))
	}
	return scores
}

// ScoreSingleFieldImportance mirrors ContextFieldSelector._score_single_field_importance.
func (s *ContextFieldSelector) ScoreSingleFieldImportance(fieldName string, context *entities.OrderedMap[any]) float64 {
	coreFields := map[string]bool{"id": true, "title": true, "name": true, "status": true}
	if coreFields[fieldName] {
		return 1.0
	}
	important := map[string]bool{"description": true, "priority": true, "assignees": true, "created_at": true}
	if important[fieldName] {
		return 0.8
	}
	metadata := map[string]bool{"labels": true, "tags": true, "metadata": true, "updated_at": true}
	if metadata[fieldName] {
		return 0.6
	}
	if v, ok := context.Get(fieldName); ok {
		switch val := v.(type) {
		case []any:
			if len(value_objects.PyStr(val)) > 1000 {
				return 0.3
			}
		case *entities.OrderedMap[any]:
			if len(value_objects.PyStr(val)) > 1000 {
				return 0.3
			}
		}
	}
	return 0.5
}

// GetProfileConfig mirrors ContextFieldSelector.get_profile_config.
func (s *ContextFieldSelector) GetProfileConfig(profile any) *entities.OrderedMap[any] {
	key := "profile_config:" + value_objects.PyStr(profile)
	if v, ok := s.cache[key]; ok {
		if m, ok := v.(*entities.OrderedMap[any]); ok {
			return m
		}
	}
	config := s.GetProfileConfiguration(profile)
	s.cache[key] = config
	return config
}

// MergeSelections mirrors ContextFieldSelector.merge_selections.
func (s *ContextFieldSelector) MergeSelections(selections []*entities.OrderedMap[any]) *entities.OrderedMap[any] {
	merged := entities.NewOrderedMap[any]()
	for _, sel := range selections {
		if sel == nil {
			continue
		}
		for _, k := range sel.Keys() {
			v, _ := sel.Get(k)
			merged.Set(k, v)
		}
	}
	return merged
}

// SelectFields mirrors ContextFieldSelector.select_fields.
func (s *ContextFieldSelector) SelectFields(
	context *entities.OrderedMap[any],
	profile any,
	customFields []string,
	excludeFields []string,
	action *string,
	sizeLimit *int,
	maxFieldSize *int,
	conditionalRules *entities.OrderedMap[func(any) bool],
	transformations *entities.OrderedMap[func(any) any],
) *entities.OrderedMap[any] {
	if name, ok := profile.(string); ok && name == "custom" {
		if cfg, ok := s.cache["profile:"+name].(*FieldSelectionConfig); ok {
			if cfg.IncludeFields != nil {
				customFields = cfg.IncludeFields
			}
			for _, pattern := range cfg.ExcludePatterns {
				if strings.HasPrefix(pattern, "*") && strings.HasSuffix(pattern, "*") {
					substr := pattern[1 : len(pattern)-1]
					for _, k := range context.Keys() {
						if strings.Contains(k, substr) {
							excludeFields = append(excludeFields, k)
						}
					}
				} else if strings.HasPrefix(pattern, "*") {
					suffix := pattern[1:]
					for _, k := range context.Keys() {
						if strings.HasSuffix(k, suffix) {
							excludeFields = append(excludeFields, k)
						}
					}
				} else if strings.HasSuffix(pattern, ".*") {
					prefix := pattern[:len(pattern)-2]
					for _, k := range context.Keys() {
						if strings.HasPrefix(k, prefix) {
							excludeFields = append(excludeFields, k)
						}
					}
				}
			}
		}
	}

	if profile == nil {
		profile = FieldSetSummary
	}

	if sp, ok := profile.(SelectionProfile); ok {
		switch sp {
		case SelectionProfileMinimal:
			profile = FieldSetMinimal
		case SelectionProfileStandard:
			profile = FieldSetSummary
		case SelectionProfileDetailed:
			profile = FieldSetDetail
		case SelectionProfileComplete:
			profile = FieldSetFull
		default:
			profile = FieldSetSummary
		}
	}

	var result *entities.OrderedMap[any]
	hasDot := false
	for _, f := range customFields {
		if strings.Contains(f, ".") {
			hasDot = true
			break
		}
	}
	if len(customFields) > 0 && hasDot {
		result = s.SelectNestedFields(context, customFields)
	} else if customFields != nil {
		include := map[string]bool{}
		for _, f := range customFields {
			include[f] = true
		}
		result = entities.NewOrderedMap[any]()
		for _, k := range context.Keys() {
			if include[k] {
				v, _ := context.Get(k)
				result.Set(k, v)
			}
		}
	} else {
		fieldSets := s.taskFieldSets
		fs, isFieldSet := profile.(FieldSet)
		_, inSet := fieldSets[fs]
		if (isFieldSet && fs == FieldSetFull) || !inSet {
			result = context.Copy()
		} else {
			fieldsList := fieldSets[fs]
			if fieldsList == nil {
				result = context.Copy()
			} else {
				include := map[string]bool{}
				for _, f := range s.ExpandFieldDependencies_public(fieldsList) {
					include[f] = true
				}
				result = entities.NewOrderedMap[any]()
				for _, k := range context.Keys() {
					if include[k] {
						v, _ := context.Get(k)
						result.Set(k, v)
					}
				}
			}
		}
	}

	for _, field := range excludeFields {
		result.Delete(field)
	}

	if conditionalRules != nil {
		for _, field := range conditionalRules.Keys() {
			cond, _ := conditionalRules.Get(field)
			if _, ok := context.Get(field); ok && cond(context) {
				v, _ := context.Get(field)
				result.Set(field, v)
			}
		}
	}

	if transformations != nil {
		result = s.TransformFields(result, transformations)
	}

	if maxFieldSize != nil {
		result = s.ApplyFieldSizeLimit(result, *maxFieldSize)
	}
	if sizeLimit != nil {
		result = s.ApplySizeLimit(result, *sizeLimit)
	}
	return result
}

// ApplyFieldSizeLimit mirrors ContextFieldSelector._apply_field_size_limit.
func (s *ContextFieldSelector) ApplyFieldSizeLimit(data *entities.OrderedMap[any], maxSize int) *entities.OrderedMap[any] {
	result := entities.NewOrderedMap[any]()
	for _, key := range data.Keys() {
		value, _ := data.Get(key)
		if str, ok := value.(string); ok && len(str) > maxSize {
			if maxSize > 3 {
				result.Set(key, str[:maxSize-3]+"...")
			} else {
				result.Set(key, str[:maxSize])
			}
		} else {
			result.Set(key, value)
		}
	}
	return result
}

// DetermineFieldSetForOperation mirrors ContextFieldSelector.determine_field_set_for_operation.
func (s *ContextFieldSelector) DetermineFieldSetForOperation(operation string) FieldSet {
	return s.GetOptimalFieldSet(operation, "task")
}
