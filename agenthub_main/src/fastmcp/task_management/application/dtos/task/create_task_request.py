"""Request DTO for creating a task with hierarchical storage support"""

from __future__ import annotations

from dataclasses import dataclass, field

from ....domain.value_objects import (
    AgentRole,
    CommonLabel,
    EstimatedEffort,
    LabelValidator,
)


def resolve_legacy_role(assignee: str) -> str | None:
    """Resolve legacy role names to current ones"""
    # Map agent names to standardized role names
    legacy_mapping = {
        "coding-agent": "senior_developer",
        "test-orchestrator-agent": "qa_engineer",
        "system-architect-agent": "architect",
    }
    return legacy_mapping.get(assignee, assignee)


@dataclass
class CreateTaskRequest:
    """Request DTO for creating a task with git branch ID-centric approach"""

    # Required fields
    title: str
    git_branch_id: (
        str  # uuid - Unique git branch identifier - contains all necessary context
    )

    # Optional fields with defaults
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    details: str = ""
    estimated_effort: str = ""
    assignees: list[str] = field(default_factory=list)
    labels: list[str] = None
    due_date: str | None = None
    dependencies: list[str] = field(
        default_factory=list
    )  # List of task IDs this task depends on
    user_id: str | None = None  # User identifier for task ownership

    def __post_init__(self):
        if self.labels is None:
            self.labels = []

        # Ensure assignees is always a list, never a string
        if self.assignees is None:
            self.assignees = []
        elif isinstance(self.assignees, str):
            # Convert single string to list
            self.assignees = [self.assignees] if self.assignees.strip() else []

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
                        validated_labels.extend(
                            suggestions[:1]
                        )  # Take first suggestion
                    else:
                        validated_labels.append(
                            label_str
                        )  # Keep original if no suggestions
            self.labels = validated_labels

        # Validate estimated effort using EstimatedEffort enum
        if self.estimated_effort:
            try:
                # Just validate the effort without storing the object
                EstimatedEffort(self.estimated_effort)
            except (ValueError, AttributeError):
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
