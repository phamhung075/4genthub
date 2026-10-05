package services

import (
	"sort"
	"strings"
	"time"
	"unicode"
	"unicode/utf8"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// TemplateDomainService holds template business rules (stateless).
type TemplateDomainService struct{}

// noneAttrError is the AttributeError text Python raises when an enum attribute
// that is None is dereferenced with `.value`.
var noneAttrError = value_objects.TypeErrorf("'NoneType' object has no attribute 'value'")

func isActiveTemplate(t *entities.Template) bool {
	return t.IsActive != nil && *t.IsActive && t.Status != nil && *t.Status == value_objects.TemplateStatusActive
}

func hasPriority(t *entities.Template, ps ...value_objects.TemplatePriority) bool {
	if t.Priority == nil {
		return false
	}
	for _, p := range ps {
		if *t.Priority == p {
			return true
		}
	}
	return false
}

// isAlnum is Python's str.isalnum (False for the empty string).
func isAlnum(s string) bool {
	if s == "" {
		return false
	}
	for _, r := range s {
		if !unicode.IsLetter(r) && !unicode.IsNumber(r) {
			return false
		}
	}
	return true
}

// ValidateTemplate returns every business-rule violation (empty when valid).
func (s *TemplateDomainService) ValidateTemplate(t *entities.Template) []string {
	errs := []string{}
	if value_objects.PyStrip(t.Name) == "" {
		errs = append(errs, "Template name cannot be empty")
	}
	if value_objects.PyStrip(t.Content) == "" {
		errs = append(errs, "Template content cannot be empty")
	}
	if value_objects.PyStrip(t.Description) == "" {
		errs = append(errs, "Template description cannot be empty")
	}
	if utf8.RuneCountInString(t.Content) > 1000000 {
		errs = append(errs, "Template content exceeds maximum size limit")
	}
	if utf8.RuneCountInString(t.Name) > 255 {
		errs = append(errs, "Template name exceeds maximum length")
	}
	if utf8.RuneCountInString(t.Description) > 1000 {
		errs = append(errs, "Template description exceeds maximum length")
	}
	for _, v := range t.Variables {
		if value_objects.PyStrip(v) == "" {
			errs = append(errs, "Variable name cannot be empty")
		}
		if !isAlnum(strings.ReplaceAll(strings.ReplaceAll(v, "_", ""), "-", "")) {
			errs = append(errs, "Variable '"+v+"' contains invalid characters")
		}
	}
	for _, p := range t.FilePatterns {
		if value_objects.PyStrip(p) == "" {
			errs = append(errs, "File pattern cannot be empty")
		}
	}
	if len(t.CompatibleAgents) == 0 {
		errs = append(errs, "Template must be compatible with at least one agent")
	}
	return errs
}

// CanRenderTemplate checks activity, agent compatibility and (when given) file patterns.
func (s *TemplateDomainService) CanRenderTemplate(t *entities.Template, agentName string, filePatterns []string) bool {
	if !isActiveTemplate(t) {
		return false
	}
	if !t.IsCompatibleWithAgent(agentName) {
		return false
	}
	if len(filePatterns) > 0 && !t.MatchesFilePatterns(filePatterns) {
		return false
	}
	return true
}

func ctxString(m map[string]any, key string) string {
	v, _ := m[key].(string)
	return v
}

// CalculateTemplateScore scores a template for a task context. usageStats may be nil.
// A nil TemplateType/Category is dereferenced by Python (AttributeError) only when the
// context names a task type/category, and the same error is returned here. Non-string
// task_type/category values are treated as absent (Python would raise TypeError).
func (s *TemplateDomainService) CalculateTemplateScore(t *entities.Template, taskContext map[string]any,
	agentName string, filePatterns []string, usageStats map[string]any) (float64, error) {
	score := 0.0
	if isActiveTemplate(t) {
		score += 10.0
	}
	switch {
	case hasPriority(t, value_objects.TemplatePriorityCritical):
		score += 20.0
	case hasPriority(t, value_objects.TemplatePriorityHigh):
		score += 15.0
	case hasPriority(t, value_objects.TemplatePriorityMedium):
		score += 5.0
	}
	if t.IsCompatibleWithAgent(agentName) {
		if indexOfStr(t.CompatibleAgents, "*") >= 0 {
			score += 20.0
		} else {
			score += 30.0
		}
	}
	if tt := ctxString(taskContext, "task_type"); tt != "" {
		if t.TemplateType == nil {
			return 0, noneAttrError
		}
		if string(*t.TemplateType) == tt {
			score += 40.0
		} else if strings.Contains(string(*t.TemplateType), tt) {
			score += 20.0
		}
	}
	if cat := ctxString(taskContext, "category"); cat != "" {
		if t.Category == nil {
			return 0, noneAttrError
		}
		if string(*t.Category) == cat {
			score += 30.0
		} else if strings.Contains(string(*t.Category), cat) {
			score += 15.0
		}
	}
	if len(filePatterns) > 0 && t.MatchesFilePatterns(filePatterns) {
		score += 25.0
	}
	if len(usageStats) > 0 {
		count, _ := numOr(usageStats, "usage_count", 0)
		rate, _ := numOr(usageStats, "success_rate", 0)
		avg, _ := numOr(usageStats, "avg_generation_time", 0)
		switch {
		case count > 100:
			score += 15.0
		case count > 50:
			score += 10.0
		case count > 10:
			score += 5.0
		}
		score += rate * 10.0
		if avg < 100 {
			score += 10.0
		} else if avg < 500 {
			score += 5.0
		}
	}
	if len(t.Metadata) > 0 {
		for _, k := range sortedKeys(taskContext) {
			if mv, ok := t.Metadata[k]; ok && value_objects.PyEqual(mv, taskContext[k]) {
				score += 5.0
			}
		}
	}
	if score < 0.0 {
		return 0.0, nil
	}
	return score, nil
}

func numOr(m map[string]any, key string, def float64) (float64, bool) {
	if v, ok := m[key]; ok {
		return value_objects.PyFloat(v)
	}
	return def, true
}

func sortedKeys[V any](m map[string]V) []string {
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys
}

func indexOfStr(l []string, v string) int {
	for i, e := range l {
		if e == v {
			return i
		}
	}
	return -1
}

// GetSuggestionReason builds the human-readable reason joined with "; ".
func (s *TemplateDomainService) GetSuggestionReason(t *entities.Template, taskContext map[string]any, score float64) (string, error) {
	reasons := []string{}
	if hasPriority(t, value_objects.TemplatePriorityCritical) {
		reasons = append(reasons, "Critical priority template")
	} else if hasPriority(t, value_objects.TemplatePriorityHigh) {
		reasons = append(reasons, "High priority template")
	}
	if tt := ctxString(taskContext, "task_type"); tt != "" {
		if t.TemplateType == nil {
			return "", noneAttrError
		}
		if string(*t.TemplateType) == tt {
			reasons = append(reasons, "Exact match for "+tt+" tasks")
		} else if strings.Contains(string(*t.TemplateType), tt) {
			reasons = append(reasons, "Good match for "+tt+" tasks")
		}
	}
	if cat := ctxString(taskContext, "category"); cat != "" {
		if t.Category == nil {
			return "", noneAttrError
		}
		if string(*t.Category) == cat {
			reasons = append(reasons, "Perfect fit for "+cat+" category")
		} else if strings.Contains(string(*t.Category), cat) {
			reasons = append(reasons, "Suitable for "+cat+" category")
		}
	}
	switch {
	case score > 80:
		reasons = append(reasons, "Highly recommended based on usage patterns")
	case score > 60:
		reasons = append(reasons, "Recommended based on context match")
	case score > 40:
		reasons = append(reasons, "Good option for this type of task")
	}
	if len(reasons) == 0 {
		reasons = append(reasons, "Available template option")
	}
	return strings.Join(reasons, "; "), nil
}

func cacheStrategy(r entities.TemplateRenderRequest) string {
	if r.CacheStrategy == "" {
		return "default"
	}
	return r.CacheStrategy
}

// ValidateRenderRequest validates a render request. Python's `not request.template_id`
// is never true (a TemplateId object is always truthy), so it is not reported.
func (s *TemplateDomainService) ValidateRenderRequest(r entities.TemplateRenderRequest) []string {
	errs := []string{}
	if len(r.Variables) == 0 {
		errs = append(errs, "Variables are required")
	}
	switch cacheStrategy(r) {
	case "default", "aggressive", "minimal", "none", "custom":
	default:
		errs = append(errs, "Invalid cache strategy")
	}
	return errs
}

// MergeTemplateVariables merges template defaults (nil), task context values for
// template variables, then request variables (highest precedence). Keys from maps
// are added in sorted order because Go maps carry no insertion order.
func (s *TemplateDomainService) MergeTemplateVariables(templateVariables []string, requestVariables, taskContext map[string]any) *entities.OrderedMap[any] {
	merged := entities.NewOrderedMap[any]()
	for _, v := range templateVariables {
		merged.Set(v, nil)
	}
	for _, k := range sortedKeys(taskContext) {
		if indexOfStr(templateVariables, k) >= 0 {
			merged.Set(k, taskContext[k])
		}
	}
	for _, k := range sortedKeys(requestVariables) {
		merged.Set(k, requestVariables[k])
	}
	return merged
}

// CreateTemplateUsage builds a usage record stamped with the current UTC time.
func (s *TemplateDomainService) CreateTemplateUsage(templateID value_objects.TemplateId, taskID, projectID, agentName *string,
	variablesUsed map[string]any, outputPath *string, generationTimeMs int, cacheHit bool) entities.TemplateUsage {
	if len(variablesUsed) == 0 {
		variablesUsed = map[string]any{}
	}
	return entities.TemplateUsage{TemplateID: templateID, TaskID: taskID, ProjectID: projectID, AgentName: agentName,
		VariablesUsed: variablesUsed, OutputPath: outputPath, GenerationTimeMs: generationTimeMs, CacheHit: cacheHit,
		UsedAt: time.Now().UTC().Truncate(time.Microsecond)}
}

// ShouldCacheResult applies the cache strategy rules.
func (s *TemplateDomainService) ShouldCacheResult(t *entities.Template, r entities.TemplateRenderRequest) bool {
	if r.ForceRegenerate {
		return false
	}
	switch cacheStrategy(r) {
	case "none":
		return false
	case "aggressive":
		return true
	case "minimal":
		return hasPriority(t, value_objects.TemplatePriorityHigh, value_objects.TemplatePriorityCritical)
	}
	return true
}

// GetCacheTTL is the cache lifetime in seconds.
func (s *TemplateDomainService) GetCacheTTL(t *entities.Template, r entities.TemplateRenderRequest) int {
	switch cacheStrategy(r) {
	case "aggressive":
		return 3600 * 24
	case "minimal":
		return 300
	}
	switch {
	case hasPriority(t, value_objects.TemplatePriorityCritical):
		return 3600 * 6
	case hasPriority(t, value_objects.TemplatePriorityHigh):
		return 3600 * 2
	}
	return 3600
}
