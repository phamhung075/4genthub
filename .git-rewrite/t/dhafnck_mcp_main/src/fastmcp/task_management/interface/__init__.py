"""Interface Layer - DDD Compliant Architecture"""

# Lazy import to avoid circular dependencies
# The DDDCompliantMCPTools will be imported when actually needed
__all__ = [
    "DDDCompliantMCPTools",
]

def __getattr__(name):
    """Lazy import for DDDCompliantMCPTools to avoid circular imports."""
    if name == "DDDCompliantMCPTools":
        from .ddd_compliant_mcp_tools import DDDCompliantMCPTools
        return DDDCompliantMCPTools
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'") 