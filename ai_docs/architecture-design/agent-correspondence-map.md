# Agent Correspondence Map

## Overview
This document maps the correspondence between:
- `.claude/agents/` - Agent capability descriptions and calling conditions
- `agenthub_main/agent-library/agents/` - Actual agent implementations

## Status: 2025-09-11

### ✅ Agents with Both Description and Implementation (33 agents)

| .claude/agents Description | agent-library Implementation | Status |
|---------------------------|------------------------------|---------|
| analytics-setup-agent.md | analytics-setup-agent/ | ✅ Match |
| branding-agent.md | branding-agent/ | ✅ Match |
| code-reviewer-agent.md | code-reviewer-agent/ | ✅ Match |
| coding-agent.md | coding-agent/ | ✅ Match |
| community-strategy-agent.md | community-strategy-agent/ | ✅ Match |
| compliance-scope-agent.md | compliance-scope-agent/ | ✅ Match |
| core-concept-agent.md | core-concept-agent/ | ✅ Match |
| debugger-agent.md | debugger-agent/ | ✅ Match |
| deep-research-agent.md | deep-research-agent/ | ✅ Match |
| design-system-agent.md | design-system-agent/ | ✅ Match |
| devops-agent.md | devops-agent/ | ✅ Match |
| documentation-agent.md | documentation-agent/ | ✅ Match |
| efficiency-optimization-agent.md | efficiency-optimization-agent/ | ✅ Match |
| elicitation-agent.md | elicitation-agent/ | ✅ Match |
| ethical-review-agent.md | ethical-review-agent/ | ✅ Match |
| health-monitor-agent.md | health-monitor-agent/ | ✅ Match |
| llm-ai-agents-and-eng-research.md | llm-ai-agents-research/ | ✅ Name variation |
| marketing-strategy-orchestrator-agent.md | marketing-strategy-orchestrator-agent/ | ✅ Match |
| master-orchestrator-agent.md | master-orchestrator-agent/ | ✅ Match (renamed from uber_orchestrator) |
| performance-load-tester-agent.md | performance-load-tester-agent/ | ✅ Match |
| project-initiator-agent.md | project-initiator-agent/ | ✅ Match |
| prototyping-agent.md | prototyping-agent/ | ✅ Match |
| root-cause-analysis-agent.md | root-cause-analysis-agent/ | ✅ Match |
| security-auditor-agent.md | security-auditor-agent/ | ✅ Match |
| system-architect-agent.md | system-architect-agent/ | ✅ Match |
| task-planning-agent.md | task-planning-agent/ | ✅ Match |
| technology-advisor-agent.md | technology-advisor-agent/ | ✅ Match |
| test-orchestrator-agent.md | test-orchestrator-agent/ | ✅ Match |
| uat-coordinator-agent.md | uat-coordinator-agent/ | ✅ Match |
| ui-specialist-agent.md | ui-specialist-agent/ | ✅ Match (renamed from ui_designer_expert_shadcn) |

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
| creative-ideation-agent/ | Creative ideation | Similar to idea_generation_agent |
| ml-specialist-agent/ | ML specialization | Similar to brainjs_ml_agent |

## Recommendations

1. **High Priority**:
   - Implement `claude-code-troubleshooter` in agent-library
   - Implement `mcp_configuration_agent` in agent-library
   - Implement `meta-agent` in agent-library

2. **Consolidation Opportunities**:
   - Merge `creative-ideation-agent` with `idea_generation_agent`
   - Merge `ml-specialist-agent` with `brainjs_ml_agent`

3. **Naming Standardization**:
   - `llm-ai-agents-and-eng-research.md` → Consider renaming to match `llm-ai-agents-research`

## Total Agent Count
- **33 agents** with both description and implementation (functional)
- **17 agents** with description only (pending implementation)
- **2 agents** with implementation only (need descriptions)
- **Total unique agents**: ~50 (with overlaps to consolidate)

## Notes
- The `.claude/agents/` directory stores agent capability descriptions and conditions for when to call each agent
- The `agent-library/` directory contains the actual agent implementations with YAML configurations
- Not all agents need implementations - some may be placeholders or future features
- The master-orchestrator-agent serves as the primary entry point for all agent coordination