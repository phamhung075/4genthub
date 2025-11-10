"""AgentConfiguration Value Object"""

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AgentConfiguration:
    """Value object representing an agent's configuration.

    This is immutable and contains all the configuration data for an agent,
    including system prompt, tools, capabilities, and other settings.

    Attributes:
        system_prompt: The main system prompt for the agent
        tools: List of tool names available to the agent
        capabilities: Dict of capability names and their configurations
        rules: List of rules the agent must follow
        output_format: Dict specifying output formatting requirements
        metadata: Additional configuration metadata
    """

    system_prompt: str
    tools: tuple[str, ...] = field(default_factory=tuple)
    capabilities: dict[str, Any] = field(default_factory=dict)
    rules: tuple[str, ...] = field(default_factory=tuple)
    output_format: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.system_prompt or not self.system_prompt.strip():
            raise ValueError("Agent system_prompt cannot be empty")

        # Ensure tools and rules are tuples for immutability
        if isinstance(self.tools, list):
            object.__setattr__(self, 'tools', tuple(self.tools))
        if isinstance(self.rules, list):
            object.__setattr__(self, 'rules', tuple(self.rules))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentConfiguration":
        """Create AgentConfiguration from dictionary.

        Args:
            data: Dictionary containing configuration data

        Returns:
            AgentConfiguration instance

        Raises:
            ValueError: If required fields are missing
        """
        return cls(
            system_prompt=data.get("system_prompt", ""),
            tools=tuple(data.get("tools", [])),
            capabilities=data.get("capabilities", {}),
            rules=tuple(data.get("rules", [])),
            output_format=data.get("output_format", {}),
            metadata=data.get("metadata", {})
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary for storage.

        Returns:
            Dictionary representation of the configuration
        """
        return {
            "system_prompt": self.system_prompt,
            "tools": list(self.tools),
            "capabilities": self.capabilities,
            "rules": list(self.rules),
            "output_format": self.output_format,
            "metadata": self.metadata
        }

    def to_json(self) -> str:
        """Convert configuration to JSON string.

        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict(), indent=2)

    def with_system_prompt(self, system_prompt: str) -> "AgentConfiguration":
        """Create a new configuration with updated system prompt.

        Args:
            system_prompt: New system prompt

        Returns:
            New AgentConfiguration instance with updated prompt
        """
        return AgentConfiguration(
            system_prompt=system_prompt,
            tools=self.tools,
            capabilities=self.capabilities,
            rules=self.rules,
            output_format=self.output_format,
            metadata=self.metadata
        )

    def with_tools(self, tools: list[str]) -> "AgentConfiguration":
        """Create a new configuration with updated tools list.

        Args:
            tools: New list of tools

        Returns:
            New AgentConfiguration instance with updated tools
        """
        return AgentConfiguration(
            system_prompt=self.system_prompt,
            tools=tuple(tools),
            capabilities=self.capabilities,
            rules=self.rules,
            output_format=self.output_format,
            metadata=self.metadata
        )

    def merge_capabilities(self, new_capabilities: dict[str, Any]) -> "AgentConfiguration":
        """Create a new configuration with merged capabilities.

        Args:
            new_capabilities: Capabilities to merge

        Returns:
            New AgentConfiguration instance with merged capabilities
        """
        merged = {**self.capabilities, **new_capabilities}
        return AgentConfiguration(
            system_prompt=self.system_prompt,
            tools=self.tools,
            capabilities=merged,
            rules=self.rules,
            output_format=self.output_format,
            metadata=self.metadata
        )
