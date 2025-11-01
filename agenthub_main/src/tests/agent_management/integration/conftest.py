"""
Integration Test Configuration for Agent Management

This module provides pytest fixtures for integration testing with a real database.
It sets up an isolated test database, creates schema, and handles cleanup.
"""

import pytest
import os
import json
import tempfile
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from fastmcp.task_management.infrastructure.database.database_config import DatabaseConfig, Base
from fastmcp.agent_management.infrastructure.database.models import (
    AgentTemplateORM,
    UserAgentInstanceORM
)
from fastmcp.agent_management.domain.entities import AgentTemplate, UserAgentInstance
from fastmcp.agent_management.domain.value_objects import (
    AgentTemplateId,
    UserAgentInstanceId,
    UserId,
    AgentConfiguration
)
from datetime import datetime, timezone


@pytest.fixture(scope="session")
def test_database_url():
    """
    Create a temporary SQLite database for integration tests.

    Uses SQLite in-memory database for fast, isolated testing.
    """
    # Use in-memory SQLite for fast tests
    return "sqlite:///:memory:"


@pytest.fixture(scope="session")
def test_engine(test_database_url):
    """
    Create SQLAlchemy engine for test database.

    Returns:
        Engine: SQLAlchemy engine configured for testing
    """
    engine = create_engine(
        test_database_url,
        echo=False,  # Set to True for SQL debugging
        connect_args={"check_same_thread": False}  # For SQLite threading
    )

    # Create all tables
    Base.metadata.create_all(engine)

    yield engine

    # Cleanup
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_engine):
    """
    Create a fresh database session for each test.

    Provides transaction isolation - each test gets a clean database state.

    Yields:
        Session: SQLAlchemy session for database operations
    """
    # Create session factory
    SessionLocal = sessionmaker(bind=test_engine)
    session = SessionLocal()

    # Start a transaction
    connection = test_engine.connect()
    transaction = connection.begin()

    # Bind session to transaction
    session = Session(bind=connection)

    yield session

    # Rollback transaction (undoes all changes)
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def sample_agent_template(db_session):
    """
    Create a sample agent template in the database for testing.

    Returns:
        AgentTemplate: A coding-agent template with full configuration
    """
    template_id = AgentTemplateId.generate_new()
    configuration = AgentConfiguration(
        system_prompt="You are a coding agent that helps with development tasks",
        tools=["Read", "Write", "Edit", "Bash", "Grep"],
        capabilities={
            "languages": ["Python", "JavaScript", "TypeScript"],
            "frameworks": ["FastAPI", "React"]
        },
        rules=["Write clean code", "Follow DRY principles", "Add tests"],
        output_format="markdown",
        metadata={"author": "test", "version": "1.0.0"}
    )

    # Create ORM model (serialize lists/dicts to JSON for SQLite compatibility)
    template_orm = AgentTemplateORM(
        id=str(template_id.value),
        slug="coding-agent",
        name="Coding Agent",
        description="Test coding agent for development tasks",
        category="development",
        version="1.0.0",
        system_prompt=configuration.system_prompt,
        tools=json.dumps(list(configuration.tools)),  # Serialize to JSON
        capabilities=json.dumps(configuration.capabilities),  # Serialize to JSON
        rules=json.dumps(list(configuration.rules)) if configuration.rules else None,  # Serialize to JSON
        output_format=configuration.output_format,
        metadata_json=json.dumps(configuration.metadata),  # Serialize to JSON
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    # Save to database
    db_session.add(template_orm)
    db_session.commit()
    db_session.refresh(template_orm)

    # Convert to domain entity
    template = AgentTemplate(
        id=template_id,
        slug=template_orm.slug,
        name=template_orm.name,
        description=template_orm.description,
        category=template_orm.category,
        version=template_orm.version,
        default_configuration=configuration,
        metadata=template_orm.metadata_json or {},
        created_at=template_orm.created_at,
        updated_at=template_orm.updated_at
    )

    return template


@pytest.fixture
def sample_user_id():
    """
    Generate a sample user ID for testing.

    Returns:
        UserId: A randomly generated user ID
    """
    return UserId.generate_new()


@pytest.fixture
def sample_user_instance(db_session, sample_agent_template, sample_user_id):
    """
    Create a sample user agent instance in the database.

    Returns:
        UserAgentInstance: A user's customized coding agent instance
    """
    instance_id = UserAgentInstanceId.generate_new()

    # Customized configuration
    custom_configuration = AgentConfiguration(
        system_prompt="Customized coding agent prompt for my workflow",
        tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob"],  # Added Glob
        capabilities={
            "languages": ["Python", "JavaScript", "TypeScript", "Go"],  # Added Go
            "frameworks": ["FastAPI", "React", "Next.js"]  # Added Next.js
        },
        rules=[
            "Write clean code",
            "Follow DRY principles",
            "Add tests",
            "Use type hints"  # Added custom rule
        ],
        output_format="markdown",
        metadata={}
    )

    # Create ORM model (serialize lists/dicts to JSON for SQLite compatibility)
    instance_orm = UserAgentInstanceORM(
        id=str(instance_id.value),
        user_id=str(sample_user_id.value),
        template_id=str(sample_agent_template.id.value),
        agent_name="My Custom Coding Agent",
        is_customized=True,
        customization_notes="Added Glob tool and Go language support",
        system_prompt=custom_configuration.system_prompt,
        tools=json.dumps(list(custom_configuration.tools)),  # Serialize to JSON
        capabilities=json.dumps(custom_configuration.capabilities),  # Serialize to JSON
        rules=json.dumps(list(custom_configuration.rules)) if custom_configuration.rules else None,  # Serialize to JSON
        output_format=custom_configuration.output_format,
        visibility="private",
        metadata_json=json.dumps({}),  # Serialize to JSON
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    # Save to database
    db_session.add(instance_orm)
    db_session.commit()
    db_session.refresh(instance_orm)

    # Convert to domain entity
    instance = UserAgentInstance(
        id=instance_id,
        user_id=sample_user_id,
        template_id=sample_agent_template.id,
        agent_name=instance_orm.agent_name,
        is_customized=instance_orm.is_customized,
        configuration=custom_configuration,
        visibility=instance_orm.visibility,
        last_used_at=None,  # Not in ORM model yet
        metadata={},
        created_at=instance_orm.created_at,
        updated_at=instance_orm.updated_at
    )

    return instance


@pytest.fixture(autouse=True)
def reset_database_config():
    """
    Reset DatabaseConfig singleton before each test.

    This ensures tests don't interfere with each other through shared state.
    """
    DatabaseConfig.reset_instance()
    yield
    DatabaseConfig.reset_instance()
