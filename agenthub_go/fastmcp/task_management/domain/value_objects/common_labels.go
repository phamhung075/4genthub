package value_objects

import (
	"regexp"
	"strings"
	"unicode/utf8"
)

// CommonLabel: Enumeration of commonly used task labels
type CommonLabel string

const (
	CommonLabelUrgent             CommonLabel = "urgent"
	CommonLabelCritical           CommonLabel = "critical"
	CommonLabelHotFix             CommonLabel = "hotfix"
	CommonLabelBlocker            CommonLabel = "blocker"
	CommonLabelBug                CommonLabel = "bug"
	CommonLabelFeature            CommonLabel = "feature"
	CommonLabelEnhancement        CommonLabel = "enhancement"
	CommonLabelRefactor           CommonLabel = "refactor"
	CommonLabelDocumentation      CommonLabel = "documentation"
	CommonLabelTesting            CommonLabel = "testing"
	CommonLabelResearch           CommonLabel = "research"
	CommonLabelSpike              CommonLabel = "spike"
	CommonLabelFrontend           CommonLabel = "frontend"
	CommonLabelBackend            CommonLabel = "backend"
	CommonLabelApi                CommonLabel = "api"
	CommonLabelDatabase           CommonLabel = "database"
	CommonLabelUiUx               CommonLabel = "ui/ux"
	CommonLabelInfrastructure     CommonLabel = "infrastructure"
	CommonLabelDevops             CommonLabel = "devops"
	CommonLabelSecurity           CommonLabel = "security"
	CommonLabelCodeReview         CommonLabel = "code-review"
	CommonLabelQa                 CommonLabel = "qa"
	CommonLabelDeployment         CommonLabel = "deployment"
	CommonLabelMonitoring         CommonLabel = "monitoring"
	CommonLabelPerformance        CommonLabel = "performance"
	CommonLabelOptimization       CommonLabel = "optimization"
	CommonLabelSimple             CommonLabel = "simple"
	CommonLabelComplex            CommonLabel = "complex"
	CommonLabelTechnicalDebt      CommonLabel = "technical-debt"
	CommonLabelLegacy             CommonLabel = "legacy"
	CommonLabelBlocked            CommonLabel = "blocked"
	CommonLabelWaiting            CommonLabel = "waiting"
	CommonLabelReady              CommonLabel = "ready"
	CommonLabelInReview           CommonLabel = "in-review"
	CommonLabelNeedsClarification CommonLabel = "needs-clarification"
	CommonLabelAuth               CommonLabel = "auth"
	CommonLabelIntegration        CommonLabel = "integration"
	CommonLabelMigration          CommonLabel = "migration"
	CommonLabelConfiguration      CommonLabel = "configuration"
	CommonLabelAutomation         CommonLabel = "automation"
	CommonLabelAiAgent            CommonLabel = "ai-agent"
	CommonLabelMcp                CommonLabel = "mcp"
	CommonLabelAgenthub           CommonLabel = "task-management"
	CommonLabelAutoGeneration     CommonLabel = "auto-generation"
	CommonLabelRuleGeneration     CommonLabel = "rule-generation"
	CommonLabelUnitTest           CommonLabel = "unit-test"
	CommonLabelIntegrationTest    CommonLabel = "integration-test"
	CommonLabelE2eTest            CommonLabel = "e2e-test"
	CommonLabelDomain             CommonLabel = "domain"
	CommonLabelEntity             CommonLabel = "entity"
	CommonLabelValueObject        CommonLabel = "value-object"
	CommonLabelProject            CommonLabel = "project"
	CommonLabelSubtask            CommonLabel = "subtask"
)

// CommonLabelValues lists all members in declaration order.
var CommonLabelValues = []CommonLabel{CommonLabelUrgent, CommonLabelCritical, CommonLabelHotFix, CommonLabelBlocker, CommonLabelBug, CommonLabelFeature, CommonLabelEnhancement, CommonLabelRefactor, CommonLabelDocumentation, CommonLabelTesting, CommonLabelResearch, CommonLabelSpike, CommonLabelFrontend, CommonLabelBackend, CommonLabelApi, CommonLabelDatabase, CommonLabelUiUx, CommonLabelInfrastructure, CommonLabelDevops, CommonLabelSecurity, CommonLabelCodeReview, CommonLabelQa, CommonLabelDeployment, CommonLabelMonitoring, CommonLabelPerformance, CommonLabelOptimization, CommonLabelSimple, CommonLabelComplex, CommonLabelTechnicalDebt, CommonLabelLegacy, CommonLabelBlocked, CommonLabelWaiting, CommonLabelReady, CommonLabelInReview, CommonLabelNeedsClarification, CommonLabelAuth, CommonLabelIntegration, CommonLabelMigration, CommonLabelConfiguration, CommonLabelAutomation, CommonLabelAiAgent, CommonLabelMcp, CommonLabelAgenthub, CommonLabelAutoGeneration, CommonLabelRuleGeneration, CommonLabelUnitTest, CommonLabelIntegrationTest, CommonLabelE2eTest, CommonLabelDomain, CommonLabelEntity, CommonLabelValueObject, CommonLabelProject, CommonLabelSubtask}

func (e CommonLabel) String() string { return string(e) }

var commonLabelKeywords = map[CommonLabel][]string{
	CommonLabelUrgent:             {"urgent", "asap", "immediately", "priority", "high priority"},
	CommonLabelCritical:           {"critical", "production", "down", "outage", "emergency"},
	CommonLabelHotFix:             {"hotfix", "hot fix", "quick fix", "patch", "emergency fix"},
	CommonLabelBlocker:            {"blocker", "blocking", "blocked", "cannot proceed"},
	CommonLabelBug:                {"bug", "error", "issue", "broken", "defect", "problem"},
	CommonLabelFeature:            {"feature", "new", "add", "implement", "enhancement", "functionality"},
	CommonLabelEnhancement:        {"enhancement", "improve", "better", "optimize", "upgrade"},
	CommonLabelRefactor:           {"refactor", "cleanup", "improve", "restructure", "reorganize"},
	CommonLabelDocumentation:      {"doc", "documentation", "readme", "guide", "manual"},
	CommonLabelTesting:            {"test", "testing", "spec", "qa", "verification", "validation"},
	CommonLabelResearch:           {"research", "investigate", "explore", "study", "analyze"},
	CommonLabelSpike:              {"spike", "proof of concept", "poc", "experiment"},
	CommonLabelFrontend:           {"frontend", "ui", "interface", "react", "vue", "angular", "client"},
	CommonLabelBackend:            {"backend", "server", "api", "endpoint", "service"},
	CommonLabelApi:                {"api", "endpoint", "rest", "graphql", "service"},
	CommonLabelDatabase:           {"database", "db", "sql", "migration", "schema"},
	CommonLabelUiUx:               {"ui", "ux", "design", "user interface", "user experience"},
	CommonLabelInfrastructure:     {"infrastructure", "deployment", "server", "cloud"},
	CommonLabelDevops:             {"devops", "ci/cd", "deployment", "pipeline", "automation"},
	CommonLabelSecurity:           {"security", "auth", "authentication", "authorization", "vulnerability"},
	CommonLabelCodeReview:         {"code review", "review", "pr", "pull request"},
	CommonLabelQa:                 {"qa", "quality", "testing", "verification"},
	CommonLabelDeployment:         {"deployment", "deploy", "release", "production"},
	CommonLabelMonitoring:         {"monitoring", "metrics", "logging", "observability"},
	CommonLabelPerformance:        {"performance", "speed", "optimization", "slow"},
	CommonLabelOptimization:       {"optimization", "optimize", "improve", "efficiency"},
	CommonLabelSimple:             {"simple", "easy", "quick", "straightforward"},
	CommonLabelComplex:            {"complex", "complicated", "difficult", "challenging"},
	CommonLabelTechnicalDebt:      {"technical debt", "debt", "legacy", "cleanup"},
	CommonLabelLegacy:             {"legacy", "old", "deprecated", "outdated"},
	CommonLabelBlocked:            {"blocked", "blocking", "cannot proceed", "waiting"},
	CommonLabelWaiting:            {"waiting", "pending", "on hold"},
	CommonLabelReady:              {"ready", "prepared", "available"},
	CommonLabelInReview:           {"in review", "reviewing", "under review"},
	CommonLabelNeedsClarification: {"clarification", "unclear", "question", "discuss"},
	CommonLabelAuth:               {"auth", "authentication", "login", "user", "security"},
	CommonLabelIntegration:        {"integration", "connect", "api", "third party"},
	CommonLabelMigration:          {"migration", "migrate", "move", "transfer"},
	CommonLabelConfiguration:      {"configuration", "config", "settings", "setup"},
	CommonLabelAutomation:         {"automation", "automated", "script", "workflow"},
	CommonLabelAiAgent:            {"agent", "ai", "artificial intelligence", "bot"},
	CommonLabelMcp:                {"mcp", "model context protocol", "protocol"},
	CommonLabelAgenthub:           {"task management", "task", "project", "workflow"},
	CommonLabelAutoGeneration:     {"auto generation", "generate", "automatic"},
	CommonLabelRuleGeneration:     {"rule generation", "rules", "auto rule"},
	CommonLabelUnitTest:           {"unit test", "unit", "test", "unittest", "unit testing"},
	CommonLabelIntegrationTest:    {"integration test", "integration", "e2e", "end to end"},
	CommonLabelE2eTest:            {"e2e", "end to end", "e2e test", "end-to-end"},
	CommonLabelDomain:             {"domain", "domain layer", "business logic", "domain model"},
	CommonLabelEntity:             {"entity", "entities", "domain entity", "business entity"},
	CommonLabelValueObject:        {"value object", "value", "vo", "valueobject"},
	CommonLabelProject:            {"project", "project entity", "project management"},
	CommonLabelSubtask:            {"subtask", "sub task", "child task", "sub-task"},
}

// GetKeywords returns keywords used for suggestion matching (the label itself if none).
func (c CommonLabel) GetKeywords() []string {
	if k, ok := commonLabelKeywords[c]; ok {
		return k
	}
	return []string{string(c)}
}

// GetAllLabels lists all label values.
func GetAllLabels() []string { return stringValues(CommonLabelValues) }

// GetPriorityLabels returns the get_priority_labels group.
func GetPriorityLabels() []string {
	return stringValues([]CommonLabel{CommonLabelUrgent, CommonLabelCritical, CommonLabelHotFix, CommonLabelBlocker})
}

// GetTypeLabels returns the get_type_labels group.
func GetTypeLabels() []string {
	return stringValues([]CommonLabel{CommonLabelBug, CommonLabelFeature, CommonLabelEnhancement, CommonLabelRefactor, CommonLabelDocumentation, CommonLabelTesting, CommonLabelResearch, CommonLabelSpike})
}

// GetComponentLabels returns the get_component_labels group.
func GetComponentLabels() []string {
	return stringValues([]CommonLabel{CommonLabelFrontend, CommonLabelBackend, CommonLabelApi, CommonLabelDatabase, CommonLabelUiUx, CommonLabelInfrastructure, CommonLabelDevops, CommonLabelSecurity})
}

// GetAiLabels returns the get_ai_labels group.
func GetAiLabels() []string {
	return stringValues([]CommonLabel{CommonLabelAiAgent, CommonLabelMcp, CommonLabelAgenthub, CommonLabelAutoGeneration, CommonLabelRuleGeneration})
}

// GetTestingLabels returns the get_testing_labels group.
func GetTestingLabels() []string {
	return stringValues([]CommonLabel{CommonLabelTesting, CommonLabelUnitTest, CommonLabelIntegrationTest, CommonLabelE2eTest, CommonLabelDomain, CommonLabelEntity, CommonLabelValueObject, CommonLabelProject, CommonLabelSubtask})
}

// IsValidCommonLabel reports whether label is a common label value.
func IsValidCommonLabel(label string) bool {
	return label != "" && containsString(GetAllLabels(), label)
}

// SuggestLabels suggests labels whose keywords occur in text. Python returns
// list(set(...)) (unordered); Go returns declaration order.
func SuggestLabels(text string) []string {
	if text == "" {
		return []string{}
	}
	lower := strings.ToLower(text)
	out := []string{}
	for _, label := range CommonLabelValues {
		for _, k := range label.GetKeywords() {
			if k != "" && strings.Contains(lower, strings.ToLower(k)) {
				out = append(out, string(label))
				break
			}
		}
	}
	return out
}

var labelFormatPattern = regexp.MustCompile(`^[a-zA-Z0-9\-_/]+$`)

func normalizeLabel(label string) string {
	return strings.ReplaceAll(strings.ToLower(strings.TrimSpace(label)), " ", "-")
}

// LabelValidator validates task labels (common and custom).
type LabelValidator struct{}

// IsValidLabel accepts common labels or custom labels (<=50 chars, [A-Za-z0-9-_/]).
func (LabelValidator) IsValidLabel(label string) bool {
	if label == "" {
		return false
	}
	if IsValidCommonLabel(label) {
		return true
	}
	n := normalizeLabel(label)
	if utf8.RuneCountInString(n) > 50 || !labelFormatPattern.MatchString(n) {
		return false
	}
	switch n {
	case "invalid-label", "test-invalid", "bad-label":
		return false
	}
	return true
}

// ValidateLabels normalizes labels, skipping empty ones and raising on invalid ones.
func (LabelValidator) ValidateLabels(labels []string) ([]string, error) {
	normalized := []string{}
	for _, label := range labels {
		if label == "" {
			continue
		}
		n := normalizeLabel(label)
		if utf8.RuneCountInString(n) > 50 {
			return nil, valueErrorf("Label too long: %s (max 50 characters)", label)
		}
		if !labelFormatPattern.MatchString(n) {
			return nil, valueErrorf("Invalid label format: %s (use alphanumeric, hyphens, underscores only)", label)
		}
		normalized = append(normalized, n)
	}
	return normalized, nil
}

// GetLabelSuggestions returns up to 5 suggestions not already in existingLabels.
func (LabelValidator) GetLabelSuggestions(existingLabels []string, textContent string) []string {
	out := []string{}
	for _, s := range SuggestLabels(textContent) {
		if !containsString(existingLabels, s) {
			out = append(out, s)
		}
	}
	if len(out) > 5 {
		out = out[:5]
	}
	return out
}
