package services

import (
	"fmt"
	"reflect"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// ContextInheritanceService handles the logic for merging and inheriting contexts
// across the hierarchy: Global → Project → Branch → Task with proper override and
// precedence rules (Python application/services/context_inheritance_service.py).
//
// Every Python dict whose key order is observable is an *entities.OrderedMap[any];
// a nil pointer represents Python None. Logging is dropped.
type ContextInheritanceService struct {
	Repository any
	UserID     *string
}

// NewContextInheritanceService mirrors __init__(repository=None, user_id=None).
func NewContextInheritanceService(repository any, userID *string) *ContextInheritanceService {
	return &ContextInheritanceService{Repository: repository, UserID: userID}
}

// getUserScopedRepository mirrors _get_user_scoped_repository. The Go repository
// interfaces expose no with_user/user_id/session attributes, and the Python
// reconstruction branch has no Go equivalent, so the repository is returned unchanged.
func (s *ContextInheritanceService) getUserScopedRepository(repository any) any {
	return repository
}

// WithUser creates a new service instance scoped to a specific user.
func (s *ContextInheritanceService) WithUser(userID string) *ContextInheritanceService {
	return NewContextInheritanceService(s.Repository, &userID)
}

// GetInheritedContext is the simplified sync method that returns None (nil), indicating
// no inheritance data is available.
func (s *ContextInheritanceService) GetInheritedContext(level, contextID string) *entities.OrderedMap[any] {
	return nil
}

// InheritProjectFromGlobal inherits project context from global context with project
// overrides.
func (s *ContextInheritanceService) InheritProjectFromGlobal(globalContext, projectContext *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	inherited := zpCtxInhDeepCopyMap(globalContext)

	projectConfig := entities.NewOrderedMap[any]()
	projectConfig.Set("team_preferences", zpCtxInhGetOr(projectContext, "team_preferences", entities.NewOrderedMap[any]()))
	projectConfig.Set("technology_stack", zpCtxInhGetOr(projectContext, "technology_stack", entities.NewOrderedMap[any]()))
	projectConfig.Set("project_workflow", zpCtxInhGetOr(projectContext, "project_workflow", entities.NewOrderedMap[any]()))
	projectConfig.Set("local_standards", zpCtxInhGetOr(projectContext, "local_standards", entities.NewOrderedMap[any]()))

	inherited = s.deepMerge(inherited, projectConfig)

	known := map[string]bool{
		"team_preferences": true, "technology_stack": true, "project_workflow": true,
		"local_standards": true, "global_overrides": true, "delegation_rules": true,
		"created_at": true, "updated_at": true,
	}
	for _, key := range projectContext.Keys() {
		if known[key] {
			continue
		}
		value, _ := projectContext.Get(key)
		inherited.Set(key, value)
	}

	globalOverridesAny, _ := projectContext.Get("global_overrides")
	globalOverrides, _ := zpCtxInhDict(globalOverridesAny)
	globalOverridesLen := 0
	if globalOverrides != nil {
		globalOverridesLen = globalOverrides.Len()
	}
	if value_objects.PyTruthy(globalOverridesAny) && globalOverrides != nil {
		inherited = s.applyOverrides(inherited, globalOverrides)
	}

	projectDelegationAny, _ := projectContext.Get("delegation_rules")
	if value_objects.PyTruthy(projectDelegationAny) {
		if projectDelegation, ok := zpCtxInhDict(projectDelegationAny); ok {
			baseAny, _ := inherited.Get("delegation_rules")
			base, _ := zpCtxInhDict(baseAny)
			inherited.Set("delegation_rules", s.mergeDelegationRules(base, projectDelegation))
		}
	}

	meta := entities.NewOrderedMap[any]()
	meta.Set("inherited_from", "global")
	meta.Set("global_context_version", zpCtxInhVersion(globalContext))
	meta.Set("project_overrides_applied", globalOverridesLen)
	meta.Set("inheritance_disabled", zpCtxInhGetOr(projectContext, "inheritance_disabled", false))
	inherited.Set("inheritance_metadata", meta)

	return inherited
}

// InheritBranchFromProject inherits branch context from project context with
// branch-specific overrides.
func (s *ContextInheritanceService) InheritBranchFromProject(projectContext, branchContext *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	inherited := zpCtxInhDeepCopyMap(projectContext)

	branchConfig := entities.NewOrderedMap[any]()
	branchConfig.Set("branch_workflow", zpCtxInhGetOr(branchContext, "branch_workflow", entities.NewOrderedMap[any]()))
	branchConfig.Set("branch_standards", zpCtxInhGetOr(branchContext, "branch_standards", entities.NewOrderedMap[any]()))
	branchConfig.Set("agent_assignments", zpCtxInhGetOr(branchContext, "agent_assignments", entities.NewOrderedMap[any]()))

	inherited = s.deepMerge(inherited, branchConfig)

	known := map[string]bool{
		"branch_workflow": true, "branch_standards": true, "agent_assignments": true,
		"local_overrides": true, "delegation_rules": true, "created_at": true, "updated_at": true,
	}
	for _, key := range branchContext.Keys() {
		if known[key] {
			continue
		}
		value, _ := branchContext.Get(key)
		inherited.Set(key, value)
	}

	localOverridesAny, _ := branchContext.Get("local_overrides")
	localOverrides, _ := zpCtxInhDict(localOverridesAny)
	localOverridesLen := 0
	if localOverrides != nil {
		localOverridesLen = localOverrides.Len()
	}
	if value_objects.PyTruthy(localOverridesAny) && localOverrides != nil {
		inherited = s.applyOverrides(inherited, localOverrides)
	}

	branchDelegationAny, _ := branchContext.Get("delegation_rules")
	if value_objects.PyTruthy(branchDelegationAny) {
		if branchDelegation, ok := zpCtxInhDict(branchDelegationAny); ok {
			baseAny, _ := inherited.Get("delegation_rules")
			base, _ := zpCtxInhDict(baseAny)
			inherited.Set("delegation_rules", s.mergeDelegationRules(base, branchDelegation))
		}
	}

	meta := entities.NewOrderedMap[any]()
	meta.Set("inherited_from", "project")
	meta.Set("project_context_version", zpCtxInhVersion(projectContext))
	meta.Set("branch_overrides_applied", localOverridesLen)
	meta.Set("inheritance_disabled", zpCtxInhGetOr(branchContext, "inheritance_disabled", false))
	meta.Set("inheritance_chain", []any{"global", "project", "branch"})
	inherited.Set("inheritance_metadata", meta)

	return inherited
}

// InheritTaskFromBranch inherits task context from branch context with task-specific
// data.
func (s *ContextInheritanceService) InheritTaskFromBranch(branchContext, taskContext *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	inherited := zpCtxInhDeepCopyMap(branchContext)

	taskDataAny, _ := taskContext.Get("task_data")
	if value_objects.PyTruthy(taskDataAny) {
		inherited.Set("task_data", taskDataAny)
	}

	known := map[string]bool{
		"task_data": true, "local_overrides": true, "implementation_notes": true,
		"delegation_status": true, "created_at": true, "updated_at": true,
	}
	for _, key := range taskContext.Keys() {
		if known[key] {
			continue
		}
		value, _ := taskContext.Get(key)
		inherited.Set(key, value)
	}

	localOverridesAny, _ := taskContext.Get("local_overrides")
	localOverrides, _ := zpCtxInhDict(localOverridesAny)
	localOverridesLen := 0
	if localOverrides != nil {
		localOverridesLen = localOverrides.Len()
	}
	if value_objects.PyTruthy(localOverridesAny) && localOverrides != nil {
		inherited = s.applyOverrides(inherited, localOverrides)
	}

	implementationNotesAny, _ := taskContext.Get("implementation_notes")
	if value_objects.PyTruthy(implementationNotesAny) {
		inherited.Set("implementation_notes", implementationNotesAny)
	}

	customRulesAny, _ := taskContext.Get("custom_inheritance_rules")
	customRules, _ := zpCtxInhDict(customRulesAny)
	customRulesLen := 0
	if customRules != nil {
		customRulesLen = customRules.Len()
	}
	if value_objects.PyTruthy(customRulesAny) && customRules != nil {
		inherited = s.applyCustomInheritanceRules(inherited, customRules)
	}

	delegationTriggersAny, _ := taskContext.Get("delegation_triggers")
	if value_objects.PyTruthy(delegationTriggersAny) {
		inherited.Set("delegation_triggers", delegationTriggersAny)
	}

	meta := entities.NewOrderedMap[any]()
	meta.Set("inherited_from", "branch")
	meta.Set("branch_context_version", zpCtxInhVersion(branchContext))
	meta.Set("local_overrides_applied", localOverridesLen)
	meta.Set("custom_rules_applied", customRulesLen)
	meta.Set("force_local_only", zpCtxInhGetOr(taskContext, "force_local_only", false))
	meta.Set("inheritance_chain", []any{"global", "project", "branch", "task"})
	inherited.Set("inheritance_metadata", meta)

	return inherited
}

// deepMerge deep merges two dictionaries with override precedence.
func (s *ContextInheritanceService) deepMerge(base, override *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	result := zpCtxInhDeepCopyMap(base)
	if result == nil {
		result = entities.NewOrderedMap[any]()
	}
	if override == nil {
		return result
	}
	for _, key := range override.Keys() {
		value, _ := override.Get(key)
		if existing, ok := result.Get(key); ok {
			baseDict, baseIsDict := zpCtxInhDict(existing)
			overDict, overIsDict := zpCtxInhDict(value)
			baseList, baseIsList := zpCtxInhList(existing)
			overList, overIsList := zpCtxInhList(value)
			switch {
			case baseIsDict && overIsDict:
				result.Set(key, s.deepMerge(baseDict, overDict))
			case baseIsList && overIsList:
				result.Set(key, s.mergeLists(baseList, overList, key))
			default:
				result.Set(key, zpCtxInhDeepCopy(value))
			}
		} else {
			result.Set(key, zpCtxInhDeepCopy(value))
		}
	}
	return result
}

// mergeLists merges lists based on context-specific strategies.
func (s *ContextInheritanceService) mergeLists(baseList, overrideList []any, key string) []any {
	switch key {
	case "assignees", "labels", "technologies", "frameworks":
		// Combine and deduplicate, preserving order (dict.fromkeys).
		out := make([]any, 0, len(baseList)+len(overrideList))
		for _, item := range append(append([]any{}, baseList...), overrideList...) {
			dup := false
			for _, seen := range out {
				if value_objects.PyEqual(seen, item) {
					dup = true
					break
				}
			}
			if !dup {
				out = append(out, item)
			}
		}
		return out
	case "requirements", "checklist", "next_steps":
		return append(append([]any{}, baseList...), overrideList...)
	default:
		return zpCtxInhDeepCopy(overrideList).([]any)
	}
}

// applyOverrides applies explicit overrides to context using dot notation for nested keys.
func (s *ContextInheritanceService) applyOverrides(context, overrides *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	result := zpCtxInhDeepCopyMap(context)
	if result == nil {
		result = entities.NewOrderedMap[any]()
	}
	if overrides == nil {
		return result
	}
	for _, overridePath := range overrides.Keys() {
		overrideValue, _ := overrides.Get(overridePath)
		pathParts := strings.Split(overridePath, ".")
		current := result
		for _, part := range pathParts[:len(pathParts)-1] {
			if !current.Has(part) {
				current.Set(part, entities.NewOrderedMap[any]())
			}
			next, _ := current.Get(part)
			nextMap, ok := zpCtxInhDict(next)
			if !ok {
				// Python would raise TypeError navigating a non-dict; replace it.
				nextMap = entities.NewOrderedMap[any]()
				current.Set(part, nextMap)
			}
			current = nextMap
		}
		current.Set(pathParts[len(pathParts)-1], zpCtxInhDeepCopy(overrideValue))
	}
	return result
}

// mergeDelegationRules merges delegation rules with project-specific additions.
func (s *ContextInheritanceService) mergeDelegationRules(baseRules, projectRules *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	merged := zpCtxInhDeepCopyMap(baseRules)
	if merged == nil {
		merged = entities.NewOrderedMap[any]()
	}
	if projectRules == nil {
		return merged
	}
	if projectRules.Has("auto_delegate") {
		projectAuto, _ := projectRules.Get("auto_delegate")
		mergedAutoAny, _ := merged.Get("auto_delegate")
		mergedAuto, ok := zpCtxInhDict(mergedAutoAny)
		if !ok {
			mergedAuto = entities.NewOrderedMap[any]()
		}
		if projectAutoMap, ok := zpCtxInhDict(projectAuto); ok {
			for _, key := range projectAutoMap.Keys() {
				value, _ := projectAutoMap.Get(key)
				mergedAuto.Set(key, value)
			}
		}
		merged.Set("auto_delegate", mergedAuto)
	}
	if projectRules.Has("thresholds") {
		projectThresholds, _ := projectRules.Get("thresholds")
		mergedThresholdsAny, _ := merged.Get("thresholds")
		mergedThresholds, ok := zpCtxInhDict(mergedThresholdsAny)
		if !ok {
			mergedThresholds = entities.NewOrderedMap[any]()
		}
		if projectThresholdsMap, ok := zpCtxInhDict(projectThresholds); ok {
			for _, key := range projectThresholdsMap.Keys() {
				value, _ := projectThresholdsMap.Get(key)
				mergedThresholds.Set(key, value)
			}
		}
		merged.Set("thresholds", mergedThresholds)
	}
	for _, key := range projectRules.Keys() {
		if key == "auto_delegate" || key == "thresholds" {
			continue
		}
		value, _ := projectRules.Get(key)
		merged.Set(key, zpCtxInhDeepCopy(value))
	}
	return merged
}

// applyCustomInheritanceRules applies custom inheritance rules for specific task
// requirements.
func (s *ContextInheritanceService) applyCustomInheritanceRules(context, customRules *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	result := zpCtxInhDeepCopyMap(context)
	if result == nil {
		result = entities.NewOrderedMap[any]()
	}
	if customRules == nil {
		return result
	}
	for _, ruleType := range customRules.Keys() {
		ruleConfig, _ := customRules.Get(ruleType)
		switch ruleType {
		case "exclude_keys":
			result = s.processExcludeKeys(result, ruleConfig)
		case "force_values":
			result = s.processForceValues(result, ruleConfig)
		case "conditional_overrides":
			result = s.processConditionalOverrides(result, ruleConfig)
		case "merge_strategies":
			result = s.processMergeStrategies(result, ruleConfig)
		}
	}
	return result
}

// processExcludeKeys removes specified keys from the inherited context.
func (s *ContextInheritanceService) processExcludeKeys(context *entities.OrderedMap[any], excludeConfig any) *entities.OrderedMap[any] {
	result := zpCtxInhDeepCopyMap(context)
	if result == nil {
		result = entities.NewOrderedMap[any]()
	}
	excludeList, _ := zpCtxInhList(excludeConfig)
	for _, item := range excludeList {
		keyPath, ok := item.(string)
		if !ok {
			continue
		}
		pathParts := strings.Split(keyPath, ".")
		current := result
		broke := false
		for _, part := range pathParts[:len(pathParts)-1] {
			next, present := current.Get(part)
			nextMap, isDict := zpCtxInhDict(next)
			if present && isDict {
				current = nextMap
			} else {
				broke = true
				break
			}
		}
		if broke {
			continue
		}
		finalKey := pathParts[len(pathParts)-1]
		if current.Has(finalKey) {
			current.Delete(finalKey)
		}
	}
	return result
}

// processForceValues forces specific values regardless of inheritance.
func (s *ContextInheritanceService) processForceValues(context *entities.OrderedMap[any], forceConfig any) *entities.OrderedMap[any] {
	config, _ := zpCtxInhDict(forceConfig)
	if config == nil {
		config = entities.NewOrderedMap[any]()
	}
	return s.applyOverrides(context, config)
}

// processConditionalOverrides applies overrides based on conditions.
func (s *ContextInheritanceService) processConditionalOverrides(context *entities.OrderedMap[any], conditionalConfig any) *entities.OrderedMap[any] {
	result := zpCtxInhDeepCopyMap(context)
	if result == nil {
		result = entities.NewOrderedMap[any]()
	}
	conditions, _ := zpCtxInhList(conditionalConfig)
	for _, item := range conditions {
		conditionEntry, ok := zpCtxInhDict(item)
		if !ok {
			continue
		}
		conditionAny, _ := conditionEntry.Get("condition")
		condition, _ := zpCtxInhDict(conditionAny)
		if condition == nil {
			condition = entities.NewOrderedMap[any]()
		}
		if s.evaluateCondition(result, condition) {
			overridesAny, _ := conditionEntry.Get("overrides")
			overrides, _ := zpCtxInhDict(overridesAny)
			if overrides == nil {
				overrides = entities.NewOrderedMap[any]()
			}
			result = s.applyOverrides(result, overrides)
		}
	}
	return result
}

// processMergeStrategies applies custom merge strategies for specific keys. The Python
// implementation returns the context as-is for now.
func (s *ContextInheritanceService) processMergeStrategies(context *entities.OrderedMap[any], strategyConfig any) *entities.OrderedMap[any] {
	return context
}

// evaluateCondition evaluates a condition against the current context.
func (s *ContextInheritanceService) evaluateCondition(context, condition *entities.OrderedMap[any]) bool {
	conditionTypeAny, _ := condition.Get("type")
	conditionType, _ := conditionTypeAny.(string)

	switch conditionType {
	case "key_exists":
		keyAny, _ := condition.Get("key")
		keyPath, _ := keyAny.(string)
		return s.keyExists(context, keyPath)
	case "key_equals":
		keyAny, _ := condition.Get("key")
		keyPath, _ := keyAny.(string)
		expectedValue, _ := condition.Get("value")
		actualValue, ok := zpCtxInhGetNested(context, keyPath)
		if !ok {
			actualValue = nil
		}
		return value_objects.PyEqual(actualValue, expectedValue)
	case "key_contains":
		keyAny, _ := condition.Get("key")
		keyPath, _ := keyAny.(string)
		searchValue, _ := condition.Get("value")
		actualValue, ok := zpCtxInhGetNested(context, keyPath)
		if !ok || !value_objects.PyTruthy(actualValue) {
			return false
		}
		needle, ok := searchValue.(string)
		if !ok {
			return false
		}
		return strings.Contains(value_objects.PyStr(actualValue), needle)
	}
	return false
}

// keyExists checks if a nested key exists in context.
func (s *ContextInheritanceService) keyExists(context *entities.OrderedMap[any], keyPath string) bool {
	_, ok := zpCtxInhGetNested(context, keyPath)
	return ok
}

// getNestedValue gets a value from a nested key path. A missing path yields nil.
func (s *ContextInheritanceService) getNestedValue(context *entities.OrderedMap[any], keyPath string) any {
	value, _ := zpCtxInhGetNested(context, keyPath)
	return value
}

// getTimestamp returns the current timestamp in ISO format with a Z suffix.
func (s *ContextInheritanceService) getTimestamp() string {
	return zpCtxInhTimestamp()
}

// ValidateInheritanceChain validates that inheritance was applied correctly.
func (s *ContextInheritanceService) ValidateInheritanceChain(contextLevel, contextID string, resolvedContext *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	metadata := entities.NewOrderedMap[any]()
	metadata.Set("context_level", contextLevel)
	metadata.Set("context_id", contextID)
	metadata.Set("validation_timestamp", s.getTimestamp())

	if resolvedContext == nil {
		return zpCtxInhValidationErrorResult(metadata, "NoneType")
	}

	result := entities.NewOrderedMap[any]()
	issues := []any{}
	warnings := []any{}
	result.Set("valid", true)
	result.Set("issues", issues)
	result.Set("warnings", warnings)
	result.Set("metadata", metadata)

	inheritanceMetadataAny, _ := resolvedContext.Get("inheritance_metadata")
	inheritanceMetadata, metadataIsDict := zpCtxInhDict(inheritanceMetadataAny)
	if !value_objects.PyTruthy(inheritanceMetadataAny) {
		issues = append(issues, "Missing inheritance metadata")
		result.Set("valid", false)
	} else if metadataIsDict {
		var expectedChain []any
		switch contextLevel {
		case "task":
			expectedChain = []any{"global", "project", "branch", "task"}
		case "branch":
			expectedChain = []any{"global", "project", "branch"}
		}
		if expectedChain != nil {
			actualChain, ok := inheritanceMetadata.Get("inheritance_chain")
			if !ok {
				actualChain = []any{}
			}
			if !zpCtxInhListsEqual(actualChain, expectedChain) {
				warnings = append(warnings, fmt.Sprintf(
					"Unexpected inheritance chain: %s, expected: %s",
					value_objects.PyStr(actualChain), value_objects.PyStr(expectedChain)))
			}
		}
	} else {
		// A truthy non-dict raises AttributeError in Python's try block.
		return zpCtxInhValidationErrorResult(metadata, zpCtxInhPyTypeName(inheritanceMetadataAny))
	}

	localOverridesAny, _ := resolvedContext.Get("local_overrides")
	localOverrides, _ := zpCtxInhDict(localOverridesAny)
	if value_objects.PyTruthy(localOverridesAny) && localOverrides != nil {
		for _, overridePath := range localOverrides.Keys() {
			if !s.keyExists(resolvedContext, overridePath) {
				issues = append(issues, "Override path not found in resolved context: "+overridePath)
				result.Set("valid", false)
			}
		}
	}

	result.Set("issues", issues)
	result.Set("warnings", warnings)
	return result
}

// ===============================================
// PACKAGE-LEVEL HELPERS (all prefixed zpCtxInh)
// ===============================================

// zpCtxInhDict reports whether v is a Python-dict-like value (a non-nil OrderedMap).
func zpCtxInhDict(v any) (*entities.OrderedMap[any], bool) {
	m, ok := v.(*entities.OrderedMap[any])
	if !ok || m == nil {
		return nil, false
	}
	return m, true
}

// zpCtxInhList normalizes a Python-list-like value (any slice or array) to []any.
func zpCtxInhList(v any) ([]any, bool) {
	if v == nil {
		return nil, false
	}
	if list, ok := v.([]any); ok {
		return list, true
	}
	rv := reflect.ValueOf(v)
	if rv.Kind() == reflect.Slice || rv.Kind() == reflect.Array {
		out := make([]any, rv.Len())
		for i := 0; i < rv.Len(); i++ {
			out[i] = rv.Index(i).Interface()
		}
		return out, true
	}
	return nil, false
}

// zpCtxInhDeepCopy mirrors copy.deepcopy for JSON-like values.
func zpCtxInhDeepCopy(v any) any {
	switch x := v.(type) {
	case nil:
		return nil
	case *entities.OrderedMap[any]:
		return zpCtxInhDeepCopyMap(x)
	}
	if list, ok := zpCtxInhList(v); ok {
		out := make([]any, len(list))
		for i, item := range list {
			out[i] = zpCtxInhDeepCopy(item)
		}
		return out
	}
	return v
}

// zpCtxInhDeepCopyMap deep-copies an OrderedMap (nil stays nil, like deepcopy(None)).
func zpCtxInhDeepCopyMap(m *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	if m == nil {
		return nil
	}
	out := entities.NewOrderedMap[any]()
	for _, key := range m.Keys() {
		value, _ := m.Get(key)
		out.Set(key, zpCtxInhDeepCopy(value))
	}
	return out
}

// zpCtxInhGetOr mirrors dict.get(key, default).
func zpCtxInhGetOr(m *entities.OrderedMap[any], key string, def any) any {
	if m != nil {
		if value, ok := m.Get(key); ok {
			return value
		}
	}
	return def
}

// zpCtxInhGetNested mirrors the lookup in _get_nested_value; ok is false where Python
// would raise KeyError/TypeError.
func zpCtxInhGetNested(context *entities.OrderedMap[any], keyPath string) (any, bool) {
	var current any = context
	for _, part := range strings.Split(keyPath, ".") {
		m, ok := zpCtxInhDict(current)
		if !ok {
			return nil, false
		}
		value, ok := m.Get(part)
		if !ok {
			return nil, false
		}
		current = value
	}
	return current, true
}

// zpCtxInhListsEqual mirrors Python list == (element-wise equality).
func zpCtxInhListsEqual(a, b any) bool {
	listA, okA := zpCtxInhList(a)
	listB, okB := zpCtxInhList(b)
	if !okA || !okB {
		return value_objects.PyEqual(a, b)
	}
	if len(listA) != len(listB) {
		return false
	}
	for i := range listA {
		if !value_objects.PyEqual(listA[i], listB[i]) {
			return false
		}
	}
	return true
}

// zpCtxInhVersion mirrors global_context.get("metadata", {}).get("version", 1).
func zpCtxInhVersion(m *entities.OrderedMap[any]) any {
	if m == nil {
		return 1
	}
	metadataAny, _ := m.Get("metadata")
	metadata, ok := zpCtxInhDict(metadataAny)
	if !ok {
		return 1
	}
	if version, ok := metadata.Get("version"); ok {
		return version
	}
	return 1
}

// zpCtxInhTimestamp mirrors datetime.now(UTC).isoformat().replace("+00:00", "Z").
func zpCtxInhTimestamp() string {
	return strings.ReplaceAll(value_objects.IsoFormat(time.Now().UTC()), "+00:00", "Z")
}

// zpCtxInhValidationErrorResult builds the dict returned by validate_inheritance_chain's
// except branch.
func zpCtxInhValidationErrorResult(metadata *entities.OrderedMap[any], typeName string) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	out.Set("valid", false)
	out.Set("issues", []any{fmt.Sprintf("Validation error: '%s' object has no attribute 'get'", typeName)})
	out.Set("warnings", []any{})
	out.Set("metadata", metadata)
	return out
}

// zpCtxInhPyTypeName approximates the type name Python prints in an AttributeError.
func zpCtxInhPyTypeName(v any) string {
	switch v.(type) {
	case nil:
		return "NoneType"
	case bool:
		return "bool"
	case int, int8, int16, int32, int64, uint, uint8, uint16, uint32, uint64:
		return "int"
	case float32, float64:
		return "float"
	case string:
		return "str"
	case []any:
		return "list"
	case *entities.OrderedMap[any]:
		return "dict"
	}
	return fmt.Sprintf("%T", v)
}
