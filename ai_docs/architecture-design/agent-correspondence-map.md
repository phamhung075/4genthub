# Agent Correspondence Map

## Overview
This document maps the correspondence between:
- `.claude/agents/` - Agent capability descriptions and calling conditions
- `dhafnck_mcp_main/agent-library/agents/` - Actual agent implementations

## Status: 2025-09-11

### ✅ Agents with Both Description and Implementation (33 agents)

| .claude/agents Description | agent-library Implementation | Status |
|---------------------------|------------------------------|---------|
| analytics_setup_agent.md | analytics_setup_agent/ | ✅ Match |
| branding_agent.md | branding_agent/ | ✅ Match |
| code_reviewer_agent.md | code_reviewer_agent/ | ✅ Match |
| coding_agent.md | coding_agent/ | ✅ Match |
| community_strategy_agent.md | community_strategy_agent/ | ✅ Match |
| compliance_scope_agent.md | compliance_scope_agent/ | ✅ Match |
| core_concept_agent.md | core_concept_agent/ | ✅ Match |
| debugger_agent.md | debugger_agent/ | ✅ Match |
| deep_research_agent.md | deep_research_agent/ | ✅ Match |
| design_system_agent.md | design_system_agent/ | ✅ Match |
| devops_agent.md | devops_agent/ | ✅ Match |
| documentation_agent.md | documentation_agent/ | ✅ Match |
| efficiency_optimization_agent.md | efficiency_optimization_agent/ | ✅ Match |
| elicitation_agent.md | elicitation_agent/ | ✅ Match |
| ethical_review_agent.md | ethical_review_agent/ | ✅ Match |
| health_monitor_agent.md | health_monitor_agent/ | ✅ Match |
| llm-ai-agents-and-eng-research.md | llm_ai_agents_research/ | ✅ Name variation |
| marketing_strategy_orchestrator_agent.md | marketing_strategy_orchestrator_agent/ | ✅ Match |
| master_orchestrator_agent.md | master_orchestrator_agent/ | ✅ Match (renamed from uber_orchestrator) |
| performance_load_tester_agent.md | performance_load_tester_agent/ | ✅ Match |
| project_initiator_agent.md | project_initiator_agent/ | ✅ Match |
| prototyping_agent.md | prototyping_agent/ | ✅ Match |
| root_cause_analysis_agent.md | root_cause_analysis_agent/ | ✅ Match |
| security_auditor_agent.md | security_auditor_agent/ | ✅ Match |
| system_architect_agent.md | system_architect_agent/ | ✅ Match |
| task_planning_agent.md | task_planning_agent/ | ✅ Match |
| technology_advisor_agent.md | technology_advisor_agent/ | ✅ Match |
| test_orchestrator_agent.md | test_orchestrator_agent/ | ✅ Match |
| uat_coordinator_agent.md | uat_coordinator_agent/ | ✅ Match |
| ui_specialist_agent.md | ui_specialist_agent/ | ✅ Match (renamed from ui_designer_expert_shadcn) |

### 📝 Agents with Description Only (No Implementation)

These agents exist in `.claude/agents/` but don't have implementations in `agent-library/`:

| .claude/agents Description | Purpose | Priority |
|---------------------------|----------|----------|
| adaptive_deployment_strategist_agent.md | Deployment strategies | Medium |
| brainjs_ml_agent.md | Brain.js ML implementation | Low |
| claude-code-troubleshooter.md | Claude Code debugging | High |
| content_strategy_agent.md | Content planning | Medium |
| growth_hacking_idea_agent.md | Growth strategies | Low |
| hello-world-agent.md | Simple greeting agent | Low |
| idea_generation_agent.md | Creative idea generation | Medium |
| idea_refinement_agent.md | Idea improvement | Medium |
| mcp_configuration_agent.md | MCP setup | High |
| mcp_researcher_agent.md | MCP research | Medium |
| meta-agent.md | Agent generation | High |
| prd_architect_agent.md | PRD documentation | Medium |
| remediation_agent.md | Issue remediation | Medium |
| seo_sem_agent.md | SEO/SEM optimization | Low |
| swarm_scaler_agent.md | Distributed scaling | Low |
| tech_spec_agent.md | Technical specifications | Medium |
| work-completion-summary.md | Work summaries | Low |

### 🔧 Agents with Implementation Only (No Description)

These agents exist in `agent-library/` but don't have descriptions in `.claude/agents/`:

| agent-library Implementation | Purpose | Action Needed |
|------------------------------|----------|--------------|
| creative_ideation_agent/ | Creative ideation | Similar to idea_generation_agent |
| ml_specialist_agent/ | ML specialization | Similar to brainjs_ml_agent |

## Recommendations

1. **High Priority**:
   - Implement `claude-code-troubleshooter` in agent-library
   - Implement `mcp_configuration_agent` in agent-library
   - Implement `meta-agent` in agent-library

2. **Consolidation Opportunities**:
   - Merge `creative_ideation_agent` with `idea_generation_agent`
   - Merge `ml_specialist_agent` with `brainjs_ml_agent`

3. **Naming Standardization**:
   - `llm-ai-agents-and-eng-research.md` → Consider renaming to match `llm_ai_agents_research`

## Total Agent Count
- **33 agents** with both description and implementation (functional)
- **17 agents** with description only (pending implementation)
- **2 agents** with implementation only (need descriptions)
- **Total unique agents**: ~50 (with overlaps to consolidate)

## Notes
- The `.claude/agents/` directory stores agent capability descriptions and conditions for when to call each agent
- The `agent-library/` directory contains the actual agent implementations with YAML configurations
- Not all agents need implementations - some may be placeholders or future features
- The master_orchestrator_agent serves as the primary entry point for all agent coordination