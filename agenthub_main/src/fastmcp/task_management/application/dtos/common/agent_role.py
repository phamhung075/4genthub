"""Definition of an agent role with specific rules and context"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AgentRole:
    """Definition of an agent role with specific rules and context"""

    name: str
    persona: str
    primary_focus: str
    rules: list[str]
    context_instructions: list[str]
    tools_guidance: list[str]
    output_format: str
    persona_icon: str | None = None
