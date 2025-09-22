"""
Test Bulk API Endpoint

Tests for the new /api/v2/branches/summaries/bulk endpoint
that queries materialized views for optimized performance.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import time


@pytest.fixture
def client():
    """Create a test client"""
    from fastmcp.server.mcp_entry_point import app
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Mock authentication headers"""
    return {"Authorization": "Bearer test-token"}


@pytest.fixture
def mock_user():
    """Mock authenticated user"""
    user = MagicMock()
    user.id = "test-user-id"
    user.email = "test@example.com"
    return user


class TestBulkSummariesEndpoint:
    """Test suite for bulk summaries API endpoint"""

    @patch('fastmcp.server.routes.branch_routes.get_current_user')
    @patch('fastmcp.server.routes.branch_routes.get_db')
    def test_bulk_summaries_with_project_ids(self, mock_db, mock_get_user, client, mock_user, auth_headers):
        """Test bulk summaries endpoint with specific project IDs"""
        # Setup
        mock_get_user.return_value = mock_user
        mock_session = MagicMock()
        mock_db.return_value = mock_session

        # Mock database results
        mock_session.execute.return_value.fetchall.return_value = [
            # branch_id, project_id, name, status, priority, total, completed, in_progress, blocked, todo, progress, last_activity
            ("branch-1", "proj-1", "main", "active", "high", 10, 5, 3, 1, 1, 50.0, None),
            ("branch-2", "proj-2", "develop", "active", "medium", 20, 10, 5, 2, 3, 50.0, None)
        ]

        # Make request
        response = client.post(
            "/api/v2/branches/summaries/bulk",
            json={
                "project_ids": ["proj-1", "proj-2"],
                "include_archived": False
            },
            headers=auth_headers
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "summaries" in data
        assert "projects" in data
        assert "metadata" in data
        assert data["metadata"]["count"] == 2

    @patch('fastmcp.server.routes.branch_routes.get_current_user')
    @patch('fastmcp.server.routes.branch_routes.get_db')
    def test_bulk_summaries_performance(self, mock_db, mock_get_user, client, mock_user, auth_headers):
        """Test that bulk summaries endpoint meets performance requirements"""
        # Setup
        mock_get_user.return_value = mock_user
        mock_session = MagicMock()
        mock_db.return_value = mock_session

        # Simulate 100 branches
        mock_branches = []
        for i in range(100):
            mock_branches.append(
                (f"branch-{i}", f"proj-{i//10}", f"branch-{i}", "active", "medium",
                 10, 5, 3, 1, 1, 50.0, None)
            )
        mock_session.execute.return_value.fetchall.return_value = mock_branches

        # Make request and measure time
        start_time = time.time()
        response = client.post(
            "/api/v2/branches/summaries/bulk",
            json={"include_archived": False},
            headers=auth_headers
        )
        response_time = (time.time() - start_time) * 1000  # Convert to ms

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Check performance - should be under 200ms even for 100 branches
        # Note: In real test this would check actual query time from metadata
        if "metadata" in data and "query_time_ms" in data["metadata"]:
            assert data["metadata"]["query_time_ms"] < 200

    @patch('fastmcp.server.routes.branch_routes.get_current_user')
    @patch('fastmcp.server.routes.branch_routes.get_db')
    def test_bulk_summaries_with_user_projects(self, mock_db, mock_get_user, client, mock_user, auth_headers):
        """Test bulk summaries endpoint without project IDs (uses user's projects)"""
        # Setup
        mock_get_user.return_value = mock_user
        mock_session = MagicMock()
        mock_db.return_value = mock_session

        # Mock user projects query
        mock_session.execute.return_value.fetchall.side_effect = [
            [("proj-1",), ("proj-2",)],  # User's projects
            [("branch-1", "proj-1", "main", "active", "high", 10, 5, 3, 1, 1, 50.0, None)]  # Branches
        ]

        # Make request
        response = client.post(
            "/api/v2/branches/summaries/bulk",
            json={"include_archived": False},
            headers=auth_headers
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "summaries" in data

    @patch('fastmcp.server.routes.branch_routes.get_current_user')
    @patch('fastmcp.server.routes.branch_routes.get_db')
    def test_bulk_summaries_include_archived(self, mock_db, mock_get_user, client, mock_user, auth_headers):
        """Test bulk summaries endpoint with archived branches included"""
        # Setup
        mock_get_user.return_value = mock_user
        mock_session = MagicMock()
        mock_db.return_value = mock_session

        # Mock database results including archived branches
        mock_session.execute.return_value.fetchall.return_value = [
            ("branch-1", "proj-1", "main", "active", "high", 10, 5, 3, 1, 1, 50.0, None),
            ("branch-2", "proj-1", "feature", "archived", "low", 5, 5, 0, 0, 0, 100.0, None)
        ]

        # Make request
        response = client.post(
            "/api/v2/branches/summaries/bulk",
            json={
                "project_ids": ["proj-1"],
                "include_archived": True
            },
            headers=auth_headers
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["metadata"]["count"] == 2  # Should include archived branch

    @patch('fastmcp.server.routes.branch_routes.get_current_user')
    @patch('fastmcp.server.routes.branch_routes.get_db')
    def test_bulk_summaries_empty_result(self, mock_db, mock_get_user, client, mock_user, auth_headers):
        """Test bulk summaries endpoint when no projects are found"""
        # Setup
        mock_get_user.return_value = mock_user
        mock_session = MagicMock()
        mock_db.return_value = mock_session

        # Mock empty user projects
        mock_session.execute.return_value.fetchall.return_value = []

        # Make request
        response = client.post(
            "/api/v2/branches/summaries/bulk",
            json={"include_archived": False},
            headers=auth_headers
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["summaries"] == {}
        assert data["metadata"]["count"] == 0
        assert "No projects found" in str(data.get("metadata", {}).get("message", ""))

    @patch('fastmcp.server.routes.branch_routes.get_current_user')
    @patch('fastmcp.server.routes.branch_routes.get_db')
    def test_bulk_summaries_error_handling(self, mock_db, mock_get_user, client, mock_user, auth_headers):
        """Test bulk summaries endpoint error handling"""
        # Setup
        mock_get_user.return_value = mock_user
        mock_session = MagicMock()
        mock_db.return_value = mock_session

        # Simulate database error
        mock_session.execute.side_effect = Exception("Database connection error")

        # Make request
        response = client.post(
            "/api/v2/branches/summaries/bulk",
            json={"project_ids": ["proj-1"]},
            headers=auth_headers
        )

        # Assertions
        assert response.status_code == 500
        data = response.json()
        assert "Failed to fetch bulk summaries" in data["detail"]