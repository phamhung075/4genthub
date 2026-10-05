// Package services ports ai_task_planning/domain/services.
package services

import (
	"strings"
	"unicode/utf8"

	"agenthub/fastmcp/ai_task_planning/domain/entities"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// RequirementPattern is a common pattern found in requirements.
type RequirementPattern string

const (
	PatternCrudOperations           RequirementPattern = "crud_operations"
	PatternUserAuthentication       RequirementPattern = "user_authentication"
	PatternAPIIntegration           RequirementPattern = "api_integration"
	PatternUIComponent              RequirementPattern = "ui_component"
	PatternDatabaseSchema           RequirementPattern = "database_schema"
	PatternTestingRequirement       RequirementPattern = "testing_requirement"
	PatternSecurityRequirement      RequirementPattern = "security_requirement"
	PatternPerformanceRequirement   RequirementPattern = "performance_requirement"
	PatternDocumentationRequirement RequirementPattern = "documentation_requirement"
	PatternBugFix                   RequirementPattern = "bug_fix"
	PatternRefactoring              RequirementPattern = "refactoring"
	PatternDeployment               RequirementPattern = "deployment"
	PatternMonitoring               RequirementPattern = "monitoring"
)

// allPatterns lists the members in declaration order.
var allPatterns = []RequirementPattern{PatternCrudOperations, PatternUserAuthentication, PatternAPIIntegration,
	PatternUIComponent, PatternDatabaseSchema, PatternTestingRequirement, PatternSecurityRequirement,
	PatternPerformanceRequirement, PatternDocumentationRequirement, PatternBugFix, PatternRefactoring,
	PatternDeployment, PatternMonitoring}

// AnalyzedRequirement is the result of requirement analysis.
type AnalyzedRequirement struct {
	OriginalRequirement     *entities.RequirementItem
	DetectedPatterns        []RequirementPattern
	ComplexityIndicators    *tmentities.OrderedMap[any]
	SuggestedAgents         []string
	EstimatedEffortHours    float64
	RiskFactors             []string
	Dependencies            []string
	TechnicalConsiderations []string
}

type patternKeywords struct {
	pattern  RequirementPattern
	keywords []string
}

var patternKeywordTable = []patternKeywords{
	{PatternCrudOperations, []string{"create", "read", "update", "delete", "crud", "manage", "add", "edit", "remove"}},
	{PatternUserAuthentication, []string{"login", "logout", "authenticate", "authorization", "auth", "jwt", "session", "password", "user", "signin", "signup", "register"}},
	{PatternAPIIntegration, []string{"api", "endpoint", "rest", "graphql", "integration", "third-party", "external", "webhook", "http", "service"}},
	{PatternUIComponent, []string{"ui", "component", "interface", "frontend", "react", "vue", "angular", "button", "form", "modal", "dashboard", "page", "view", "screen"}},
	{PatternDatabaseSchema, []string{"database", "schema", "table", "model", "migration", "sql", "postgres", "mysql", "mongodb", "relation", "foreign key", "index"}},
	{PatternTestingRequirement, []string{"test", "testing", "unit test", "integration test", "e2e", "spec", "coverage", "assertion", "mock", "stub"}},
	{PatternSecurityRequirement, []string{"security", "secure", "encryption", "https", "ssl", "vulnerability", "audit", "compliance", "gdpr", "owasp"}},
	{PatternPerformanceRequirement, []string{"performance", "speed", "optimization", "cache", "latency", "throughput", "scalability", "load", "benchmark"}},
	{PatternDocumentationRequirement, []string{"document", "documentation", "readme", "guide", "manual", "wiki", "help", "tutorial", "api docs"}},
	{PatternBugFix, []string{"bug", "fix", "error", "issue", "problem", "defect", "broken", "crash", "exception", "failure"}},
	{PatternRefactoring, []string{"refactor", "cleanup", "restructure", "reorganize", "improve", "optimize", "modernize", "technical debt"}},
	{PatternDeployment, []string{"deploy", "deployment", "production", "staging", "ci/cd", "pipeline", "docker", "kubernetes", "infrastructure"}},
	{PatternMonitoring, []string{"monitor", "monitoring", "logging", "metrics", "alerting", "observability", "analytics", "tracking"}},
}

var agentSpecializations = map[RequirementPattern][]string{
	PatternCrudOperations:           {"coding-agent"},
	PatternUserAuthentication:       {"coding-agent", "security-auditor-agent"},
	PatternAPIIntegration:           {"coding-agent", "system-architect-agent"},
	PatternUIComponent:              {"shadcn-ui-expert-agent", "design-system-agent"},
	PatternDatabaseSchema:           {"coding-agent", "system-architect-agent"},
	PatternTestingRequirement:       {"test-orchestrator-agent"},
	PatternSecurityRequirement:      {"security-auditor-agent"},
	PatternPerformanceRequirement:   {"performance-load-tester-agent", "efficiency-optimization-agent"},
	PatternDocumentationRequirement: {"documentation-agent"},
	PatternBugFix:                   {"debugger-agent", "root-cause-analysis-agent"},
	PatternRefactoring:              {"code-reviewer-agent", "system-architect-agent"},
	PatternDeployment:               {"devops-agent"},
	PatternMonitoring:               {"health-monitor-agent", "analytics-setup-agent"},
}

var complexityWeights = map[RequirementPattern]float64{
	PatternCrudOperations: 2.0, PatternUserAuthentication: 4.0, PatternAPIIntegration: 3.0, PatternUIComponent: 2.5,
	PatternDatabaseSchema: 3.5, PatternTestingRequirement: 1.5, PatternSecurityRequirement: 4.5,
	PatternPerformanceRequirement: 4.0, PatternDocumentationRequirement: 1.0, PatternBugFix: 3.0,
	PatternRefactoring: 3.5, PatternDeployment: 3.0, PatternMonitoring: 2.5,
}

// RequirementAnalyzer analyzes requirements with keyword patterns and heuristics.
type RequirementAnalyzer struct{}

func NewRequirementAnalyzer() *RequirementAnalyzer { return &RequirementAnalyzer{} }

func containsAny(text string, keywords []string) bool {
	for _, k := range keywords {
		if strings.Contains(text, k) {
			return true
		}
	}
	return false
}

func hasPattern(ps []RequirementPattern, p RequirementPattern) bool {
	for _, x := range ps {
		if x == p {
			return true
		}
	}
	return false
}

// weightSum is sum(weights) where an empty sum is the int 0.
func weightSum(patterns []RequirementPattern) float64 {
	ws := make([]float64, len(patterns))
	for i, p := range patterns {
		ws[i] = complexityWeights[p]
	}
	return tmvo.PySum(ws)
}

// AnalyzeRequirement extracts patterns, complexity, agents, effort, risks and dependencies.
func (a *RequirementAnalyzer) AnalyzeRequirement(r *entities.RequirementItem) *AnalyzedRequirement {
	text := tmvo.PyLower(r.Description + " " + strings.Join(r.AcceptanceCriteria, " ") + " " + strings.Join(r.Constraints, " "))
	patterns := a.detectPatterns(text)
	indicators := a.analyzeComplexity(r, patterns, text)
	return &AnalyzedRequirement{
		OriginalRequirement:     r,
		DetectedPatterns:        patterns,
		ComplexityIndicators:    indicators,
		SuggestedAgents:         a.suggestAgents(patterns),
		EstimatedEffortHours:    a.estimateEffort(patterns, indicators, len(r.AcceptanceCriteria)),
		RiskFactors:             a.identifyRisks(patterns, text),
		Dependencies:            a.inferDependencies(patterns),
		TechnicalConsiderations: a.technicalConsiderations(patterns),
	}
}

// AnalyzeRequirementsBatch analyzes each requirement, then appends cross-requirement
// dependencies.
func (a *RequirementAnalyzer) AnalyzeRequirementsBatch(reqs []*entities.RequirementItem) []*AnalyzedRequirement {
	analyzed := make([]*AnalyzedRequirement, len(reqs))
	for i, r := range reqs {
		analyzed[i] = a.AnalyzeRequirement(r)
	}
	for i, an := range analyzed {
		for j, other := range analyzed {
			if i != j {
				an.Dependencies = append(an.Dependencies, detectCrossDependencies(an, other)...)
			}
		}
	}
	return analyzed
}

func (a *RequirementAnalyzer) detectPatterns(text string) []RequirementPattern {
	detected := []RequirementPattern{}
	for _, pk := range patternKeywordTable {
		if containsAny(text, pk.keywords) {
			detected = append(detected, pk.pattern)
		}
	}
	return detected
}

func (a *RequirementAnalyzer) analyzeComplexity(r *entities.RequirementItem, patterns []RequirementPattern, text string) *tmentities.OrderedMap[any] {
	ind := tmentities.NewOrderedMap[any]()
	if len(patterns) == 0 {
		ind.Set("pattern_complexity", 0) // sum() of nothing is the int 0
	} else {
		ind.Set("pattern_complexity", weightSum(patterns))
	}
	ind.Set("description_length", utf8.RuneCountInString(r.Description))
	ind.Set("criteria_count", len(r.AcceptanceCriteria))
	ind.Set("constraints_count", len(r.Constraints))
	switch {
	case containsAny(text, []string{"complex", "advanced", "sophisticated", "enterprise", "scalable", "distributed"}):
		ind.Set("keyword_complexity", "high")
	case containsAny(text, []string{"integrate", "configure", "implement", "design", "develop"}):
		ind.Set("keyword_complexity", "medium")
	case containsAny(text, []string{"simple", "basic", "straightforward", "minor", "quick"}):
		ind.Set("keyword_complexity", "low")
	default:
		ind.Set("keyword_complexity", "medium")
	}
	return ind
}

// suggestAgents returns the de-duplicated agents (Python builds a set, so its order is
// unspecified; first-seen order here).
func (a *RequirementAnalyzer) suggestAgents(patterns []RequirementPattern) []string {
	var set tmentities.StringSet
	for _, p := range patterns {
		for _, ag := range agentSpecializations[p] {
			set.Add(ag)
		}
	}
	if set.Len() == 0 {
		set.Add("coding-agent")
	}
	return set.Items()
}

func (a *RequirementAnalyzer) estimateEffort(patterns []RequirementPattern, ind *tmentities.OrderedMap[any], criteriaCount int) float64 {
	base := 0.0
	if len(patterns) > 0 {
		base = weightSum(patterns)
	}
	mult := 1.0
	switch kc, _ := ind.Get("keyword_complexity"); kc {
	case "high":
		mult = 1.5
	case "low":
		mult = 0.7
	}
	crit := 1.0 + float64(float64(criteriaCount)*0.1)
	return float64(float64(base*mult) * crit)
}

var riskTable = map[RequirementPattern]string{
	PatternSecurityRequirement:    "Security implementation requires careful review to avoid vulnerabilities",
	PatternUserAuthentication:     "Authentication system must be thoroughly tested to prevent security breaches",
	PatternAPIIntegration:         "Third-party API integration may have rate limits or availability issues",
	PatternDatabaseSchema:         "Database changes require careful migration planning to avoid data loss",
	PatternPerformanceRequirement: "Performance targets may be difficult to achieve without architecture changes",
}

func (a *RequirementAnalyzer) identifyRisks(patterns []RequirementPattern, text string) []string {
	risks := []string{}
	for _, p := range patterns {
		if r, ok := riskTable[p]; ok {
			risks = append(risks, r)
		}
	}
	if strings.Contains(text, "external") || strings.Contains(text, "third-party") {
		risks = append(risks, "External dependency may introduce reliability risks")
	}
	if strings.Contains(text, "migration") {
		risks = append(risks, "Data migration requires backup and rollback planning")
	}
	if strings.Contains(text, "real-time") || strings.Contains(text, "live") {
		risks = append(risks, "Real-time requirements may need specialized infrastructure")
	}
	return risks
}

func (a *RequirementAnalyzer) inferDependencies(patterns []RequirementPattern) []string {
	deps := []string{}
	for _, p := range patterns {
		switch p {
		case PatternUIComponent:
			deps = append(deps, string(PatternAPIIntegration), string(PatternDatabaseSchema))
		case PatternAPIIntegration:
			deps = append(deps, string(PatternDatabaseSchema))
		case PatternTestingRequirement, PatternDeployment:
			deps = append(deps, "depends_on_implementation")
		}
	}
	return deps
}

func detectCrossDependencies(a1, a2 *AnalyzedRequirement) []string {
	deps := []string{}
	if hasPattern(a1.DetectedPatterns, PatternTestingRequirement) && !hasPattern(a2.DetectedPatterns, PatternTestingRequirement) {
		deps = append(deps, a2.OriginalRequirement.ID)
	}
	if hasPattern(a1.DetectedPatterns, PatternUIComponent) && hasPattern(a2.DetectedPatterns, PatternAPIIntegration) {
		deps = append(deps, a2.OriginalRequirement.ID)
	}
	return deps
}

var techTable = map[RequirementPattern][]string{
	PatternSecurityRequirement:    {"Follow OWASP security guidelines", "Implement proper input validation", "Use secure encryption for sensitive data"},
	PatternPerformanceRequirement: {"Consider caching strategies", "Database query optimization may be needed", "Load testing required to validate performance"},
	PatternAPIIntegration:         {"API documentation review required", "Error handling for network failures", "Rate limiting considerations"},
	PatternDatabaseSchema:         {"Database migration strategy needed", "Consider indexing for query performance", "Backup strategy before schema changes"},
}

func (a *RequirementAnalyzer) technicalConsiderations(patterns []RequirementPattern) []string {
	out := []string{}
	for _, p := range patterns {
		out = append(out, techTable[p]...)
	}
	return out
}

// GeneratePlanningInsights summarises a batch. `agent_recommendations` and
// `risk_summary` come from Python sets (unspecified order); first-seen order here.
// `total_estimated_hours` is the int 0 for an empty batch (sum() of nothing).
func (a *RequirementAnalyzer) GeneratePlanningInsights(analyzed []*AnalyzedRequirement) *tmentities.OrderedMap[any] {
	ins := tmentities.NewOrderedMap[any]()
	ins.Set("total_requirements", len(analyzed))
	var total any = 0
	if len(analyzed) > 0 {
		hs := make([]float64, len(analyzed))
		for i, ar := range analyzed {
			hs[i] = ar.EstimatedEffortHours
		}
		total = tmvo.PySum(hs)
	}
	ins.Set("total_estimated_hours", total)

	var allPats []RequirementPattern
	var allAgents, allRisks []string
	for _, ar := range analyzed {
		allPats = append(allPats, ar.DetectedPatterns...)
		allAgents = append(allAgents, ar.SuggestedAgents...)
		allRisks = append(allRisks, ar.RiskFactors...)
	}
	dist := tmentities.NewOrderedMap[any]()
	for _, p := range allPatterns {
		n := 0
		for _, x := range allPats {
			if x == p {
				n++
			}
		}
		if n > 0 {
			dist.Set(string(p), n)
		}
	}
	ins.Set("pattern_distribution", dist)

	rec := tmentities.NewOrderedMap[any]()
	var agentSet tmentities.StringSet
	for _, ag := range allAgents {
		agentSet.Add(ag)
	}
	for _, ag := range agentSet.Items() {
		n := 0
		for _, x := range allAgents {
			if x == ag {
				n++
			}
		}
		rec.Set(ag, n)
	}
	ins.Set("agent_recommendations", rec)

	var riskSet tmentities.StringSet
	for _, r := range allRisks {
		riskSet.Add(r)
	}
	ins.Set("risk_summary", riskSet.Items())

	cd := tmentities.NewOrderedMap[any]()
	for _, level := range []string{"low", "medium", "high"} {
		n := 0
		for _, ar := range analyzed {
			if kc, _ := ar.ComplexityIndicators.Get("keyword_complexity"); kc == level {
				n++
			}
		}
		cd.Set(level, n)
	}
	ins.Set("complexity_distribution", cd)

	phases := []string{}
	for _, ph := range []struct {
		name     string
		patterns []RequirementPattern
	}{
		{"planning", []RequirementPattern{PatternDocumentationRequirement}},
		{"architecture", []RequirementPattern{PatternDatabaseSchema, PatternSecurityRequirement}},
		{"implementation", []RequirementPattern{PatternCrudOperations, PatternUIComponent, PatternAPIIntegration}},
		{"testing", []RequirementPattern{PatternTestingRequirement}},
		{"deployment", []RequirementPattern{PatternDeployment, PatternMonitoring}},
	} {
		for _, p := range ph.patterns {
			if hasPattern(allPats, p) {
				phases = append(phases, ph.name)
				break
			}
		}
	}
	ins.Set("suggested_phases", phases)
	return ins
}
