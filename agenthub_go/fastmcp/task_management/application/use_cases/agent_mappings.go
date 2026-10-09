// Package use_cases ports task_management/application/use_cases/agent_mappings.py.
package use_cases

import (
	"strings"

	"agenthub/fastmcp/task_management/domain/value_objects"
)

// DeprecatedAgentMappings maps deprecated agent names to active kebab-case names.
var DeprecatedAgentMappings = map[string]string{
	// Documentation consolidation
	"tech_spec_agent":     "documentation-agent",
	"tech-spec-agent":     "documentation-agent",
	"prd_architect_agent": "documentation-agent",
	"prd-architect-agent": "documentation-agent",
	"documentation-agent": "documentation-agent",
	// Research consolidation
	"mcp_researcher_agent": "deep-research-agent",
	"mcp-researcher-agent": "deep-research-agent",
	"deep-research-agent":  "deep-research-agent",
	// Creative consolidation
	"idea_generation_agent":   "creative-ideation-agent",
	"idea-generation-agent":   "creative-ideation-agent",
	"idea_refinement_agent":   "creative-ideation-agent",
	"idea-refinement-agent":   "creative-ideation-agent",
	"creative-ideation-agent": "creative-ideation-agent",
	// Marketing consolidation
	"seo_sem_agent":                         "marketing-strategy-orchestrator-agent",
	"seo-sem-agent":                         "marketing-strategy-orchestrator-agent",
	"growth_hacking_idea_agent":             "marketing-strategy-orchestrator-agent",
	"growth-hacking-idea-agent":             "marketing-strategy-orchestrator-agent",
	"content_strategy_agent":                "marketing-strategy-orchestrator-agent",
	"content-strategy-agent":                "marketing-strategy-orchestrator-agent",
	"marketing-strategy-orchestrator-agent": "marketing-strategy-orchestrator-agent",
	// DevOps consolidation
	"swarm_scaler_agent":                   "devops-agent",
	"swarm-scaler-agent":                   "devops-agent",
	"adaptive_deployment_strategist_agent": "devops-agent",
	"adaptive-deployment-strategist-agent": "devops-agent",
	"mcp_configuration_agent":              "devops-agent",
	"mcp-configuration-agent":              "devops-agent",
	"devops-agent":                         "devops-agent",
	// Debug consolidation
	"remediation_agent": "debugger-agent",
	"remediation-agent": "debugger-agent",
	"debugger-agent":    "debugger-agent",
	// Specialized agent mappings
	"brainjs_ml_agent":                "ml-specialist-agent",
	"brainjs-ml-agent":                "ml-specialist-agent",
	"ml-specialist-agent":             "ml-specialist-agent",
	"ui_designer_expert_shadcn_agent": "shadcn-ui-expert-agent",
	"ui-designer-expert-shadcn-agent": "shadcn-ui-expert-agent",
	"shadcn-ui-expert-agent":          "shadcn-ui-expert-agent",
	// Map all other agents from underscore/@ to kebab-case
	"master-orchestrator-agent":     "master-orchestrator-agent",
	"coding-agent":                  "coding-agent",
	"code-reviewer-agent":           "code-reviewer-agent",
	"branding-agent":                "branding-agent",
	"system-architect-agent":        "system-architect-agent",
	"task-planning-agent":           "task-planning-agent",
	"elicitation-agent":             "elicitation-agent",
	"technology-advisor-agent":      "technology-advisor-agent",
	"security-auditor-agent":        "security-auditor-agent",
	"test-orchestrator-agent":       "test-orchestrator-agent",
	"performance-load-tester-agent": "performance-load-tester-agent",
	"uat-coordinator-agent":         "uat-coordinator-agent",
	"health-monitor-agent":          "health-monitor-agent",
	"project-initiator-agent":       "project-initiator-agent",
	"ethical-review-agent":          "ethical-review-agent",
	"compliance-scope-agent":        "compliance-scope-agent",
	"core-concept-agent":            "core-concept-agent",
	"community-strategy-agent":      "community-strategy-agent",
	"design-system-agent":           "design-system-agent",
	"prototyping-agent":             "prototyping-agent",
	"root-cause-analysis-agent":     "root-cause-analysis-agent",
	"efficiency-optimization-agent": "efficiency-optimization-agent",
	"analytics-setup-agent":         "analytics-setup-agent",
	"llm-ai-agents-research":        "llm-ai-agents-research",
}

// ResolveAgentName resolves an agent name to the standard kebab-case format.
func ResolveAgentName(agentName string) string {
	if agentName == "" {
		return ""
	}
	if v, ok := DeprecatedAgentMappings[agentName]; ok {
		return v
	}
	stripped := strings.TrimLeft(agentName, "@")
	if v, ok := DeprecatedAgentMappings[stripped]; ok {
		return v
	}
	normalized := strings.TrimLeft(strings.ReplaceAll(agentName, "-", "_"), "@")
	if v, ok := DeprecatedAgentMappings[normalized]; ok {
		return v
	}
	hyphenated := strings.TrimLeft(strings.ReplaceAll(agentName, "_", "-"), "@")
	if v, ok := DeprecatedAgentMappings[hyphenated]; ok {
		return v
	}
	standardized := value_objects.PyLower(strings.ReplaceAll(stripped, "_", "-"))
	if !strings.HasSuffix(standardized, "-agent") && !strings.HasSuffix(standardized, "-research") {
		if !strings.Contains(standardized, "agent") {
			standardized = standardized + "-agent"
		}
	}
	return standardized
}

// IsDeprecatedAgent reports whether an agent name maps to a different name.
func IsDeprecatedAgent(agentName string) bool {
	cleanName := strings.TrimLeft(agentName, "@")
	if v, ok := DeprecatedAgentMappings[cleanName]; ok {
		return v != cleanName
	}
	normalized := strings.ReplaceAll(cleanName, "-", "_")
	if v, ok := DeprecatedAgentMappings[normalized]; ok {
		return v != normalized
	}
	hyphenated := strings.ReplaceAll(cleanName, "_", "-")
	if v, ok := DeprecatedAgentMappings[hyphenated]; ok {
		return v != hyphenated
	}
	return false
}
