"""Context Domain Entities"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
import json
from pathlib import Path
from ..value_objects.priority import Priority, PriorityLevel
from ..value_objects.task_status import TaskStatus, TaskStatusEnum
from ..value_objects.task_id import TaskId
from .global_context_schema import GlobalContextNestedData
import uuid


# Unified Context System Entities

@dataclass
class GlobalContext:
    """
    Global context entity for organization-wide settings with nested categorization support.
    
    This entity uses a modern nested structure for global context data organization.
    """
    id: str  # User-scoped global context ID
    organization_name: str
    global_settings: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Nested structure support (v2.0)
    _nested_data: Optional[GlobalContextNestedData] = field(default=None, init=False)
    
    def __post_init__(self):
        """Initialize nested structure if not already present."""
        if self._nested_data is None:
            self._ensure_nested_structure()
    
    def _ensure_nested_structure(self) -> None:
        """Ensure nested structure is initialized."""
        if self._nested_data is None:
            # Initialize empty nested structure
            self._nested_data = GlobalContextNestedData()
    
    def get_nested_data(self) -> GlobalContextNestedData:
        """Get the nested data structure, ensuring it's initialized."""
        self._ensure_nested_structure()
        return self._nested_data
    
    def set_nested_value(self, path: str, value: Any) -> None:
        """Set a value in the nested structure using dot notation."""
        nested_data = self.get_nested_data()
        nested_data.set_nested_value(path, value)
        self._sync_to_flat_structure()
    
    def get_nested_value(self, path: str, default: Any = None) -> Any:
        """Get a value from the nested structure using dot notation."""
        nested_data = self.get_nested_data()
        return nested_data.get_nested_value(path, default)
    
    def _sync_to_flat_structure(self) -> None:
        """Convert nested structure to flat format."""
        if self._nested_data:
            self.global_settings = self._nested_data.to_dict()
    
    def update_global_settings(self, settings: Dict[str, Any], use_nested: bool = True) -> None:
        """
        Update global settings with support for both flat and nested structures.
        
        Args:
            settings: Settings to update
            use_nested: If True, use nested structure directly
        """
        if use_nested:
            # Update nested structure and sync back
            if not isinstance(settings, dict):
                raise ValueError("Settings must be a dictionary")
            
            nested_data = self.get_nested_data()
            
            # If settings contain nested structure directly
            if any(key in ["organization", "development", "security", "operations", "preferences"] for key in settings.keys()):
                # Direct nested update
                for category in ["organization", "development", "security", "operations", "preferences"]:
                    if category in settings:
                        getattr(nested_data, category).update(settings[category])
            else:
                # Update flat settings directly
                nested_data.from_dict(settings)
            
            self._sync_to_flat_structure()
        else:
            # Direct flat structure update
            self.global_settings.update(settings)
    
    def get_organization_standards(self) -> Dict[str, Any]:
        """Get organization standards from nested structure."""
        return self.get_nested_value("organization.standards", {})
    
    def get_security_policies(self) -> Dict[str, Any]:
        """Get security policies from nested structure."""
        security_data = self.get_nested_data().security
        return {
            "authentication": security_data.get("authentication", {}),
            "encryption": security_data.get("encryption", {}),
            "access_control": security_data.get("access_control", {})
        }
    
    def get_development_patterns(self) -> Dict[str, Any]:
        """Get development patterns from nested structure."""
        return self.get_nested_value("development.patterns", {})
    
    def get_user_preferences(self) -> Dict[str, Any]:
        """Get user preferences from nested structure."""
        preferences = self.get_nested_data().preferences
        return {
            "user_interface": preferences.get("user_interface", {}),
            "agent_behavior": preferences.get("agent_behavior", {}),
            "workflow": preferences.get("workflow", {})
        }
    
    def dict(self) -> Dict[str, Any]:
        """Convert to dictionary with support for both structures."""
        self._ensure_nested_structure()
        
        # Sync nested to flat format
        self._sync_to_flat_structure()
        
        result = {
            "id": self.id,
            "organization_name": self.organization_name,
            "global_settings": self.global_settings,
            "metadata": self.metadata.copy()
        }
        
        # Add nested structure information to metadata
        if self._nested_data:
            result["metadata"]["schema_version"] = self._nested_data._schema_version
            result["metadata"]["nested_structure"] = self._nested_data.to_dict()
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GlobalContext':
        """Create GlobalContext from dictionary with nested structure support."""
        instance = cls(
            id=data.get("id", ""),
            organization_name=data.get("organization_name", ""),
            global_settings=data.get("global_settings", {}),
            metadata=data.get("metadata", {})
        )
        
        # Check if nested structure exists in metadata
        if "nested_structure" in instance.metadata:
            nested_dict = instance.metadata["nested_structure"]
            instance._nested_data = GlobalContextNestedData.from_dict(nested_dict)
        else:
            # Force migration from flat structure
            instance._ensure_nested_structure()
        
        return instance


@dataclass
class ProjectContext:
    """Project context entity for project-specific settings."""
    id: str  # Project UUID
    project_name: str
    project_info: Dict[str, Any] = field(default_factory=dict)  # Name, description, version, status
    team_preferences: Dict[str, Any] = field(default_factory=dict)  # Review requirements, merge strategy
    technology_stack: Dict[str, Any] = field(default_factory=dict)  # Frontend, backend, database, infrastructure
    project_workflow: Dict[str, Any] = field(default_factory=dict)  # Phases, gates, approval processes
    local_standards: Dict[str, Any] = field(default_factory=dict)  # Project-specific standards
    project_settings: Dict[str, Any] = field(default_factory=dict)  # Build configs, deployment settings
    technical_specifications: Dict[str, Any] = field(default_factory=dict)  # API specs, schemas, architecture
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "project_name": self.project_name,
            "project_info": self.project_info,
            "team_preferences": self.team_preferences,
            "technology_stack": self.technology_stack,
            "project_workflow": self.project_workflow,
            "local_standards": self.local_standards,
            "project_settings": self.project_settings,
            "technical_specifications": self.technical_specifications,
            "metadata": self.metadata
        }


@dataclass
class BranchContext:
    """Branch context entity for git branch-specific settings."""
    id: str  # Git branch UUID
    project_id: str
    git_branch_name: str
    branch_info: Dict[str, Any] = field(default_factory=dict)  # Feature name, type, status, parent
    branch_workflow: Dict[str, Any] = field(default_factory=dict)  # Implementation status, dependencies
    feature_flags: Dict[str, Any] = field(default_factory=dict)  # Feature toggles
    discovered_patterns: Dict[str, Any] = field(default_factory=dict)  # Patterns discovered
    branch_decisions: Dict[str, Any] = field(default_factory=dict)  # Technical decisions
    branch_settings: Dict[str, Any] = field(default_factory=dict)  # Legacy/general settings
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "git_branch_name": self.git_branch_name,
            "branch_info": self.branch_info,
            "branch_workflow": self.branch_workflow,
            "feature_flags": self.feature_flags,
            "discovered_patterns": self.discovered_patterns,
            "branch_decisions": self.branch_decisions,
            "branch_settings": self.branch_settings,
            "metadata": self.metadata
        }


@dataclass
class TaskContextUnified:
    """Task context entity for unified context system.
    Named TaskContextUnified to avoid conflict with existing TaskContext.
    """
    id: str  # Task UUID
    branch_id: str
    task_data: Dict[str, Any] = field(default_factory=dict)  # Title, status, progress, assignees
    execution_context: Dict[str, Any] = field(default_factory=dict)  # Files modified, tests added
    discovered_patterns: Dict[str, Any] = field(default_factory=dict)  # Patterns found
    implementation_notes: Dict[str, Any] = field(default_factory=dict)  # Challenges, solutions
    test_results: Dict[str, Any] = field(default_factory=dict)  # Test outcomes, coverage
    blockers: Dict[str, Any] = field(default_factory=dict)  # Current impediments
    progress: int = 0
    insights: List[Dict[str, Any]] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "branch_id": self.branch_id,
            "task_data": self.task_data,
            "execution_context": self.execution_context,
            "discovered_patterns": self.discovered_patterns,
            "implementation_notes": self.implementation_notes,
            "test_results": self.test_results,
            "blockers": self.blockers,
            "progress": self.progress,
            "insights": self.insights,
            "next_steps": self.next_steps,
            "metadata": self.metadata
        }


# Existing Context Entities below...


@dataclass
class ContextMetadata:
    """Context metadata structure following clean relationship chain (uses Priority and TaskStatus value objects)"""
    task_id: str  # Primary key - contains all necessary context via task -> git_branch -> project -> user
    status: TaskStatus = field(default_factory=TaskStatus.todo)
    priority: Priority = field(default_factory=Priority.medium)
    assignees: List[str] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1


@dataclass
class ContextObjective:
    """Task objective and description"""
    title: str
    description: str = ""
    estimated_effort: Optional[str] = None
    due_date: Optional[datetime] = None


@dataclass
class ContextRequirement:
    """Individual requirement item (uses Priority value object)"""
    id: str
    title: str
    completed: bool = False
    priority: Priority = field(default_factory=Priority.medium)
    notes: str = ""


@dataclass
class ContextRequirements:
    """Requirements section"""
    checklist: List[ContextRequirement] = field(default_factory=list)
    custom_requirements: List[str] = field(default_factory=list)
    completion_criteria: List[str] = field(default_factory=list)


@dataclass
class ContextTechnical:
    """Technical details section"""
    technologies: List[str] = field(default_factory=list)
    frameworks: List[str] = field(default_factory=list)
    database: str = ""
    key_files: List[str] = field(default_factory=list)
    key_directories: List[str] = field(default_factory=list)
    architecture_notes: str = ""
    patterns_used: List[str] = field(default_factory=list)


@dataclass
class ContextDependency:
    """Dependency information (uses TaskStatus value object)"""
    task_id: str
    title: str = ""
    status: TaskStatus = field(default_factory=TaskStatus.todo)
    blocking_reason: str = ""


@dataclass
class ContextDependencies:
    """Dependencies section"""
    task_dependencies: List[ContextDependency] = field(default_factory=list)
    external_dependencies: List[str] = field(default_factory=list)
    blocked_by: List[str] = field(default_factory=list)


@dataclass
class ContextProgressAction:
    """Individual progress action"""
    timestamp: str
    action: str
    agent: str
    details: str = ""
    status: str = "completed"


@dataclass
class ContextProgress:
    """Progress tracking section"""
    completed_actions: List[ContextProgressAction] = field(default_factory=list)
    current_session_summary: str = ""
    next_steps: List[str] = field(default_factory=list)
    completion_percentage: float = 0.0
    time_spent_minutes: int = 0
    # Vision System mandatory fields
    completion_summary: Optional[str] = None  # REQUIRED when task is completed
    testing_notes: Optional[str] = None  # Optional but recommended
    next_recommendations: Optional[str] = None  # Optional but recommended
    vision_alignment_score: Optional[float] = None  # Vision alignment score


@dataclass
class ContextInsight:
    """Agent insight or note"""
    timestamp: str
    agent: str
    category: str  # "insight", "challenge", "solution", "decision"
    content: str
    importance: str = "medium"  # "low", "medium", "high", "critical"


@dataclass
class ContextNotes:
    """Context notes and insights"""
    agent_insights: List[ContextInsight] = field(default_factory=list)
    challenges_encountered: List[ContextInsight] = field(default_factory=list)
    solutions_applied: List[ContextInsight] = field(default_factory=list)
    decisions_made: List[ContextInsight] = field(default_factory=list)
    general_notes: str = ""


@dataclass
class ContextSubtask:
    """Subtask information (uses TaskStatus value object)"""
    id: str
    title: str
    description: str = ""
    status: TaskStatus = field(default_factory=TaskStatus.todo)
    assignees: List[str] = field(default_factory=list)
    completed: bool = False
    progress_notes: str = ""


@dataclass
class ContextSubtasks:
    """Subtasks section"""
    items: List[ContextSubtask] = field(default_factory=list)
    total_count: int = 0
    completed_count: int = 0
    progress_percentage: float = 0.0


@dataclass
class ContextCustomSection:
    """Custom extensible section"""
    name: str
    data: Dict[str, Any] = field(default_factory=dict)
    schema_version: str = "1.0"


@dataclass
class TaskContext:
    """Complete task context structure"""
    metadata: ContextMetadata
    objective: ContextObjective
    requirements: ContextRequirements = field(default_factory=ContextRequirements)
    technical: ContextTechnical = field(default_factory=ContextTechnical)
    dependencies: ContextDependencies = field(default_factory=ContextDependencies)
    progress: ContextProgress = field(default_factory=ContextProgress)
    subtasks: ContextSubtasks = field(default_factory=ContextSubtasks)
    notes: ContextNotes = field(default_factory=ContextNotes)
    custom_sections: List[ContextCustomSection] = field(default_factory=list)
    
    # Phase 2: Progress tracking fields
    progress_timeline: Optional[List[Dict[str, Any]]] = None  # Snapshot history
    progress_milestones: Optional[Dict[str, float]] = None  # Milestone definitions
    progress_by_type: Optional[Dict[str, float]] = None  # Current progress per type
    
    def update_completion_summary(self, completion_summary: str, 
                                testing_notes: Optional[str] = None,
                                next_recommendations: Optional[str] = None) -> None:
        """Update context with completion information (Vision System requirement)"""
        if not completion_summary or not completion_summary.strip():
            raise ValueError("completion_summary cannot be empty")
        
        self.progress.completion_summary = completion_summary
        if testing_notes:
            self.progress.testing_notes = testing_notes
        if next_recommendations:
            self.progress.next_recommendations = next_recommendations
        
        # Update metadata timestamp
        self.metadata.updated_at = datetime.now(timezone.utc)
    
    def has_completion_summary(self) -> bool:
        """Check if context has a completion summary"""
        return bool(self.progress.completion_summary and self.progress.completion_summary.strip())
    
    def validate_for_task_completion(self) -> tuple[bool, List[str]]:
        """Validate context is ready for task completion"""
        errors = []
        
        if not self.has_completion_summary():
            errors.append("completion_summary is required for task completion")
        
        # Additional validations can be added here
        
        return len(errors) == 0, errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for JSON serialization"""
        def convert_dataclass(obj):
            if isinstance(obj, Priority) or isinstance(obj, TaskStatus):
                return str(obj)
            elif isinstance(obj, datetime):
                return obj.isoformat()
            elif hasattr(obj, '__dataclass_fields__'):
                return {k: convert_dataclass(v) for k, v in obj.__dict__.items()}
            elif isinstance(obj, list):
                return [convert_dataclass(item) for item in obj]
            elif isinstance(obj, dict):
                return {k: convert_dataclass(v) for k, v in obj.items()}
            else:
                return obj
        
        result = convert_dataclass(self)
        
        # Add task_id at root level for backward compatibility
        result['task_id'] = self.metadata.task_id
        
        # Restore custom fields from custom_sections to root level
        if 'custom_sections' in result:
            custom_sections_to_keep = []
            for section in result['custom_sections']:
                if section.get('name') == 'root_level_custom_fields':
                    # Restore custom fields to root level
                    if 'data' in section and isinstance(section['data'], dict):
                        result.update(section['data'])
                else:
                    # Keep other custom sections
                    custom_sections_to_keep.append(section)
            result['custom_sections'] = custom_sections_to_keep
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskContext':
        """Create TaskContext from dictionary"""
        # Handle nested format
        if 'metadata' in data:
            # New nested format - extract metadata section (clean relationship chain)
            metadata_data = data['metadata']
            metadata = ContextMetadata(
                task_id=metadata_data['task_id'],  # Only task_id following clean relationship chain
                status=TaskStatus.from_string(metadata_data.get('status', 'todo')),
                priority=Priority.from_string(metadata_data.get('priority', 'medium')),
                assignees=metadata_data.get('assignees', []),
                labels=metadata_data.get('labels', []),
                created_at=datetime.fromisoformat(metadata_data.get('created_at', datetime.now(timezone.utc).isoformat()).replace('Z', '+00:00')),
                updated_at=datetime.fromisoformat(metadata_data.get('updated_at', datetime.now(timezone.utc).isoformat()).replace('Z', '+00:00')),
                version=metadata_data.get('version', 1)
            )
        else:
            # Flat format - extract from data directly
            metadata = ContextMetadata(
                task_id=data['task_id'],  # Only task_id following clean relationship chain
                status=TaskStatus.from_string(data.get('status', 'todo')),
                priority=Priority.from_string(data.get('priority', 'medium')),
                assignees=data.get('assignees', []),
                labels=data.get('labels', [])
            )
        
        # Extract objective section
        if 'objective' in data:
            objective_data = data['objective']
            objective = ContextObjective(
                title=objective_data['title'],
                description=objective_data.get('description', ''),
                estimated_effort=objective_data.get('estimated_effort'),
                due_date=datetime.fromisoformat(objective_data.get('due_date', '').replace('Z', '+00:00')) if objective_data.get('due_date') else None
            )
        else:
            # Fallback for old format or missing objective
            objective = ContextObjective(
                title=data.get('title', f"Context for task {metadata.task_id}"),
                description=data.get('description', ''),
                estimated_effort=data.get('estimated_effort'),
                due_date=datetime.fromisoformat(data.get('due_date', '').replace('Z', '+00:00')) if data.get('due_date') else None
            )
        
        context = cls(metadata=metadata, objective=objective)
        
        # Load other sections if present with value object conversion
        if 'requirements' in data:
            req_data = data['requirements']
            context.requirements = ContextRequirements(
                checklist=[
                    ContextRequirement(
                        id=item.get('id', ''),
                        title=item.get('title', ''),
                        completed=item.get('completed', False),
                        priority=Priority.from_string(item.get('priority', 'medium')),
                        notes=item.get('notes', '')
                    ) for item in req_data.get('checklist', [])
                ],
                custom_requirements=req_data.get('custom_requirements', []),
                completion_criteria=req_data.get('completion_criteria', [])
            )
        
        if 'technical' in data:
            context.technical = ContextTechnical(**data['technical'])
            
        if 'dependencies' in data:
            dep_data = data['dependencies']
            context.dependencies = ContextDependencies(
                task_dependencies=[
                    ContextDependency(
                        task_id=item.get('task_id', ''),
                        title=item.get('title', ''),
                        status=TaskStatus.from_string(item.get('status', 'todo')),
                        blocking_reason=item.get('blocking_reason', '')
                    ) for item in dep_data.get('task_dependencies', [])
                ],
                external_dependencies=dep_data.get('external_dependencies', []),
                blocked_by=dep_data.get('blocked_by', [])
            )
            
        if 'progress' in data:
            prog_data = data['progress']
            context.progress = ContextProgress(
                completed_actions=[ContextProgressAction(**item) for item in prog_data.get('completed_actions', [])],
                current_session_summary=prog_data.get('current_session_summary', ''),
                next_steps=prog_data.get('next_steps', []),
                completion_percentage=prog_data.get('completion_percentage', 0.0),
                time_spent_minutes=prog_data.get('time_spent_minutes', 0),
                # Vision System fields
                completion_summary=prog_data.get('completion_summary'),
                testing_notes=prog_data.get('testing_notes'),
                next_recommendations=prog_data.get('next_recommendations'),
                vision_alignment_score=prog_data.get('vision_alignment_score')
            )
            
        if 'subtasks' in data:
            sub_data = data['subtasks']
            context.subtasks = ContextSubtasks(
                items=[
                    ContextSubtask(
                        id=item.get('id', ''),
                        title=item.get('title', ''),
                        description=item.get('description', ''),
                        status=TaskStatus.from_string(item.get('status', 'todo')),
                        assignees=item.get('assignees', []),
                        completed=item.get('completed', False),
                        progress_notes=item.get('progress_notes', '')
                    ) for item in sub_data.get('items', [])
                ],
                total_count=sub_data.get('total_count', 0),
                completed_count=sub_data.get('completed_count', 0),
                progress_percentage=sub_data.get('progress_percentage', 0.0)
            )
            
        if 'notes' in data:
            notes_data = data['notes']
            context.notes = ContextNotes(
                agent_insights=[ContextInsight(**item) for item in notes_data.get('agent_insights', [])],
                challenges_encountered=[ContextInsight(**item) for item in notes_data.get('challenges_encountered', [])],
                solutions_applied=[ContextInsight(**item) for item in notes_data.get('solutions_applied', [])],
                decisions_made=[ContextInsight(**item) for item in notes_data.get('decisions_made', [])],
                general_notes=notes_data.get('general_notes', '')
            )
            
        if 'custom_sections' in data:
            context.custom_sections = [ContextCustomSection(**section) for section in data['custom_sections']]
        
        # Handle custom fields at root level by storing them in custom_sections
        known_fields = {
            'metadata', 
            'objective', 
            'requirements', 
            'technical', 
            'dependencies', 
            'progress', 
            'subtasks', 
            'notes', 
            'custom_sections', 
            'task_id'  # task_id is added by to_dict
            'user_id', 'status', 
            'priority', 
            'assignees', 
            'labels',
            'title', 
            'description', 
            'estimated_effort', 
            'due_date'
        }
        
        custom_fields = {k: v for k, v in data.items() if k not in known_fields}
        if custom_fields:
            # Add custom fields as a special custom section
            custom_section = ContextCustomSection(
                name="root_level_custom_fields",
                data=custom_fields,
                schema_version="1.0"
            )
            context.custom_sections.append(custom_section)
        
        return context


class ContextSchema:
    """Context schema management and validation"""
    
    SCHEMA_VERSION = "1.0"
    
    @staticmethod
    def get_default_schema() -> Dict[str, Any]:
        """Get the default context JSON schema"""
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "title": "Task Context Schema",
            "description": "Schema for task context JSON files",
            "version": ContextSchema.SCHEMA_VERSION,
            "required": ["metadata", "objective"],
            "properties": {
                "metadata": {
                    "type": "object",
                    "required": ["task_id"],
                    "properties": {
                        "task_id": {"type": "string"},
                        "status": {"type": "string", "enum": ["todo", "in_progress", "blocked", "review", "testing", "done", "cancelled"]},
                        "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent", "critical"]},
                        "assignees": {"type": "array", "items": {"type": "string"}},
                        "labels": {"type": "array", "items": {"type": "string"}},
                        "created_at": {"type": "string", "format": "date-time"},
                        "updated_at": {"type": "string", "format": "date-time"},
                        "version": {"type": "integer", "minimum": 1}
                    }
                },
                "objective": {
                    "type": "object",
                    "required": ["title"],
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "estimated_effort": {"type": "string", "enum": ["quick", "short", "small", "medium", "large", "xlarge", "epic", "massive"]},
                        "due_date": {"type": ["string", "null"], "format": "date"}
                    }
                },
                "requirements": {
                    "type": "object",
                    "properties": {
                        "checklist": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["id", "title"],
                                "properties": {
                                    "id": {"type": "string"},
                                    "title": {"type": "string"},
                                    "completed": {"type": "boolean", "default": False},
                                    "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                                    "notes": {"type": "string"}
                                }
                            }
                        },
                        "custom_requirements": {"type": "array", "items": {"type": "string"}},
                        "completion_criteria": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "technical": {
                    "type": "object",
                    "properties": {
                        "technologies": {"type": "array", "items": {"type": "string"}},
                        "frameworks": {"type": "array", "items": {"type": "string"}},
                        "database": {"type": "string"},
                        "key_files": {"type": "array", "items": {"type": "string"}},
                        "key_directories": {"type": "array", "items": {"type": "string"}},
                        "architecture_notes": {"type": "string"},
                        "patterns_used": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "dependencies": {
                    "type": "object",
                    "properties": {
                        "task_dependencies": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["task_id"],
                                "properties": {
                                    "task_id": {"type": "string"},
                                    "title": {"type": "string"},
                                    "status": {"type": "string"},
                                    "blocking_reason": {"type": "string"}
                                }
                            }
                        },
                        "external_dependencies": {"type": "array", "items": {"type": "string"}},
                        "blocked_by": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "progress": {
                    "type": "object",
                    "properties": {
                        "completed_actions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["timestamp", "action", "agent"],
                                "properties": {
                                    "timestamp": {"type": "string", "format": "date-time"},
                                    "action": {"type": "string"},
                                    "agent": {"type": "string"},
                                    "details": {"type": "string"},
                                    "status": {"type": "string", "enum": ["completed", "in_progress", "failed"]}
                                }
                            }
                        },
                        "current_session_summary": {"type": "string"},
                        "next_steps": {"type": "array", "items": {"type": "string"}},
                        "completion_percentage": {"type": "number", "minimum": 0, "maximum": 100},
                        "time_spent_minutes": {"type": "integer", "minimum": 0}
                    }
                },
                "subtasks": {
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["id", "title"],
                                "properties": {
                                    "id": {"type": "string"},
                                    "title": {"type": "string"},
                                    "description": {"type": "string"},
                                    "status": {"type": "string", "enum": ["todo", "in_progress", "done", "cancelled"]},
                                    "assignees": {"type": "array", "items": {"type": "string"}},
                                    "completed": {"type": "boolean"},
                                    "progress_notes": {"type": "string"}
                                }
                            }
                        },
                        "total_count": {"type": "integer", "minimum": 0},
                        "completed_count": {"type": "integer", "minimum": 0},
                        "progress_percentage": {"type": "number", "minimum": 0, "maximum": 100}
                    }
                },
                "notes": {
                    "type": "object",
                    "properties": {
                        "agent_insights": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["timestamp", "agent", "category", "content"],
                                "properties": {
                                    "timestamp": {"type": "string", "format": "date-time"},
                                    "agent": {"type": "string"},
                                    "category": {"type": "string", "enum": ["insight", "challenge", "solution", "decision"]},
                                    "content": {"type": "string"},
                                    "importance": {"type": "string", "enum": ["low", "medium", "high", "critical"]}
                                }
                            }
                        },
                        "challenges_encountered": {"type": "array", "items": {"$ref": "#/properties/notes/properties/agent_insights/items"}},
                        "solutions_applied": {"type": "array", "items": {"$ref": "#/properties/notes/properties/agent_insights/items"}},
                        "decisions_made": {"type": "array", "items": {"$ref": "#/properties/notes/properties/agent_insights/items"}},
                        "general_notes": {"type": "string"}
                    }
                },
                "custom_sections": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["name"],
                        "properties": {
                            "name": {"type": "string"},
                            "data": {"type": "object"},
                            "schema_version": {"type": "string", "default": "1.0"}
                        }
                    }
                }
            }
        }
    
    @staticmethod
    def validate_context(context_data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate context data against schema"""
        errors = []
        
        # Basic validation
        if not isinstance(context_data, dict):
            errors.append("Context data must be a dictionary")
            return False, errors
        
        # Check required fields
        if 'metadata' not in context_data:
            errors.append("Missing required field: metadata")
        if 'objective' not in context_data:
            errors.append("Missing required field: objective")
        
        # Validate metadata
        if 'metadata' in context_data:
            metadata = context_data['metadata']
            if 'task_id' not in metadata:
                errors.append("Missing required field: metadata.task_id")
        
        # Validate objective
        if 'objective' in context_data:
            objective = context_data['objective']
            if 'title' not in objective:
                errors.append("Missing required field: objective.title")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def create_empty_context(task_id: str, title: str, **kwargs) -> TaskContext:
        """Create an empty context with minimal required fields (clean relationship chain)"""
        metadata = ContextMetadata(
            task_id=task_id,  # Only task_id following clean relationship chain
            status=TaskStatus(kwargs.get('status', TaskStatusEnum.TODO.value)),
            priority=Priority(kwargs.get('priority', PriorityLevel.MEDIUM.label)),
            assignees=kwargs.get('assignees', []),
            labels=kwargs.get('labels', [])
        )
        
        objective = ContextObjective(
            title=title,
            description=kwargs.get('description', ''),
            estimated_effort=kwargs.get('estimated_effort'),
            due_date=kwargs.get('due_date')
        )
        
        return TaskContext(metadata=metadata, objective=objective) 