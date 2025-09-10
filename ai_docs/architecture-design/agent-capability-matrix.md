# Agent Capability Matrix - Optimization Plan

**Date**: 2025-09-09  
**Goal**: Eliminate redundancy, clarify responsibilities, optimize to ~30 agents

## Current vs. Optimized Agent Structure

### ❌ AGENTS TO MERGE/REMOVE (12 agents → consolidated into others)

| Current Agent | Merge Into | Reason |
|--------------|------------|---------|
| `tech_spec_agent` | `documentation_agent` | Same role, different doc types |
| `prd_architect_agent` | `documentation_agent` | Same role, different doc types |
| `mcp_researcher_agent` | `deep_research_agent` | Too narrow, MCP is just one research area |
| `idea_generation_agent` | `creative_ideation_agent` (new) | Artificial split of creative process |
| `idea_refinement_agent` | `creative_ideation_agent` (new) | Artificial split of creative process |
| `seo_sem_agent` | `marketing_orchestrator_agent` | Too granular, part of marketing |
| `growth_hacking_idea_agent` | `marketing_orchestrator_agent` | Too granular, part of marketing |
| `content_strategy_agent` | `marketing_orchestrator_agent` | Too granular, part of marketing |
| `remediation_agent` | `debugger_agent` | Remediation is part of debugging |
| `swarm_scaler_agent` | `devops_agent` | Too specific, scaling is DevOps |
| `adaptive_deployment_strategist_agent` | `devops_agent` | Deployment is core DevOps |
| `mcp_configuration_agent` | `devops_agent` | Configuration is DevOps |

### ✅ AGENTS TO RENAME (Better clarity)

| Current Name | New Name | Reason |
|-------------|----------|---------|
| `uber_orchestrator_agent` | `master_orchestrator_agent` | "Uber" is unclear |
| `brainjs_ml_agent` | `ml_specialist_agent` | Too library-specific |
| `ui_designer_expert_shadcn_agent` | `ui_specialist_agent` | Too framework-specific |

### ✅ AGENTS TO KEEP (Core specialists - 27 agents)

#### Tier 1: Master Coordinators (3)
| Agent | Primary Role | Delegates To |
|-------|-------------|--------------|
| `master_orchestrator_agent` | Top-level project coordination | All orchestrators |
| `task_planning_agent` | Task breakdown and assignment | All specialists |
| `project_initiator_agent` | Project setup and initialization | Setup specialists |

#### Tier 2: Domain Orchestrators (3)
| Agent | Domain | Coordinates |
|-------|--------|------------|
| `test_orchestrator_agent` | Testing | All test types |
| `marketing_orchestrator_agent` | Marketing | All marketing activities |
| `system_architect_agent` | Architecture | System design |

#### Tier 3: Implementation Specialists (10)
| Agent | Specialization | Creates |
|-------|---------------|---------|
| `coding_agent` | Code implementation | Source code |
| `debugger_agent` | Bug fixing + remediation | Fixes |
| `code_reviewer_agent` | Code quality | Reviews |
| `prototyping_agent` | Rapid prototypes | POCs |
| `documentation_agent` | All documentation | Docs, specs, PRDs |
| `ui_specialist_agent` | UI/UX implementation | UI components |
| `design_system_agent` | Design patterns | Design systems |
| `ml_specialist_agent` | Machine learning | ML models |
| `devops_agent` | Infrastructure + deployment | CI/CD, configs |
| `creative_ideation_agent` | Ideas + refinement | Concepts |

#### Tier 4: Analysis Specialists (11)
| Agent | Analysis Type | Output |
|-------|--------------|--------|
| `security_auditor_agent` | Security analysis | Vulnerability reports |
| `compliance_scope_agent` | Regulatory analysis | Compliance reports |
| `ethical_review_agent` | Ethical analysis | Ethics assessments |
| `deep_research_agent` | Comprehensive research | Research reports |
| `technology_advisor_agent` | Tech recommendations | Tech decisions |
| `root_cause_analysis_agent` | Problem analysis | Root causes |
| `performance_load_tester_agent` | Performance analysis | Performance metrics |
| `health_monitor_agent` | System health | Health reports |
| `efficiency_optimization_agent` | Process optimization | Optimization plans |
| `analytics_setup_agent` | Analytics implementation | Tracking setup |
| `uat_coordinator_agent` | User acceptance | UAT results |

#### Tier 5: Specialized Support (3)
| Agent | Specialization | Purpose |
|-------|---------------|---------|
| `elicitation_agent` | Requirements gathering | Clarify needs |
| `branding_agent` | Brand identity | Brand strategy |
| `community_strategy_agent` | Community building | Community plans |
| `core_concept_agent` | Fundamental concepts | Core understanding |

## Optimized Agent Hierarchy

```
MASTER COORDINATION
├── master_orchestrator_agent (formerly uber_orchestrator)
│   ├── task_planning_agent
│   └── project_initiator_agent
│
DOMAIN ORCHESTRATORS  
├── test_orchestrator_agent
├── marketing_orchestrator_agent (absorbs 4 agents)
└── system_architect_agent
│
IMPLEMENTATION SPECIALISTS
├── Development Team
│   ├── coding_agent
│   ├── debugger_agent (absorbs remediation)
│   ├── code_reviewer_agent
│   └── prototyping_agent
│
├── Documentation Team
│   └── documentation_agent (absorbs tech_spec, prd_architect)
│
├── UI/Design Team
│   ├── ui_specialist_agent (formerly shadcn-specific)
│   └── design_system_agent
│
├── Infrastructure Team
│   └── devops_agent (absorbs swarm_scaler, deployment_strategist, mcp_config)
│
└── Innovation Team
    ├── ml_specialist_agent (formerly brainjs_ml)
    └── creative_ideation_agent (merges generation + refinement)
│
ANALYSIS SPECIALISTS
├── Security & Compliance
│   ├── security_auditor_agent
│   ├── compliance_scope_agent
│   └── ethical_review_agent
│
├── Research & Advisory
│   ├── deep_research_agent (absorbs mcp_researcher)
│   ├── technology_advisor_agent
│   └── root_cause_analysis_agent
│
└── Monitoring & Optimization
    ├── performance_load_tester_agent
    ├── health_monitor_agent
    ├── efficiency_optimization_agent
    └── analytics_setup_agent
```

## Clear Role Boundaries

### Who Creates Files?
**FILE CREATORS** (Can write/edit):
- `coding_agent` - Source code
- `documentation_agent` - All ai_docs
- `ui_specialist_agent` - UI components
- `test_orchestrator_agent` - Test files
- `devops_agent` - Config files
- `ml_specialist_agent` - ML models

### Who Only Analyzes?
**COORDINATORS** (Read-only):
- `master_orchestrator_agent` - Coordinates
- `task_planning_agent` - Plans
- `security_auditor_agent` - Audits
- `compliance_scope_agent` - Assesses
- `deep_research_agent` - Researches
- `root_cause_analysis_agent` - Analyzes

### Who Has Domain Tools?
**SPECIALISTS** with unique MCP tools:
- `ui_specialist_agent` - shadcn tools
- `test_orchestrator_agent` - browser tools
- `ml_specialist_agent` - ML frameworks
- `marketing_orchestrator_agent` - marketing tools
- `analytics_setup_agent` - analytics tools

## Migration Plan

### Phase 1: Consolidation (Week 1)
1. Merge documentation agents (3→1)
2. Merge research agents (2→1)  
3. Merge idea agents (2→1)
4. Merge marketing agents (4→1)

### Phase 2: Integration (Week 2)
1. Merge remediation into debugger
2. Merge scaling/deployment into devops (3→1)
3. Update all agent references

### Phase 3: Renaming (Week 3)
1. Rename uber_orchestrator
2. Rename brainjs_ml_agent
3. Rename shadcn_ui_agent
4. Update all code references

### Phase 4: Testing (Week 4)
1. Test each consolidated agent
2. Verify delegation patterns
3. Update documentation

## Success Metrics

### Before Optimization
- 42 agents total
- 12+ redundant agents
- Unclear boundaries
- Confusing names

### After Optimization  
- 30 agents total (-28% reduction)
- Zero redundancy
- Clear role boundaries
- Consistent naming
- Improved performance

## Benefits

1. **Reduced Complexity**: 28% fewer agents to maintain
2. **Clear Responsibilities**: No overlap or confusion
3. **Better Performance**: Less agent switching overhead
4. **Easier Onboarding**: Clear hierarchy and roles
5. **Maintainability**: Consistent patterns and naming