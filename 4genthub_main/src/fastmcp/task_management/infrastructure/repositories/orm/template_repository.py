"""
ORM Template Repository Implementation

This module implements the Template Repository using SQLAlchemy ORM,
providing template management with full database capabilities.
"""

import logging
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text

from ....domain.entities.template import Template, TemplateUsage
from ....domain.value_objects.template_id import TemplateId
from ....domain.enums.template_enums import TemplateType, TemplateCategory, TemplateStatus, TemplatePriority
from ....domain.repositories.template_repository import TemplateRepositoryInterface
from ..base_orm_repository import BaseORMRepository
from ...database.models import Template as ORMTemplate

logger = logging.getLogger(__name__)


class ORMTemplateRepository(BaseORMRepository[ORMTemplate], TemplateRepositoryInterface):
    """ORM implementation of template repository using SQLAlchemy"""
    
    def __init__(self):
        """Initialize the ORM template repository"""
        super().__init__(ORMTemplate)
    
    def save(self, template: Template) -> bool:
        """
        Save a template to the database
        
        Args:
            template: Template entity to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_db_session() as session:
                # Check if template exists
                existing = session.query(ORMTemplate).filter(
                    ORMTemplate.id == str(template.id)
                ).first()
                
                if existing:
                    # Update existing template
                    existing.name = template.name
                    existing.type = template.template_type.value
                    existing.content = self._serialize_template_content(template)
                    existing.category = template.category.value
                    existing.tags = self._extract_tags_from_template(template)
                    existing.updated_at = datetime.now(timezone.utc)
                    existing.created_by = getattr(template, 'created_by', 'system')
                else:
                    # Create new template
                    orm_template = ORMTemplate(
                        id=str(template.id),
                        name=template.name,
                        type=template.template_type.value,
                        content=self._serialize_template_content(template),
                        category=template.category.value,
                        tags=self._extract_tags_from_template(template),
                        usage_count=0,
                        created_at=template.created_at,
                        updated_at=template.updated_at,
                        created_by=getattr(template, 'created_by', 'system')
                    )
                    session.add(orm_template)
                
                session.commit()
                logger.info(f"Template saved successfully: {template.id}")
                return True
                
        except Exception as e:
            logger.error(f"Error saving template {template.id}: {e}")
            return False
    
    def get_by_id(self, template_id: TemplateId) -> Optional[Template]:
        """
        Get a template by its ID
        
        Args:
            template_id: Template identifier
            
        Returns:
            Template entity or None if not found
        """
        try:
            with self.get_db_session() as session:
                orm_template = session.query(ORMTemplate).filter(
                    ORMTemplate.id == str(template_id)
                ).first()
                
                if orm_template:
                    return self._orm_to_domain(orm_template)
                return None
                
        except Exception as e:
            logger.error(f"Error getting template {template_id}: {e}")
            return None
    
    def list_templates(
        self, 
        template_type: Optional[TemplateType] = None,
        category: Optional[TemplateCategory] = None,
        status: Optional[TemplateStatus] = None,
        priority: Optional[TemplatePriority] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Template]:
        """
        List templates with optional filtering and pagination
        
        Args:
            template_type: Filter by template type
            category: Filter by category
            status: Filter by status
            priority: Filter by priority
            limit: Maximum number of templates to return
            offset: Number of templates to skip
            
        Returns:
            List of template entities
        """
        try:
            with self.get_db_session() as session:
                query = session.query(ORMTemplate)
                
                # Apply filters
                if template_type:
                    query = query.filter(ORMTemplate.type == template_type.value)
                if category:
                    query = query.filter(ORMTemplate.category == category.value)
                
                # Order by usage count descending, then by name
                query = query.order_by(ORMTemplate.usage_count.desc(), ORMTemplate.name)
                
                # Apply pagination
                if offset:
                    query = query.offset(offset)
                if limit:
                    query = query.limit(limit)
                
                orm_templates = query.all()
                return [self._orm_to_domain(template) for template in orm_templates]
                
        except Exception as e:
            logger.error(f"Error listing templates: {e}")
            return []
    
    def delete(self, template_id: TemplateId) -> bool:
        """
        Delete a template by its ID
        
        Args:
            template_id: Template identifier
            
        Returns:
            True if deleted, False if not found or error
        """
        try:
            with self.get_db_session() as session:
                orm_template = session.query(ORMTemplate).filter(
                    ORMTemplate.id == str(template_id)
                ).first()
                
                if orm_template:
                    session.delete(orm_template)
                    session.commit()
                    logger.info(f"Template deleted successfully: {template_id}")
                    return True
                return False
                
        except Exception as e:
            logger.error(f"Error deleting template {template_id}: {e}")
            return False
    
    def get_templates_by_type(self, template_type: TemplateType) -> List[Template]:
        """
        Get all templates of a specific type
        
        Args:
            template_type: Type of templates to retrieve
            
        Returns:
            List of template entities
        """
        return self.list_templates(template_type=template_type)
    
    def get_templates_by_category(self, category: TemplateCategory) -> List[Template]:
        """
        Get all templates in a specific category
        
        Args:
            category: Category of templates to retrieve
            
        Returns:
            List of template entities
        """
        return self.list_templates(category=category)
    
    def search_templates_by_tags(self, tags: List[str]) -> List[Template]:
        """
        Search templates by tags
        
        Args:
            tags: List of tags to search for
            
        Returns:
            List of template entities matching the tags
        """
        try:
            with self.get_db_session() as session:
                # Build query to find templates with any of the specified tags
                conditions = []
                for tag in tags:
                    # Use JSON_CONTAINS for tag search
                    conditions.append(
                        text(f"JSON_SEARCH(tags, 'one', '{tag}') IS NOT NULL")
                    )
                
                if conditions:
                    query = session.query(ORMTemplate).filter(or_(*conditions))
                    orm_templates = query.order_by(ORMTemplate.usage_count.desc()).all()
                    return [self._orm_to_domain(template) for template in orm_templates]
                return []
                
        except Exception as e:
            logger.error(f"Error searching templates by tags {tags}: {e}")
            return []
    
    def increment_usage_count(self, template_id: TemplateId) -> bool:
        """
        Increment the usage count for a template
        
        Args:
            template_id: Template identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_db_session() as session:
                orm_template = session.query(ORMTemplate).filter(
                    ORMTemplate.id == str(template_id)
                ).first()
                
                if orm_template:
                    orm_template.usage_count += 1
                    orm_template.updated_at = datetime.now(timezone.utc)
                    session.commit()
                    logger.debug(f"Usage count incremented for template: {template_id}")
                    return True
                return False
                
        except Exception as e:
            logger.error(f"Error incrementing usage count for template {template_id}: {e}")
            return False
    
    def save_usage(self, usage: TemplateUsage) -> bool:
        """
        Save template usage record
        
        Args:
            usage: Template usage record
            
        Returns:
            True if successful, False otherwise
        """
        # For now, just increment usage count
        # TODO: Implement full usage tracking with separate table
        return self.increment_usage_count(usage.template_id)
    
    def get_usage_stats(self, template_id: TemplateId) -> Dict[str, Any]:
        """
        Get usage statistics for a template
        
        Args:
            template_id: Template identifier
            
        Returns:
            Dictionary with usage statistics
        """
        try:
            with self.get_db_session() as session:
                orm_template = session.query(ORMTemplate).filter(
                    ORMTemplate.id == str(template_id)
                ).first()
                
                if orm_template:
                    return {
                        'template_id': str(template_id),
                        'total_usage': orm_template.usage_count,
                        'last_used': orm_template.updated_at,
                        'created_at': orm_template.created_at
                    }
                return {}
                
        except Exception as e:
            logger.error(f"Error getting usage stats for template {template_id}: {e}")
            return {}
    
    def get_analytics(self) -> Dict[str, Any]:
        """
        Get template analytics and insights
        
        Returns:
            Dictionary with analytics data
        """
        try:
            with self.get_db_session() as session:
                # Get total template count
                total_templates = session.query(func.count(ORMTemplate.id)).scalar()
                
                # Get templates by type
                type_stats = {}
                type_counts = session.query(
                    ORMTemplate.type, 
                    func.count(ORMTemplate.id)
                ).group_by(ORMTemplate.type).all()
                
                for template_type, count in type_counts:
                    type_stats[template_type] = count
                
                # Get templates by category
                category_stats = {}
                category_counts = session.query(
                    ORMTemplate.category,
                    func.count(ORMTemplate.id)
                ).group_by(ORMTemplate.category).all()
                
                for category, count in category_counts:
                    category_stats[category] = count
                
                # Get most used templates
                most_used = session.query(ORMTemplate).order_by(
                    ORMTemplate.usage_count.desc()
                ).limit(10).all()
                
                most_used_templates = [
                    {
                        'id': template.id,
                        'name': template.name,
                        'usage_count': template.usage_count
                    }
                    for template in most_used
                ]
                
                return {
                    'total_templates': total_templates,
                    'templates_by_type': type_stats,
                    'templates_by_category': category_stats,
                    'most_used_templates': most_used_templates,
                    'generated_at': datetime.now(timezone.utc).isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting template analytics: {e}")
            return {}
    
    def _serialize_template_content(self, template: Template) -> Dict[str, Any]:
        """
        Serialize template to JSON content for storage
        
        Args:
            template: Template entity
            
        Returns:
            Dictionary representation for JSON storage
        """
        return {
            'description': template.description,
            'content': template.content,
            'status': template.status.value,
            'priority': template.priority.value,
            'compatible_agents': template.compatible_agents,
            'file_patterns': template.file_patterns,
            'variables': template.variables,
            'metadata': template.metadata,
            'version': template.version,
            'is_active': template.is_active
        }
    
    def _extract_tags_from_template(self, template: Template) -> List[str]:
        """
        Extract tags from template for search indexing
        
        Args:
            template: Template entity
            
        Returns:
            List of tags
        """
        tags = []
        
        # Add type and category as tags
        tags.append(template.template_type.value)
        tags.append(template.category.value)
        tags.append(template.status.value)
        tags.append(template.priority.value)
        
        # Add compatible agents as tags
        tags.extend(template.compatible_agents)
        
        # Add metadata keys as tags
        tags.extend(template.metadata.keys())
        
        # Remove duplicates and empty strings
        return list(set(tag for tag in tags if tag))
    
    def _orm_to_domain(self, orm_template: ORMTemplate) -> Template:
        """
        Convert ORM template to domain entity
        
        Args:
            orm_template: ORM template instance
            
        Returns:
            Template domain entity
        """
        content_data = orm_template.content if isinstance(orm_template.content, dict) else {}
        
        return Template(
            id=TemplateId(orm_template.id),
            name=orm_template.name,
            description=content_data.get('description', ''),
            content=content_data.get('content', ''),
            template_type=TemplateType(orm_template.type),
            category=TemplateCategory(orm_template.category),
            status=TemplateStatus(content_data.get('status', 'active')),
            priority=TemplatePriority(content_data.get('priority', 'medium')),
            compatible_agents=content_data.get('compatible_agents', []),
            file_patterns=content_data.get('file_patterns', []),
            variables=content_data.get('variables', []),
            metadata=content_data.get('metadata', {}),
            created_at=orm_template.created_at,
            updated_at=orm_template.updated_at,
            version=content_data.get('version', 1),
            is_active=content_data.get('is_active', True)
        )