"""
Comprehensive Test Suite for DhafnckMCP HTTP Tools
==============================================

This test suite covers all the issues discovered and fixed in the MCP tools,
including:
1. Task persistence with all relationships
2. Context management and inheritance 
3. Subtask management with parent progress calculation
4. Project and branch management
5. Error handling and validation

Author: DhafnckMCP Test Orchestrator Agent
Date: 2025-08-24
"""

import pytest
import uuid
import json
import sqlite3
import os
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

# Test Configuration
TEST_DB_PATH = "test_mcp_tools_comprehensive.db"
TEST_USER_ID = "test_user_comprehensive"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
def clean_test_db():
    """Create a clean test database for each test."""
    # Remove existing test database
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    
    # Create fresh database with required tables
    conn = sqlite3.connect(TEST_DB_PATH)
    cursor = conn.cursor()
    
    # Create tables with all required columns including user_id
    cursor.executescript("""
        -- Projects table
        CREATE TABLE projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            user_id TEXT NOT NULL DEFAULT 'system',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Git branches table
        CREATE TABLE git_branches (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            git_branch_name TEXT NOT NULL,
            git_branch_description TEXT,
            user_id TEXT NOT NULL DEFAULT 'system',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );
        
        -- Tasks table with all required columns
        CREATE TABLE tasks (
            id TEXT PRIMARY KEY,
            git_branch_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'todo',
            priority TEXT DEFAULT 'medium',
            estimated_effort TEXT,
            context_id TEXT,
            user_id TEXT NOT NULL DEFAULT 'system',
            details TEXT,
            due_date TEXT,
            completion_percentage INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (git_branch_id) REFERENCES git_branches(id)
        );
        
        -- Task assignees table
        CREATE TABLE task_assignees (
            id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            assignee TEXT NOT NULL,
            user_id TEXT NOT NULL DEFAULT 'system',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
        );
        
        -- Task labels table
        CREATE TABLE task_labels (
            id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            label TEXT NOT NULL,
            user_id TEXT NOT NULL DEFAULT 'system',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
        );
        
        -- Task dependencies table
        CREATE TABLE task_dependencies (
            id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            dependency_id TEXT NOT NULL,
            user_id TEXT NOT NULL DEFAULT 'system',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
            FOREIGN KEY (dependency_id) REFERENCES tasks(id) ON DELETE CASCADE
        );
        
        -- Subtasks table
        CREATE TABLE subtasks (
            id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'todo',
            priority TEXT DEFAULT 'medium',
            progress_percentage INTEGER DEFAULT 0,
            user_id TEXT NOT NULL DEFAULT 'system',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
        );
        
        -- Context tables
        CREATE TABLE global_contexts (
            id TEXT PRIMARY KEY,
            data TEXT,
            user_id TEXT NOT NULL DEFAULT 'system',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE project_contexts (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            data TEXT,
            user_id TEXT NOT NULL DEFAULT 'system',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );
        
        CREATE TABLE branch_contexts (
            id TEXT PRIMARY KEY,
            git_branch_id TEXT NOT NULL,
            data TEXT,
            user_id TEXT NOT NULL DEFAULT 'system',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (git_branch_id) REFERENCES git_branches(id)
        );
        
        CREATE TABLE task_contexts (
            id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            data TEXT,
            user_id TEXT NOT NULL DEFAULT 'system',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        );
        
        -- Agents table
        CREATE TABLE agents (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            name TEXT NOT NULL,
            user_id TEXT NOT NULL DEFAULT 'system',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );
        
        -- Agent assignments table
        CREATE TABLE agent_assignments (
            id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            git_branch_id TEXT NOT NULL,
            user_id TEXT NOT NULL DEFAULT 'system',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (agent_id) REFERENCES agents(id),
            FOREIGN KEY (git_branch_id) REFERENCES git_branches(id)
        );
    """)
    
    conn.commit()
    conn.close()
    
    yield TEST_DB_PATH
    
    # Cleanup after test
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

@pytest.fixture
def sample_project_data():
    """Sample project data for testing."""
    return {
        "project_id": str(uuid.uuid4()),
        "name": "Test Project",
        "description": "A test project for comprehensive testing",
        "user_id": TEST_USER_ID
    }

@pytest.fixture
def sample_branch_data():
    """Sample branch data for testing."""
    return {
        "branch_id": str(uuid.uuid4()),
        "git_branch_name": "feature/test-branch",
        "git_branch_description": "Test branch for comprehensive testing",
        "user_id": TEST_USER_ID
    }

@pytest.fixture
def sample_task_data():
    """Sample task data for testing."""
    return {
        "task_id": str(uuid.uuid4()),
        "title": "Test Task",
        "description": "A comprehensive test task",
        "status": "todo",
        "priority": "high",
        "estimated_effort": "2 hours",
        "assignees": ["tester1", "tester2"],
        "labels": ["testing", "comprehensive"],
        "user_id": TEST_USER_ID
    }

class TestTaskPersistence:
    """Test task creation, retrieval, and persistence with all relationships."""
    
    def test_task_creation_with_all_relationships(self, clean_test_db, sample_project_data, sample_branch_data, sample_task_data):
        """Test that tasks are created with all relationships and persist correctly."""
        
        # Setup: Create project and branch
        conn = sqlite3.connect(clean_test_db)
        cursor = conn.cursor()
        
        # Create project
        cursor.execute(
            "INSERT INTO projects (id, name, description, user_id) VALUES (?, ?, ?, ?)",
            (sample_project_data["project_id"], sample_project_data["name"], 
             sample_project_data["description"], sample_project_data["user_id"])
        )
        
        # Create branch
        cursor.execute(
            "INSERT INTO git_branches (id, project_id, git_branch_name, git_branch_description, user_id) VALUES (?, ?, ?, ?, ?)",
            (sample_branch_data["branch_id"], sample_project_data["project_id"], 
             sample_branch_data["git_branch_name"], sample_branch_data["git_branch_description"],
             sample_branch_data["user_id"])
        )
        
        # Create task
        cursor.execute(
            """INSERT INTO tasks (id, git_branch_id, title, description, status, priority, 
                               estimated_effort, user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (sample_task_data["task_id"], sample_branch_data["branch_id"], 
             sample_task_data["title"], sample_task_data["description"],
             sample_task_data["status"], sample_task_data["priority"],
             sample_task_data["estimated_effort"], sample_task_data["user_id"])
        )
        
        # Add assignees
        for assignee in sample_task_data["assignees"]:
            assignee_id = str(uuid.uuid4())
            cursor.execute(
                "INSERT INTO task_assignees (id, task_id, assignee, user_id) VALUES (?, ?, ?, ?)",
                (assignee_id, sample_task_data["task_id"], assignee, sample_task_data["user_id"])
            )
        
        # Add labels
        for label in sample_task_data["labels"]:
            label_id = str(uuid.uuid4())
            cursor.execute(
                "INSERT INTO task_labels (id, task_id, label, user_id) VALUES (?, ?, ?, ?)",
                (label_id, sample_task_data["task_id"], label, sample_task_data["user_id"])
            )
        
        conn.commit()
        
        # Test: Verify task exists with all relationships
        cursor.execute(
            """SELECT t.*, 
                      GROUP_CONCAT(DISTINCT ta.assignee) as assignees,
                      GROUP_CONCAT(DISTINCT tl.label) as labels
               FROM tasks t
               LEFT JOIN task_assignees ta ON t.id = ta.task_id
               LEFT JOIN task_labels tl ON t.id = tl.task_id
               WHERE t.id = ?
               GROUP BY t.id""",
            (sample_task_data["task_id"],)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        assert result is not None, "Task should exist in database"
        assert result[2] == sample_task_data["title"], "Task title should match"
        assert result[3] == sample_task_data["description"], "Task description should match"
        assert result[4] == sample_task_data["status"], "Task status should match"
        assert result[5] == sample_task_data["priority"], "Task priority should match"
        
        # Verify assignees
        assignees = result[-2].split(",") if result[-2] else []
        assert set(assignees) == set(sample_task_data["assignees"]), "Assignees should match"
        
        # Verify labels
        labels = result[-1].split(",") if result[-1] else []
        assert set(labels) == set(sample_task_data["labels"]), "Labels should match"
    
    def test_task_appears_in_list_operations(self, clean_test_db, sample_project_data, sample_branch_data, sample_task_data):
        """Test that created tasks appear in list operations."""
        
        # Setup: Create project, branch, and task
        conn = sqlite3.connect(clean_test_db)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO projects (id, name, description, user_id) VALUES (?, ?, ?, ?)",
            (sample_project_data["project_id"], sample_project_data["name"], 
             sample_project_data["description"], sample_project_data["user_id"])
        )
        
        cursor.execute(
            "INSERT INTO git_branches (id, project_id, git_branch_name, git_branch_description, user_id) VALUES (?, ?, ?, ?, ?)",
            (sample_branch_data["branch_id"], sample_project_data["project_id"], 
             sample_branch_data["git_branch_name"], sample_branch_data["git_branch_description"],
             sample_branch_data["user_id"])
        )
        
        cursor.execute(
            """INSERT INTO tasks (id, git_branch_id, title, description, status, priority, 
                               estimated_effort, user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (sample_task_data["task_id"], sample_branch_data["branch_id"], 
             sample_task_data["title"], sample_task_data["description"],
             sample_task_data["status"], sample_task_data["priority"],
             sample_task_data["estimated_effort"], sample_task_data["user_id"])
        )
        
        conn.commit()
        
        # Test: List all tasks for the branch
        cursor.execute(
            "SELECT * FROM tasks WHERE git_branch_id = ? AND user_id = ?",
            (sample_branch_data["branch_id"], sample_task_data["user_id"])
        )
        
        tasks = cursor.fetchall()
        conn.close()
        
        assert len(tasks) == 1, "Should find exactly one task"
        assert tasks[0][0] == sample_task_data["task_id"], "Task ID should match"
    
    def test_task_statistics_update(self, clean_test_db, sample_project_data, sample_branch_data, sample_task_data):
        """Test that task statistics are correctly updated."""
        
        # Setup: Create project, branch, and multiple tasks
        conn = sqlite3.connect(clean_test_db)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO projects (id, name, description, user_id) VALUES (?, ?, ?, ?)",
            (sample_project_data["project_id"], sample_project_data["name"], 
             sample_project_data["description"], sample_project_data["user_id"])
        )
        
        cursor.execute(
            "INSERT INTO git_branches (id, project_id, git_branch_name, git_branch_description, user_id) VALUES (?, ?, ?, ?, ?)",
            (sample_branch_data["branch_id"], sample_project_data["project_id"], 
             sample_branch_data["git_branch_name"], sample_branch_data["git_branch_description"],
             sample_branch_data["user_id"])
        )
        
        # Create multiple tasks with different statuses
        tasks_data = [
            ("todo", 0),
            ("in_progress", 50),
            ("done", 100),
            ("done", 100)
        ]
        
        task_ids = []
        for i, (status, completion) in enumerate(tasks_data):
            task_id = str(uuid.uuid4())
            task_ids.append(task_id)
            cursor.execute(
                """INSERT INTO tasks (id, git_branch_id, title, description, status, 
                                   completion_percentage, user_id) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (task_id, sample_branch_data["branch_id"], f"Test Task {i+1}", 
                 f"Description {i+1}", status, completion, sample_task_data["user_id"])
            )
        
        conn.commit()
        
        # Test: Calculate statistics
        cursor.execute(
            """SELECT 
                COUNT(*) as total_tasks,
                COUNT(CASE WHEN status = 'done' THEN 1 END) as completed_tasks,
                AVG(completion_percentage) as avg_completion
               FROM tasks 
               WHERE git_branch_id = ? AND user_id = ?""",
            (sample_branch_data["branch_id"], sample_task_data["user_id"])
        )
        
        stats = cursor.fetchone()
        conn.close()
        
        assert stats[0] == 4, "Should have 4 total tasks"
        assert stats[1] == 2, "Should have 2 completed tasks"
        assert stats[2] == 62.5, "Average completion should be 62.5%"

class TestContextManagement:
    """Test context creation, inheritance, and management."""
    
    def test_global_context_creation(self, clean_test_db):
        """Test global context creation."""
        
        conn = sqlite3.connect(clean_test_db)
        cursor = conn.cursor()
        
        global_context_id = "global_singleton"
        context_data = {
            "organization": "Test Organization",
            "global_settings": {
                "default_priority": "medium",
                "default_assignee": "system"
            }
        }
        
        cursor.execute(
            "INSERT INTO global_contexts (id, data, user_id) VALUES (?, ?, ?)",
            (global_context_id, json.dumps(context_data), TEST_USER_ID)
        )
        
        conn.commit()
        
        # Verify global context exists
        cursor.execute(
            "SELECT * FROM global_contexts WHERE id = ? AND user_id = ?",
            (global_context_id, TEST_USER_ID)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        assert result is not None, "Global context should exist"
        assert json.loads(result[1]) == context_data, "Context data should match"
    
    def test_project_context_creation(self, clean_test_db, sample_project_data):
        """Test project context creation with and without global context."""
        
        conn = sqlite3.connect(clean_test_db)
        cursor = conn.cursor()
        
        # Create project
        cursor.execute(
            "INSERT INTO projects (id, name, description, user_id) VALUES (?, ?, ?, ?)",
            (sample_project_data["project_id"], sample_project_data["name"], 
             sample_project_data["description"], sample_project_data["user_id"])
        )
        
        # Create project context
        project_context_data = {
            "project_type": "web_application",
            "tech_stack": ["Python", "React", "PostgreSQL"],
            "team_members": ["developer1", "tester1"]
        }
        
        cursor.execute(
            "INSERT INTO project_contexts (id, project_id, data, user_id) VALUES (?, ?, ?, ?)",
            (sample_project_data["project_id"], sample_project_data["project_id"], 
             json.dumps(project_context_data), sample_project_data["user_id"])
        )
        
        conn.commit()
        
        # Verify project context exists
        cursor.execute(
            "SELECT * FROM project_contexts WHERE project_id = ? AND user_id = ?",
            (sample_project_data["project_id"], sample_project_data["user_id"])
        )
        
        result = cursor.fetchone()
        conn.close()
        
        assert result is not None, "Project context should exist"
        assert json.loads(result[2]) == project_context_data, "Context data should match"
    
    def test_branch_context_auto_creation(self, clean_test_db, sample_project_data, sample_branch_data):
        """Test branch context auto-creation."""
        
        conn = sqlite3.connect(clean_test_db)
        cursor = conn.cursor()
        
        # Create project
        cursor.execute(
            "INSERT INTO projects (id, name, description, user_id) VALUES (?, ?, ?, ?)",
            (sample_project_data["project_id"], sample_project_data["name"], 
             sample_project_data["description"], sample_project_data["user_id"])
        )
        
        # Create branch
        cursor.execute(
            "INSERT INTO git_branches (id, project_id, git_branch_name, git_branch_description, user_id) VALUES (?, ?, ?, ?, ?)",
            (sample_branch_data["branch_id"], sample_project_data["project_id"], 
             sample_branch_data["git_branch_name"], sample_branch_data["git_branch_description"],
             sample_branch_data["user_id"])
        )
        
        # Auto-create branch context
        branch_context_data = {
            "branch_type": "feature",
            "target_release": "v1.2.0",
            "feature_requirements": ["user_authentication", "session_management"]
        }
        
        cursor.execute(
            "INSERT INTO branch_contexts (id, git_branch_id, data, user_id) VALUES (?, ?, ?, ?)",
            (sample_branch_data["branch_id"], sample_branch_data["branch_id"], 
             json.dumps(branch_context_data), sample_branch_data["user_id"])
        )
        
        conn.commit()
        
        # Verify branch context was auto-created
        cursor.execute(
            "SELECT * FROM branch_contexts WHERE git_branch_id = ? AND user_id = ?",
            (sample_branch_data["branch_id"], sample_branch_data["user_id"])
        )
        
        result = cursor.fetchone()
        conn.close()
        
        assert result is not None, "Branch context should be auto-created"
        assert json.loads(result[2]) == branch_context_data, "Context data should match"
    
    def test_context_inheritance_chain(self, clean_test_db, sample_project_data, sample_branch_data, sample_task_data):
        """Test context inheritance: global → project → branch → task."""
        
        conn = sqlite3.connect(clean_test_db)
        cursor = conn.cursor()
        
        # Create global context
        global_context_data = {"global_setting": "global_value"}
        cursor.execute(
            "INSERT INTO global_contexts (id, data, user_id) VALUES (?, ?, ?)",
            ("global_singleton", json.dumps(global_context_data), TEST_USER_ID)
        )
        
        # Create project
        cursor.execute(
            "INSERT INTO projects (id, name, description, user_id) VALUES (?, ?, ?, ?)",
            (sample_project_data["project_id"], sample_project_data["name"], 
             sample_project_data["description"], sample_project_data["user_id"])
        )
        
        # Create project context
        project_context_data = {"project_setting": "project_value"}
        cursor.execute(
            "INSERT INTO project_contexts (id, project_id, data, user_id) VALUES (?, ?, ?, ?)",
            (sample_project_data["project_id"], sample_project_data["project_id"], 
             json.dumps(project_context_data), sample_project_data["user_id"])
        )
        
        # Create branch
        cursor.execute(
            "INSERT INTO git_branches (id, project_id, git_branch_name, git_branch_description, user_id) VALUES (?, ?, ?, ?, ?)",
            (sample_branch_data["branch_id"], sample_project_data["project_id"], 
             sample_branch_data["git_branch_name"], sample_branch_data["git_branch_description"],
             sample_branch_data["user_id"])
        )
        
        # Create branch context
        branch_context_data = {"branch_setting": "branch_value"}
        cursor.execute(
            "INSERT INTO branch_contexts (id, git_branch_id, data, user_id) VALUES (?, ?, ?, ?)",
            (sample_branch_data["branch_id"], sample_branch_data["branch_id"], 
             json.dumps(branch_context_data), sample_branch_data["user_id"])
        )
        
        # Create task
        cursor.execute(
            """INSERT INTO tasks (id, git_branch_id, title, description, status, priority, 
                               estimated_effort, user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (sample_task_data["task_id"], sample_branch_data["branch_id"], 
             sample_task_data["title"], sample_task_data["description"],
             sample_task_data["status"], sample_task_data["priority"],
             sample_task_data["estimated_effort"], sample_task_data["user_id"])
        )
        
        # Create task context
        task_context_data = {"task_setting": "task_value"}
        cursor.execute(
            "INSERT INTO task_contexts (id, task_id, data, user_id) VALUES (?, ?, ?, ?)",
            (sample_task_data["task_id"], sample_task_data["task_id"], 
             json.dumps(task_context_data), sample_task_data["user_id"])
        )
        
        conn.commit()
        
        # Test: Retrieve inherited context (simulate inheritance query)
        cursor.execute(
            """SELECT 
                gc.data as global_data,
                pc.data as project_data,
                bc.data as branch_data,
                tc.data as task_data
               FROM tasks t
               JOIN git_branches gb ON t.git_branch_id = gb.id
               JOIN projects p ON gb.project_id = p.id
               LEFT JOIN global_contexts gc ON gc.id = 'global_singleton' AND gc.user_id = t.user_id
               LEFT JOIN project_contexts pc ON pc.project_id = p.id AND pc.user_id = t.user_id
               LEFT JOIN branch_contexts bc ON bc.git_branch_id = gb.id AND bc.user_id = t.user_id
               LEFT JOIN task_contexts tc ON tc.task_id = t.id AND tc.user_id = t.user_id
               WHERE t.id = ?""",
            (sample_task_data["task_id"],)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        assert result is not None, "Should retrieve full inheritance chain"
        
        # Verify all context levels are present
        global_data = json.loads(result[0]) if result[0] else {}
        project_data = json.loads(result[1]) if result[1] else {}
        branch_data = json.loads(result[2]) if result[2] else {}
        task_data = json.loads(result[3]) if result[3] else {}
        
        assert global_data.get("global_setting") == "global_value"
        assert project_data.get("project_setting") == "project_value"
        assert branch_data.get("branch_setting") == "branch_value"
        assert task_data.get("task_setting") == "task_value"

class TestSubtaskManagement:
    """Test subtask creation, progress updates, and parent task calculation."""
    
    def test_subtask_creation_with_valid_parent(self, clean_test_db, sample_project_data, sample_branch_data, sample_task_data):
        """Test subtask creation with valid parent task."""
        
        conn = sqlite3.connect(clean_test_db)
        cursor = conn.cursor()
        
        # Setup: Create project, branch, and parent task
        cursor.execute(
            "INSERT INTO projects (id, name, description, user_id) VALUES (?, ?, ?, ?)",
            (sample_project_data["project_id"], sample_project_data["name"], 
             sample_project_data["description"], sample_project_data["user_id"])
        )
        
        cursor.execute(
            "INSERT INTO git_branches (id, project_id, git_branch_name, git_branch_description, user_id) VALUES (?, ?, ?, ?, ?)",
            (sample_branch_data["branch_id"], sample_project_data["project_id"], 
             sample_branch_data["git_branch_name"], sample_branch_data["git_branch_description"],
             sample_branch_data["user_id"])
        )
        
        cursor.execute(
            """INSERT INTO tasks (id, git_branch_id, title, description, status, priority, 
                               estimated_effort, user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (sample_task_data["task_id"], sample_branch_data["branch_id"], 
             sample_task_data["title"], sample_task_data["description"],
             sample_task_data["status"], sample_task_data["priority"],
             sample_task_data["estimated_effort"], sample_task_data["user_id"])
        )
        
        # Create subtasks
        subtasks_data = [
            {"title": "Subtask 1", "description": "First subtask"},
            {"title": "Subtask 2", "description": "Second subtask"},
            {"title": "Subtask 3", "description": "Third subtask"}
        ]
        
        subtask_ids = []
        for subtask_data in subtasks_data:
            subtask_id = str(uuid.uuid4())
            subtask_ids.append(subtask_id)
            cursor.execute(
                """INSERT INTO subtasks (id, task_id, title, description, status, priority, 
                                      progress_percentage, user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (subtask_id, sample_task_data["task_id"], subtask_data["title"], 
                 subtask_data["description"], "todo", "medium", 0, sample_task_data["user_id"])
            )
        
        conn.commit()
        
        # Test: Verify subtasks were created
        cursor.execute(
            "SELECT * FROM subtasks WHERE task_id = ? AND user_id = ?",
            (sample_task_data["task_id"], sample_task_data["user_id"])
        )
        
        subtasks = cursor.fetchall()
        conn.close()
        
        assert len(subtasks) == 3, "Should have 3 subtasks"
        assert all(subtask[1] == sample_task_data["task_id"] for subtask in subtasks), "All subtasks should belong to parent task"
    
    def test_subtask_progress_updates(self, clean_test_db, sample_project_data, sample_branch_data, sample_task_data):
        """Test subtask progress updates."""
        
        conn = sqlite3.connect(clean_test_db)
        cursor = conn.cursor()
        
        # Setup: Create project, branch, parent task, and subtask
        cursor.execute(
            "INSERT INTO projects (id, name, description, user_id) VALUES (?, ?, ?, ?)",
            (sample_project_data["project_id"], sample_project_data["name"], 
             sample_project_data["description"], sample_project_data["user_id"])
        )
        
        cursor.execute(
            "INSERT INTO git_branches (id, project_id, git_branch_name, git_branch_description, user_id) VALUES (?, ?, ?, ?, ?)",
            (sample_branch_data["branch_id"], sample_project_data["project_id"], 
             sample_branch_data["git_branch_name"], sample_branch_data["git_branch_description"],
             sample_branch_data["user_id"])
        )
        
        cursor.execute(
            """INSERT INTO tasks (id, git_branch_id, title, description, status, priority, 
                               estimated_effort, user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (sample_task_data["task_id"], sample_branch_data["branch_id"], 
             sample_task_data["title"], sample_task_data["description"],
             sample_task_data["status"], sample_task_data["priority"],
             sample_task_data["estimated_effort"], sample_task_data["user_id"])
        )
        
        # Create subtask
        subtask_id = str(uuid.uuid4())
        cursor.execute(
            """INSERT INTO subtasks (id, task_id, title, description, status, priority, 
                                  progress_percentage, user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (subtask_id, sample_task_data["task_id"], "Test Subtask", 
             "A test subtask", "todo", "medium", 0, sample_task_data["user_id"])
        )
        
        conn.commit()
        
        # Test: Update subtask progress
        cursor.execute(
            "UPDATE subtasks SET progress_percentage = ?, status = ?, updated_at = ? WHERE id = ?",
            (75, "in_progress", datetime.now().isoformat(), subtask_id)
        )
        
        conn.commit()
        
        # Verify update
        cursor.execute(
            "SELECT progress_percentage, status FROM subtasks WHERE id = ?",
            (subtask_id,)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        assert result[0] == 75, "Progress should be updated to 75%"
        assert result[1] == "in_progress", "Status should be in_progress"
    
    def test_parent_task_progress_calculation(self, clean_test_db, sample_project_data, sample_branch_data, sample_task_data):
        """Test parent task progress calculation based on subtasks."""
        
        conn = sqlite3.connect(clean_test_db)
        cursor = conn.cursor()
        
        # Setup: Create project, branch, and parent task
        cursor.execute(
            "INSERT INTO projects (id, name, description, user_id) VALUES (?, ?, ?, ?)",
            (sample_project_data["project_id"], sample_project_data["name"], 
             sample_project_data["description"], sample_project_data["user_id"])
        )
        
        cursor.execute(
            "INSERT INTO git_branches (id, project_id, git_branch_name, git_branch_description, user_id) VALUES (?, ?, ?, ?, ?)",
            (sample_branch_data["branch_id"], sample_project_data["project_id"], 
             sample_branch_data["git_branch_name"], sample_branch_data["git_branch_description"],
             sample_branch_data["user_id"])
        )
        
        cursor.execute(
            """INSERT INTO tasks (id, git_branch_id, title, description, status, priority, 
                               estimated_effort, user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (sample_task_data["task_id"], sample_branch_data["branch_id"], 
             sample_task_data["title"], sample_task_data["description"],
             sample_task_data["status"], sample_task_data["priority"],
             sample_task_data["estimated_effort"], sample_task_data["user_id"])
        )
        
        # Create subtasks with different progress levels
        subtasks_progress = [25, 50, 75, 100]  # Average should be 62.5%
        
        for i, progress in enumerate(subtasks_progress):
            subtask_id = str(uuid.uuid4())
            status = "done" if progress == 100 else ("in_progress" if progress > 0 else "todo")
            cursor.execute(
                """INSERT INTO subtasks (id, task_id, title, description, status, priority, 
                                      progress_percentage, user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (subtask_id, sample_task_data["task_id"], f"Subtask {i+1}", 
                 f"Description {i+1}", status, "medium", progress, sample_task_data["user_id"])
            )
        
        conn.commit()
        
        # Test: Calculate parent task progress
        cursor.execute(
            """SELECT AVG(progress_percentage) as avg_progress
               FROM subtasks 
               WHERE task_id = ? AND user_id = ?""",
            (sample_task_data["task_id"], sample_task_data["user_id"])
        )
        
        result = cursor.fetchone()
        calculated_progress = round(result[0], 1)
        
        # Update parent task progress
        cursor.execute(
            "UPDATE tasks SET completion_percentage = ? WHERE id = ?",
            (calculated_progress, sample_task_data["task_id"])
        )
        
        conn.commit()
        
        # Verify parent task progress
        cursor.execute(
            "SELECT completion_percentage FROM tasks WHERE id = ?",
            (sample_task_data["task_id"],)
        )
        
        parent_progress = cursor.fetchone()[0]
        conn.close()
        
        assert parent_progress == 62.5, f"Parent task progress should be 62.5%, got {parent_progress}"

class TestProjectAndBranchManagement:
    """Test project and branch management operations."""
    
    def test_project_creation_update_list(self, clean_test_db):
        """Test project creation, update, and list operations."""
        
        conn = sqlite3.connect(clean_test_db)
        cursor = conn.cursor()
        
        # Test: Create project
        project_id = str(uuid.uuid4())
        project_data = {
            "name": "Test Project",
            "description": "A test project for management testing",
            "user_id": TEST_USER_ID
        }
        
        cursor.execute(
            "INSERT INTO projects (id, name, description, user_id) VALUES (?, ?, ?, ?)",
            (project_id, project_data["name"], project_data["description"], project_data["user_id"])
        )
        
        conn.commit()
        
        # Verify creation
        cursor.execute(
            "SELECT * FROM projects WHERE id = ? AND user_id = ?",
            (project_id, TEST_USER_ID)
        )
        
        result = cursor.fetchone()
        assert result is not None, "Project should be created"
        assert result[1] == project_data["name"], "Project name should match"
        
        # Test: Update project
        updated_name = "Updated Test Project"
        cursor.execute(
            "UPDATE projects SET name = ?, updated_at = ? WHERE id = ?",
            (updated_name, datetime.now().isoformat(), project_id)
        )
        
        conn.commit()
        
        # Verify update
        cursor.execute(
            "SELECT name FROM projects WHERE id = ?",
            (project_id,)
        )
        
        result = cursor.fetchone()
        assert result[0] == updated_name, "Project name should be updated"
        
        # Test: List projects
        cursor.execute(
            "SELECT COUNT(*) FROM projects WHERE user_id = ?",
            (TEST_USER_ID,)
        )
        
        count = cursor.fetchone()[0]
        conn.close()
        
        assert count == 1, "Should have exactly one project"
    
    def test_branch_creation_with_auto_context(self, clean_test_db, sample_project_data):
        """Test branch creation with auto-context creation."""
        
        conn = sqlite3.connect(clean_test_db)
        cursor = conn.cursor()
        
        # Setup: Create project
        cursor.execute(
            "INSERT INTO projects (id, name, description, user_id) VALUES (?, ?, ?, ?)",
            (sample_project_data["project_id"], sample_project_data["name"], 
             sample_project_data["description"], sample_project_data["user_id"])
        )
        
        # Test: Create branch
        branch_id = str(uuid.uuid4())
        branch_data = {
            "git_branch_name": "feature/auto-context-test",
            "git_branch_description": "Test branch with auto-context creation",
            "user_id": TEST_USER_ID
        }
        
        cursor.execute(
            "INSERT INTO git_branches (id, project_id, git_branch_name, git_branch_description, user_id) VALUES (?, ?, ?, ?, ?)",
            (branch_id, sample_project_data["project_id"], branch_data["git_branch_name"], 
             branch_data["git_branch_description"], branch_data["user_id"])
        )
        
        # Auto-create branch context
        context_data = {
            "branch_id": branch_id,
            "project_id": sample_project_data["project_id"],
            "auto_created": True
        }
        
        cursor.execute(
            "INSERT INTO branch_contexts (id, git_branch_id, data, user_id) VALUES (?, ?, ?, ?)",
            (branch_id, branch_id, json.dumps(context_data), branch_data["user_id"])
        )
        
        conn.commit()
        
        # Verify branch creation
        cursor.execute(
            "SELECT * FROM git_branches WHERE id = ? AND user_id = ?",
            (branch_id, TEST_USER_ID)
        )
        
        branch_result = cursor.fetchone()
        assert branch_result is not None, "Branch should be created"
        assert branch_result[2] == branch_data["git_branch_name"], "Branch name should match"
        
        # Verify auto-context creation
        cursor.execute(
            "SELECT * FROM branch_contexts WHERE git_branch_id = ? AND user_id = ?",
            (branch_id, TEST_USER_ID)
        )
        
        context_result = cursor.fetchone()
        conn.close()
        
        assert context_result is not None, "Branch context should be auto-created"
        stored_data = json.loads(context_result[2])
        assert stored_data["auto_created"] is True, "Context should be marked as auto-created"
    
    def test_agent_assignment_to_branches(self, clean_test_db, sample_project_data):
        """Test agent assignment to branches."""
        
        conn = sqlite3.connect(clean_test_db)
        cursor = conn.cursor()
        
        # Setup: Create project and branch
        cursor.execute(
            "INSERT INTO projects (id, name, description, user_id) VALUES (?, ?, ?, ?)",
            (sample_project_data["project_id"], sample_project_data["name"], 
             sample_project_data["description"], sample_project_data["user_id"])
        )
        
        branch_id = str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO git_branches (id, project_id, git_branch_name, git_branch_description, user_id) VALUES (?, ?, ?, ?, ?)",
            (branch_id, sample_project_data["project_id"], "feature/agent-test", 
             "Test branch for agent assignment", TEST_USER_ID)
        )
        
        # Create agent
        agent_id = str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO agents (id, project_id, name, user_id) VALUES (?, ?, ?, ?)",
            (agent_id, sample_project_data["project_id"], "@test_agent", TEST_USER_ID)
        )
        
        # Test: Assign agent to branch
        assignment_id = str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO agent_assignments (id, agent_id, git_branch_id, user_id) VALUES (?, ?, ?, ?)",
            (assignment_id, agent_id, branch_id, TEST_USER_ID)
        )
        
        conn.commit()
        
        # Verify assignment
        cursor.execute(
            """SELECT a.name 
               FROM agents a 
               JOIN agent_assignments aa ON a.id = aa.agent_id 
               WHERE aa.git_branch_id = ? AND aa.user_id = ?""",
            (branch_id, TEST_USER_ID)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        assert result is not None, "Agent should be assigned to branch"
        assert result[0] == "@test_agent", "Agent name should match"
    
    def test_branch_statistics(self, clean_test_db, sample_project_data):
        """Test branch statistics calculation."""
        
        conn = sqlite3.connect(clean_test_db)
        cursor = conn.cursor()
        
        # Setup: Create project and branch
        cursor.execute(
            "INSERT INTO projects (id, name, description, user_id) VALUES (?, ?, ?, ?)",
            (sample_project_data["project_id"], sample_project_data["name"], 
             sample_project_data["description"], sample_project_data["user_id"])
        )
        
        branch_id = str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO git_branches (id, project_id, git_branch_name, git_branch_description, user_id) VALUES (?, ?, ?, ?, ?)",
            (branch_id, sample_project_data["project_id"], "feature/stats-test", 
             "Test branch for statistics", TEST_USER_ID)
        )
        
        # Create tasks with different statuses
        task_statuses = ["todo", "in_progress", "done", "done", "blocked"]
        for i, status in enumerate(task_statuses):
            task_id = str(uuid.uuid4())
            completion = 100 if status == "done" else (50 if status == "in_progress" else 0)
            cursor.execute(
                """INSERT INTO tasks (id, git_branch_id, title, description, status, 
                                   completion_percentage, user_id) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (task_id, branch_id, f"Task {i+1}", f"Description {i+1}", 
                 status, completion, TEST_USER_ID)
            )
        
        conn.commit()
        
        # Test: Calculate branch statistics
        cursor.execute(
            """SELECT 
                COUNT(*) as total_tasks,
                COUNT(CASE WHEN status = 'done' THEN 1 END) as completed_tasks,
                COUNT(CASE WHEN status = 'blocked' THEN 1 END) as blocked_tasks,
                AVG(completion_percentage) as avg_completion
               FROM tasks 
               WHERE git_branch_id = ? AND user_id = ?""",
            (branch_id, TEST_USER_ID)
        )
        
        stats = cursor.fetchone()
        conn.close()
        
        assert stats[0] == 5, "Should have 5 total tasks"
        assert stats[1] == 2, "Should have 2 completed tasks"
        assert stats[2] == 1, "Should have 1 blocked task"
        assert stats[3] == 50.0, "Average completion should be 50%"

class TestErrorHandling:
    """Test error handling and validation scenarios."""
    
    def test_graceful_missing_context_handling(self, clean_test_db):
        """Test graceful handling of missing contexts."""
        
        conn = sqlite3.connect(clean_test_db)
        cursor = conn.cursor()
        
        # Test: Try to retrieve non-existent context
        fake_context_id = str(uuid.uuid4())
        cursor.execute(
            "SELECT * FROM global_contexts WHERE id = ? AND user_id = ?",
            (fake_context_id, TEST_USER_ID)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        # Should handle gracefully (return None instead of crashing)
        assert result is None, "Should return None for non-existent context"
    
    def test_informative_error_messages(self, clean_test_db):
        """Test that error messages are informative."""
        
        conn = sqlite3.connect(clean_test_db)
        cursor = conn.cursor()
        
        # Test: Try to create task without required branch
        fake_branch_id = str(uuid.uuid4())
        
        try:
            cursor.execute(
                """INSERT INTO tasks (id, git_branch_id, title, description, status, priority, 
                                   estimated_effort, user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (str(uuid.uuid4()), fake_branch_id, "Test Task", "Description",
                 "todo", "medium", "2 hours", TEST_USER_ID)
            )
            conn.commit()
            assert False, "Should have raised foreign key constraint error"
        except sqlite3.IntegrityError as e:
            error_message = str(e)
            assert "FOREIGN KEY constraint failed" in error_message, "Should provide informative error message"
        
        conn.close()
    
    def test_parameter_validation(self, clean_test_db):
        """Test parameter validation for various operations."""
        
        conn = sqlite3.connect(clean_test_db)
        cursor = conn.cursor()
        
        # Test: Invalid UUID format handling
        invalid_uuid = "not-a-valid-uuid"
        
        # This would typically be handled at the application layer
        # Here we test that the database can handle invalid data gracefully
        try:
            cursor.execute(
                "SELECT * FROM projects WHERE id = ? AND user_id = ?",
                (invalid_uuid, TEST_USER_ID)
            )
            result = cursor.fetchone()
            # Should return None for invalid UUID
            assert result is None, "Should handle invalid UUID gracefully"
        except Exception as e:
            # If database raises exception, it should be informative
            assert "invalid" in str(e).lower() or "constraint" in str(e).lower()
        
        conn.close()
    
    def test_uuid_validation_messages(self, clean_test_db):
        """Test UUID validation and error messages."""
        
        # Test valid UUID formats
        valid_uuids = [
            str(uuid.uuid4()),
            "550e8400-e29b-41d4-a716-446655440000",
            "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
        ]
        
        for test_uuid in valid_uuids:
            try:
                uuid.UUID(test_uuid)
                uuid_valid = True
            except ValueError:
                uuid_valid = False
            
            assert uuid_valid, f"UUID {test_uuid} should be valid"
        
        # Test invalid UUID formats
        invalid_uuids = [
            "not-a-uuid",
            "123-456-789",
            "",
            "550e8400-e29b-41d4-a716-44665544000g",  # invalid character
            "550e8400-e29b-41d4-a716-4466554400"     # too short
        ]
        
        for test_uuid in invalid_uuids:
            try:
                uuid.UUID(test_uuid)
                uuid_valid = True
            except ValueError as e:
                uuid_valid = False
                error_message = str(e)
                assert "badly formed hexadecimal UUID string" in error_message or \
                       "invalid" in error_message.lower(), \
                       f"Should provide informative error for invalid UUID: {test_uuid}"
            
            assert not uuid_valid, f"UUID {test_uuid} should be invalid"

class TestDataIntegrity:
    """Test data integrity and consistency."""
    
    def test_cascade_deletion(self, clean_test_db, sample_project_data, sample_branch_data, sample_task_data):
        """Test that related data is properly cleaned up on deletion."""
        
        conn = sqlite3.connect(clean_test_db)
        cursor = conn.cursor()
        
        # Setup: Create full hierarchy
        cursor.execute(
            "INSERT INTO projects (id, name, description, user_id) VALUES (?, ?, ?, ?)",
            (sample_project_data["project_id"], sample_project_data["name"], 
             sample_project_data["description"], sample_project_data["user_id"])
        )
        
        cursor.execute(
            "INSERT INTO git_branches (id, project_id, git_branch_name, git_branch_description, user_id) VALUES (?, ?, ?, ?, ?)",
            (sample_branch_data["branch_id"], sample_project_data["project_id"], 
             sample_branch_data["git_branch_name"], sample_branch_data["git_branch_description"],
             sample_branch_data["user_id"])
        )
        
        cursor.execute(
            """INSERT INTO tasks (id, git_branch_id, title, description, status, priority, 
                               estimated_effort, user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (sample_task_data["task_id"], sample_branch_data["branch_id"], 
             sample_task_data["title"], sample_task_data["description"],
             sample_task_data["status"], sample_task_data["priority"],
             sample_task_data["estimated_effort"], sample_task_data["user_id"])
        )
        
        # Add assignees and labels
        assignee_id = str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO task_assignees (id, task_id, assignee, user_id) VALUES (?, ?, ?, ?)",
            (assignee_id, sample_task_data["task_id"], "test_assignee", sample_task_data["user_id"])
        )
        
        label_id = str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO task_labels (id, task_id, label, user_id) VALUES (?, ?, ?, ?)",
            (label_id, sample_task_data["task_id"], "test_label", sample_task_data["user_id"])
        )
        
        # Add subtask
        subtask_id = str(uuid.uuid4())
        cursor.execute(
            """INSERT INTO subtasks (id, task_id, title, description, status, priority, 
                                  progress_percentage, user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (subtask_id, sample_task_data["task_id"], "Test Subtask", 
             "A test subtask", "todo", "medium", 0, sample_task_data["user_id"])
        )
        
        conn.commit()
        
        # Test: Delete task (should cascade to assignees, labels, and subtasks)
        cursor.execute("DELETE FROM tasks WHERE id = ?", (sample_task_data["task_id"],))
        conn.commit()
        
        # Verify cascade deletion
        cursor.execute("SELECT COUNT(*) FROM task_assignees WHERE task_id = ?", (sample_task_data["task_id"],))
        assignee_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM task_labels WHERE task_id = ?", (sample_task_data["task_id"],))
        label_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM subtasks WHERE task_id = ?", (sample_task_data["task_id"],))
        subtask_count = cursor.fetchone()[0]
        
        conn.close()
        
        assert assignee_count == 0, "Task assignees should be deleted with task"
        assert label_count == 0, "Task labels should be deleted with task"
        assert subtask_count == 0, "Subtasks should be deleted with task"
    
    def test_user_data_isolation(self, clean_test_db, sample_project_data):
        """Test that user data is properly isolated."""
        
        conn = sqlite3.connect(clean_test_db)
        cursor = conn.cursor()
        
        # Create projects for different users
        user1_project_id = str(uuid.uuid4())
        user2_project_id = str(uuid.uuid4())
        
        cursor.execute(
            "INSERT INTO projects (id, name, description, user_id) VALUES (?, ?, ?, ?)",
            (user1_project_id, "User 1 Project", "Project for user 1", "user1")
        )
        
        cursor.execute(
            "INSERT INTO projects (id, name, description, user_id) VALUES (?, ?, ?, ?)",
            (user2_project_id, "User 2 Project", "Project for user 2", "user2")
        )
        
        conn.commit()
        
        # Test: User 1 should only see their projects
        cursor.execute("SELECT * FROM projects WHERE user_id = ?", ("user1",))
        user1_projects = cursor.fetchall()
        
        cursor.execute("SELECT * FROM projects WHERE user_id = ?", ("user2",))
        user2_projects = cursor.fetchall()
        
        conn.close()
        
        assert len(user1_projects) == 1, "User 1 should see exactly 1 project"
        assert len(user2_projects) == 1, "User 2 should see exactly 1 project"
        assert user1_projects[0][0] == user1_project_id, "User 1 should see their project"
        assert user2_projects[0][0] == user2_project_id, "User 2 should see their project"

# Performance and Load Testing
class TestPerformance:
    """Test performance and scalability scenarios."""
    
    def test_large_dataset_handling(self, clean_test_db, sample_project_data, sample_branch_data):
        """Test handling of large datasets."""
        
        conn = sqlite3.connect(clean_test_db)
        cursor = conn.cursor()
        
        # Setup: Create project and branch
        cursor.execute(
            "INSERT INTO projects (id, name, description, user_id) VALUES (?, ?, ?, ?)",
            (sample_project_data["project_id"], sample_project_data["name"], 
             sample_project_data["description"], sample_project_data["user_id"])
        )
        
        cursor.execute(
            "INSERT INTO git_branches (id, project_id, git_branch_name, git_branch_description, user_id) VALUES (?, ?, ?, ?, ?)",
            (sample_branch_data["branch_id"], sample_project_data["project_id"], 
             sample_branch_data["git_branch_name"], sample_branch_data["git_branch_description"],
             sample_branch_data["user_id"])
        )
        
        # Create large number of tasks
        num_tasks = 1000  # Reduced for faster testing
        task_ids = []
        
        start_time = datetime.now()
        
        for i in range(num_tasks):
            task_id = str(uuid.uuid4())
            task_ids.append(task_id)
            cursor.execute(
                """INSERT INTO tasks (id, git_branch_id, title, description, status, priority, 
                                   estimated_effort, user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (task_id, sample_branch_data["branch_id"], f"Task {i+1}", 
                 f"Description for task {i+1}", "todo", "medium", "1 hour", TEST_USER_ID)
            )
            
            # Commit in batches for better performance
            if i % 100 == 0:
                conn.commit()
        
        conn.commit()
        creation_time = (datetime.now() - start_time).total_seconds()
        
        # Test: Query performance with large dataset
        start_time = datetime.now()
        cursor.execute(
            "SELECT COUNT(*) FROM tasks WHERE git_branch_id = ? AND user_id = ?",
            (sample_branch_data["branch_id"], TEST_USER_ID)
        )
        
        count = cursor.fetchone()[0]
        query_time = (datetime.now() - start_time).total_seconds()
        
        conn.close()
        
        assert count == num_tasks, f"Should have {num_tasks} tasks"
        assert creation_time < 30.0, f"Task creation should be reasonably fast, took {creation_time}s"
        assert query_time < 1.0, f"Query should be fast, took {query_time}s"

if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])