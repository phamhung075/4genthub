"""
Context Management Tool Descriptions Package

This module provides the unified context management tool descriptions for the MCP interface.
Supports the complete 4-tier hierarchy: Global → Project → Branch → Task
"""

from .manage_unified_context_description import (
    MANAGE_UNIFIED_CONTEXT_DESCRIPTION,
    MANAGE_UNIFIED_CONTEXT_PARAMETERS
)

# For backward compatibility, alias the unified descriptions
MANAGE_CONTEXT_DESCRIPTION = MANAGE_UNIFIED_CONTEXT_DESCRIPTION
MANAGE_CONTEXT_PARAMETERS = MANAGE_UNIFIED_CONTEXT_PARAMETERS

# Collect all context descriptions in the standard format expected by description_loader
CONTEXT_DESCRIPTIONS = {
    "manage_context": {
        "description": MANAGE_UNIFIED_CONTEXT_DESCRIPTION,
        "parameters": MANAGE_UNIFIED_CONTEXT_PARAMETERS
    },
    "manage_unified_context": {
        "description": MANAGE_UNIFIED_CONTEXT_DESCRIPTION,
        "parameters": MANAGE_UNIFIED_CONTEXT_PARAMETERS
    }
}

__all__ = [
    'MANAGE_CONTEXT_DESCRIPTION',
    'MANAGE_CONTEXT_PARAMETERS',
    'MANAGE_UNIFIED_CONTEXT_DESCRIPTION',
    'MANAGE_UNIFIED_CONTEXT_PARAMETERS',
    'CONTEXT_DESCRIPTIONS'
]