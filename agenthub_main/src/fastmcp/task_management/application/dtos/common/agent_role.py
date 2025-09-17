"""Definition of an agent role with specific rules and context"""

from dataclasses import dataclass
from typing import List, Optional

@dataclass
class AgentRole:
    """Definition of an agent role with specific rules and context"""
    name: str
    persona: str
    primary_focus: str
    rules: List[str]
    context_instructions: List[str]
    tools_guidance: List[str]
    output_format: str
    persona_icon: Optional[str] = None 