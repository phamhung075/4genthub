package value_objects

import (
	"os"
	"path/filepath"
	"strings"

	"gopkg.in/yaml.v3"
)

// AgentRole: Enumeration of all available agent roles - matches agenthub_main/agent-library/agents
type AgentRole string

const (
	AgentRoleAnalyticsSetup                AgentRole = "analytics-setup-agent"
	AgentRoleCoding                        AgentRole = "coding-agent"
	AgentRoleCodeReviewer                  AgentRole = "code-reviewer-agent"
	AgentRoleDebugger                      AgentRole = "debugger-agent"
	AgentRoleCoreConcept                   AgentRole = "core-concept-agent"
	AgentRoleDesignSystem                  AgentRole = "design-system-agent"
	AgentRoleSystemArchitect               AgentRole = "system-architect-agent"
	AgentRoleUiSpecialist                  AgentRole = "shadcn-ui-expert-agent"
	AgentRolePerformanceLoadTester         AgentRole = "performance-load-tester-agent"
	AgentRoleTestOrchestrator              AgentRole = "test-orchestrator-agent"
	AgentRoleUatCoordinator                AgentRole = "uat-coordinator-agent"
	AgentRoleDevops                        AgentRole = "devops-agent"
	AgentRoleDocumentation                 AgentRole = "documentation-agent"
	AgentRoleElicitation                   AgentRole = "elicitation-agent"
	AgentRoleMasterOrchestrator            AgentRole = "master-orchestrator-agent"
	AgentRoleProjectInitiator              AgentRole = "project-initiator-agent"
	AgentRoleTaskPlanning                  AgentRole = "task-planning-agent"
	AgentRoleComplianceScope               AgentRole = "compliance-scope-agent"
	AgentRoleEthicalReview                 AgentRole = "ethical-review-agent"
	AgentRoleSecurityAuditor               AgentRole = "security-auditor-agent"
	AgentRoleEfficiencyOptimization        AgentRole = "efficiency-optimization-agent"
	AgentRoleHealthMonitor                 AgentRole = "health-monitor-agent"
	AgentRoleBranding                      AgentRole = "branding-agent"
	AgentRoleCommunityStrategy             AgentRole = "community-strategy-agent"
	AgentRoleMarketingStrategyOrchestrator AgentRole = "marketing-strategy-orchestrator-agent"
	AgentRoleDeepResearch                  AgentRole = "deep-research-agent"
	AgentRoleLlmAiAgentsResearch           AgentRole = "llm-ai-agents-research"
	AgentRoleRootCauseAnalysis             AgentRole = "root-cause-analysis-agent"
	AgentRoleTechnologyAdvisor             AgentRole = "technology-advisor-agent"
	AgentRoleMlSpecialist                  AgentRole = "ml-specialist-agent"
	AgentRoleCreativeIdeation              AgentRole = "creative-ideation-agent"
	AgentRolePrototyping                   AgentRole = "prototyping-agent"
)

// AgentRoleValues lists all members in declaration order.
var AgentRoleValues = []AgentRole{AgentRoleAnalyticsSetup, AgentRoleCoding, AgentRoleCodeReviewer, AgentRoleDebugger, AgentRoleCoreConcept, AgentRoleDesignSystem, AgentRoleSystemArchitect, AgentRoleUiSpecialist, AgentRolePerformanceLoadTester, AgentRoleTestOrchestrator, AgentRoleUatCoordinator, AgentRoleDevops, AgentRoleDocumentation, AgentRoleElicitation, AgentRoleMasterOrchestrator, AgentRoleProjectInitiator, AgentRoleTaskPlanning, AgentRoleComplianceScope, AgentRoleEthicalReview, AgentRoleSecurityAuditor, AgentRoleEfficiencyOptimization, AgentRoleHealthMonitor, AgentRoleBranding, AgentRoleCommunityStrategy, AgentRoleMarketingStrategyOrchestrator, AgentRoleDeepResearch, AgentRoleLlmAiAgentsResearch, AgentRoleRootCauseAnalysis, AgentRoleTechnologyAdvisor, AgentRoleMlSpecialist, AgentRoleCreativeIdeation, AgentRolePrototyping}

func (e AgentRole) String() string { return string(e) }

// GetAllRoles lists all role slugs.
func GetAllRoles() []string { return stringValues(AgentRoleValues) }

// GetRoleBySlug returns the role for slug, or false when unknown.
func GetRoleBySlug(slug string) (AgentRole, bool) {
	for _, r := range AgentRoleValues {
		if string(r) == slug {
			return r, true
		}
	}
	return "", false
}

// IsValidRole reports whether slug is a known role.
func IsValidRole(slug string) bool { _, ok := GetRoleBySlug(slug); return ok }

// FolderName is the slug with hyphens replaced by underscores.
func (r AgentRole) FolderName() string { return strings.ReplaceAll(string(r), "-", "_") }

func (r AgentRole) metadataString(key string) string {
	if md := GetRoleMetadataFromYaml(r); md != nil {
		if s, ok := md[key].(string); ok {
			return s
		}
	}
	return ""
}

// DisplayName is the "name" field from the role's job_desc.yaml.
func (r AgentRole) DisplayName() string { return r.metadataString("name") }

// Description is the "role_definition" field.
func (r AgentRole) Description() string { return r.metadataString("role_definition") }

// WhenToUse is the "when_to_use" field.
func (r AgentRole) WhenToUse() string { return r.metadataString("when_to_use") }

// Groups is the "groups" field, or an empty list.
func (r AgentRole) Groups() []any {
	if md := GetRoleMetadataFromYaml(r); md != nil {
		if g, ok := md["groups"].([]any); ok {
			return g
		}
	}
	return []any{}
}

// GetSupportedRoles lists supported roles for rule generation.
func GetSupportedRoles() []string { return GetAllRoles() }

// GetRoleMetadata returns metadata for a role slug, or nil.
func GetRoleMetadata(roleSlug string) map[string]any {
	r, ok := GetRoleBySlug(roleSlug)
	if !ok {
		return nil
	}
	return GetRoleMetadataFromYaml(r)
}

// GetRoleFolderName returns the folder name for a slug.
func GetRoleFolderName(roleSlug string) (string, bool) {
	r, ok := GetRoleBySlug(roleSlug)
	if !ok {
		return "", false
	}
	return r.FolderName(), true
}

// GetYamlLibPath returns the agent-library path for a role.
func GetYamlLibPath(role AgentRole) (string, bool) {
	if !IsValidRole(string(role)) {
		return "", false
	}
	return "cursor_agent/agent-library/" + role.FolderName(), true
}

// GetRoleMetadataFromYaml reads cursor_agent/agent-library/<folder>/job_desc.yaml
// (relative to the working directory) and adds "folder_name" and "slug".
// It returns nil for unknown roles, missing files, parse errors, or empty documents.
func GetRoleMetadataFromYaml(role AgentRole) map[string]any {
	if !IsValidRole(string(role)) {
		return nil
	}
	folder := role.FolderName()
	data, err := os.ReadFile(filepath.Join("cursor_agent", "agent-library", folder, "job_desc.yaml"))
	if err != nil {
		return nil
	}
	var doc map[string]any
	if err := yaml.Unmarshal(data, &doc); err != nil || len(doc) == 0 {
		return nil
	}
	doc["folder_name"] = folder
	doc["slug"] = string(role)
	return doc
}

// LegacyRoleMappings maps legacy role names to current slugs.
var LegacyRoleMappings = map[string]string{
	"senior_developer":  "coding-agent",
	"platform_engineer": "devops-agent",
	"qa_engineer":       "test-orchestrator-agent",
	"code_reviewer":     "code-reviewer-agent",
	"devops_engineer":   "devops-agent",
	"security_engineer": "security-auditor-agent",
	"technical_writer":  "documentation-agent",
	"task_planner":      "task-planning-agent",
	"context_engineer":  "core-concept-agent",
	"cache_engineer":    "efficiency-optimization-agent",
	"metrics_engineer":  "analytics-setup-agent",
	"cli_engineer":      "coding-agent",
}

// legacyRoleOrder preserves the Python dict insertion order for listing.
var legacyRoleOrder = []string{
	"senior_developer", "platform_engineer", "qa_engineer", "code_reviewer", "devops_engineer",
	"security_engineer", "technical_writer", "task_planner", "context_engineer", "cache_engineer",
	"metrics_engineer", "cli_engineer",
}

// ResolveLegacyRole resolves legacy or variant role names to a current slug.
func ResolveLegacyRole(legacyRole string) (string, bool) {
	if legacyRole == "" {
		return "", false
	}
	clean := strings.TrimLeft(strings.TrimSpace(legacyRole), "@")
	if IsValidRole(clean) {
		return clean, true
	}
	if resolved, ok := LegacyRoleMappings[clean]; ok && IsValidRole(resolved) {
		return resolved, true
	}
	if v := strings.ReplaceAll(clean, "-", "_"); IsValidRole(v) {
		return v, true
	}
	if v := strings.ReplaceAll(clean, "_", "-"); IsValidRole(v) {
		return v, true
	}
	return "", false
}

// GetAllRoleSlugsWithLegacy returns current slugs followed by legacy names.
func GetAllRoleSlugsWithLegacy() []string {
	return append(GetAllRoles(), legacyRoleOrder...)
}
