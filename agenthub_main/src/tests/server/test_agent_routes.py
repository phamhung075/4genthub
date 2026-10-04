"""Route tests for /api/v2/agents/metadata.

AgentAPIController.get_agent_metadata returns a plain dict, so the route must
return that dict (or raise 500 when success is false) instead of reading
result.success / result.model_dump.
"""

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fastmcp.auth.interface.fastapi_auth import get_current_user, get_db
from fastmcp.server.routes import agent_routes


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(agent_routes.router)
    user = MagicMock()
    user.id = "user-1"
    user.email = "test@example.com"
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: MagicMock()
    yield TestClient(app)
    app.dependency_overrides.clear()


def _stub_controller(monkeypatch, payload):
    controller = MagicMock()
    controller.get_agent_metadata.return_value = payload
    monkeypatch.setattr(agent_routes, "agent_controller", controller)
    return controller


def test_metadata_returns_the_controller_dict(client, monkeypatch):
    payload = {
        "success": True,
        "agents": [{"id": "coding-agent"}],
        "total": 1,
        "source": "facade",
    }
    controller = _stub_controller(monkeypatch, payload)

    response = client.get("/api/v2/agents/metadata")

    assert response.status_code == 200
    assert response.json() == payload
    controller.get_agent_metadata.assert_called_once()
    assert controller.get_agent_metadata.call_args.kwargs["user_id"] == "user-1"


def test_metadata_reports_500_with_the_controller_message(client, monkeypatch):
    _stub_controller(
        monkeypatch, {"success": False, "message": "agent store unavailable"}
    )

    response = client.get("/api/v2/agents/metadata")

    assert response.status_code == 500
    assert response.json()["detail"] == "agent store unavailable"


def test_metadata_reports_500_when_no_message(client, monkeypatch):
    _stub_controller(monkeypatch, {"success": False})

    response = client.get("/api/v2/agents/metadata")

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to fetch agent metadata"


def test_metadata_serves_the_real_controller_dict(client, monkeypatch):
    facade = MagicMock()
    facade.list_all_agents.return_value = {
        "success": True,
        "agents": [{"id": "coding-agent"}, {"id": "debugger-agent"}],
    }
    monkeypatch.setattr(
        agent_routes.agent_controller.facade_service,
        "get_agent_facade",
        lambda project_id=None, user_id=None: facade,
    )

    response = client.get("/api/v2/agents/metadata")

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "agents": [{"id": "coding-agent"}, {"id": "debugger-agent"}],
        "total": 2,
        "source": "facade",
    }
