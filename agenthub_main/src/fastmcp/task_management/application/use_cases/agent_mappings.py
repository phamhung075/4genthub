"""
Agent Name Mappings for Backward Compatibility
Generated: 2025-09-09
Purpose: Support deprecated agent names during migration period
"""

# Agent consolidation mappings (deprecated → active kebab-case)
DEPRECATED_AGENT_MAPPINGS = {
    # Documentation consolidation
    "tech_spec_agent": "documentation-agent",
    "tech-spec-agent": "documentation-agent",
    "prd_architect_agent": "documentation-agent",
    "prd-architect-agent": "documentation-agent",
    "documentation-agent": "documentation-agent",
    "documentation-agent": "documentation-agent",
    
    # Research consolidation  
    "mcp_researcher_agent": "deep-research-agent",
    "mcp-researcher-agent": "deep-research-agent",
    "deep-research-agent": "deep-research-agent",
    "deep-research-agent": "deep-research-agent",
    
    # Creative consolidation
    "idea_generation_agent": "creative-ideation-agent",
    "idea-generation-agent": "creative-ideation-agent",
    "idea_refinement_agent": "creative-ideation-agent",
    "idea-refinement-agent": "creative-ideation-agent",
    "creative-ideation-agent": "creative-ideation-agent",
    "creative-ideation-agent": "creative-ideation-agent",
    
    # Marketing consolidation
    "seo_sem_agent": "marketing-strategy-orchestrator-agent",
    "seo-sem-agent": "marketing-strategy-orchestrator-agent",
    "growth_hacking_idea_agent": "marketing-strategy-orchestrator-agent",
    "growth-hacking-idea-agent": "marketing-strategy-orchestrator-agent",
    "content_strategy_agent": "marketing-strategy-orchestrator-agent",
    "content-strategy-agent": "marketing-strategy-orchestrator-agent",
    "marketing-strategy-orchestrator-agent": "marketing-strategy-orchestrator-agent",
    "marketing-strategy-orchestrator-agent": "marketing-strategy-orchestrator-agent",
    
    # DevOps consolidation
    "swarm_scaler_agent": "devops-agent",
    "swarm-scaler-agent": "devops-agent",
    "adaptive_deployment_strategist_agent": "devops-agent",
    "adaptive-deployment-strategist-agent": "devops-agent",
    "mcp_configuration_agent": "devops-agent",
    "mcp-configuration-agent": "devops-agent",
    "devops-agent": "devops-agent",
    "devops-agent": "devops-agent",
    
    # Debug consolidation
    "remediation_agent": "debugger-agent",
    "remediation-agent": "debugger-agent",
    "debugger-agent": "debugger-agent",
    "debugger-agent": "debugger-agent",
    
    # Specialized agent mappings
    "brainjs_ml_agent": "ml-specialist-agent",
    "brainjs-ml-agent": "ml-specialist-agent",
    "ml-specialist-agent": "ml-specialist-agent",
    "ml-specialist-agent": "ml-specialist-agent",
    "ui_designer_expert_shadcn_agent": "shadcn-ui-expert-agent",
    "ui-designer-expert-shadcn-agent": "shadcn-ui-expert-agent",
    "shadcn-ui-expert-agent": "shadcn-ui-expert-agent",
    "shadcn-ui-expert-agent": "shadcn-ui-expert-agent",
    
    # Map all other agents from underscore/@ to kebab-case
    "master-orchestrator-agent": "master-orchestrator-agent",
    "coding-agent": "coding-agent",
    "coding-agent": "coding-agent",
    "code-reviewer-agent": "code-reviewer-agent",
    "code-reviewer-agent": "code-reviewer-agent",
    "branding-agent": "branding-agent",
    "branding-agent": "branding-agent",
    "system-architect-agent": "system-architect-agent",
    "system-architect-agent": "system-architect-agent",
    "task-planning-agent": "task-planning-agent",
    "task-planning-agent": "task-planning-agent",
    "elicitation-agent": "elicitation-agent",
    "elicitation-agent": "elicitation-agent",
    "technology-advisor-agent": "technology-advisor-agent",
    "technology-advisor-agent": "technology-advisor-agent",
    "security-auditor-agent": "security-auditor-agent",
    "security-auditor-agent": "security-auditor-agent",
    "test-orchestrator-agent": "test-orchestrator-agent",
    "test-orchestrator-agent": "test-orchestrator-agent",
    "performance-load-tester-agent": "performance-load-tester-agent",
    "performance-load-tester-agent": "performance-load-tester-agent",
    "uat-coordinator-agent": "uat-coordinator-agent",
    "uat-coordinator-agent": "uat-coordinator-agent",
    "health-monitor-agent": "health-monitor-agent",
    "health-monitor-agent": "health-monitor-agent",
    "project-initiator-agent": "project-initiator-agent",
    "project-initiator-agent": "project-initiator-agent",
    "ethical-review-agent": "ethical-review-agent",
    "ethical-review-agent": "ethical-review-agent",
    "compliance-scope-agent": "compliance-scope-agent",
    "compliance-scope-agent": "compliance-scope-agent",
    "core-concept-agent": "core-concept-agent",
    "core-concept-agent": "core-concept-agent",
    "community-strategy-agent": "community-strategy-agent",
    "community-strategy-agent": "community-strategy-agent",
    "design-system-agent": "design-system-agent",
    "design-system-agent": "design-system-agent",
    "prototyping-agent": "prototyping-agent",
    "prototyping-agent": "prototyping-agent",
    "root-cause-analysis-agent": "root-cause-analysis-agent",
    "root-cause-analysis-agent": "root-cause-analysis-agent",
    "efficiency-optimization-agent": "efficiency-optimization-agent",
    "efficiency-optimization-agent": "efficiency-optimization-agent",
    "analytics-setup-agent": "analytics-setup-agent",
    "analytics-setup-agent": "analytics-setup-agent",
    "llm-ai-agents-research": "llm-ai-agents-research",
    "llm-ai-agents-research": "llm-ai-agents-research",
}

def resolve_agent_name(agent_name: str) -> str:
    """
    Resolve agent name to standard kebab-case format.

    Args:
        agent_name: The agent name to resolve (can be @prefixed, underscore, or kebab-case)

    Returns:
        The standard kebab-case agent name
    """
    # Handle empty string
    if not agent_name:
        return ""

    # Direct lookup first (handles @, underscore, and kebab variations)
    if agent_name in DEPRECATED_AGENT_MAPPINGS:
        return DEPRECATED_AGENT_MAPPINGS[agent_name]
    
    # Strip @ prefix and try again
    stripped = agent_name.lstrip('@')
    if stripped in DEPRECATED_AGENT_MAPPINGS:
        return DEPRECATED_AGENT_MAPPINGS[stripped]
    
    # Convert to underscore format and try
    normalized = agent_name.replace('-', '_').lstrip('@')
    if normalized in DEPRECATED_AGENT_MAPPINGS:
        return DEPRECATED_AGENT_MAPPINGS[normalized]
    
    # Convert to hyphenated and try
    hyphenated = agent_name.replace('_', '-').lstrip('@')
    if hyphenated in DEPRECATED_AGENT_MAPPINGS:
        return DEPRECATED_AGENT_MAPPINGS[hyphenated]
    
    # If not in mappings, standardize to kebab-case
    # Remove @ prefix, replace underscores with hyphens
    standardized = agent_name.lstrip('@').replace('_', '-').lower()
    
    # Ensure it ends with -agent if not already
    if not standardized.endswith('-agent') and not standardized.endswith('-research'):
        if 'agent' not in standardized:
            standardized = f"{standardized}-agent"
    
    return standardized

def is_deprecated_agent(agent_name: str) -> bool:
    """
    Check if an agent name is deprecated.

    Args:
        agent_name: The agent name to check

    Returns:
        True if the agent is deprecated (maps to a different name)
    """
    # Strip @ prefix if present
    clean_name = agent_name.lstrip('@')

    # Check if the name is in the mappings
    if clean_name in DEPRECATED_AGENT_MAPPINGS:
        # It's deprecated only if it maps to a different name
        return DEPRECATED_AGENT_MAPPINGS[clean_name] != clean_name

    # Check underscore version
    normalized = clean_name.replace('-', '_')
    if normalized in DEPRECATED_AGENT_MAPPINGS:
        return DEPRECATED_AGENT_MAPPINGS[normalized] != normalized

    # Check hyphenated version
    hyphenated = clean_name.replace('_', '-')
    if hyphenated in DEPRECATED_AGENT_MAPPINGS:
        return DEPRECATED_AGENT_MAPPINGS[hyphenated] != hyphenated

    return False