"""Template Domain Enums"""

from enum import Enum
from ..value_objects.priority import PriorityLevel


class TemplateType(Enum):
    """Template type enumeration"""
    TASK = "task"
    PROJECT = "project"
    WORKFLOW = "workflow"
    DOCUMENTATION = "documentation"
    CODE = "code"
    CONFIGURATION = "configuration"
    SCRIPT = "script"
    REPORT = "report"
    EMAIL = "email"
    NOTIFICATION = "notification"
    CUSTOM = "custom"


class TemplateCategory(Enum):
    """Template category enumeration"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    DOCUMENTATION = "documentation"
    COMMUNICATION = "communication"
    ANALYSIS = "analysis"
    REPORTING = "reporting"
    AUTOMATION = "automation"
    MONITORING = "monitoring"
    SECURITY = "security"
    MAINTENANCE = "maintenance"
    GENERAL = "general"


class TemplateStatus(Enum):
    """Template status enumeration"""
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    UNDER_REVIEW = "under_review"
    PENDING_APPROVAL = "pending_approval"


class TemplatePriority(Enum):
    """Template priority enumeration"""
    LOW = PriorityLevel.LOW.label
    MEDIUM = PriorityLevel.MEDIUM.label
    HIGH = PriorityLevel.HIGH.label
    CRITICAL = PriorityLevel.CRITICAL.label


class CacheStrategy(Enum):
    """Cache strategy enumeration"""
    DEFAULT = "default"
    AGGRESSIVE = "aggressive"
    MINIMAL = "minimal"
    NONE = "none"
    CUSTOM = "custom"


class TemplateCompatibility(Enum):
    """Template compatibility enumeration"""
    ALL = "all"
    SPECIFIC = "specific"
    NONE = "none"


class TemplateValidationStatus(Enum):
    """Template validation status enumeration"""
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"
    NOT_VALIDATED = "not_validated"


class TemplateRenderStatus(Enum):
    """Template render status enumeration"""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    PENDING = "pending"
    CANCELLED = "cancelled" 