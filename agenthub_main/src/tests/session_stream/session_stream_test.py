"""Tenant isolation and ingest/view flow for streamed sessions.

Run this file with ``--noconftest``:

    python3 -m pytest --noconftest -p no:cacheprovider src/tests/session_stream/session_stream_test.py -q

The repo's ``src/tests/conftest.py`` cannot be used for this file, for two reasons:

1. Its autouse ``set_mcp_db_path_for_tests`` fixture calls ``initialize_database(None)``,
   which retries a Postgres connection (it expects a database ``agenthub_test``) inside a
   sleep loop; with no such server the run never reaches the first test. Observed here:
   no output in 120s, with the stack parked in
   ``task_management/infrastructure/database/connection_retry.py`` beneath
   ``conftest.py:1675``.
2. It replaces ``sys.modules["fastapi"]`` and ``fastapi.testclient`` with mocks, so the
   real ``FastAPI``/``TestClient`` this file needs (its websocket tests) are not what the
   imports return.

This file needs neither: it builds an in-memory SQLite engine in the ``db`` fixture.
Without the flag the run hangs before the first test; with the flag it passes
(16 passed in ~2.4s).
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.websockets import WebSocketDisconnect

from fastmcp.auth.unified_token_validator import AuthResult
from fastmcp.server.routes import session_stream_routes as routes
from fastmcp.session_stream import repository as repo
from fastmcp.task_management.infrastructure.database.models import (
    AgentSession,
    AgentSessionEvent,
)


@pytest.fixture
def db(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    AgentSession.__table__.create(engine)
    AgentSessionEvent.__table__.create(engine)
    maker = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(repo, "_default_factory", maker)
    return maker


def _sid(user, key="s1", connector="c1"):
    return repo.upsert_session(user, connector, key, key)["id"]


def test_session_id_is_deterministic_and_user_scoped():
    assert repo.session_id_for("a", "c", "k") == repo.session_id_for("a", "c", "k")
    assert repo.session_id_for("a", "c", "k") != repo.session_id_for("b", "c", "k")


def test_users_cannot_see_each_others_sessions_or_events(db):
    a = _sid("user-a")
    b = _sid("user-b")
    assert a != b
    repo.append_events("user-a", a, [{"type": "message", "payload": {"t": "secret"}}])

    assert [s["id"] for s in repo.list_sessions("user-a")] == [a]
    assert [s["id"] for s in repo.list_sessions("user-b")] == [b]
    assert repo.get_session_for_user("user-b", a) is None
    assert repo.list_events("user-b", a) == []
    with pytest.raises(PermissionError):
        repo.append_events("user-b", a, [{"type": "message"}])


def test_seq_is_assigned_by_server_and_monotonic(db):
    sid = _sid("user-a")
    first = repo.append_events("user-a", sid, [{"payload": {}}, {"payload": {}}])
    second = repo.append_events("user-a", sid, [{"payload": {}}])
    assert [e["seq"] for e in first + second] == [1, 2, 3]
    assert [e["seq"] for e in repo.list_events("user-a", sid, after_seq=1)] == [2, 3]


def test_batch_limit(db):
    sid = _sid("user-a")
    with pytest.raises(ValueError):
        repo.append_events("user-a", sid, [{}] * (repo.MAX_EVENTS_PER_BATCH + 1))


@pytest.fixture
def client(db, monkeypatch):
    tokens = {
        "tok-a": AuthResult(valid=True, user_id="user-a", scopes=["sessions:write"]),
        "tok-b": AuthResult(valid=True, user_id="user-b", scopes=["sessions:write"]),
        "tok-ro": AuthResult(valid=True, user_id="user-a", scopes=["read"]),
    }

    async def fake_validate(token, client_info=None):
        return tokens.get(token, AuthResult(valid=False))

    class U:
        def __init__(self, id):
            self.id = id

    async def fake_ws_user(token):
        return {"jwt-a": U("user-a"), "jwt-b": U("user-b")}.get(token)

    monkeypatch.setattr(routes, "validate_token_universal", fake_validate)
    monkeypatch.setattr(routes, "validate_websocket_token", fake_ws_user)
    app = FastAPI()
    app.include_router(routes.router)
    return TestClient(app)


def _ingest(ws, key="s1"):
    ws.send_json({"type": "hello", "connector_id": "c1"})
    assert ws.receive_json()["type"] == "ready"
    ws.send_json({"type": "session", "session_key": key, "name": "coder"})
    ack = ws.receive_json()
    assert ack["type"] == "session_ack"
    return ack["session_id"]


def test_connector_rejects_bad_token_and_missing_scope(client):
    for tok in ("nope", "tok-ro"):
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(f"/ws/connector?token={tok}"):
                pass


def test_ingest_then_owner_can_replay_but_other_user_cannot(client):
    with client.websocket_connect("/ws/connector?token=tok-a") as ws:
        sid = _ingest(ws)
        ws.send_json(
            {
                "type": "events",
                "session_key": "s1",
                "events": [{"type": "message", "payload": {"text": "hi"}}],
            }
        )
        assert ws.receive_json() == {
            "type": "events_ack",
            "session_id": sid,
            "last_seq": 1,
        }

    with client.websocket_connect(f"/ws/sessions/{sid}?token=jwt-a") as viewer:
        ev = viewer.receive_json()
        assert ev["seq"] == 1 and ev["payload"] == {"text": "hi"}

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/sessions/{sid}?token=jwt-b"):
            pass


def test_events_for_unregistered_session_key_are_refused(client):
    with client.websocket_connect("/ws/connector?token=tok-a") as ws:
        ws.send_json({"type": "hello", "connector_id": "c1"})
        ws.receive_json()
        ws.send_json({"type": "events", "session_key": "nope", "events": [{}]})
        assert ws.receive_json()["type"] == "error"


def test_disconnect_marks_sessions_offline(client, db):
    with client.websocket_connect("/ws/connector?token=tok-a") as ws:
        sid = _ingest(ws)
    assert repo.get_session_for_user("user-a", sid)["status"] == "offline"


def test_live_event_reaches_already_connected_viewer_and_viewer_can_leave(client):
    with client.websocket_connect("/ws/connector?token=tok-a") as ws:
        sid = _ingest(ws)
        with client.websocket_connect(f"/ws/sessions/{sid}?token=jwt-a") as viewer:
            ws.send_json(
                {
                    "type": "events",
                    "session_key": "s1",
                    "events": [{"type": "output", "payload": {"text": "live"}}],
                }
            )
            assert ws.receive_json()["type"] == "events_ack"
            ev = viewer.receive_json()
            assert ev["seq"] == 1 and ev["payload"] == {"text": "live"}
        # leaving an idle viewer must not leak its subscription
        assert sid not in routes.hub._subs


# ---- regressions found in review ----


def test_non_object_events_and_odd_project_do_not_crash_the_connector(client):
    with client.websocket_connect("/ws/connector?token=tok-a") as ws:
        ws.send_json({"type": "hello", "connector_id": "c1"})
        ws.receive_json()
        ws.send_json(
            {"type": "session", "session_key": "s1", "name": "n", "project": {"x": 1}}
        )
        ack = ws.receive_json()
        assert ack["type"] == "session_ack"
        ws.send_json({"type": "events", "session_key": "s1", "events": [1, "x", None]})
        assert ws.receive_json() == {
            "type": "error",
            "error": "each event must be an object",
        }
        # socket is still usable
        ws.send_json(
            {"type": "events", "session_key": "s1", "events": [{"payload": {"a": 1}}]}
        )
        assert ws.receive_json()["type"] == "events_ack"


def test_hello_cannot_switch_connector_id(client):
    with client.websocket_connect("/ws/connector?token=tok-a") as ws:
        ws.send_json({"type": "hello", "connector_id": "c1"})
        ws.receive_json()
        ws.send_json({"type": "hello", "connector_id": "c2"})
        assert ws.receive_json()["error"] == "connector_id already set"


def test_reconnect_does_not_mark_live_sessions_offline(client):
    with client.websocket_connect("/ws/connector?token=tok-a") as old:
        sid = _ingest(old)
        with client.websocket_connect("/ws/connector?token=tok-a") as new:
            assert _ingest(new) == sid
        # the newer socket closed first here, but the older one is still open
        assert repo.get_session_for_user("user-a", sid)["status"] == "active"
    assert repo.get_session_for_user("user-a", sid)["status"] == "offline"


def test_viewer_message_does_not_end_the_stream(client):
    with client.websocket_connect("/ws/connector?token=tok-a") as ws:
        sid = _ingest(ws)
        with client.websocket_connect(f"/ws/sessions/{sid}?token=jwt-a") as viewer:
            viewer.send_text("ping")
            ws.send_json(
                {
                    "type": "events",
                    "session_key": "s1",
                    "events": [{"payload": {"n": 1}}],
                }
            )
            assert ws.receive_json()["type"] == "events_ack"
            assert viewer.receive_json()["seq"] == 1


def test_overflowing_viewer_is_told_to_reconnect():
    import asyncio

    from fastmcp.session_stream.hub import OVERFLOW, QUEUE_SIZE, SessionHub

    h = SessionHub()
    q = h.subscribe("s")
    h.publish("s", [{"seq": i} for i in range(1, QUEUE_SIZE + 2)])
    assert q.get_nowait() == OVERFLOW and q.empty()
    assert "s" not in h._subs
    assert isinstance(q, asyncio.Queue)


def test_model_timestamps_are_naive_utc(db):
    sid = _sid("user-a")
    with db() as s:
        row = s.get(AgentSession, sid)
        assert row.created_at.tzinfo is None and row.last_seen.tzinfo is None


def test_oversized_payload_is_truncated_by_json_size(db):
    sid = _sid("user-a")
    big = {"t": "x" * (repo.MAX_PAYLOAD_CHARS + 1)}
    [ev] = repo.append_events("user-a", sid, [{"payload": big}])
    assert ev["payload"] == {"truncated": True}
