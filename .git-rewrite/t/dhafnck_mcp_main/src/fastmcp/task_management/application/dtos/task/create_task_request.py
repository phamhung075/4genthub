"""Request DTO for creating a task with hierarchical storage support"""

from dataclasses import dataclass, field
from typing import List, Optional

from ....domain.enums.common_labels import CommonLabel, LabelValidator
from ....domain.enums.estimated_effort import EstimatedEffort
from ....domain.enums.agent_roles import AgentRole

def resolve_legacy_role(assignee: str) -> Optional[str]:
    """Resolve legacy role names to current ones"""
    # Simple mapping for legacy roles
    legacy_mapping = {
        "coding_agent": "senior_developer",
        "test_orchestrator_agent": "qa_engineer", 
        "system_architect_agent": "architect"
    }
    return legacy_mapping.get(assignee, assignee)


@dataclass
class CreateTaskRequest:
    """Request DTO for creating a task with git branch ID-centric approach"""
    # Required fields
    title: str
    git_branch_id: str  # uuid - Unique git branch identifier - contains all necessary context
    
    # Optional fields with defaults
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    details: str = ""
    estimated_effort: str = ""
    assignees: List[str] = field(default_factory=list)
    labels: List[str] = None
    due_date: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)  # List of task IDs this task depends on
    user_id: Optional[str] = None  # User identifier for task ownership
    
    def __post_init__(self):
        if self.labels is None:
            self.labels = []
        
        # Validate and suggest labels using CommonLabel enum
        if self.labels:
            validated_labels = []
            for label in self.labels:
                # Skip None or empty labels
                if not label:
                    continue
                
                # Ensure label is a string
                label_str = str(label).strip()
                if not label_str:
                    continue
                    
                if LabelValidator.is_valid_label(label_str):
                    validated_labels.append(label_str)
                else:
                    # Try to find a close match or suggest alternatives
                    suggestions = CommonLabel.suggest_labels(label_str)
                    if suggestions:
                        validated_labels.extend(suggestions[:1])  # Take first suggestion
                    else:
                        validated_labels.append(label_str)  # Keep original if no suggestions
            self.labels = validated_labels
        
        # Validate estimated effort using EstimatedEffort enum
        if self.estimated_effort:
            try:
                # Just validate the effort without storing the object
                EstimatedEffort(self.estimated_effort)
            except (ValueError, AttributeError) as e:
                # If validation fails, keep the original value
                # The effort will be validated at the domain layer
                pass
        
        # Validate assignees using AgentRole enum
        if self.assignees:
            validated_assignees = []
            for assignee in self.assignees:
                if assignee and assignee.strip():
                    # Try to resolve legacy role names
                    resolved_assignee = resolve_legacy_role(assignee)
                    if resolved_assignee:
                        # Ensure resolved assignee has @ prefix
                        if not resolved_assignee.startswith("@"):
                            resolved_assignee = f"@{resolved_assignee}"
                        validated_assignees.append(resolved_assignee)
                    elif AgentRole.is_valid_role(assignee):
                        # Ensure valid agent role has @ prefix
                        if not assignee.startswith("@"):
                            assignee = f"@{assignee}"
                        validated_assignees.append(assignee)
                    elif assignee.startswith("@"):  # Already has @ prefix, keep as is
                        validated_assignees.append(assignee)
                    else:
                        # Keep original if not a valid role but not empty
                        validated_assignees.append(assignee)
            self.assignees = validated_assignees 