"""Context Field Selector for Selective Query Optimization

This module implements selective field queries to reduce database load and network bandwidth
by fetching only required fields instead of full context objects.
"""

import logging
from typing import List, Dict, Any, Optional, Set, Union
from enum import Enum

logger = logging.getLogger(__name__)


class FieldSet(Enum):
    """Predefined field sets for common operations"""
    MINIMAL = "minimal"
    SUMMARY = "summary"
    DETAIL = "detail"
    FULL = "full"


class ContextFieldSelector:
    """Provides selective field queries for context entities"""
    
    # Define field sets for each entity type
    TASK_FIELD_SETS = {
        FieldSet.MINIMAL: ["id", "title", "status"],
        FieldSet.SUMMARY: ["id", "title", "status", "priority", "assignees"],
        FieldSet.DETAIL: [
            "id", "title", "description", "status", "priority", 
            "assignees", "labels", "estimated_effort", "progress_percentage"
        ],
        FieldSet.FULL: None  # All fields
    }
    
    PROJECT_FIELD_SETS = {
        FieldSet.MINIMAL: ["id", "name", "status"],
        FieldSet.SUMMARY: ["id", "name", "status", "description", "created_at"],
        FieldSet.DETAIL: [
            "id", "name", "description", "status", "created_at", 
            "updated_at", "owner", "team_members"
        ],
        FieldSet.FULL: None  # All fields
    }
    
    CONTEXT_FIELD_SETS = {
        FieldSet.MINIMAL: ["id", "level", "data"],
        FieldSet.SUMMARY: ["id", "level", "data", "created_at", "updated_at"],
        FieldSet.DETAIL: [
            "id", "level", "data", "metadata", "created_at", 
            "updated_at", "parent_id", "children_ids"
        ],
        FieldSet.FULL: None  # All fields
    }
    
    # Field dependencies - some fields require others to be fetched
    FIELD_DEPENDENCIES = {
        "assignees": ["assignee_ids"],  # Need IDs to fetch assignee details
        "labels": ["label_ids"],  # Need IDs to fetch label details
        "progress_percentage": ["subtasks", "completed_subtasks"],  # Calculate from subtasks
        "team_members": ["team_member_ids"],  # Need IDs to fetch member details
    }
    
    def __init__(self):
        """Initialize the field selector"""
        self._cache = {}  # Simple in-memory cache for field mappings
        self._metrics = {
            "queries_optimized": 0,
            "fields_reduced": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
    
    def get_task_fields(
        self,
        task_id: str,
        fields: Optional[Union[List[str], FieldSet]] = None
    ) -> Dict[str, Any]:
        """
        Fetch only specified fields for a task
        
        Args:
            task_id: The task ID to fetch
            fields: List of field names or a FieldSet enum value
            
        Returns:
            Dictionary containing only requested fields
        """
        # Check if requesting full fields
        requesting_full = isinstance(fields, FieldSet) and fields == FieldSet.FULL
        
        # Resolve field set if enum provided
        if isinstance(fields, FieldSet):
            fields = self.TASK_FIELD_SETS.get(fields)
        
        # Default to summary if no fields specified (and not requesting full)
        if fields is None and not requesting_full:
            fields = self.TASK_FIELD_SETS[FieldSet.SUMMARY]
        
        # Expand field dependencies
        if fields:
            fields = self._expand_field_dependencies(fields)
        
        # Log optimization metrics
        self._metrics["queries_optimized"] += 1
        if fields:
            full_field_count = 50  # Approximate full task field count
            self._metrics["fields_reduced"] += (full_field_count - len(fields))
        
        logger.debug(f"Fetching task {task_id} with fields: {fields}")
        
        # Return field specification for database query
        return {
            "entity_type": "task",
            "entity_id": task_id,
            "fields": fields,
            "optimized": fields is not None
        }
    
    def get_project_fields(
        self,
        project_id: str,
        fields: Optional[Union[List[str], FieldSet]] = None
    ) -> Dict[str, Any]:
        """
        Fetch only specified fields for a project
        
        Args:
            project_id: The project ID to fetch
            fields: List of field names or a FieldSet enum value
            
        Returns:
            Dictionary containing only requested fields
        """
        # Check if requesting full fields
        requesting_full = isinstance(fields, FieldSet) and fields == FieldSet.FULL
        
        # Resolve field set if enum provided
        if isinstance(fields, FieldSet):
            fields = self.PROJECT_FIELD_SETS.get(fields)
        
        # Default to summary if no fields specified (and not requesting full)
        if fields is None and not requesting_full:
            fields = self.PROJECT_FIELD_SETS[FieldSet.SUMMARY]
        
        # Expand field dependencies
        if fields:
            fields = self._expand_field_dependencies(fields)
        
        # Log optimization metrics
        self._metrics["queries_optimized"] += 1
        if fields:
            full_field_count = 30  # Approximate full project field count
            self._metrics["fields_reduced"] += (full_field_count - len(fields))
        
        logger.debug(f"Fetching project {project_id} with fields: {fields}")
        
        # Return field specification for database query
        return {
            "entity_type": "project",
            "entity_id": project_id,
            "fields": fields,
            "optimized": fields is not None
        }
    
    def get_context_fields(
        self,
        context_id: str,
        level: str,
        fields: Optional[Union[List[str], FieldSet]] = None
    ) -> Dict[str, Any]:
        """
        Fetch only specified fields for a context
        
        Args:
            context_id: The context ID to fetch
            level: The context level (global, project, branch, task)
            fields: List of field names or a FieldSet enum value
            
        Returns:
            Dictionary containing only requested fields
        """
        # Check if requesting full fields
        requesting_full = isinstance(fields, FieldSet) and fields == FieldSet.FULL
        
        # Resolve field set if enum provided
        if isinstance(fields, FieldSet):
            fields = self.CONTEXT_FIELD_SETS.get(fields)
        
        # Default to summary if no fields specified (and not requesting full)
        if fields is None and not requesting_full:
            fields = self.CONTEXT_FIELD_SETS[FieldSet.SUMMARY]
        
        # Expand field dependencies
        if fields:
            fields = self._expand_field_dependencies(fields)
        
        # Log optimization metrics
        self._metrics["queries_optimized"] += 1
        if fields:
            full_field_count = 20  # Approximate full context field count
            self._metrics["fields_reduced"] += (full_field_count - len(fields))
        
        logger.debug(f"Fetching context {context_id} ({level}) with fields: {fields}")
        
        # Return field specification for database query
        return {
            "entity_type": "context",
            "entity_id": context_id,
            "level": level,
            "fields": fields,
            "optimized": fields is not None
        }
    
    def build_optimized_query(
        self,
        entity_class: Any,
        fields: Optional[List[str]]
    ) -> Any:
        """
        Build an optimized SQLAlchemy query for selective fields
        
        Args:
            entity_class: The SQLAlchemy model class
            fields: List of field names to select
            
        Returns:
            SQLAlchemy query object configured for selective fields
        """
        if fields is None:
            # Return full entity query
            return entity_class
        
        # Build selective query
        # This would be integrated with SQLAlchemy in the repository layer
        field_attrs = []
        for field in fields:
            if hasattr(entity_class, field):
                field_attrs.append(getattr(entity_class, field))
            else:
                logger.warning(f"Field {field} not found in {entity_class.__name__}")
        
        return field_attrs
    
    def _expand_field_dependencies(self, fields: List[str]) -> List[str]:
        """
        Expand fields to include their dependencies
        
        Args:
            fields: Original field list
            
        Returns:
            Expanded field list with dependencies
        """
        expanded = set(fields)
        
        for field in fields:
            if field in self.FIELD_DEPENDENCIES:
                deps = self.FIELD_DEPENDENCIES[field]
                expanded.update(deps)
        
        return list(expanded)
    
    def get_optimal_field_set(
        self,
        operation: str,
        entity_type: str
    ) -> FieldSet:
        """
        Determine optimal field set based on operation type
        
        Args:
            operation: The operation being performed
            entity_type: The entity type (task, project, context)
            
        Returns:
            Recommended FieldSet enum value
        """
        # High-frequency operations need minimal fields
        if operation in ["list", "status", "count", "exists"]:
            return FieldSet.MINIMAL
        
        # Summary operations need moderate fields
        if operation in ["get", "search", "filter"]:
            return FieldSet.SUMMARY
        
        # Detail operations need more fields
        if operation in ["update", "create", "workflow"]:
            return FieldSet.DETAIL
        
        # Debug/admin operations might need all fields
        if operation in ["debug", "audit", "export"]:
            return FieldSet.FULL
        
        # Default to summary
        return FieldSet.SUMMARY
    
    def cache_field_mapping(
        self,
        entity_id: str,
        fields: List[str],
        data: Dict[str, Any]
    ) -> None:
        """
        Cache field mapping for faster subsequent queries
        
        Args:
            entity_id: The entity ID
            fields: Fields that were requested
            data: The fetched data
        """
        cache_key = f"{entity_id}:{','.join(sorted(fields))}"
        self._cache[cache_key] = data
        logger.debug(f"Cached field mapping for {entity_id}")
    
    def get_cached_fields(
        self,
        entity_id: str,
        fields: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached field data if available
        
        Args:
            entity_id: The entity ID
            fields: Fields being requested
            
        Returns:
            Cached data if available, None otherwise
        """
        cache_key = f"{entity_id}:{','.join(sorted(fields))}"
        
        if cache_key in self._cache:
            self._metrics["cache_hits"] += 1
            logger.debug(f"Cache hit for {entity_id}")
            return self._cache[cache_key]
        
        self._metrics["cache_misses"] += 1
        return None
    
    def get_metrics(self) -> Dict[str, int]:
        """
        Get optimization metrics
        
        Returns:
            Dictionary of performance metrics
        """
        return self._metrics.copy()
    
    def reset_metrics(self) -> None:
        """Reset performance metrics"""
        self._metrics = {
            "queries_optimized": 0,
            "fields_reduced": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
    
    def estimate_savings(
        self,
        entity_type: str,
        field_set: FieldSet
    ) -> Dict[str, float]:
        """
        Estimate performance savings for a given field set
        
        Args:
            entity_type: The entity type
            field_set: The field set to use
            
        Returns:
            Dictionary with estimated savings percentages
        """
        # Get field counts
        if entity_type == "task":
            full_fields = 50
            field_sets = self.TASK_FIELD_SETS
        elif entity_type == "project":
            full_fields = 30
            field_sets = self.PROJECT_FIELD_SETS
        elif entity_type == "context":
            full_fields = 20
            field_sets = self.CONTEXT_FIELD_SETS
        else:
            return {"error": "Unknown entity type"}
        
        # Calculate savings
        if field_set == FieldSet.FULL or field_sets[field_set] is None:
            selected_fields = full_fields
        else:
            selected_fields = len(field_sets[field_set])
        
        field_reduction = ((full_fields - selected_fields) / full_fields) * 100
        
        # Estimate other savings (rough approximations)
        query_time_savings = field_reduction * 0.7  # 70% correlation with field reduction
        bandwidth_savings = field_reduction * 0.9   # 90% correlation with field reduction
        cache_efficiency = min(field_reduction * 1.2, 95)  # Up to 95% better cache usage
        
        return {
            "field_reduction_percent": round(field_reduction, 1),
            "query_time_savings_percent": round(query_time_savings, 1),
            "bandwidth_savings_percent": round(bandwidth_savings, 1),
            "cache_efficiency_percent": round(cache_efficiency, 1),
            "selected_fields": selected_fields,
            "full_fields": full_fields
        }