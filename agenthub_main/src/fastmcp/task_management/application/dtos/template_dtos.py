"""Template Data Transfer Objects"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from datetime import datetime


@dataclass
class TemplateCreateDTO:
    """DTO for creating a new template"""
    name: str
    description: str
    content: str
    template_type: str
    category: str
    priority: str = "medium"
    compatible_agents: List[str] = None
    file_patterns: List[str] = None
    variables: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.compatible_agents is None:
            self.compatible_agents = ["*"]
        if self.file_patterns is None:
            self.file_patterns = []
        if self.variables is None:
            self.variables = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TemplateUpdateDTO:
    """DTO for updating an existing template"""
    template_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    template_type: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    compatible_agents: Optional[List[str]] = None
    file_patterns: Optional[List[str]] = None
    variables: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


@dataclass
class TemplateResponseDTO:
    """DTO for template response"""
    id: str
    name: str
    description: str
    content: str
    template_type: str
    category: str
    status: str
    priority: str
    compatible_agents: List[str]
    file_patterns: List[str]
    variables: List[str]
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str
    version: int
    is_active: bool


@dataclass
class TemplateListDTO:
    """DTO for template list response"""
    templates: List[TemplateResponseDTO]
    total_count: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool


@dataclass
class TemplateRenderRequestDTO:
    """DTO for template render request"""
    template_id: str
    variables: Dict[str, Any]
    task_context: Optional[Dict[str, Any]] = None
    output_path: Optional[str] = None
    cache_strategy: str = "default"
    force_regenerate: bool = False


@dataclass
class TemplateRenderResponseDTO:
    """DTO for template render response"""
    content: str
    template_id: str
    variables_used: Dict[str, Any]
    generated_at: str
    generation_time_ms: int
    cache_hit: bool
    output_path: Optional[str] = None


@dataclass
class TemplateSuggestionDTO:
    """DTO for template suggestion"""
    template_id: str
    name: str
    description: str
    template_type: str
    category: str
    priority: str
    suggestion_score: float
    suggestion_reason: str
    compatible_agents: List[str]
    file_patterns: List[str]
    variables: List[str]


@dataclass
class TemplateSuggestionRequestDTO:
    """DTO for template suggestion request"""
    task_context: Dict[str, Any]
    agent_type: Optional[str] = None
    file_patterns: Optional[List[str]] = None
    limit: int = 10


@dataclass
class TemplateUsageDTO:
    """DTO for template usage tracking following clean relationship chain"""
    template_id: str
    task_id: Optional[str] = None  # Contains all necessary context via task -> git_branch -> project -> user
    agent_name: Optional[str] = None
    variables_used: Dict[str, Any] = None
    output_path: Optional[str] = None
    generation_time_ms: int = 0
    cache_hit: bool = False
    used_at: Optional[str] = None
    
    def __post_init__(self):
        if self.variables_used is None:
            self.variables_used = {}
        if self.used_at is None:
            self.used_at = datetime.now(timezone.utc).isoformat()


@dataclass
class TemplateAnalyticsDTO:
    """DTO for template analytics following clean relationship chain"""
    template_id: Optional[str] = None
    usage_count: int = 0
    success_rate: float = 0.0
    avg_generation_time: float = 0.0
    total_generation_time: int = 0
    cache_hit_rate: float = 0.0
    most_used_variables: List[Dict[str, Any]] = None
    usage_by_agent: Dict[str, int] = None
    usage_by_task: Dict[str, int] = None  # Task usage instead of project (follows clean relationship chain)
    usage_over_time: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.most_used_variables is None:
            self.most_used_variables = []
        if self.usage_by_agent is None:
            self.usage_by_agent = {}
        if self.usage_by_task is None:
            self.usage_by_task = {}
        if self.usage_over_time is None:
            self.usage_over_time = []


@dataclass
class TemplateSearchDTO:
    """DTO for template search"""
    query: str
    template_type: Optional[str] = None
    category: Optional[str] = None
    agent_compatible: Optional[str] = None
    is_active: Optional[bool] = None
    limit: int = 50
    offset: int = 0


@dataclass
class TemplateValidationDTO:
    """DTO for template validation response"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    template_id: Optional[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


@dataclass
class TemplateCacheDTO:
    """DTO for template cache operations"""
    template_id: Optional[str] = None
    cache_key: Optional[str] = None
    operation: str = "get"  # get, set, delete, clear
    ttl: Optional[int] = None
    data: Optional[Dict[str, Any]] = None 