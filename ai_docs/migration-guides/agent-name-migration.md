# Agent Name Migration Quick Reference

**Status**: Active Migration Guide
**Updated**: 2025-09-11
**Purpose**: Quick reference for migrating from deprecated agent names to active names

## Quick Migration Table

### Documentation Agents
| Deprecated Name | Active Name | Migration Status |
|-----------------|-------------|------------------|
| `tech_spec_agent` | `documentation_agent` | ✅ Use `documentation_agent` |
| `tech-spec-agent` | `@documentation_agent` | ✅ Use `@documentation_agent` |
| `prd_architect_agent` | `documentation_agent` | ✅ Use `documentation_agent` |
| `prd-architect-agent` | `@documentation_agent` | ✅ Use `@documentation_agent` |

### Research Agents
| Deprecated Name | Active Name | Migration Status |
|-----------------|-------------|------------------|
| `mcp_researcher_agent` | `deep_research_agent` | ✅ Use `deep_research_agent` |
| `mcp-researcher-agent` | `@deep_research_agent` | ✅ Use `@deep_research_agent` |

### Creative Agents  
| Deprecated Name | Active Name | Migration Status |
|-----------------|-------------|------------------|
| `idea_generation_agent` | `creative_ideation_agent` | ✅ Use `creative_ideation_agent` |
| `idea-generation-agent` | `@creative_ideation_agent` | ✅ Use `@creative_ideation_agent` |
| `idea_refinement_agent` | `creative_ideation_agent` | ✅ Use `creative_ideation_agent` |
| `idea-refinement-agent` | `@creative_ideation_agent` | ✅ Use `@creative_ideation_agent` |

### Marketing Agents
| Deprecated Name | Active Name | Migration Status |
|-----------------|-------------|------------------|
| `seo_sem_agent` | `marketing_strategy_orchestrator_agent` | ✅ Use `marketing_strategy_orchestrator_agent` |
| `seo-sem-agent` | `@marketing_strategy_orchestrator_agent` | ✅ Use `@marketing_strategy_orchestrator_agent` |
| `growth_hacking_idea_agent` | `marketing_strategy_orchestrator_agent` | ✅ Use `marketing_strategy_orchestrator_agent` |
| `growth-hacking-idea-agent` | `@marketing_strategy_orchestrator_agent` | ✅ Use `@marketing_strategy_orchestrator_agent` |
| `content_strategy_agent` | `marketing_strategy_orchestrator_agent` | ✅ Use `marketing_strategy_orchestrator_agent` |
| `content-strategy-agent` | `@marketing_strategy_orchestrator_agent` | ✅ Use `@marketing_strategy_orchestrator_agent` |

### DevOps Agents
| Deprecated Name | Active Name | Migration Status |
|-----------------|-------------|------------------|
| `swarm_scaler_agent` | `devops_agent` | ✅ Use `devops_agent` |
| `swarm-scaler-agent` | `@devops_agent` | ✅ Use `@devops_agent` |
| `adaptive_deployment_strategist_agent` | `devops_agent` | ✅ Use `devops_agent` |
| `adaptive-deployment-strategist-agent` | `@devops_agent` | ✅ Use `@devops_agent` |
| `mcp_configuration_agent` | `devops_agent` | ✅ Use `devops_agent` |
| `mcp-configuration-agent` | `@devops_agent` | ✅ Use `@devops_agent` |

### Debug Agents
| Deprecated Name | Active Name | Migration Status |
|-----------------|-------------|------------------|
| `remediation_agent` | `debugger_agent` | ✅ Use `debugger_agent` |
| `remediation-agent` | `@debugger_agent` | ✅ Use `@debugger_agent` |

### Renamed Agents
| Deprecated Name | Active Name | Migration Status |
|-----------------|-------------|------------------|
| `brainjs_ml_agent` | `ml_specialist_agent` | ✅ Use `ml_specialist_agent` |
| `brainjs-ml-agent` | `@ml_specialist_agent` | ✅ Use `@ml_specialist_agent` |
| `ui_designer_expert_shadcn_agent` | `ui_specialist_agent` | ✅ Use `ui_specialist_agent` |
| `ui-designer-expert-shadcn-agent` | `@ui_specialist_agent` | ✅ Use `@ui_specialist_agent` |

## Migration Steps

### 1. Find and Replace in Code
```bash
# Search for deprecated agent names in your codebase
grep -r "tech_spec_agent" .
grep -r "prd_architect_agent" .
grep -r "mcp_researcher_agent" .
# ... etc for other deprecated names

# Replace with active names
sed -i 's/tech_spec_agent/@documentation_agent/g' **/*.py
sed -i 's/prd_architect_agent/@documentation_agent/g' **/*.py
# ... etc for other replacements
```

### 2. Update Configuration Files
```yaml
# Before
agents:
  documentation: tech_spec_agent
  research: mcp_researcher_agent
  creative: idea_generation_agent

# After  
agents:
  documentation: @documentation_agent
  research: @deep_research_agent
  creative: @creative_ideation_agent
```

### 3. Update API Calls
```python
# Before
task = Task(subagent_type="tech_spec_agent", ...)
response = call_agent("prd_architect_agent", task)

# After
task = Task(subagent_type="@documentation_agent", ...)
response = call_agent("@documentation_agent", task)
```

### 4. Update Documentation
```markdown
<!-- Before -->
Use the `tech_spec_agent` for technical specifications.
The `mcp_researcher_agent` handles research tasks.

<!-- After -->
Use the `@documentation_agent` for technical specifications.
The `@deep_research_agent` handles research tasks.
```

## Automated Migration Tools

### Check for Deprecated Usage
```python
from fastmcp.task_management.application.use_cases.agent_mappings import is_deprecated_agent

# Check if agent names in your code are deprecated
agent_names = ["tech_spec_agent", "@documentation_agent", "unknown_agent"]
for name in agent_names:
    if is_deprecated_agent(name):
        print(f"⚠️  {name} is deprecated")
    else:
        print(f"✅ {name} is active")
```

### Resolve Deprecated Names
```python
from fastmcp.task_management.application.use_cases.agent_mappings import resolve_agent_name

# Automatically resolve deprecated names
deprecated_names = ["tech_spec_agent", "mcp_researcher_agent", "idea_generation_agent"]
for name in deprecated_names:
    active_name = resolve_agent_name(name)
    print(f"Migrate: {name} → {active_name}")
```

## Migration Script Example

```python
#!/usr/bin/env python3
"""
Agent Name Migration Script
Automatically find and report deprecated agent usage
"""

import os
import re
from pathlib import Path
from fastmcp.task_management.application.use_cases.agent_mappings import (
    DEPRECATED_AGENT_MAPPINGS,
    resolve_agent_name,
    is_deprecated_agent
)

def find_deprecated_usage(directory: str = "."):
    """Find deprecated agent usage in code files"""
    deprecated_usage = []
    
    for root, dirs, files in os.walk(directory):
        # Skip .git, __pycache__, etc.
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for file in files:
            if file.endswith(('.py', '.yaml', '.yml', '.json')):
                file_path = Path(root) / file
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check for each deprecated agent name
                for deprecated_name in DEPRECATED_AGENT_MAPPINGS.keys():
                    if deprecated_name in content:
                        active_name = resolve_agent_name(deprecated_name)
                        deprecated_usage.append({
                            'file': str(file_path),
                            'deprecated_name': deprecated_name,
                            'active_name': active_name
                        })
    
    return deprecated_usage

def generate_migration_report():
    """Generate migration report"""
    usage = find_deprecated_usage()
    
    if not usage:
        print("✅ No deprecated agent names found!")
        return
    
    print("⚠️  Deprecated Agent Usage Found:")
    print("=" * 50)
    
    for item in usage:
        print(f"File: {item['file']}")
        print(f"  Deprecated: {item['deprecated_name']}")
        print(f"  Replace with: {item['active_name']}")
        print()
    
    print(f"Total files with deprecated usage: {len(set(item['file'] for item in usage))}")
    print(f"Total deprecated references: {len(usage)}")

if __name__ == "__main__":
    generate_migration_report()
```

## Backward Compatibility

### Current Status
- ✅ **All deprecated names still work** - No breaking changes
- ✅ **Both formats supported** - Underscore and hyphen formats
- ✅ **Automatic resolution** - Deprecated names automatically map to active names
- ✅ **Function preservation** - All functionality maintained after consolidation

### Timeline
- **Phase 1** (Current): Deprecated names work with backward compatibility
- **Phase 2** (Future): Warnings added for deprecated usage  
- **Phase 3** (Future): Deprecated names removed (major version bump)

## Verification

### Test Your Migration
```python
# Test that your migrated code uses active agent names
from fastmcp.task_management.application.use_cases.agent_mappings import is_deprecated_agent

def verify_agent_names(agent_list):
    """Verify that agent names are not deprecated"""
    for agent_name in agent_list:
        if is_deprecated_agent(agent_name):
            print(f"❌ {agent_name} is deprecated - update required")
            return False
        else:
            print(f"✅ {agent_name} is active")
    return True

# Example usage
my_agents = ["@documentation_agent", "@deep_research_agent", "@creative_ideation_agent"]
if verify_agent_names(my_agents):
    print("🎉 All agent names are current!")
```

## Questions and Support

### Common Questions

**Q: Do I need to migrate immediately?**
A: No, deprecated names still work. However, migrating ensures better long-term compatibility.

**Q: Will my existing code break?**
A: No, all deprecated names are automatically resolved to active names.

**Q: Can I use both underscore and hyphen formats?**
A: Yes, both formats are supported: `@documentation_agent` (recommended) and `documentation-agent` (legacy).

**Q: How do I know if an agent name is deprecated?**
A: Use the `is_deprecated_agent()` function or check this migration guide.

### Need Help?

1. **Check the comprehensive documentation**: `/ai_docs/core-architecture/deprecated-agent-mappings.md`
2. **Review test examples**: `/dhafnck_mcp_main/src/tests/task_management/application/use_cases/agent_mappings_test.py`  
3. **Use the migration script** provided above to find deprecated usage
4. **Run tests** to ensure your migrations work correctly

## Related Resources

- **Full Documentation**: `/ai_docs/core-architecture/deprecated-agent-mappings.md`
- **Agent Architecture**: `/ai_docs/core-architecture/architecture.md`
- **API Documentation**: `/ai_docs/api-integration/agent-api.md`
- **Testing Guide**: `/ai_docs/testing-qa/agent-testing.md`