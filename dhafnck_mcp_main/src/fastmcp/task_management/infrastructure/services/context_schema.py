"""Context JSON Schema Definition and Validation"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import json
from pathlib import Path

# Import value objects
from ...domain.value_objects.task_status import TaskStatus, TaskStatusEnum
from ...domain.value_objects.priority import Priority, PriorityLevel


@dataclass
class ContextMetadata:
    """Context metadata structure (uses value objects)"""
    task_id: str
    project_id: str
    git_branch_id: str = "main"
    user_id: Optional[str] = None
    status: TaskStatus = field(default_factory=TaskStatus.todo)
    priority: Priority = field(default_factory=Priority.medium)
    assignees: List[str] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    version: str = "1.0"


@dataclass
class ContextObjective:
    """Task objective and description"""
    title: str
    description: str = ""
    estimated_effort: str = "medium"
    due_date: Optional[str] = None


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
    key_files: List[str] = field(default_factory=list)
    key_directories: List[str] = field(default_factory=list)
    architecture_notes: str = ""
    patterns_used: List[str] = field(default_factory=list)


@dataclass
class ContextDependency:
    """Dependency information (uses TaskStatus value object)"""
    task_id: str
    title: str = ""
    status: TaskStatus = field(default_factory=lambda: TaskStatus.from_string("unknown"))
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
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for JSON serialization"""
        def convert_dataclass(obj):
            if isinstance(obj, (TaskStatus, Priority)):
                return str(obj)
            elif hasattr(obj, '__dataclass_fields__'):
                return {k: convert_dataclass(v) for k, v in obj.__dict__.items()}
            elif isinstance(obj, list):
                return [convert_dataclass(item) for item in obj]
            elif isinstance(obj, dict):
                return {k: convert_dataclass(v) for k, v in obj.items()}
            else:
                return obj
        
        return convert_dataclass(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskContext':
        """Create TaskContext from dictionary"""
        # Handle metadata with value object conversion
        metadata_data = data.get('metadata', {})
        metadata = ContextMetadata(
            task_id=metadata_data.get('task_id', ''),
            project_id=metadata_data.get('project_id', ''),
            git_branch_id=metadata_data.get('git_branch_id', 'main'),
            user_id=metadata_data.get('user_id', ''),  # DDD: No fallback defaults
            status=TaskStatus.from_string(metadata_data.get('status', 'todo')),
            priority=Priority.from_string(metadata_data.get('priority', 'medium')),
            assignees=metadata_data.get('assignees', []),
            labels=metadata_data.get('labels', []),
            created_at=metadata_data.get('created_at', datetime.now().isoformat()),
            updated_at=metadata_data.get('updated_at', datetime.now().isoformat()),
            version=metadata_data.get('version', '1.0')
        )
        
        objective_data = data.get('objective', {})
        objective = ContextObjective(**objective_data)
        
        context = cls(metadata=metadata, objective=objective)
        
        # Load other sections if present with value object conversion
        if 'requirements' in data:
            req_data = data['requirements']
            requirements = ContextRequirements(
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
            context.requirements = requirements
            
        if 'technical' in data:
            context.technical = ContextTechnical(**data['technical'])
            
        if 'dependencies' in data:
            dep_data = data['dependencies']
            dependencies = ContextDependencies(
                task_dependencies=[
                    ContextDependency(
                        task_id=item.get('task_id', ''),
                        title=item.get('title', ''),
                        status=TaskStatus.from_string(item.get('status', 'unknown')),
                        blocking_reason=item.get('blocking_reason', '')
                    ) for item in dep_data.get('task_dependencies', [])
                ],
                external_dependencies=dep_data.get('external_dependencies', []),
                blocked_by=dep_data.get('blocked_by', [])
            )
            context.dependencies = dependencies
            
        if 'progress' in data:
            prog_data = data['progress']
            context.progress = ContextProgress(**prog_data)
            
        if 'subtasks' in data:
            sub_data = data['subtasks']
            subtasks = ContextSubtasks(
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
            context.subtasks = subtasks
            
        if 'notes' in data:
            notes_data = data['notes']
            context.notes = ContextNotes(**notes_data)
            
        if 'custom_sections' in data:
            context.custom_sections = [ContextCustomSection(**section) for section in data['custom_sections']]
        
        return context


class ContextSchema:
    """Context schema management and validation"""
    
    SCHEMA_VERSION = "1.0"
    
    @staticmethod
    def get_default_schema() -> Dict[str, Any]:
        """Get the default context schema"""
        return {
            "version": ContextSchema.SCHEMA_VERSION,
            "type": "object",
            "required": ["metadata", "objective"],
            "properties": {
                "metadata": {
                    "type": "object",
                    "required": ["task_id", "project_id"],
                    "properties": {
                        "task_id": {"type": "string"},
                        "project_id": {"type": "string"},
                        "git_branch_id": {"type": "string", "default": "main"},
                        "user_id": {"type": ["string", "null"], "default": null},
                        "status": {"type": "string", "enum": [status.value for status in TaskStatusEnum]},
                        "priority": {"type": "string", "enum": [priority.label for priority in PriorityLevel]},
                        "assignees": {"type": "array", "items": {"type": "string"}},
                        "labels": {"type": "array", "items": {"type": "string"}},
                        "created_at": {"type": "string", "format": "date-time"},
                        "updated_at": {"type": "string", "format": "date-time"},
                        "version": {"type": "string", "default": "1.0"}
                    }
                },
                "objective": {
                    "type": "object",
                    "required": ["title"],
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "estimated_effort": {"type": "string"},
                        "due_date": {"type": ["string", "null"], "format": "date-time"}
                    }
                },
                "requirements": {
                    "type": "object",
                    "properties": {
                        "checklist": {"type": "array", "items": {"$ref": "#/definitions/requirement"}},
                        "custom_requirements": {"type": "array", "items": {"type": "string"}},
                        "completion_criteria": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "technical": {
                    "type": "object",
                    "properties": {
                        "technologies": {"type": "array", "items": {"type": "string"}},
                        "frameworks": {"type": "array", "items": {"type": "string"}},
                        "key_files": {"type": "array", "items": {"type": "string"}},
                        "key_directories": {"type": "array", "items": {"type": "string"}},
                        "architecture_notes": {"type": "string"},
                        "patterns_used": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "dependencies": {
                    "type": "object",
                    "properties": {
                        "task_dependencies": {"type": "array", "items": {"$ref": "#/definitions/dependency"}},
                        "external_dependencies": {"type": "array", "items": {"type": "string"}},
                        "blocked_by": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "progress": {
                    "type": "object",
                    "properties": {
                        "completed_actions": {"type": "array", "items": {"$ref": "#/definitions/action"}},
                        "current_session_summary": {"type": "string"},
                        "next_steps": {"type": "array", "items": {"type": "string"}},
                        "completion_percentage": {"type": "number", "minimum": 0, "maximum": 100},
                        "time_spent_minutes": {"type": "integer", "minimum": 0}
                    }
                },
                "subtasks": {
                    "type": "object",
                    "properties": {
                        "items": {"type": "array", "items": {"$ref": "#/definitions/subtask"}},
                        "total_count": {"type": "integer", "minimum": 0},
                        "completed_count": {"type": "integer", "minimum": 0},
                        "progress_percentage": {"type": "number", "minimum": 0, "maximum": 100}
                    }
                },
                "notes": {
                    "type": "object",
                    "properties": {
                        "agent_insights": {"type": "array", "items": {"$ref": "#/definitions/insight"}},
                        "challenges_encountered": {"type": "array", "items": {"$ref": "#/definitions/insight"}},
                        "solutions_applied": {"type": "array", "items": {"$ref": "#/definitions/insight"}},
                        "decisions_made": {"type": "array", "items": {"$ref": "#/definitions/insight"}},
                        "general_notes": {"type": "string"}
                    }
                },
                "custom_sections": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["name", "data"],
                        "properties": {
                            "name": {"type": "string"},
                            "data": {"type": "object"},
                            "schema_version": {"type": "string"}
                        }
                    }
                }
            },
            "definitions": {
                "requirement": {
                    "type": "object",
                    "required": ["id", "title"],
                    "properties": {
                        "id": {"type": "string"},
                        "title": {"type": "string"},
                        "completed": {"type": "boolean"},
                        "priority": {"type": "string", "enum": [priority.label for priority in PriorityLevel]},
                        "notes": {"type": "string"}
                    }
                },
                "dependency": {
                    "type": "object",
                    "required": ["task_id"],
                    "properties": {
                        "task_id": {"type": "string"},
                        "title": {"type": "string"},
                        "status": {"type": "string", "enum": [status.value for status in TaskStatusEnum] + ["unknown"]},
                        "blocking_reason": {"type": "string"}
                    }
                },
                "action": {
                    "type": "object",
                    "required": ["timestamp", "action", "agent"],
                    "properties": {
                        "timestamp": {"type": "string", "format": "date-time"},
                        "action": {"type": "string"},
                        "agent": {"type": "string"},
                        "details": {"type": "string"},
                        "status": {"type": "string"}
                    }
                },
                "subtask": {
                    "type": "object",
                    "required": ["id", "title"],
                    "properties": {
                        "id": {"type": "string"},
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "status": {"type": "string", "enum": [status.value for status in TaskStatusEnum]},
                        "assignees": {"type": "array", "items": {"type": "string"}},
                        "completed": {"type": "boolean"},
                        "progress_notes": {"type": "string"}
                    }
                },
                "insight": {
                    "type": "object",
                    "required": ["timestamp", "agent", "category", "content"],
                    "properties": {
                        "timestamp": {"type": "string", "format": "date-time"},
                        "agent": {"type": "string"},
                        "category": {"type": "string"},
                        "content": {"type": "string"},
                        "importance": {"type": "string", "enum": ["low", "medium", "high", "critical"]}
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
        
        # Check required sections
        required_sections = ["metadata", "objective"]
        for section in required_sections:
            if section not in context_data:
                errors.append(f"Missing required section: {section}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def create_empty_context(task_id: str, project_id: str, title: str, **kwargs) -> TaskContext:
        """Create an empty context with basic information"""
        metadata = ContextMetadata(
            task_id=task_id,
            project_id=project_id,
            git_branch_id=kwargs.get('git_branch_id', 'main'),
            user_id=kwargs.get('user_id', ''),  # DDD: No fallback defaults
            status=TaskStatus.from_string(kwargs.get('status', 'todo')),
            priority=Priority.from_string(kwargs.get('priority', 'medium')),
            assignees=kwargs.get('assignees', []),
            labels=kwargs.get('labels', [])
        )
        
        objective = ContextObjective(
            title=title,
            description=kwargs.get('description', ''),
            estimated_effort=kwargs.get('estimated_effort', 'medium'),
            due_date=kwargs.get('due_date')
        )
        
        return TaskContext(metadata=metadata, objective=objective) 