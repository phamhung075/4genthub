# Agent Capability Matrix - Optimization Plan

**Date**: 2025-09-09  
**Goal**: Eliminate redundancy, clarify responsibilities, optimize to ~30 agents

## Current vs. Optimized Agent Structure

### ❌ AGENTS TO MERGE/REMOVE (12 agents → consolidated into others)

| Current Agent | Merge Into | Reason |
|--------------|------------|---------|
| `tech_spec_agent` | `documentation-agent` | Same role, different doc types |
| `prd_architect_agent` | `documentation-agent` | Same role, different doc types |
| `mcp_researcher_agent` | `deep-research-agent` | Too narrow, MCP is just one research area |
| `idea_generation_agent` | `creative-ideation-agent` (new) | Artificial split of creative process |
| `idea_refinement_agent` | `creative-ideation-agent` (new) | Artificial split of creative process |
| `seo_sem_agent` | `marketing_orchestrator_agent` | Too granular, part of marketing |
| `growth_hacking_idea_agent` | `marketing_orchestrator_agent` | Too granular, part of marketing |
| `content_strategy_agent` | `marketing_orchestrator_agent` | Too granular, part of marketing |
| `remediation_agent` | `debugger-agent` | Remediation is part of debugging |
| `swarm_scaler_agent` | `devops-agent` | Too specific, scaling is DevOps |
| `adaptive_deployment_strategist_agent` | `devops-agent` | Deployment is core DevOps |
| `mcp_configuration_agent` | `devops-agent` | Configuration is DevOps |

### ✅ AGENTS TO RENAME (Better clarity)

| Current Name | New Name | Reason |
|-------------|----------|---------|
| `master-orchestrator-agent` | `master-orchestrator-agent` | "Uber" is unclear |
| `brainjs_ml_agent` | `ml-specialist-agent` | Too library-specific |
| `ui_designer_expert_shadcn_agent` | `shadcn-ui-expert-agent` | Too framework-specific |

### ✅ AGENTS TO KEEP (Core specialists - 27 agents)

#### Tier 1: Master Coordinators (3)
| Agent | Primary Role | Delegates To |
|-------|-------------|--------------|
| `master-orchestrator-agent` | Top-level project coordination | All orchestrators |
| `task-planning-agent` | Task breakdown and assignment | All specialists |
| `project-initiator-agent` | Project setup and initialization | Setup specialists |

#### Tier 2: Domain Orchestrators (3)
| Agent | Domain | Coordinates |
|-------|--------|------------|
| `test-orchestrator-agent` | Testing | All test types |
| `marketing_orchestrator_agent` | Marketing | All marketing activities |
| `system-architect-agent` | Architecture | System design |

#### Tier 3: Implementation Specialists (10)
| Agent | Specialization | Creates |
|-------|---------------|---------|
| `coding-agent` | Code implementation | Source code |
| `debugger-agent` | Bug fixing + remediation | Fixes |
| `code-reviewer-agent` | Code quality | Reviews |
| `prototyping-agent` | Rapid prototypes | POCs |
| `documentation-agent` | All documentation | Docs, specs, PRDs |
| `shadcn-ui-expert-agent` | UI/UX implementation | UI components |
| `design-system-agent` | Design patterns | Design systems |
| `ml-specialist-agent` | Machine learning | ML models |
| `devops-agent` | Infrastructure + deployment | CI/CD, configs |
| `creative-ideation-agent` | Ideas + refinement | Concepts |

#### Tier 4: Analysis Specialists (11)
| Agent | Analysis Type | Output |
|-------|--------------|--------|
| `security-auditor-agent` | Security analysis | Vulnerability reports |
| `compliance-scope-agent` | Regulatory analysis | Compliance reports |
| `ethical-review-agent` | Ethical analysis | Ethics assessments |
| `deep-research-agent` | Comprehensive research | Research reports |
| `technology-advisor-agent` | Tech recommendations | Tech decisions |
| `root-cause-analysis-agent` | Problem analysis | Root causes |
| `performance-load-tester-agent` | Performance analysis | Performance metrics |
| `health-monitor-agent` | System health | Health reports |
| `efficiency-optimization-agent` | Process optimization | Optimization plans |
| `analytics-setup-agent` | Analytics implementation | Tracking setup |
| `uat-coordinator-agent` | User acceptance | UAT results |

#### Tier 5: Specialized Support (3)
| Agent | Specialization | Purpose |
|-------|---------------|---------|
| `elicitation-agent` | Requirements gathering | Clarify needs |
| `branding-agent` | Brand identity | Brand strategy |
| `community-strategy-agent` | Community building | Community plans |
| `core-concept-agent` | Fundamental concepts | Core understanding |

## Optimized Agent Hierarchy

```
MASTER COORDINATION
├── master-orchestrator-agent (formerly uber_orchestrator)
│   ├── task-planning-agent
│   └── project-initiator-agent
│
DOMAIN ORCHESTRATORS  
├── test-orchestrator-agent
├── marketing_orchestrator_agent (absorbs 4 agents)
└── system-architect-agent
│
IMPLEMENTATION SPECIALISTS
├── Development Team
│   ├── coding-agent
│   ├── debugger-agent (absorbs remediation)
│   ├── code-reviewer-agent
│   └── prototyping-agent
│
├── Documentation Team
│   └── documentation-agent (absorbs tech_spec, prd_architect)
│
├── UI/Design Team
│   ├── shadcn-ui-expert-agent (formerly shadcn-specific)
│   └── design-system-agent
│
├── Infrastructure Team
│   └── devops-agent (absorbs swarm_scaler, deployment_strategist, mcp_config)
│
└── Innovation Team
    ├── ml-specialist-agent (formerly brainjs_ml)
    └── creative-ideation-agent (merges generation + refinement)
│
ANALYSIS SPECIALISTS
├── Security & Compliance
│   ├── security-auditor-agent
│   ├── compliance-scope-agent
│   └── ethical-review-agent
│
├── Research & Advisory
│   ├── deep-research-agent (absorbs mcp_researcher)
│   ├── technology-advisor-agent
│   └── root-cause-analysis-agent
│
└── Monitoring & Optimization
    ├── performance-load-tester-agent
    ├── health-monitor-agent
    ├── efficiency-optimization-agent
    └── analytics-setup-agent
```

## Clear Role Boundaries

### Who Creates Files?
**FILE CREATORS** (Can write/edit):
- `coding-agent` - Source code
- `documentation-agent` - All ai_docs
- `shadcn-ui-expert-agent` - UI components
- `test-orchestrator-agent` - Test files
- `devops-agent` - Config files
- `ml-specialist-agent` - ML models

### Who Only Analyzes?
**COORDINATORS** (Read-only):
- `master-orchestrator-agent` - Coordinates
- `task-planning-agent` - Plans
- `security-auditor-agent` - Audits
- `compliance-scope-agent` - Assesses
- `deep-research-agent` - Researches
- `root-cause-analysis-agent` - Analyzes

### Who Has Domain Tools?
**SPECIALISTS** with unique MCP tools:
- `shadcn-ui-expert-agent` - shadcn tools
- `test-orchestrator-agent` - browser tools
- `ml-specialist-agent` - ML frameworks
- `marketing_orchestrator_agent` - marketing tools
- `analytics-setup-agent` - analytics tools

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
- 32 agents total
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
