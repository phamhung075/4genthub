# Deprecated Agent Mappings System

**Status**: Active (Backward Compatibility Support)
**Created**: 2025-09-09
**Last Updated**: 2025-09-11
**Purpose**: Support deprecated agent names during migration period

## Overview

The Deprecated Agent Mappings system provides backward compatibility for agent names that have been consolidated, renamed, or deprecated during system evolution. This system ensures that existing code, configurations, and user workflows continue to function while providing a clear migration path to current agent names.

## System Architecture

### Core Components

1. **DEPRECATED_AGENT_MAPPINGS**: Dictionary mapping old agent names to new ones
2. **resolve_agent_name()**: Function to resolve deprecated names to active names
3. **is_deprecated_agent()**: Function to check if an agent name is deprecated

### File Locations

- **Implementation**: `/dhafnck_mcp_main/src/fastmcp/task_management/application/use_cases/agent_mappings.py`
- **Tests**: `/dhafnck_mcp_main/src/tests/task_management/application/use_cases/agent_mappings_test.py`

## Agent Consolidation Categories

### 1. Documentation Consolidation
Multiple specialized documentation agents have been consolidated into a single `documentation_agent`:

```python
# Deprecated → Active
"tech_spec_agent" → "documentation_agent"
"tech-spec-agent" → "@documentation_agent" 
"prd_architect_agent" → "documentation_agent"
"prd-architect-agent" → "@documentation_agent"
```

**Rationale**: Technical specifications and PRD (Product Requirements Document) creation are both documentation tasks that benefit from unified handling.

### 2. Research Consolidation
Research-related agents have been consolidated:

```python
# Deprecated → Active
"mcp_researcher_agent" → "deep_research_agent"
"mcp-researcher-agent" → "deep-research-agent"
```

**Rationale**: MCP-specific research is now handled by the more comprehensive deep research agent.

### 3. Creative Consolidation
Multiple creative agents have been unified:

```python
# Deprecated → Active
"idea_generation_agent" → "creative_ideation_agent"
"idea-generation-agent" → "creative-ideation-agent"
"idea_refinement_agent" → "creative_ideation_agent"
"idea-refinement-agent" → "creative-ideation-agent"
```

**Rationale**: Idea generation and refinement are closely related creative processes that benefit from unified context and workflow.

### 4. Marketing Consolidation
Marketing-related agents have been consolidated into a single orchestrator:

```python
# Deprecated → Active
"seo_sem_agent" → "marketing_strategy_orchestrator_agent"
"seo-sem-agent" → "marketing-strategy-orchestrator-agent"
"growth_hacking_idea_agent" → "marketing_strategy_orchestrator_agent"
"growth-hacking-idea-agent" → "marketing-strategy-orchestrator-agent"
"content_strategy_agent" → "marketing_strategy_orchestrator_agent"
"content-strategy-agent" → "marketing-strategy-orchestrator-agent"
```

**Rationale**: SEO/SEM, growth hacking, and content strategy are interconnected marketing disciplines that require coordinated strategy.

### 5. DevOps Consolidation
DevOps-related agents have been unified:

```python
# Deprecated → Active
"swarm_scaler_agent" → "devops_agent"
"swarm-scaler-agent" → "devops-agent"
"adaptive_deployment_strategist_agent" → "devops_agent"
"adaptive-deployment-strategist-agent" → "devops-agent"
"mcp_configuration_agent" → "devops_agent"
"mcp-configuration-agent" → "devops-agent"
```

**Rationale**: Scaling, deployment, and configuration are core DevOps responsibilities that benefit from unified management.

### 6. Debug Consolidation
Debugging and remediation agents have been consolidated:

```python
# Deprecated → Active
"remediation_agent" → "debugger_agent"
"remediation-agent" → "@debugger_agent"
```

**Rationale**: Bug remediation is a core debugging function that fits naturally within the debugger agent's responsibilities.

### 7. Renamings
Some agents have been renamed for clarity:

```python
# Deprecated → Active
"brainjs_ml_agent" → "ml_specialist_agent"
"brainjs-ml-agent" → "ml-specialist-agent"
"ui_designer_expert_shadcn_agent" → "ui_specialist_agent"
"ui-designer-expert-shadcn-agent" → "ui-specialist-agent"
```

**Rationale**: New names are more descriptive and not tied to specific technologies.

## Technical Implementation

### Name Resolution Logic

```python
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
```

### Deprecation Detection

```python
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
```

## Format Handling

### Underscore and Hyphen Support
The system supports both naming conventions:

- **Underscore format**: `tech_spec_agent`
- **Hyphen format**: `tech-spec-agent`

Both formats are handled consistently:
- Input format is preserved when possible
- Deprecated names in either format map to the appropriate new format
- Mixed formats are normalized and resolved properly

### Edge Cases Handled

1. **Mixed separators**: `tech-spec_agent` → resolved properly
2. **Case sensitivity**: Only exact case matches are considered deprecated
3. **Special characters**: Names with special characters are returned unchanged
4. **Empty strings**: Handled gracefully
5. **Unicode characters**: Supported without normalization
6. **Whitespace**: Leading/trailing whitespace preserved

## Migration Path

### For Developers

1. **Update Code References**:
   ```python
   # Old
   task = Task(subagent_type="tech_spec_agent", ...)
   
   # New (Recommended)
   task = Task(subagent_type="documentation_agent", ...)
   ```

2. **Update Configuration Files**:
   ```yaml
   # Old
   default_agents:
     - tech_spec_agent
     - mcp_researcher_agent
   
   # New
   default_agents:
     - documentation_agent
     - deep_research_agent
   ```

3. **Update Documentation**:
   - Replace references to deprecated agent names
   - Update examples and tutorials
   - Modify integration guides

### For Users

1. **Command Line Usage**:
   ```bash
   # Old (still works)
   claude-code --agent tech_spec_agent
   
   # New (recommended)
   claude-code --agent documentation_agent
   ```

2. **API Calls**:
   ```python
   # Old (still works)
   response = call_agent("prd_architect_agent", task)
   
   # New (recommended)
   response = call_agent("documentation_agent", task)
   ```

## Backward Compatibility Guarantees

### What's Guaranteed

1. **Functional Compatibility**: All deprecated agent names continue to work
2. **Behavior Preservation**: Consolidated agents maintain the functionality of their deprecated predecessors
3. **API Stability**: Existing integrations continue to function without modification
4. **Format Flexibility**: Both underscore and hyphen formats are supported indefinitely

### What's Not Guaranteed

1. **Performance**: Deprecated name resolution has minimal overhead but active names are more efficient
2. **Future Features**: New capabilities may only be available through active agent names
3. **Documentation**: New documentation focuses on active agent names
4. **Examples**: New code examples use active agent names

## Monitoring and Analytics

### Deprecation Usage Tracking

To monitor usage of deprecated agent names and plan migration strategies:

1. **Logging**: All deprecated name resolutions are logged
2. **Metrics**: Usage statistics are collected for each deprecated name
3. **Alerts**: High-volume usage of deprecated names can trigger alerts
4. **Reporting**: Regular reports show deprecation usage patterns

### Migration Progress

Track migration progress with:

```python
# Example monitoring code
deprecated_usage = get_deprecated_agent_usage()
total_requests = get_total_agent_requests()
migration_progress = 1 - (deprecated_usage / total_requests)
```

## Testing Strategy

### Comprehensive Test Coverage

The test suite covers:

1. **All Deprecated Names**: Every name in DEPRECATED_AGENT_MAPPINGS is tested
2. **Both Formats**: Underscore and hyphen formats for each name
3. **Edge Cases**: Special characters, unicode, empty strings, whitespace
4. **Consistency**: resolve_agent_name and is_deprecated_agent consistency
5. **Idempotency**: Resolving a name multiple times produces consistent results

### Test Categories

1. **Structure Tests**: Verify DEPRECATED_AGENT_MAPPINGS format and content
2. **Resolution Tests**: Test resolve_agent_name functionality
3. **Detection Tests**: Test is_deprecated_agent functionality  
4. **Edge Case Tests**: Handle unusual inputs gracefully
5. **Consistency Tests**: Ensure function behavior alignment

## Future Considerations

### Deprecation Lifecycle

1. **Phase 1 - Active Deprecation** (Current):
   - Deprecated names work with backward compatibility
   - Warnings may be logged for deprecated usage
   - Documentation focuses on active names

2. **Phase 2 - Soft Removal** (Future):
   - Deprecated names still work but with warnings
   - Strong encouragement to migrate
   - Migration tools and automation provided

3. **Phase 3 - Hard Removal** (Future):
   - Deprecated names no longer supported
   - Breaking change with major version bump
   - Complete migration required

### Extension Points

The system is designed for easy extension:

1. **New Mappings**: Additional deprecated names can be added easily
2. **Complex Resolutions**: Support for more sophisticated mapping logic
3. **Dynamic Mappings**: Runtime configuration of deprecation mappings
4. **Migration Assistance**: Tools to help identify and migrate deprecated usage

## Best Practices

### For System Maintainers

1. **Document Changes**: Every addition to DEPRECATED_AGENT_MAPPINGS should be documented
2. **Test Coverage**: New mappings must include comprehensive test coverage
3. **Communication**: Deprecations should be communicated to users and developers
4. **Monitoring**: Track usage patterns to inform future decisions

### For Developers

1. **Use Active Names**: Always use active agent names in new code
2. **Check Deprecation**: Use is_deprecated_agent() to check names before use
3. **Update Legacy Code**: Gradually migrate deprecated names in existing code
4. **Test Both Formats**: Test code with both underscore and hyphen formats

### For Users

1. **Stay Current**: Use active agent names for better long-term compatibility
2. **Check Documentation**: Consult current documentation for agent capabilities
3. **Plan Migrations**: Gradually update configurations and scripts
4. **Monitor Usage**: Be aware of which agents are deprecated in your workflows

## Related Documentation

- **Agent Architecture**: `/ai_docs/core-architecture/architecture.md`
- **Task Management**: `/ai_docs/core-architecture/task-management.md`
- **API Integration**: `/ai_docs/api-integration/agent-api.md`
- **Migration Guides**: `/ai_docs/migration-guides/agent-migration.md`
- **Testing Guidelines**: `/ai_docs/testing-qa/agent-testing.md`

## Support and Questions

For questions about deprecated agent mappings:

1. **Check Test Files**: Comprehensive examples in test files
2. **Review Code**: Implementation is straightforward and well-documented
3. **Consult Documentation**: This document covers most use cases
4. **System Logs**: Check logs for deprecation warnings and usage patterns

## Version History

- **2025-09-09**: Initial implementation with agent consolidation mappings
- **2025-09-11**: Comprehensive documentation and test coverage added
- **2025-09-11**: Added migration guides and best practices documentation