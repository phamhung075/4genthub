"""
WebSocket Authorization Test Suite for All Entity Types

This test suite validates WebSocket authorization enforcement across all 4 entity types:
- Tasks
- Subtasks
- Branches (Git Branches)
- Projects

SECURITY REQUIREMENTS TESTED:
1. Users only receive WebSocket events for entities they own
2. Authorization enforcement is consistent across all entity types
3. No data leakage to unauthorized users
4. Event filtering based on user_id/owner_id

TEST COVERAGE:
- Task CRUD events (created, updated, deleted, completed)
- Subtask CRUD events
- Branch CRUD events
- Project CRUD events
- Multi-user authorization (owner vs non-owner)
- Authorization bypass prevention
"""

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

# Import modules to test
from fastmcp.server.routes.websocket_routes import (
    active_connections,
    broadcast_data_change,
    connection_users,
)

logger = logging.getLogger(__name__)


class TestWebSocketAuthorizationAllEntities:
    """
    Comprehensive authorization tests for all entity types

    Validates that WebSocket events are only sent to authorized users
    across Tasks, Subtasks, Branches, and Projects.
    """

    @pytest.mark.asyncio
    async def test_task_authorization_owner_receives_event(self):
        """Test that task owner receives WebSocket events"""
        # Setup
        owner_user_id = "user-owner-123"
        task_id = "task-abc-123"

        # Mock WebSocket connection for owner
        mock_owner_ws = AsyncMock()
        mock_owner_ws.client_state = MagicMock()
        mock_owner_ws.client_state.name = "CONNECTED"
        active_connections[owner_user_id] = mock_owner_ws
        connection_users[owner_user_id] = owner_user_id

        try:
            # Broadcast task created event
            await broadcast_data_change(
                event_type="created",
                entity_type="task",
                entity_id=task_id,
                user_id=owner_user_id,
                data={
                    "primary": {"id": task_id, "title": "Test Task", "status": "todo"}
                },
            )

            # Assert owner received the message
            assert mock_owner_ws.send_json.called
            sent_message = mock_owner_ws.send_json.call_args[0][0]
            assert sent_message["payload"]["entity"] == "task"
            assert sent_message["payload"]["action"] == "created"
            assert sent_message["metadata"]["entity_id"] == task_id

        finally:
            # Cleanup
            active_connections.clear()
            connection_users.clear()

    @pytest.mark.asyncio
    async def test_task_authorization_non_owner_blocked(self):
        """Test that non-owner does NOT receive task WebSocket events"""
        # Setup
        owner_user_id = "user-owner-123"
        other_user_id = "user-other-456"
        task_id = "task-abc-123"

        # Mock WebSocket connection for non-owner
        mock_other_ws = AsyncMock()
        mock_other_ws.client_state = MagicMock()
        mock_other_ws.client_state.name = "CONNECTED"
        active_connections[other_user_id] = mock_other_ws
        connection_users[other_user_id] = other_user_id

        try:
            # Broadcast task created event for owner
            await broadcast_data_change(
                event_type="created",
                entity_type="task",
                entity_id=task_id,
                user_id=owner_user_id,  # Owner is different user
                data={
                    "primary": {"id": task_id, "title": "Test Task", "status": "todo"}
                },
            )

            # Assert non-owner did NOT receive the message
            assert not mock_other_ws.send_json.called, (
                "Non-owner should not receive task events"
            )

        finally:
            # Cleanup
            active_connections.clear()
            connection_users.clear()

    @pytest.mark.asyncio
    async def test_subtask_authorization_owner_receives_event(self):
        """Test that subtask owner receives WebSocket events"""
        # Setup
        owner_user_id = "user-owner-123"
        task_id = "task-abc-123"
        subtask_id = "subtask-def-456"

        # Mock WebSocket connection for owner
        mock_owner_ws = AsyncMock()
        mock_owner_ws.client_state = MagicMock()
        mock_owner_ws.client_state.name = "CONNECTED"
        active_connections[owner_user_id] = mock_owner_ws
        connection_users[owner_user_id] = owner_user_id

        try:
            # Broadcast subtask created event
            await broadcast_data_change(
                event_type="created",
                entity_type="subtask",
                entity_id=subtask_id,
                user_id=owner_user_id,
                data={
                    "primary": {
                        "id": subtask_id,
                        "task_id": task_id,
                        "title": "Test Subtask",
                        "status": "todo",
                    }
                },
            )

            # Assert owner received the message
            assert mock_owner_ws.send_json.called
            sent_message = mock_owner_ws.send_json.call_args[0][0]
            assert sent_message["payload"]["entity"] == "subtask"
            assert sent_message["payload"]["action"] == "created"
            assert sent_message["metadata"]["entity_id"] == subtask_id

        finally:
            # Cleanup
            active_connections.clear()
            connection_users.clear()

    @pytest.mark.asyncio
    async def test_branch_authorization_owner_receives_event(self):
        """Test that branch owner receives WebSocket events"""
        # Setup
        owner_user_id = "user-owner-123"
        project_id = "project-abc-123"
        branch_id = "branch-ghi-789"

        # Mock WebSocket connection for owner
        mock_owner_ws = AsyncMock()
        mock_owner_ws.client_state = MagicMock()
        mock_owner_ws.client_state.name = "CONNECTED"
        active_connections[owner_user_id] = mock_owner_ws
        connection_users[owner_user_id] = owner_user_id

        try:
            # Broadcast branch created event
            await broadcast_data_change(
                event_type="created",
                entity_type="branch",
                entity_id=branch_id,
                user_id=owner_user_id,
                data={
                    "primary": {
                        "id": branch_id,
                        "project_id": project_id,
                        "name": "feature/new-feature",
                        "git_branch_name": "feature/new-feature",
                    }
                },
            )

            # Assert owner received the message
            assert mock_owner_ws.send_json.called
            sent_message = mock_owner_ws.send_json.call_args[0][0]
            assert sent_message["payload"]["entity"] == "branch"
            assert sent_message["payload"]["action"] == "created"
            assert sent_message["metadata"]["entity_id"] == branch_id

        finally:
            # Cleanup
            active_connections.clear()
            connection_users.clear()

    @pytest.mark.asyncio
    async def test_project_authorization_owner_receives_event(self):
        """Test that project owner receives WebSocket events"""
        # Setup
        owner_user_id = "user-owner-123"
        project_id = "project-jkl-012"

        # Mock WebSocket connection for owner
        mock_owner_ws = AsyncMock()
        mock_owner_ws.client_state = MagicMock()
        mock_owner_ws.client_state.name = "CONNECTED"
        active_connections[owner_user_id] = mock_owner_ws
        connection_users[owner_user_id] = owner_user_id

        try:
            # Broadcast project created event
            await broadcast_data_change(
                event_type="created",
                entity_type="project",
                entity_id=project_id,
                user_id=owner_user_id,
                data={
                    "primary": {
                        "id": project_id,
                        "name": "Test Project",
                        "description": "Project for authorization testing",
                    }
                },
            )

            # Assert owner received the message
            assert mock_owner_ws.send_json.called
            sent_message = mock_owner_ws.send_json.call_args[0][0]
            assert sent_message["payload"]["entity"] == "project"
            assert sent_message["payload"]["action"] == "created"
            assert sent_message["metadata"]["entity_id"] == project_id

        finally:
            # Cleanup
            active_connections.clear()
            connection_users.clear()

    @pytest.mark.asyncio
    async def test_all_entities_multi_user_authorization(self):
        """Test authorization across all entity types with multiple users"""
        # Setup
        owner_user_id = "user-owner-123"
        other_user_id = "user-other-456"

        # Mock WebSocket connections for both users
        mock_owner_ws = AsyncMock()
        mock_owner_ws.client_state = MagicMock()
        mock_owner_ws.client_state.name = "CONNECTED"

        mock_other_ws = AsyncMock()
        mock_other_ws.client_state = MagicMock()
        mock_other_ws.client_state.name = "CONNECTED"

        active_connections[owner_user_id] = mock_owner_ws
        active_connections[other_user_id] = mock_other_ws
        connection_users[owner_user_id] = owner_user_id
        connection_users[other_user_id] = other_user_id

        try:
            # Test all entity types
            test_cases = [
                ("task", "task-123", {"id": "task-123", "title": "Test Task"}),
                (
                    "subtask",
                    "subtask-456",
                    {"id": "subtask-456", "title": "Test Subtask"},
                ),
                ("branch", "branch-789", {"id": "branch-789", "name": "feature/test"}),
                (
                    "project",
                    "project-012",
                    {"id": "project-012", "name": "Test Project"},
                ),
            ]

            for entity_type, entity_id, entity_data in test_cases:
                # Reset call counts
                mock_owner_ws.send_json.reset_mock()
                mock_other_ws.send_json.reset_mock()

                # Broadcast event for owner
                await broadcast_data_change(
                    event_type="updated",
                    entity_type=entity_type,
                    entity_id=entity_id,
                    user_id=owner_user_id,
                    data={"primary": entity_data},
                )

                # Assert owner received event
                assert mock_owner_ws.send_json.called, (
                    f"Owner should receive {entity_type} event"
                )

                # Assert non-owner did NOT receive event
                assert not mock_other_ws.send_json.called, (
                    f"Non-owner should NOT receive {entity_type} event"
                )

                # Verify event content
                sent_message = mock_owner_ws.send_json.call_args[0][0]
                assert sent_message["payload"]["entity"] == entity_type
                assert sent_message["payload"]["action"] == "updated"
                assert sent_message["metadata"]["entity_id"] == entity_id

        finally:
            # Cleanup
            active_connections.clear()
            connection_users.clear()

    @pytest.mark.asyncio
    async def test_all_crud_actions_authorization(self):
        """Test authorization for all CRUD actions (created, updated, deleted, completed)"""
        # Setup
        owner_user_id = "user-owner-123"
        task_id = "task-xyz-999"

        # Mock WebSocket connection for owner
        mock_owner_ws = AsyncMock()
        mock_owner_ws.client_state = MagicMock()
        mock_owner_ws.client_state.name = "CONNECTED"
        active_connections[owner_user_id] = mock_owner_ws
        connection_users[owner_user_id] = owner_user_id

        try:
            # Test all CRUD actions
            crud_actions = ["created", "updated", "completed", "deleted"]

            for action in crud_actions:
                # Reset call count
                mock_owner_ws.send_json.reset_mock()

                # Broadcast event
                await broadcast_data_change(
                    event_type=action,
                    entity_type="task",
                    entity_id=task_id,
                    user_id=owner_user_id,
                    data={
                        "primary": {
                            "id": task_id,
                            "title": "Test Task",
                            "status": "completed" if action == "completed" else "todo",
                        }
                    },
                )

                # Assert owner received event
                assert mock_owner_ws.send_json.called, (
                    f"Owner should receive {action} event"
                )

                # Verify action in message
                sent_message = mock_owner_ws.send_json.call_args[0][0]
                assert sent_message["payload"]["action"] == action

        finally:
            # Cleanup
            active_connections.clear()
            connection_users.clear()
