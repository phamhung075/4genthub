package services

import (
	"fmt"
	"sort"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// RuleCompositionResult is CompositionResult specialised to the entity inheritance type.
type RuleCompositionResult = value_objects.CompositionResult[*entities.RuleInheritance]

// IRuleCompositionService is the interface of the rule composition domain service.
type IRuleCompositionService interface {
	ComposeRules(rules []*entities.RuleContent, outputFormat value_objects.RuleFormat, strategy string) *RuleCompositionResult
	ResolveConflicts(rules []*entities.RuleContent) map[string]any
	MergeSectionContent(content1, content2 string) string
}

type composeFunc func(rules []*entities.RuleContent, f value_objects.RuleFormat) (string, []string, []string, error)

// RuleCompositionService implements the rule composition business logic.
type RuleCompositionService struct {
	conflictStrategy value_objects.ConflictResolution
	strategies       map[string]composeFunc
}

// NewRuleCompositionService builds the service; Python's default strategy is MERGE.
func NewRuleCompositionService(conflict value_objects.ConflictResolution) *RuleCompositionService {
	s := &RuleCompositionService{conflictStrategy: conflict}
	s.strategies = map[string]composeFunc{
		"intelligent":    s.intelligentComposition,
		"sequential":     s.sequentialComposition,
		"priority_merge": s.priorityMergeComposition,
	}
	return s
}

func newRuleCompositionResult(composed string, sources []string, chain []*entities.RuleInheritance, resolved []string,
	metadata map[string]any, success bool, warnings []string) (*RuleCompositionResult, error) {
	r, err := value_objects.NewCompositionResult(composed, sources, chain, resolved, metadata, success)
	if err != nil {
		return nil, err
	}
	r.Warnings = warnings
	return r, nil
}

func rulePaths(rules []*entities.RuleContent) []string {
	paths := make([]string, len(rules))
	for i, r := range rules {
		paths[i] = r.RulePath()
	}
	return paths
}

// ComposeRules composes multiple rules into a single result. Any failure inside the
// strategy (including the "Successful composition must have content" validation of the
// result itself) yields an unsuccessful result carrying the message.
func (s *RuleCompositionService) ComposeRules(rules []*entities.RuleContent, outputFormat value_objects.RuleFormat, strategy string) *RuleCompositionResult {
	if len(rules) == 0 {
		r, _ := newRuleCompositionResult("", []string{}, []*entities.RuleInheritance{}, []string{}, map[string]any{}, false,
			[]string{"No rules provided for composition"})
		return r
	}
	sorted := sortRulesByPriority(rules)
	run, ok := s.strategies[strategy]
	if !ok {
		run = s.intelligentComposition
	}
	result, err := func() (*RuleCompositionResult, error) {
		composed, resolved, warnings, err := run(sorted, outputFormat)
		if err != nil {
			return nil, err
		}
		metadata := map[string]any{
			"strategy": strategy, "total_rules": len(rules), "conflicts_resolved": len(resolved),
			"output_format": outputFormat.String(), "timestamp": float64(time.Now().UnixNano()) / 1e9,
		}
		return newRuleCompositionResult(composed, rulePaths(sorted), s.buildInheritanceChain(sorted), resolved, metadata, true, warnings)
	}()
	if err != nil {
		r, _ := newRuleCompositionResult("", rulePaths(rules), []*entities.RuleInheritance{}, []string{},
			map[string]any{"error": err.Error()}, false, []string{"Composition failed: " + err.Error()})
		return r
	}
	return result
}

// ResolveConflicts detects and resolves conflicts between every pair of rules.
func (s *RuleCompositionService) ResolveConflicts(rules []*entities.RuleContent) map[string]any {
	conflicts, log := []map[string]any{}, []map[string]any{}
	for i, r1 := range rules {
		for _, r2 := range rules[i+1:] {
			for _, c := range detectRuleConflicts(r1, r2) {
				log = append(log, s.resolveSingleRuleConflict(c))
				conflicts = append(conflicts, c)
			}
		}
	}
	return map[string]any{"total_conflicts": len(conflicts), "conflicts": conflicts, "resolutions": log,
		"strategy_used": s.conflictStrategy.String()}
}

// MergeSectionContent merges the content of two sections, appending lines of the second
// that the first lacks.
func (s *RuleCompositionService) MergeSectionContent(content1, content2 string) string {
	if content1 == "" {
		return content2
	}
	if content2 == "" || content1 == content2 {
		return content1
	}
	lines1 := strings.Split(value_objects.PyStrip(content1), "\n")
	lines2 := strings.Split(value_objects.PyStrip(content2), "\n")
	merged := append([]string{}, lines1...)
	for _, line := range lines2 {
		found := false
		for _, l := range lines1 {
			if l == line {
				found = true
				break
			}
		}
		if !found {
			merged = append(merged, line)
		}
	}
	return strings.Join(merged, "\n")
}

// sortRulesByPriority orders by descending score (core 1000, workflow 500). RuleMetadata
// has no `priority`, so Python's metadata bonus never applies. The sort is stable.
func sortRulesByPriority(rules []*entities.RuleContent) []*entities.RuleContent {
	score := func(r *entities.RuleContent) int {
		switch r.RuleType() {
		case value_objects.RuleTypeCore:
			return 1000
		case value_objects.RuleTypeWorkflow:
			return 500
		}
		return 0
	}
	out := append([]*entities.RuleContent{}, rules...)
	sort.SliceStable(out, func(i, j int) bool { return score(out[i]) > score(out[j]) })
	return out
}

func (s *RuleCompositionService) mergeOrOverride(merged *entities.OrderedMap[string], name, content, path string) []string {
	existing, _ := merged.Get(name)
	if s.conflictStrategy == value_objects.ConflictResolutionOverride {
		merged.Set(name, content)
		return []string{fmt.Sprintf("Section '%s' overridden from %s", name, path)}
	}
	merged.Set(name, s.MergeSectionContent(existing, content))
	return []string{fmt.Sprintf("Section '%s' merged from %s", name, path)}
}

func (s *RuleCompositionService) intelligentComposition(rules []*entities.RuleContent, f value_objects.RuleFormat) (string, []string, []string, error) {
	sections, variables, metadata := entities.NewOrderedMap[string](), entities.NewOrderedMap[any](), entities.NewOrderedMap[any]()
	resolved, warnings := []string{}, []string{}
	for _, rule := range rules {
		for _, name := range rule.Sections.Keys() {
			content, _ := rule.Sections.Get(name)
			if sections.Has(name) {
				resolved = append(resolved, s.mergeOrOverride(sections, name, content, rule.RulePath())...)
			} else {
				sections.Set(name, content)
			}
		}
		for _, name := range rule.Variables.Keys() {
			value, _ := rule.Variables.Get(name)
			if existing, ok := variables.Get(name); ok {
				if !value_objects.PyEqual(existing, value) {
					warnings = append(warnings, fmt.Sprintf("Variable '%s' conflict in %s", name, rule.RulePath()))
					variables.Set(name, value)
					resolved = append(resolved, fmt.Sprintf("Variable '%s' resolved from %s", name, rule.RulePath()))
				}
			} else {
				variables.Set(name, value)
			}
		}
		for _, key := range rule.ParsedContent.Keys() {
			if key != "sections" && key != "variables" {
				v, _ := rule.ParsedContent.Get(key)
				metadata.Set(key, v)
			}
		}
	}
	composed, err := generateComposedContent(sections, variables, metadata, f)
	return composed, resolved, warnings, err
}

func (s *RuleCompositionService) sequentialComposition(rules []*entities.RuleContent, f value_objects.RuleFormat) (string, []string, []string, error) {
	var all []string
	for _, r := range rules {
		all = append(all, "# From "+r.RulePath(), r.RawContent, "")
	}
	return strings.Join(all, "\n"), []string{}, []string{}, nil
}

func (s *RuleCompositionService) priorityMergeComposition(rules []*entities.RuleContent, f value_objects.RuleFormat) (string, []string, []string, error) {
	base := rules[0]
	sections, variables := base.Sections.Copy(), base.Variables.Copy()
	resolved := []string{}
	for _, rule := range rules[1:] {
		for _, name := range rule.Sections.Keys() {
			if !sections.Has(name) {
				content, _ := rule.Sections.Get(name)
				sections.Set(name, content)
				resolved = append(resolved, fmt.Sprintf("Added section '%s' from %s", name, rule.RulePath()))
			}
		}
		for _, name := range rule.Variables.Keys() {
			if !variables.Has(name) {
				v, _ := rule.Variables.Get(name)
				variables.Set(name, v)
				resolved = append(resolved, fmt.Sprintf("Added variable '%s' from %s", name, rule.RulePath()))
			}
		}
	}
	composed, err := generateComposedContent(sections, variables, base.ParsedContent, f)
	return composed, resolved, []string{}, err
}

func detectRuleConflicts(r1, r2 *entities.RuleContent) []map[string]any {
	conflicts := []map[string]any{}
	for _, name := range r1.Sections.Keys() {
		if c2, ok := r2.Sections.Get(name); ok {
			if c1, _ := r1.Sections.Get(name); c1 != c2 {
				conflicts = append(conflicts, map[string]any{"type": "section", "name": name, "rule1_path": r1.RulePath(),
					"rule2_path": r2.RulePath(), "rule1_content": c1, "rule2_content": c2})
			}
		}
	}
	for _, name := range r1.Variables.Keys() {
		if v2, ok := r2.Variables.Get(name); ok {
			if v1, _ := r1.Variables.Get(name); !value_objects.PyEqual(v1, v2) {
				conflicts = append(conflicts, map[string]any{"type": "variable", "name": name, "rule1_path": r1.RulePath(),
					"rule2_path": r2.RulePath(), "rule1_value": v1, "rule2_value": v2})
			}
		}
	}
	return conflicts
}

func (s *RuleCompositionService) resolveSingleRuleConflict(c map[string]any) map[string]any {
	res := map[string]any{"conflict": c, "strategy": s.conflictStrategy.String(), "resolved_value": nil, "resolution_reason": ""}
	isSection := c["type"] == "section"
	switch s.conflictStrategy {
	case value_objects.ConflictResolutionMerge:
		if isSection {
			res["resolved_value"] = s.MergeSectionContent(c["rule1_content"].(string), c["rule2_content"].(string))
			res["resolution_reason"] = "Merged section content"
		} else if c["type"] == "variable" {
			res["resolved_value"] = c["rule2_value"]
			res["resolution_reason"] = "Used latest variable value"
		}
	case value_objects.ConflictResolutionOverride:
		if isSection {
			res["resolved_value"] = c["rule2_content"]
		} else {
			res["resolved_value"] = c["rule2_value"]
		}
		res["resolution_reason"] = "Override with latest value"
	}
	return res
}

func (s *RuleCompositionService) buildInheritanceChain(rules []*entities.RuleContent) []*entities.RuleInheritance {
	chain := []*entities.RuleInheritance{}
	for i, rule := range rules[:len(rules)-1] {
		inh := entities.NewRuleInheritance(rule.RulePath(), rules[i+1].RulePath(), value_objects.InheritanceTypeContent)
		inh.InheritedSections = rule.Sections.Keys()
		for _, k := range rule.Variables.Keys() {
			v, _ := rule.Variables.Get(k)
			inh.MergedVariables[k] = v
		}
		inh.InheritanceDepth = i + 1
		chain = append(chain, inh)
	}
	return chain
}

func generateComposedContent(sections *entities.OrderedMap[string], variables, metadata *entities.OrderedMap[any], f value_objects.RuleFormat) (string, error) {
	switch f {
	case value_objects.RuleFormatMdc:
		return generateMdcContent(sections, variables, metadata), nil
	case value_objects.RuleFormatJson:
		return value_objects.PyJSONDumps(composedJSON{metadata, variables, sections}, 2)
	}
	return generateMarkdownContent(sections, variables, metadata), nil
}

func generateMdcContent(sections *entities.OrderedMap[string], variables, metadata *entities.OrderedMap[any]) string {
	var parts []string
	if metadata.Len() > 0 {
		parts = append(parts, "---")
		for _, k := range metadata.Keys() {
			if k != "sections" && k != "variables" {
				v, _ := metadata.Get(k)
				parts = append(parts, k+": "+value_objects.PyStr(v))
			}
		}
		parts = append(parts, "---", "")
	}
	if variables.Len() > 0 {
		parts = append(parts, "## Variables")
		for _, k := range variables.Keys() {
			v, _ := variables.Get(k)
			parts = append(parts, "- "+k+": "+value_objects.PyStr(v))
		}
		parts = append(parts, "")
	}
	return strings.Join(appendSections(parts, sections), "\n")
}

func generateMarkdownContent(sections *entities.OrderedMap[string], variables, metadata *entities.OrderedMap[any]) string {
	var title any = "Composed Rule"
	if t, ok := metadata.Get("title"); ok {
		title = t
	}
	parts := []string{"# " + value_objects.PyStr(title), ""}
	if variables.Len() > 0 {
		parts = append(parts, "## Configuration")
		for _, k := range variables.Keys() {
			v, _ := variables.Get(k)
			parts = append(parts, "- **"+k+"**: "+value_objects.PyStr(v))
		}
		parts = append(parts, "")
	}
	return strings.Join(appendSections(parts, sections), "\n")
}

func appendSections(parts []string, sections *entities.OrderedMap[string]) []string {
	for _, name := range sections.Keys() {
		content, _ := sections.Get(name)
		parts = append(parts, "## "+name, content, "")
	}
	return parts
}

// composedJSON is the {"metadata", "variables", "sections"} document, in that key order.
type composedJSON struct {
	metadata, variables *entities.OrderedMap[any]
	sections            *entities.OrderedMap[string]
}

func (c composedJSON) KeysAny() []string { return []string{"metadata", "variables", "sections"} }
func (c composedJSON) GetAny(k string) any {
	switch k {
	case "metadata":
		return c.metadata
	case "variables":
		return c.variables
	}
	return c.sections
}
