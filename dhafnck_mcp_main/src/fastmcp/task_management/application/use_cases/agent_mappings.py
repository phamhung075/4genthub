"""
Agent Name Mappings for Backward Compatibility
Generated: 2025-09-09
Purpose: Support deprecated agent names during migration period
"""

# Agent consolidation mappings (deprecated → active)
DEPRECATED_AGENT_MAPPINGS = {
    # Documentation consolidation
    "tech_spec_agent": "documentation_agent",
    "tech-spec-agent": "documentation-agent",
    "prd_architect_agent": "documentation_agent",
    "prd-architect-agent": "documentation-agent",
    
    # Research consolidation  
    "mcp_researcher_agent": "deep_research_agent",
    "mcp-researcher-agent": "deep-research-agent",
    
    # Creative consolidation
    "idea_generation_agent": "creative_ideation_agent",
    "idea-generation-agent": "creative-ideation-agent",
    "idea_refinement_agent": "creative_ideation_agent",
    "idea-refinement-agent": "creative-ideation-agent",
    
    # Marketing consolidation
    "seo_sem_agent": "marketing_strategy_orchestrator_agent",
    "seo-sem-agent": "marketing-strategy-orchestrator-agent",
    "growth_hacking_idea_agent": "marketing_strategy_orchestrator_agent",
    "growth-hacking-idea-agent": "marketing-strategy-orchestrator-agent",
    "content_strategy_agent": "marketing_strategy_orchestrator_agent",
    "content-strategy-agent": "marketing-strategy-orchestrator-agent",
    
    # DevOps consolidation
    "swarm_scaler_agent": "devops_agent",
    "swarm-scaler-agent": "devops-agent",
    "adaptive_deployment_strategist_agent": "devops_agent",
    "adaptive-deployment-strategist-agent": "devops-agent",
    "mcp_configuration_agent": "devops_agent",
    "mcp-configuration-agent": "devops-agent",
    
    # Debug consolidation
    "remediation_agent": "debugger_agent",
    "remediation-agent": "debugger-agent",
    
    # Renamings
    "uber_orchestrator_agent": "master_orchestrator_agent",
    "uber-orchestrator-agent": "master-orchestrator-agent",
    "brainjs_ml_agent": "ml_specialist_agent",
    "brainjs-ml-agent": "ml-specialist-agent",
    "ui_designer_expert_shadcn_agent": "ui_specialist_agent",
    "ui-designer-expert-shadcn-agent": "ui-specialist-agent",
}

def resolve_agent_name(agent_name: str) -> str:
    """
    Resolve agent name, handling deprecated names.
    
    Args:
        agent_name: The agent name to resolve
        
    Returns:
        The active agent name (mapped if deprecated)
    """
    # Normalize to underscore format
    normalized = agent_name.replace('-', '_')
    
    # Check if deprecated
    if normalized in DEPRECATED_AGENT_MAPPINGS:
        return DEPRECATED_AGENT_MAPPINGS[normalized]
    
    # Check hyphenated version
    hyphenated = agent_name.replace('_', '-')
    if hyphenated in DEPRECATED_AGENT_MAPPINGS:
        return DEPRECATED_AGENT_MAPPINGS[hyphenated]
    
    # Return original if not deprecated
    return agent_name

def is_deprecated_agent(agent_name: str) -> bool:
    """
    Check if an agent name is deprecated.
    
    Args:
        agent_name: The agent name to check
        
    Returns:
        True if the agent is deprecated
    """
    normalized = agent_name.replace('-', '_')
    hyphenated = agent_name.replace('_', '-')
    
    return (normalized in DEPRECATED_AGENT_MAPPINGS or 
            hyphenated in DEPRECATED_AGENT_MAPPINGS)