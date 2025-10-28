"""Domain Value Objects for MCP Task Management"""

from .base_entity_id import EntityId
from .task_id import TaskId
from .subtask_id import SubtaskId
from .project_id import ProjectId
from .git_branch_id import GitBranchId
from .agent_id import AgentId
from .template_id import TemplateId
from .task_status import TaskStatus, TaskStatusEnum
from .priority import Priority
from .pagination import PaginationRequest, PaginationResult
from .progress_percentage import ProgressPercentage

# Enum imports (moved from domain/enums/)
from .agent_roles import AgentRole, get_role_metadata_from_yaml, resolve_legacy_role
from .common_labels import CommonLabel, LabelValidator
from .compliance_enums import (
    ComplianceLevel, ValidationResult, AuditLevel,
    ComplianceStatus, ValidationSeverity
)
from .error_severity import ErrorSeverity
from .estimated_effort import EstimatedEffort, EffortLevel
from .progress_enums import ProgressState
from .rule_enums import (
    RuleFormat, RuleType, ConflictResolution, InheritanceType,
    SyncOperation, ClientAuthMethod, SyncStatus
)
from .template_enums import (
    TemplateType, TemplateCategory, TemplateStatus, TemplatePriority,
    CacheStrategy, TemplateCompatibility, TemplateValidationStatus,
    TemplateRenderStatus
)

__all__ = [
    # Entity IDs and Core Value Objects
    'EntityId',
    'TaskId',
    'SubtaskId',
    'ProjectId',
    'GitBranchId',
    'AgentId',
    'TemplateId',
    'TaskStatus',
    'TaskStatusEnum',
    'Priority',
    'PaginationRequest',
    'PaginationResult',
    'ProgressPercentage',

    # Agent Roles
    'AgentRole',
    'get_role_metadata_from_yaml',
    'resolve_legacy_role',

    # Common Labels
    'CommonLabel',
    'LabelValidator',

    # Compliance & Validation
    'ComplianceLevel',
    'ValidationResult',
    'AuditLevel',
    'ComplianceStatus',
    'ValidationSeverity',

    # Error Handling
    'ErrorSeverity',

    # Effort Estimation
    'EstimatedEffort',
    'EffortLevel',

    # Progress
    'ProgressState',

    # Rules
    'RuleFormat',
    'RuleType',
    'ConflictResolution',
    'InheritanceType',
    'SyncOperation',
    'ClientAuthMethod',
    'SyncStatus',

    # Templates
    'TemplateType',
    'TemplateCategory',
    'TemplateStatus',
    'TemplatePriority',
    'CacheStrategy',
    'TemplateCompatibility',
    'TemplateValidationStatus',
    'TemplateRenderStatus',
] 