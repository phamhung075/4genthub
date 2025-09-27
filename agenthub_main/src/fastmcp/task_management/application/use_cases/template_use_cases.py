"""Template Use Cases - Application Layer Business Logic"""

from typing import Dict, Any, List, Optional
import logging

from ...domain.entities.template import Template, TemplateResult, TemplateRenderRequest, TemplateUsage
from ...domain.value_objects.template_id import TemplateId
from ...domain.enums.template_enums import TemplateType, TemplateCategory, TemplateStatus, TemplatePriority
from ...domain.services.template_domain_service import TemplateDomainService
from ...domain.exceptions.template_exceptions import TemplateNotFoundError, TemplateValidationError, TemplateRenderError
from ..dtos.template_dtos import (
    TemplateCreateDTO, TemplateUpdateDTO, TemplateResponseDTO, TemplateListDTO,
    TemplateRenderRequestDTO, TemplateRenderResponseDTO, TemplateSuggestionDTO,
    TemplateSuggestionRequestDTO, TemplateUsageDTO, TemplateAnalyticsDTO,
    TemplateSearchDTO, TemplateValidationDTO
)

logger = logging.getLogger(__name__)


class TemplateUseCases:
    """Template use cases orchestrating business logic"""
    
    def __init__(
        self,
        template_repository,  # Will be injected from infrastructure
        template_domain_service: TemplateDomainService,
        template_engine_service,  # Will be injected from infrastructure
        cache_service=None,  # Optional cache service
    ):
        self.template_repository = template_repository
        self.template_domain_service = template_domain_service
        self.template_engine_service = template_engine_service
        self.cache_service = cache_service
    
    async def create_template(self, create_dto: TemplateCreateDTO) -> TemplateResponseDTO:
        """Create a new template"""
        try:
            # Create template entity
            template = Template(
                id=TemplateId.generate(),
                name=create_dto.name,
                description=create_dto.description,
                content=create_dto.content,
                template_type=TemplateType(create_dto.template_type),
                category=TemplateCategory(create_dto.category),
                status=TemplateStatus.ACTIVE,
                priority=TemplatePriority(create_dto.priority),
                compatible_agents=create_dto.compatible_agents,
                file_patterns=create_dto.file_patterns,
                variables=create_dto.variables,
                metadata=create_dto.metadata
                # Timestamps handled automatically by BaseTimestampEntity
            )
            
            # Validate template
            validation_errors = self.template_domain_service.validate_template(template)
            if validation_errors:
                raise TemplateValidationError(
                    "Template validation failed",
                    template.id.value,
                    validation_errors
                )
            
            # Save template
            saved_template = await self.template_repository.save(template)
            
            # Return response DTO
            return self._template_to_response_dto(saved_template)
            
        except Exception as e:
            logger.error(f"Failed to create template: {e}")
            raise
    
    async def get_template(self, template_id: str) -> TemplateResponseDTO:
        """Get template by ID"""
        try:
            template = await self.template_repository.get_by_id(TemplateId(template_id))
            if not template:
                raise TemplateNotFoundError(template_id)
            
            return self._template_to_response_dto(template)
            
        except Exception as e:
            logger.error(f"Failed to get template {template_id}: {e}")
            raise
    
    async def update_template(self, update_dto: TemplateUpdateDTO) -> TemplateResponseDTO:
        """Update existing template"""
        try:
            # Get existing template
            template = await self.template_repository.get_by_id(TemplateId(update_dto.template_id))
            if not template:
                raise TemplateNotFoundError(update_dto.template_id)
            
            # Update fields
            if update_dto.name is not None:
                template.name = update_dto.name
            if update_dto.description is not None:
                template.description = update_dto.description
            if update_dto.content is not None:
                template.update_content(update_dto.content)
            if update_dto.template_type is not None:
                template.template_type = TemplateType(update_dto.template_type)
            if update_dto.category is not None:
                template.category = TemplateCategory(update_dto.category)
            if update_dto.priority is not None:
                template.priority = TemplatePriority(update_dto.priority)
            if update_dto.compatible_agents is not None:
                template.compatible_agents = update_dto.compatible_agents
            if update_dto.file_patterns is not None:
                template.file_patterns = update_dto.file_patterns
            if update_dto.variables is not None:
                template.variables = update_dto.variables
            if update_dto.metadata is not None:
                template.update_metadata(update_dto.metadata)
            if update_dto.is_active is not None:
                if update_dto.is_active:
                    template.activate()
                else:
                    template.deactivate()
            
            # Validate updated template
            validation_errors = self.template_domain_service.validate_template(template)
            if validation_errors:
                raise TemplateValidationError(
                    "Template validation failed",
                    template.id.value,
                    validation_errors
                )
            
            # Save updated template
            updated_template = await self.template_repository.save(template)
            
            return self._template_to_response_dto(updated_template)
            
        except Exception as e:
            logger.error(f"Failed to update template {update_dto.template_id}: {e}")
            raise
    
    async def delete_template(self, template_id: str) -> bool:
        """Delete template"""
        try:
            template = await self.template_repository.get_by_id(TemplateId(template_id))
            if not template:
                raise TemplateNotFoundError(template_id)
            
            # Archive instead of hard delete
            template.archive()
            await self.template_repository.save(template)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete template {template_id}: {e}")
            raise
    
    async def list_templates(self, search_dto: TemplateSearchDTO) -> TemplateListDTO:
        """List templates with filtering and pagination"""
        try:
            templates, total_count = await self.template_repository.list_templates(
                template_type=search_dto.template_type,
                category=search_dto.category,
                agent_compatible=search_dto.agent_compatible,
                is_active=search_dto.is_active,
                limit=search_dto.limit,
                offset=search_dto.offset
            )
            
            template_dtos = [self._template_to_response_dto(t) for t in templates]
            
            return TemplateListDTO(
                templates=template_dtos,
                total_count=total_count,
                page=search_dto.offset // search_dto.limit + 1,
                page_size=search_dto.limit,
                has_next=(search_dto.offset + search_dto.limit) < total_count,
                has_previous=search_dto.offset > 0
            )
            
        except Exception as e:
            logger.error(f"Failed to list templates: {e}")
            raise
    
    async def render_template(self, render_dto: TemplateRenderRequestDTO) -> TemplateRenderResponseDTO:
        """Render template with variables"""
        try:
            # Get template
            template = await self.template_repository.get_by_id(TemplateId(render_dto.template_id))
            if not template:
                raise TemplateNotFoundError(render_dto.template_id)
            
            # Create render request
            render_request = TemplateRenderRequest(
                template_id=template.id,
                variables=render_dto.variables,
                task_context=render_dto.task_context,
                output_path=render_dto.output_path,
                cache_strategy=render_dto.cache_strategy,
                force_regenerate=render_dto.force_regenerate
            )
            
            # Validate render request
            validation_errors = self.template_domain_service.validate_render_request(render_request)
            if validation_errors:
                raise TemplateRenderError(
                    "Template render request validation failed",
                    template.id.value,
                    {"validation_errors": validation_errors}
                )
            
            # Render template
            result = await self.template_engine_service.render_template(render_request)
            
            # Track usage
            usage = self.template_domain_service.create_template_usage(
                template_id=template.id,
                variables_used=result.variables_used,
                output_path=result.output_path,
                generation_time_ms=result.generation_time_ms,
                cache_hit=result.cache_hit
            )
            await self.template_repository.save_usage(usage)
            
            return TemplateRenderResponseDTO(
                content=result.content,
                template_id=result.template_id.value,
                variables_used=result.variables_used,
                generated_at=result.generated_at.isoformat(),
                generation_time_ms=result.generation_time_ms,
                cache_hit=result.cache_hit,
                output_path=result.output_path
            )
            
        except Exception as e:
            logger.error(f"Failed to render template {render_dto.template_id}: {e}")
            raise
    
    async def suggest_templates(self, suggestion_dto: TemplateSuggestionRequestDTO) -> List[TemplateSuggestionDTO]:
        """Suggest templates based on context"""
        try:
            # Get all active templates
            templates, _ = await self.template_repository.list_templates(
                is_active=True,
                limit=1000  # Get all active templates
            )
            
            suggestions = []
            
            for template in templates:
                # Check if template can be rendered
                if not self.template_domain_service.can_render_template(
                    template, 
                    suggestion_dto.agent_type if suggestion_dto.agent_type else None,
                    suggestion_dto.file_patterns
                ):
                    continue
                
                # Get usage stats for scoring
                usage_stats = await self.template_repository.get_usage_stats(template.id)
                
                # Calculate score
                score = self.template_domain_service.calculate_template_score(
                    template,
                    suggestion_dto.task_context,
                    suggestion_dto.agent_type if suggestion_dto.agent_type else None,
                    suggestion_dto.file_patterns,
                    usage_stats
                )
                
                if score > 0:
                    reason = self.template_domain_service.get_suggestion_reason(
                        template,
                        suggestion_dto.task_context,
                        score
                    )
                    
                    suggestions.append(TemplateSuggestionDTO(
                        template_id=template.id.value,
                        name=template.name,
                        description=template.description,
                        template_type=template.template_type.value,
                        category=template.category.value,
                        priority=template.priority.value,
                        suggestion_score=score,
                        suggestion_reason=reason,
                        compatible_agents=template.compatible_agents,
                        file_patterns=template.file_patterns,
                        variables=template.variables
                    ))
            
            # Sort by score and return top suggestions
            suggestions.sort(key=lambda x: x.suggestion_score, reverse=True)
            return suggestions[:suggestion_dto.limit]
            
        except Exception as e:
            logger.error(f"Failed to suggest templates: {e}")
            raise
    
    async def validate_template(self, template_id: str) -> TemplateValidationDTO:
        """Validate template"""
        try:
            template = await self.template_repository.get_by_id(TemplateId(template_id))
            if not template:
                raise TemplateNotFoundError(template_id)
            
            errors = self.template_domain_service.validate_template(template)
            warnings = []  # Could add warning logic here
            
            return TemplateValidationDTO(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                template_id=template_id
            )
            
        except Exception as e:
            logger.error(f"Failed to validate template {template_id}: {e}")
            raise
    
    async def get_template_analytics(self, template_id: Optional[str] = None) -> TemplateAnalyticsDTO:
        """Get template analytics"""
        try:
            analytics_data = await self.template_repository.get_analytics(template_id)
            
            return TemplateAnalyticsDTO(
                template_id=template_id,
                usage_count=analytics_data.get('usage_count', 0),
                success_rate=analytics_data.get('success_rate', 0.0),
                avg_generation_time=analytics_data.get('avg_generation_time', 0.0),
                total_generation_time=analytics_data.get('total_generation_time', 0),
                cache_hit_rate=analytics_data.get('cache_hit_rate', 0.0),
                most_used_variables=analytics_data.get('most_used_variables', []),
                usage_by_agent=analytics_data.get('usage_by_agent', {}),
                usage_by_project=analytics_data.get('usage_by_project', {}),
                usage_over_time=analytics_data.get('usage_over_time', [])
            )
            
        except Exception as e:
            logger.error(f"Failed to get template analytics: {e}")
            raise
    
    def _template_to_response_dto(self, template: Template) -> TemplateResponseDTO:
        """Convert template entity to response DTO"""
        return TemplateResponseDTO(
            id=template.id.value,
            name=template.name,
            description=template.description,
            content=template.content,
            template_type=template.template_type.value,
            category=template.category.value,
            status=template.status.value,
            priority=template.priority.value,
            compatible_agents=template.compatible_agents,
            file_patterns=template.file_patterns,
            variables=template.variables,
            metadata=template.metadata,
            created_at=template.created_at.isoformat(),
            updated_at=template.updated_at.isoformat(),
            version=template.version,
            is_active=template.is_active
        ) 