#!/usr/bin/env python3
"""Database initialization - creates initial projects and branches if needed"""

import logging
import os
from typing import Optional
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class DatabaseInitializer:
    """Handles initial database setup with default projects and branches"""

    def __init__(self, database_url: Optional[str] = None):
        """Initialize with database connection"""
        if database_url:
            self.database_url = database_url
        else:
            # Build database URL from environment variables
            db_type = os.getenv('DATABASE_TYPE', 'postgresql')
            if db_type == 'postgresql':
                host = os.getenv('DATABASE_HOST', 'localhost')
                port = os.getenv('DATABASE_PORT', '5432')
                name = os.getenv('DATABASE_NAME', 'postgresdb')
                user = os.getenv('DATABASE_USER', 'agenthub_user')
                password = os.getenv('DATABASE_PASSWORD', 'agenthub_password')
                self.database_url = f"postgresql://{user}:{password}@{host}:{port}/{name}"
            else:
                # SQLite or other database types
                self.database_url = os.getenv('DATABASE_URL', 'sqlite:///agenthub_dev.db')

    def create_default_project(self, user_id: str) -> Optional[str]:
        """Create a default project for a user if they don't have any"""
        try:
            engine = create_engine(self.database_url)

            with engine.connect() as conn:
                trans = conn.begin()

                try:
                    # Check if user has any projects
                    result = conn.execute(text("""
                        SELECT id FROM projects
                        WHERE user_id = :user_id
                        LIMIT 1;
                    """), {"user_id": user_id})

                    existing_project = result.fetchone()

                    if existing_project:
                        logger.info(f"User {user_id} already has projects")
                        return str(existing_project[0])

                    # Create default project
                    project_id = str(uuid.uuid4())
                    now = datetime.now(timezone.utc)

                    logger.info(f"Creating default project for user {user_id}")
                    conn.execute(text("""
                        INSERT INTO projects (id, name, description, user_id, status, metadata, created_at, updated_at)
                        VALUES (:id, :name, :description, :user_id, :status, :metadata, :created_at, :updated_at);
                    """), {
                        "id": project_id,
                        "name": "My First Project",
                        "description": "Welcome to agenthub! This is your default project.",
                        "user_id": user_id,
                        "status": "active",
                        "metadata": "{}",
                        "created_at": now,
                        "updated_at": now
                    })

                    # Create default branch for the project
                    branch_id = str(uuid.uuid4())
                    conn.execute(text("""
                        INSERT INTO project_git_branchs (
                            id, project_id, name, description, user_id,
                            priority, status, metadata, task_count, completed_task_count,
                            created_at, updated_at
                        )
                        VALUES (
                            :id, :project_id, :name, :description, :user_id,
                            :priority, :status, :metadata, :task_count, :completed_task_count,
                            :created_at, :updated_at
                        );
                    """), {
                        "id": branch_id,
                        "project_id": project_id,
                        "name": "main",
                        "description": "Main development branch",
                        "user_id": user_id,
                        "priority": "medium",
                        "status": "active",
                        "metadata": "{}",
                        "task_count": 0,
                        "completed_task_count": 0,
                        "created_at": now,
                        "updated_at": now
                    })

                    trans.commit()
                    logger.info(f"✅ Created default project {project_id} and branch {branch_id}")
                    return project_id

                except Exception as e:
                    trans.rollback()
                    logger.error(f"Failed to create default project: {e}")
                    raise

        except Exception as e:
            logger.error(f"❌ Error creating default project: {e}")
            return None

    def initialize_for_user(self, user_id: str) -> bool:
        """Initialize database for a specific user"""
        try:
            logger.info(f"Initializing database for user {user_id}")

            # Create default project if needed
            project_id = self.create_default_project(user_id)

            if project_id:
                logger.info(f"✅ Database initialized for user {user_id}")
                return True
            else:
                logger.info(f"Database already initialized for user {user_id}")
                return True

        except Exception as e:
            logger.error(f"❌ Failed to initialize database for user: {e}")
            return False

    def ensure_tables_exist(self) -> bool:
        """Ensure all required tables exist in the database"""
        try:
            engine = create_engine(self.database_url)

            with engine.connect() as conn:
                # Check if main tables exist
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM information_schema.tables
                    WHERE table_name IN ('projects', 'project_git_branchs', 'tasks', 'subtasks');
                """))

                table_count = result.scalar()

                if table_count < 4:
                    logger.warning("Not all required tables exist. Please run database migrations first.")
                    return False

                logger.info("✅ All required tables exist")
                return True

        except Exception as e:
            logger.error(f"❌ Error checking tables: {e}")
            return False


def initialize_database_for_current_user() -> bool:
    """Initialize database for the current authenticated user"""
    try:
        # Get current user ID from environment or authentication context
        user_id = os.getenv('CURRENT_USER_ID')

        if not user_id:
            # Try to get from a test/default user
            user_id = os.getenv('DEFAULT_USER_ID', 'default-user-001')
            logger.info(f"Using default user ID: {user_id}")

        initializer = DatabaseInitializer()

        # First ensure tables exist
        if not initializer.ensure_tables_exist():
            logger.warning("Tables don't exist, skipping initialization")
            return False

        # Then initialize for the user
        return initializer.initialize_for_user(user_id)

    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        return False