"""Template Domain Service - Core Business Logic"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from datetime import datetime
import logging

from ..entities.template import Template, TemplateResult, TemplateRenderRequest, TemplateUsage
from ..value_objects.template_id import TemplateId
from ..enums.template_enums import TemplateType, TemplateCategory, TemplateStatus, TemplatePriority
from ..exceptions.template_exceptions import TemplateNotFoundError, TemplateValidationError, TemplateRenderError

logger = logging.getLogger(__name__)


class TemplateDomainService:
    """Domain service for template business logic and rules"""
    
    def validate_template(self, template: Template) -> List[str]:
        """Validate template according to business rules"""
        errors = []
        
        # Basic validation
        if not template.name.strip():
            errors.append("Template name cannot be empty")
        
        if not template.content.strip():
            errors.append("Template content cannot be empty")
        
        if not template.description.strip():
            errors.append("Template description cannot be empty")
        
        # Content validation
        if len(template.content) > 1000000:  # 1MB limit
            errors.append("Template content exceeds maximum size limit")
        
        # Name validation
        if len(template.name) > 255:
            errors.append("Template name exceeds maximum length")
        
        # Description validation
        if len(template.description) > 1000:
            errors.append("Template description exceeds maximum length")
        
        # Variable validation
        if template.variables:
            for var in template.variables:
                if not var.strip():
                    errors.append(f"Variable name cannot be empty")
                if not var.replace('_', '').replace('-', '').isalnum():
                    errors.append(f"Variable '{var}' contains invalid characters")
        
        # File pattern validation
        if template.file_patterns:
            for pattern in template.file_patterns:
                if not pattern.strip():
                    errors.append("File pattern cannot be empty")
        
        # Agent compatibility validation
        if not template.compatible_agents:
            errors.append("Template must be compatible with at least one agent")
        
        return errors
    
    def can_render_template(self, template: Template, agent_name: str, file_patterns: Optional[List[str]] = None) -> bool:
        """Check if template can be rendered by given agent and context"""
        # Check if template is active
        if not template.is_active or template.status != TemplateStatus.ACTIVE:
            return False
        
        # Check agent compatibility
        if not template.is_compatible_with_agent(agent_name):
            return False
        
        # Check file pattern compatibility
        if file_patterns and not template.matches_file_patterns(file_patterns):
            return False
        
        return True
    
    def calculate_template_score(
        self, 
        template: Template, 
        task_context: Dict[str, Any], 
        agent_name: str,
        file_patterns: Optional[List[str]] = None,
        usage_stats: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculate suggestion score for template based on context"""
        score = 0.0
        
        # Base score for active templates
        if template.is_active and template.status == TemplateStatus.ACTIVE:
            score += 10.0
        
        # Priority score
        if template.priority == TemplatePriority.CRITICAL:
            score += 20.0
        elif template.priority == TemplatePriority.HIGH:
            score += 15.0
        elif template.priority == TemplatePriority.MEDIUM:
            score += 5.0
        
        # Agent compatibility score
        if template.is_compatible_with_agent(agent_name):
            if "*" in template.compatible_agents:
                score += 20.0
            else:
                score += 30.0
        
        # Task type matching
        task_type = task_context.get('task_type', '')
        if task_type and template.template_type.value == task_type:
            score += 40.0
        elif task_type and task_type in template.template_type.value:
            score += 20.0
        
        # Category matching
        task_category = task_context.get('category', '')
        if task_category and template.category.value == task_category:
            score += 30.0
        elif task_category and task_category in template.category.value:
            score += 15.0
        
        # File pattern matching
        if file_patterns and template.matches_file_patterns(file_patterns):
            score += 25.0
        
        # Usage statistics score
        if usage_stats:
            usage_count = usage_stats.get('usage_count', 0)
            success_rate = usage_stats.get('success_rate', 0.0)
            avg_generation_time = usage_stats.get('avg_generation_time', 0)
            
            # Usage frequency score
            if usage_count > 100:
                score += 15.0
            elif usage_count > 50:
                score += 10.0
            elif usage_count > 10:
                score += 5.0
            
            # Success rate score
            score += success_rate * 10.0
            
            # Performance score (faster is better)
            if avg_generation_time < 100:  # ms
                score += 10.0
            elif avg_generation_time < 500:
                score += 5.0
        
        # Metadata matching
        if template.metadata:
            for key, value in task_context.items():
                if key in template.metadata and template.metadata[key] == value:
                    score += 5.0
        
        return max(0.0, score)
    
    def get_suggestion_reason(
        self, 
        template: Template, 
        task_context: Dict[str, Any], 
        score: float
    ) -> str:
        """Generate human-readable reason for template suggestion"""
        reasons = []
        
        # Priority reasons
        if template.priority == TemplatePriority.CRITICAL:
            reasons.append("Critical priority template")
        elif template.priority == TemplatePriority.HIGH:
            reasons.append("High priority template")
        
        # Type matching reasons
        task_type = task_context.get('task_type', '')
        if task_type and template.template_type.value == task_type:
            reasons.append(f"Exact match for {task_type} tasks")
        elif task_type and task_type in template.template_type.value:
            reasons.append(f"Good match for {task_type} tasks")
        
        # Category matching reasons
        task_category = task_context.get('category', '')
        if task_category and template.category.value == task_category:
            reasons.append(f"Perfect fit for {task_category} category")
        elif task_category and task_category in template.category.value:
            reasons.append(f"Suitable for {task_category} category")
        
        # Usage reasons
        if score > 80:
            reasons.append("Highly recommended based on usage patterns")
        elif score > 60:
            reasons.append("Recommended based on context match")
        elif score > 40:
            reasons.append("Good option for this type of task")
        
        if not reasons:
            reasons.append("Available template option")
        
        return "; ".join(reasons)
    
    def validate_render_request(self, request: TemplateRenderRequest) -> List[str]:
        """Validate template render request"""
        errors = []
        
        if not request.template_id:
            errors.append("Template ID is required")
        
        if not request.variables:
            errors.append("Variables are required")
        
        if request.cache_strategy not in ["default", "aggressive", "minimal", "none", "custom"]:
            errors.append("Invalid cache strategy")
        
        return errors
    
    def merge_template_variables(
        self, 
        template_variables: List[str], 
        request_variables: Dict[str, Any],
        task_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Merge variables from different sources with precedence rules"""
        merged_variables = {}
        
        # Start with default values for template variables
        for var in template_variables:
            merged_variables[var] = None
        
        # Add task context variables (lower precedence)
        if task_context:
            for key, value in task_context.items():
                if key in template_variables:
                    merged_variables[key] = value
        
        # Add request variables (higher precedence)
        for key, value in request_variables.items():
            merged_variables[key] = value
        
        return merged_variables
    
    def create_template_usage(
        self,
        template_id: TemplateId,
        task_id: Optional[str] = None,
        project_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        variables_used: Optional[Dict[str, Any]] = None,
        output_path: Optional[str] = None,
        generation_time_ms: int = 0,
        cache_hit: bool = False
    ) -> TemplateUsage:
        """Create template usage record"""
        return TemplateUsage(
            template_id=template_id,
            task_id=task_id,
            project_id=project_id,
            agent_name=agent_name,
            variables_used=variables_used or {},
            output_path=output_path,
            generation_time_ms=generation_time_ms,
            cache_hit=cache_hit,
            used_at=datetime.now(timezone.utc)
        )
    
    def should_cache_result(self, template: Template, request: TemplateRenderRequest) -> bool:
        """Determine if template result should be cached"""
        if request.force_regenerate:
            return False
        
        if request.cache_strategy == "none":
            return False
        
        if request.cache_strategy == "aggressive":
            return True
        
        if request.cache_strategy == "minimal":
            # Only cache for high-priority templates
            return template.priority in [TemplatePriority.HIGH, TemplatePriority.CRITICAL]
        
        # Default caching logic
        return True
    
    def get_cache_ttl(self, template: Template, request: TemplateRenderRequest) -> int:
        """Get cache time-to-live in seconds"""
        if request.cache_strategy == "aggressive":
            return 3600 * 24  # 24 hours
        
        if request.cache_strategy == "minimal":
            return 300  # 5 minutes
        
        # Default TTL based on template priority
        if template.priority == TemplatePriority.CRITICAL:
            return 3600 * 6  # 6 hours
        elif template.priority == TemplatePriority.HIGH:
            return 3600 * 2  # 2 hours
        else:
            return 3600  # 1 hour 