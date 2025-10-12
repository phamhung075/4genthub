"""Rule Workflow Guidance Implementation

Provides comprehensive guidance for Rule Management operations.
"""

from typing import Any

from ..base import BaseWorkflowGuidance


class RuleWorkflowGuidance(BaseWorkflowGuidance):
    """Workflow guidance for Rule Management operations."""

    def generate_guidance(
        self, action: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Generate comprehensive workflow guidance for rule operations."""

        return {
            "current_state": self._determine_state(action, context),
            "rules": self._get_rule_rules(),
            "next_actions": self._get_next_actions(action, context),
            "hints": self._get_hints(action),
            "warnings": self._get_warnings(action),
            "examples": self._get_examples(action, context),
            "parameter_guidance": self._get_parameter_guidance(action),
        }

    def _determine_state(
        self, action: str, context: dict[str, Any] | None = None
    ) -> dict[str, str]:
        """Determine the current workflow state."""
        phase = {
            "list": "rule_listing",
            "backup": "rule_backup",
            "restore": "rule_restoration",
            "clean": "rule_cleanup",
            "info": "rule_information",
            "load_core": "core_rule_loading",
            "parse_rule": "rule_parsing",
            "analyze_hierarchy": "hierarchy_analysis",
            "get_dependencies": "dependency_analysis",
            "enhanced_info": "enhanced_information",
            "compose_nested_rules": "rule_composition",
            "resolve_rule_inheritance": "inheritance_resolution",
            "validate_rule_hierarchy": "hierarchy_validation",
            "build_hierarchy": "hierarchy_building",
            "load_nested": "nested_loading",
            "cache_status": "cache_inspection",
            "register_client": "client_registration",
            "authenticate_client": "client_authentication",
            "sync_client": "client_synchronization",
            "client_diff": "difference_calculation",
            "resolve_conflicts": "conflict_resolution",
            "client_status": "client_status_check",
            "client_analytics": "analytics_retrieval",
        }.get(action, "unknown")

        return {"phase": phase, "action": action, "context": "rule_management"}

    def _get_rule_rules(self) -> list[str]:
        """Get essential rules for rule management."""
        return [
            "📜 RULE: Rules define operational guidelines and constraints for the system",
            "🎯 RULE: Core rules are loaded from predefined system configurations",
            "🏗️ RULE: Rules can have hierarchical relationships and dependencies",
            "🔄 RULE: Rule inheritance allows child rules to extend parent rules",
            "✅ RULE: Rule hierarchy must be validated to prevent circular dependencies",
            "💾 RULE: Always backup rules before making significant changes",
            "🔍 RULE: Parse and analyze rules before applying them to the system",
            "🤝 RULE: Client synchronization ensures all connected clients have consistent rules",
        ]

    def _get_next_actions(
        self, action: str, context: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Get context-aware next actions with priorities."""
        target = context.get("target") if context else None

        next_actions = []

        if action == "list":
            next_actions.extend(
                [
                    {
                        "priority": "high",
                        "action": "Get detailed rule information",
                        "description": "View specific rule details and structure",
                        "example": {
                            "tool": "manage_rule",
                            "params": {"action": "info", "target": "rule_name"},
                        },
                    },
                    {
                        "priority": "medium",
                        "action": "Backup rules",
                        "description": "Create a backup before making changes",
                        "example": {
                            "tool": "manage_rule",
                            "params": {"action": "backup"},
                        },
                    },
                    {
                        "priority": "medium",
                        "action": "Analyze rule hierarchy",
                        "description": "Understand rule relationships and dependencies",
                        "example": {
                            "tool": "manage_rule",
                            "params": {"action": "analyze_hierarchy"},
                        },
                    },
                ]
            )

        elif action == "backup":
            next_actions.extend(
                [
                    {
                        "priority": "high",
                        "action": "Modify rules safely",
                        "description": "Now safe to make changes with backup available",
                        "example": {
                            "tool": "manage_rule",
                            "params": {
                                "action": "parse_rule",
                                "target": "new_rule",
                                "content": "rule_content",
                            },
                        },
                    },
                    {
                        "priority": "medium",
                        "action": "View backup status",
                        "description": "Confirm backup was successful",
                        "example": {
                            "tool": "manage_rule",
                            "params": {"action": "info", "target": "backup"},
                        },
                    },
                ]
            )

        elif action == "restore":
            next_actions.extend(
                [
                    {
                        "priority": "high",
                        "action": "Verify restoration",
                        "description": "Check that rules were restored correctly",
                        "example": {
                            "tool": "manage_rule",
                            "params": {"action": "list"},
                        },
                    },
                    {
                        "priority": "medium",
                        "action": "Validate rule hierarchy",
                        "description": "Ensure restored rules are valid",
                        "example": {
                            "tool": "manage_rule",
                            "params": {"action": "validate_rule_hierarchy"},
                        },
                    },
                ]
            )

        elif action == "load_core":
            next_actions.extend(
                [
                    {
                        "priority": "high",
                        "action": "List loaded rules",
                        "description": "See what core rules are now active",
                        "example": {
                            "tool": "manage_rule",
                            "params": {"action": "list"},
                        },
                    },
                    {
                        "priority": "medium",
                        "action": "Sync with clients",
                        "description": "Update connected clients with new rules",
                        "example": {
                            "tool": "manage_rule",
                            "params": {"action": "sync_client", "target": "client_id"},
                        },
                    },
                ]
            )

        elif action == "parse_rule":
            next_actions.extend(
                [
                    {
                        "priority": "high",
                        "action": "Validate parsed rule",
                        "description": "Check that the rule is valid",
                        "example": {
                            "tool": "manage_rule",
                            "params": {
                                "action": "validate_rule_hierarchy",
                                "target": target or "parsed_rule",
                            },
                        },
                    },
                    {
                        "priority": "medium",
                        "action": "Check dependencies",
                        "description": "Identify rule dependencies",
                        "example": {
                            "tool": "manage_rule",
                            "params": {
                                "action": "get_dependencies",
                                "target": target or "parsed_rule",
                            },
                        },
                    },
                ]
            )

        elif action == "register_client":
            next_actions.extend(
                [
                    {
                        "priority": "high",
                        "action": "Authenticate client",
                        "description": "Verify client credentials",
                        "example": {
                            "tool": "manage_rule",
                            "params": {
                                "action": "authenticate_client",
                                "target": "registered_client_id",
                            },
                        },
                    },
                    {
                        "priority": "high",
                        "action": "Sync rules to client",
                        "description": "Send current rules to the new client",
                        "example": {
                            "tool": "manage_rule",
                            "params": {
                                "action": "sync_client",
                                "target": "registered_client_id",
                            },
                        },
                    },
                ]
            )

        return next_actions

    def _get_hints(self, action: str) -> list[str]:
        """Get action-specific hints."""
        hints = {
            "list": [
                "💡 Review all active rules to understand system constraints",
                "🔍 Look for rules that might conflict with your intended changes",
                "📊 Consider the rule hierarchy and dependencies",
            ],
            "backup": [
                "💾 Backup creates a snapshot of the current rule state",
                "🕐 Include timestamp in backup name for easy identification",
                "📦 Store backups in a safe location",
            ],
            "restore": [
                "♻️ Restore overwrites current rules with backed up version",
                "⚠️ Any changes since backup will be lost",
                "✅ Always verify restoration was successful",
            ],
            "info": [
                "📋 Provides detailed information about specific rules",
                "🔍 Use target parameter to specify which rule to inspect",
                "📊 Shows rule structure, dependencies, and metadata",
            ],
            "load_core": [
                "🎯 Loads predefined system core rules",
                "🔄 This may override custom rules",
                "📋 Review loaded rules after operation",
            ],
            "parse_rule": [
                "✏️ Parses rule content into system format",
                "🔍 Validates rule syntax and structure",
                "⚠️ Check for conflicts with existing rules",
            ],
            "analyze_hierarchy": [
                "🏗️ Shows parent-child relationships between rules",
                "🔄 Identifies circular dependencies",
                "📊 Helps understand rule precedence",
            ],
            "validate_rule_hierarchy": [
                "✅ Ensures rule hierarchy is valid and consistent",
                "🚫 Detects circular dependencies",
                "⚠️ Identifies missing parent rules",
            ],
            "sync_client": [
                "🔄 Synchronizes rules with connected clients",
                "📡 Ensures all clients have consistent rule set",
                "⏱️ May take time for large rule sets",
            ],
            "cache_status": [
                "💾 Shows current cache state and statistics",
                "🔍 Helps identify performance issues",
                "🔄 Consider clearing cache if stale",
            ],
        }
        return hints.get(action, ["💡 Check action parameter for available operations"])

    def _get_warnings(self, action: str) -> list[str]:
        """Get action-specific warnings."""
        warnings = []

        if action == "restore":
            warnings.append("🚨 CRITICAL: This will overwrite all current rules!")
            warnings.append("⚠️ Any changes since the backup will be lost")
            warnings.append("💡 Consider backing up current rules first")

        elif action == "clean":
            warnings.append("⚠️ This will remove unused or invalid rules")
            warnings.append("📋 Some functionality may be affected")

        elif action == "load_core":
            warnings.append("🔄 This may override custom rules")
            warnings.append("💾 Backup current rules before loading core")

        elif action == "resolve_conflicts":
            warnings.append("⚠️ Conflict resolution may change rule behavior")
            warnings.append("📋 Review resolution results carefully")

        elif action == "compose_nested_rules":
            warnings.append("🏗️ Complex operation that may affect rule hierarchy")
            warnings.append("✅ Validate hierarchy after composition")

        return warnings

    def _get_examples(
        self, action: str, context: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Get action-specific examples."""
        examples = []

        if action == "list":
            examples.append(
                {
                    "description": "List all active rules",
                    "code": """manage_rule(
    action="list"
)""",
                }
            )

        elif action == "backup":
            examples.append(
                {
                    "description": "Create a backup of current rules",
                    "code": """manage_rule(
    action="backup",
    target="backup_20250711"
)""",
                }
            )

        elif action == "info":
            examples.append(
                {
                    "description": "Get information about a specific rule",
                    "code": """manage_rule(
    action="info",
    target="authentication_rule"
)""",
                }
            )

        elif action == "parse_rule":
            examples.append(
                {
                    "description": "Parse and validate a new rule",
                    "code": """manage_rule(
    action="parse_rule",
    target="new_security_rule",
    content="rule: enforce_https { require: protocol == 'https' }"
)""",
                }
            )

        elif action == "sync_client":
            examples.append(
                {
                    "description": "Synchronize rules with a client",
                    "code": """manage_rule(
    action="sync_client",
    target="client_abc123"
)""",
                }
            )

        return examples

    def _get_parameter_guidance(self, action: str) -> dict[str, dict[str, str]]:
        """Get parameter-specific guidance."""
        base_params = {
            "action": {
                "requirement": "REQUIRED",
                "format": "String (valid action name)",
                "tip": "Specify the rule operation to perform",
            }
        }

        action_params = {
            "list": {},
            "backup": {
                "target": {
                    "requirement": "OPTIONAL",
                    "format": "String",
                    "tip": "Backup name/identifier (e.g., 'backup_20250711')",
                }
            },
            "restore": {
                "target": {
                    "requirement": "OPTIONAL",
                    "format": "String",
                    "tip": "Backup to restore from",
                }
            },
            "info": {
                "target": {
                    "requirement": "OPTIONAL",
                    "format": "String",
                    "tip": "Rule name or 'backup' for backup info",
                }
            },
            "parse_rule": {
                "target": {
                    "requirement": "OPTIONAL",
                    "format": "String",
                    "tip": "Name for the parsed rule",
                },
                "content": {
                    "requirement": "OPTIONAL",
                    "format": "String (rule syntax)",
                    "tip": "Rule content to parse",
                },
            },
            "analyze_hierarchy": {
                "target": {
                    "requirement": "OPTIONAL",
                    "format": "String",
                    "tip": "Specific rule to analyze or empty for all",
                }
            },
            "get_dependencies": {
                "target": {
                    "requirement": "OPTIONAL",
                    "format": "String",
                    "tip": "Rule name to get dependencies for",
                }
            },
            "register_client": {
                "target": {
                    "requirement": "OPTIONAL",
                    "format": "String",
                    "tip": "Client identifier",
                },
                "content": {
                    "requirement": "OPTIONAL",
                    "format": "String (JSON)",
                    "tip": "Client registration data",
                },
            },
            "sync_client": {
                "target": {
                    "requirement": "OPTIONAL",
                    "format": "String",
                    "tip": "Client ID to sync with",
                }
            },
        }

        params = base_params.copy()
        if action in action_params:
            params.update(action_params[action])
        else:
            # Default parameters for actions not explicitly defined
            params.update(
                {
                    "target": {
                        "requirement": "OPTIONAL (default: '')",
                        "format": "String",
                        "tip": "Target for the action",
                    },
                    "content": {
                        "requirement": "OPTIONAL (default: '')",
                        "format": "String",
                        "tip": "Content for the action",
                    },
                }
            )

        return params
