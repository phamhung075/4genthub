"""
SQLAlchemy ORM Models for Task Management System

This module defines all database models using SQLAlchemy ORM,
supporting both SQLite and PostgreSQL databases.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column, String, Text, DateTime, Integer, Boolean, ForeignKey,
    UniqueConstraint, CheckConstraint, Index, JSON, Float
)
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from .database_config import Base
from .uuid_column_type import UnifiedUUID, create_uuid_column

# User-scoped global context approach implemented
# Each user gets their own global context with unique UUIDs

# Global context singleton UUID (used as a reference ID)
GLOBAL_SINGLETON_UUID = "00000000-0000-0000-0000-000000000001"


class APIToken(Base):
    """API Token model for MCP authentication"""
    __tablename__ = "api_tokens"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    token_hash: Mapped[str] = mapped_column(String, nullable=False)  # Store hashed token
    scopes: Mapped[List[str]] = mapped_column(JSON, default=list)  # List of permission scopes
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    rate_limit: Mapped[int] = mapped_column(Integer, default=1000)  # Requests per hour
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    token_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)  # Additional metadata


class Project(Base):
    """Project model - Core organizational structure"""
    __tablename__ = "projects"
    
    id: Mapped[str] = mapped_column(UnifiedUUID, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    user_id: Mapped[str] = mapped_column(String, nullable=False)  # No default - authentication required
    status: Mapped[str] = mapped_column(String, default="active")
    model_metadata: Mapped[Dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    
    # Relationships
    git_branchs: Mapped[List["ProjectGitBranch"]] = relationship("ProjectGitBranch", back_populates="project", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('id', 'user_id', name='uq_project_user'),
    )


class ProjectGitBranch(Base):
    """Git branches (task trees) - Project workspaces"""
    __tablename__ = "project_git_branchs"
    
    id: Mapped[str] = mapped_column(UnifiedUUID, primary_key=True)
    project_id: Mapped[str] = mapped_column(UnifiedUUID, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    assigned_agent_id: Mapped[Optional[str]] = mapped_column(String)
    agent_id: Mapped[Optional[str]] = mapped_column(UnifiedUUID)  # Fixed: Using UnifiedUUID for cross-database compatibility
    priority: Mapped[str] = mapped_column(String, default="medium")
    status: Mapped[str] = mapped_column(String, default="todo")
    model_metadata: Mapped[Dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    task_count: Mapped[int] = mapped_column(Integer, default=0)
    completed_task_count: Mapped[int] = mapped_column(Integer, default=0)
    user_id: Mapped[str] = mapped_column(String, nullable=False)  # User isolation field - REQUIRED
    
    # Relationships
    project: Mapped[Project] = relationship("Project", back_populates="git_branchs")
    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="git_branch", cascade="all, delete-orphan")
    branch_context: Mapped[Optional["BranchContext"]] = relationship("BranchContext", back_populates="git_branch", uselist=False)
    
    __table_args__ = (
        UniqueConstraint('id', 'project_id', name='uq_branch_project'),
    )


class Task(Base):
    """Main tasks table"""
    __tablename__ = "tasks"
    
    id: Mapped[str] = mapped_column(UnifiedUUID, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    git_branch_id: Mapped[str] = mapped_column(UnifiedUUID, ForeignKey("project_git_branchs.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="todo")
    priority: Mapped[str] = mapped_column(String, nullable=False, default="medium")
    details: Mapped[str] = mapped_column(Text, default="")
    estimated_effort: Mapped[str] = mapped_column(String, default="2 hours", nullable=False)
    due_date: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)  # Added for schema validation
    completion_summary: Mapped[str] = mapped_column(Text, default="")  # Added for schema validation
    testing_notes: Mapped[str] = mapped_column(Text, default="")  # Added for schema validation
    context_id: Mapped[Optional[str]] = mapped_column(UnifiedUUID)
    progress_percentage: Mapped[int] = mapped_column(Integer, default=0)
    user_id: Mapped[str] = mapped_column(String, nullable=False)  # User isolation field - REQUIRED (using String for Keycloak UUID)
    
    # Relationships
    git_branch: Mapped[ProjectGitBranch] = relationship("ProjectGitBranch", back_populates="tasks")
    subtasks: Mapped[List["TaskSubtask"]] = relationship("TaskSubtask", back_populates="task", cascade="all, delete-orphan")
    assignees: Mapped[List["TaskAssignee"]] = relationship("TaskAssignee", back_populates="task", cascade="all, delete-orphan")
    dependencies: Mapped[List["TaskDependency"]] = relationship("TaskDependency", foreign_keys="TaskDependency.task_id", back_populates="task", cascade="all, delete-orphan")
    labels: Mapped[List["TaskLabel"]] = relationship("TaskLabel", back_populates="task", cascade="all, delete-orphan")
    task_context: Mapped[Optional["TaskContext"]] = relationship("TaskContext", back_populates="task", uselist=False)
    
    # Create indexes for performance
    __table_args__ = (
        Index('idx_task_branch', 'git_branch_id'),
        Index('idx_task_status', 'status'),
        Index('idx_task_priority', 'priority'),
        Index('idx_task_created', 'created_at'),
    )


class TaskSubtask(Base):
    """Subtasks table"""
    __tablename__ = "task_subtasks"
    
    id: Mapped[str] = mapped_column(UnifiedUUID, primary_key=True)
    task_id: Mapped[str] = mapped_column(UnifiedUUID, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String, nullable=False, default="todo")
    priority: Mapped[str] = mapped_column(String, nullable=False, default="medium")
    assignees: Mapped[List[str]] = mapped_column(JSON, default=list)
    estimated_effort: Mapped[Optional[str]] = mapped_column(String)
    progress_percentage: Mapped[int] = mapped_column(Integer, default=0)
    progress_notes: Mapped[str] = mapped_column(Text, default="")
    blockers: Mapped[str] = mapped_column(Text, default="")
    completion_summary: Mapped[str] = mapped_column(Text, default="")
    impact_on_parent: Mapped[str] = mapped_column(Text, default="")
    insights_found: Mapped[List[str]] = mapped_column(JSON, default=list)
    user_id: Mapped[str] = mapped_column(String, nullable=False)  # Keycloak user ID - String type for UUID strings
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Relationships
    task: Mapped[Task] = relationship("Task", back_populates="subtasks")
    
    # Indexes
    __table_args__ = (
        Index('idx_subtask_task', 'task_id'),
        Index('idx_subtask_status', 'status'),
    )


class TaskAssignee(Base):
    """Task assignees table"""
    __tablename__ = "task_assignees"
    
    id: Mapped[str] = mapped_column(UnifiedUUID, primary_key=True)
    task_id: Mapped[str] = mapped_column(UnifiedUUID, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    assignee_id: Mapped[str] = mapped_column(String, nullable=False)
    agent_id: Mapped[Optional[str]] = mapped_column(UnifiedUUID)  # Fixed: Using UnifiedUUID for cross-database compatibility
    role: Mapped[str] = mapped_column(String, default="contributor")
    user_id: Mapped[str] = mapped_column(String, nullable=False)  # User isolation field - REQUIRED
    assigned_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    # Relationships
    task: Mapped[Task] = relationship("Task", back_populates="assignees")
    
    __table_args__ = (
        UniqueConstraint('task_id', 'assignee_id', name='uq_task_assignee'),
        Index('idx_assignee_task', 'task_id'),
        Index('idx_assignee_id', 'assignee_id'),
    )


class TaskDependency(Base):
    """Task dependencies table"""
    __tablename__ = "task_dependencies"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(UnifiedUUID, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    depends_on_task_id: Mapped[str] = mapped_column(UnifiedUUID, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    dependency_type: Mapped[str] = mapped_column(String, default="blocks")
    user_id: Mapped[str] = mapped_column(String, nullable=False)  # Keycloak user ID - String type for UUID strings
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    # Relationships
    task: Mapped[Task] = relationship("Task", foreign_keys=[task_id], back_populates="dependencies")
    depends_on: Mapped[Task] = relationship("Task", foreign_keys=[depends_on_task_id])
    
    __table_args__ = (
        UniqueConstraint('task_id', 'depends_on_task_id', name='uq_task_dependency'),
        CheckConstraint('task_id != depends_on_task_id', name='chk_no_self_dependency'),
    )


class Agent(Base):
    """Agents table"""
    __tablename__ = "agents"
    
    id: Mapped[str] = mapped_column(UnifiedUUID, primary_key=True)  # Entity ID - UnifiedUUID for cross-database compatibility
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    role: Mapped[str] = mapped_column(String, default="assistant")
    capabilities: Mapped[List[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String, default="available")
    availability_score: Mapped[float] = mapped_column(Float, default=1.0)
    last_active_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    model_metadata: Mapped[Dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    user_id: Mapped[str] = mapped_column(String, nullable=False)  # Keycloak user ID - String type for UUID strings
    
    # Indexes
    __table_args__ = (
        Index('idx_agent_status', 'status'),
        Index('idx_agent_availability', 'availability_score'),
    )


# HierarchicalContext model removed - replaced with granular context models (GlobalContext, ProjectContext, BranchContext, TaskContext)


class Label(Base):
    """Labels table"""
    __tablename__ = "labels"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    color: Mapped[str] = mapped_column(String, default="#0066cc")
    description: Mapped[str] = mapped_column(Text, default="")
    user_id: Mapped[str] = mapped_column(String, nullable=False)  # Required for data isolation - no defaults per DDD
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    # Relationships
    task_labels: Mapped[List["TaskLabel"]] = relationship("TaskLabel", back_populates="label", cascade="all, delete-orphan")


class TaskLabel(Base):
    """Task labels relationship table"""
    __tablename__ = "task_labels"
    
    task_id: Mapped[str] = mapped_column(UnifiedUUID, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True)
    label_id: Mapped[str] = mapped_column(String, ForeignKey("labels.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False)  # User isolation field - REQUIRED
    applied_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    # Relationships
    task: Mapped[Task] = relationship("Task", back_populates="labels")
    label: Mapped[Label] = relationship("Label", back_populates="task_labels")
    
    __table_args__ = (
        Index('idx_task_label_task', 'task_id'),
        Index('idx_task_label_label', 'label_id'),
    )


class Template(Base):
    """Templates table"""
    __tablename__ = "templates"
    
    id: Mapped[str] = mapped_column(UnifiedUUID, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    template_name: Mapped[str] = mapped_column(String, nullable=False, default="")  # Added for schema validation
    template_content: Mapped[str] = mapped_column(Text, default="")  # Fixed: Database has TEXT type
    template_type: Mapped[str] = mapped_column(String, default="general")  # Added for schema validation
    type: Mapped[str] = mapped_column(String, nullable=False)  # 'task', 'checklist', 'workflow'
    content: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    category: Mapped[str] = mapped_column(String, default="general")
    tags: Mapped[List[str]] = mapped_column(JSON, default=list)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # Optional for shared templates
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by: Mapped[str] = mapped_column(String, nullable=False)  # DDD: No default, user context required
    metadata_: Mapped[Dict[str, Any]] = mapped_column("metadata", JSON, default=dict)  # Added for schema validation
    
    __table_args__ = (
        Index('idx_template_type', 'type'),
        Index('idx_template_category', 'category'),
    )


class GlobalContext(Base):
    """Global contexts table - user-scoped organizational context with nested categorization support"""
    __tablename__ = "global_contexts"
    
    # All IDs are now UUID
    id: Mapped[str] = mapped_column(UnifiedUUID, primary_key=True, default=lambda: str(uuid.uuid4()))  # Fixed: Added default UUID generation
    organization_id: Mapped[str] = mapped_column(UnifiedUUID, nullable=True)  # Optional org ID
    
    # Core organizational configuration (flat structure - maintained for backward compatibility)
    organization_standards: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)  # Coding style, git workflow, testing requirements
    security_policies: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)  # Authentication, encryption, access control
    compliance_requirements: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)  # GDPR, HIPAA, SOC2, etc.
    shared_resources: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)  # API keys, service accounts, shared tools
    reusable_patterns: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)  # Design patterns, code templates
    global_preferences: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)  # User preferences, UI settings
    delegation_rules: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)  # Auto-delegation configuration
    
    # Nested structure support (v2.0) - New field for organized categorization
    nested_structure: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)  # Modern nested structure
    
    # User isolation - required by database migration
    user_id: Mapped[str] = mapped_column(String, nullable=False)  # User isolation field - REQUIRED
    
    # Timestamps and versioning
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    version: Mapped[int] = mapped_column(Integer, default=1)
    
    # Relationships with explicit primaryjoin
    project_contexts: Mapped[List["ProjectContext"]] = relationship(
        "ProjectContext", 
        primaryjoin="GlobalContext.id == ProjectContext.parent_global_id",
        back_populates="global_context", 
        cascade="all, delete-orphan"
    )


class ProjectContext(Base):
    """Project contexts table - inherits from global context"""
    __tablename__ = "project_contexts"
    
    # Primary key - matches actual database schema
    id: Mapped[str] = mapped_column(UnifiedUUID, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Foreign keys - all UUID now
    project_id: Mapped[Optional[str]] = mapped_column(UnifiedUUID, nullable=True)
    parent_global_id: Mapped[Optional[str]] = mapped_column(UnifiedUUID, ForeignKey("global_contexts.id"), nullable=True)
    
    # Data field (used in actual database)
    data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)
    
    # Project-specific configuration (matching CONTEXT_DATA_MODELS.md)
    project_info: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)  # Name, description, version, status
    team_preferences: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)  # Review requirements, merge strategy, notification settings
    technology_stack: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)  # Frontend, backend, database, infrastructure
    project_workflow: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)  # Phases, gates, approval processes
    local_standards: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)  # Project-specific standards and conventions
    project_settings: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)  # Build configs, deployment settings, env vars
    technical_specifications: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)  # API specs, database schemas, architecture
    global_overrides: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)  # Overrides of global settings
    delegation_rules: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)  # Project-specific delegation rules
    
    # User isolation
    user_id: Mapped[str] = mapped_column(String, nullable=False)  # REQUIRED for user isolation
    
    # Timestamps and versioning
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, server_default=func.now(), onupdate=func.now())
    version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=1)
    inheritance_disabled: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=False)
    
    # Relationships with explicit primaryjoin
    global_context: Mapped[Optional[GlobalContext]] = relationship(
        "GlobalContext", 
        primaryjoin="ProjectContext.parent_global_id == GlobalContext.id",
        back_populates="project_contexts"
    )
    branch_contexts: Mapped[List["BranchContext"]] = relationship(
        "BranchContext", 
        primaryjoin="ProjectContext.id == BranchContext.parent_project_id",
        back_populates="project_context", 
        cascade="all, delete-orphan"
    )


class BranchContext(Base):
    """Branch contexts table - inherits from project context"""
    __tablename__ = "branch_contexts"
    
    # Primary key - matches actual database schema
    id: Mapped[str] = mapped_column(UnifiedUUID, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Foreign keys
    branch_id: Mapped[Optional[str]] = mapped_column(UnifiedUUID, ForeignKey("project_git_branchs.id"), nullable=True)
    parent_project_id: Mapped[Optional[str]] = mapped_column(UnifiedUUID, ForeignKey("project_contexts.id"), nullable=True)
    
    # Data field (used in actual database)
    data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)
    
    # Branch-specific configuration (matching CONTEXT_DATA_MODELS.md)
    branch_info: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)  # Feature name, type, status, parent branch
    branch_workflow: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)  # Implementation status, dependencies installed, endpoints created
    feature_flags: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)  # Feature toggles and configuration
    discovered_patterns: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)  # Patterns discovered during development
    branch_decisions: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)  # Technical decisions made for this feature
    active_patterns: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)  # Currently active patterns and approaches
    local_overrides: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)  # Branch-specific overrides
    delegation_rules: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)  # Branch-specific delegation rules
    
    # Control flags
    inheritance_disabled: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=False)
    
    # User isolation - required by database migration
    user_id: Mapped[str] = mapped_column(String, nullable=False)  # User isolation field - REQUIRED
    
    # Timestamps and versioning
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, server_default=func.now(), onupdate=func.now())
    version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=1)
    
    # Relationships with explicit primaryjoin
    project_context: Mapped[Optional["ProjectContext"]] = relationship(
        "ProjectContext", 
        primaryjoin="BranchContext.parent_project_id == ProjectContext.id",
        back_populates="branch_contexts"
    )
    git_branch: Mapped[Optional["ProjectGitBranch"]] = relationship(
        "ProjectGitBranch", 
        primaryjoin="BranchContext.branch_id == ProjectGitBranch.id",
        back_populates="branch_context"
    )
    task_contexts: Mapped[List["TaskContext"]] = relationship(
        "TaskContext", 
        primaryjoin="BranchContext.id == TaskContext.parent_branch_context_id",
        back_populates="branch_context", 
        cascade="all, delete-orphan"
    )


class TaskContext(Base):
    """Task contexts table - inherits from branch context"""
    __tablename__ = "task_contexts"
    
    # Primary key - matches actual database schema
    id: Mapped[str] = mapped_column(UnifiedUUID, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Foreign keys
    task_id: Mapped[Optional[str]] = mapped_column(UnifiedUUID, ForeignKey("tasks.id"), nullable=True)
    parent_branch_id: Mapped[Optional[str]] = mapped_column(UnifiedUUID, ForeignKey("project_git_branchs.id"), nullable=True)
    parent_branch_context_id: Mapped[Optional[str]] = mapped_column(UnifiedUUID, ForeignKey("branch_contexts.id"), nullable=True)
    
    # Data field (used in actual database)
    data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)
    
    # Task-specific data (matching CONTEXT_DATA_MODELS.md)
    task_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)  # Title, status, progress, assignees
    execution_context: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)  # Files modified, tests added, current work
    discovered_patterns: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)  # Patterns found during implementation
    implementation_notes: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)  # Challenges, solutions, next steps
    test_results: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)  # Test outcomes, coverage, failing tests
    blockers: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)  # Current impediments and dependencies
    local_decisions: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)  # Task-specific technical decisions
    delegation_queue: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)  # Items to delegate to higher levels
    local_overrides: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)  # Task-specific overrides
    delegation_triggers: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)  # Automatic delegation conditions
    
    # Control flags
    inheritance_disabled: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=False)
    force_local_only: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=False)
    
    # User isolation - required by database migration
    user_id: Mapped[str] = mapped_column(String, nullable=False)  # User isolation field - REQUIRED
    
    # Timestamps and versioning
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, server_default=func.now(), onupdate=func.now())
    version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=1)
    
    # Relationships with explicit primaryjoin
    branch_context: Mapped[Optional["BranchContext"]] = relationship(
        "BranchContext", 
        primaryjoin="TaskContext.parent_branch_context_id == BranchContext.id",
        back_populates="task_contexts"
    )
    git_branch: Mapped[Optional["ProjectGitBranch"]] = relationship(
        "ProjectGitBranch", 
        primaryjoin="TaskContext.parent_branch_id == ProjectGitBranch.id"
    )
    task: Mapped[Optional["Task"]] = relationship(
        "Task", 
        primaryjoin="TaskContext.task_id == Task.id",
        back_populates="task_context"
    )


class ContextDelegation(Base):
    """Context delegations table - for hierarchical context propagation"""
    __tablename__ = "context_delegations"
    
    id: Mapped[str] = mapped_column(UnifiedUUID, primary_key=True)
    
    # Source and target
    source_level: Mapped[str] = mapped_column(String, nullable=False)  # 'task', 'project', 'global'
    source_id: Mapped[str] = mapped_column(UnifiedUUID, nullable=False)
    source_type: Mapped[str] = mapped_column(String, default="context")  # Added for schema validation
    target_level: Mapped[str] = mapped_column(String, nullable=False)
    target_id: Mapped[str] = mapped_column(UnifiedUUID, nullable=False)
    target_type: Mapped[str] = mapped_column(String, default="context")  # Added for schema validation
    
    # Delegation data
    delegated_data: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    delegation_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)  # Added for schema validation
    delegation_reason: Mapped[str] = mapped_column(String, nullable=False)
    trigger_type: Mapped[str] = mapped_column(String, nullable=False)  # 'manual', 'auto_pattern', 'auto_threshold'
    
    # Processing status
    auto_delegated: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String, default="pending")  # Added for schema validation
    approved: Mapped[Optional[bool]] = mapped_column(Boolean)
    processed_by: Mapped[Optional[str]] = mapped_column(String)
    rejected_reason: Mapped[Optional[str]] = mapped_column(String)
    error_message: Mapped[Optional[str]] = mapped_column(String)  # Added for schema validation
    user_id: Mapped[str] = mapped_column(String, nullable=False)  # User isolation field - REQUIRED
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    __table_args__ = (
        CheckConstraint("source_level IN ('task', 'branch', 'project', 'global')", name='chk_source_level'),
        CheckConstraint("target_level IN ('task', 'branch', 'project', 'global')", name='chk_target_level'),
        CheckConstraint("trigger_type IN ('manual', 'auto_pattern', 'auto_threshold')", name='chk_trigger_type'),
        Index('idx_delegation_source', 'source_level', 'source_id'),
        Index('idx_delegation_target', 'target_level', 'target_id'),
        Index('idx_delegation_processed', 'processed'),
    )


class ContextInheritanceCache(Base):
    """Context inheritance cache table - for performance optimization"""
    __tablename__ = "context_inheritance_cache"
    
    id: Mapped[str] = mapped_column(UnifiedUUID, primary_key=True, default=lambda: str(uuid.uuid4()))  # Added for schema validation
    context_id: Mapped[str] = mapped_column(UnifiedUUID, nullable=False)
    context_level: Mapped[str] = mapped_column(String, nullable=False)  # 'task', 'branch', 'project', 'global'
    context_type: Mapped[str] = mapped_column(String, default="hierarchical")  # Added for schema validation
    
    # Cache data
    resolved_context: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    resolved_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)  # Added for schema validation
    dependencies_hash: Mapped[str] = mapped_column(String, nullable=False)
    resolution_path: Mapped[str] = mapped_column(String, nullable=False)
    parent_chain: Mapped[List[str]] = mapped_column(JSON, default=list)  # SQLite compatible: Using JSON instead of ARRAY
    
    # Cache metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    last_hit: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    cache_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Invalidation tracking
    invalidated: Mapped[bool] = mapped_column(Boolean, default=False)
    invalidation_reason: Mapped[Optional[str]] = mapped_column(String)
    user_id: Mapped[str] = mapped_column(String, nullable=False)  # User isolation field - REQUIRED
    
    __table_args__ = (
        CheckConstraint("context_level IN ('task', 'branch', 'project', 'global')", name='chk_cache_context_level'),
        UniqueConstraint('context_id', 'context_level', name='uq_cache_context'),  # Updated unique constraint
        Index('idx_cache_level', 'context_level'),
        Index('idx_cache_expires', 'expires_at'),
        Index('idx_cache_invalidated', 'invalidated'),
    )