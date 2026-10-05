"""Session streaming: connector ingest + per-user browser viewing.

Connector (user's machine) -> WS /ws/connector?token=<api token, scope sessions:write>
Browser                    -> WS /ws/sessions/{id}?token=<Keycloak JWT>
REST                       -> GET /api/v2/sessions, GET /api/v2/sessions/{id}/events

Connector messages (JSON):
  {"type":"hello","connector_id":"..."}
  {"type":"session","session_key":"...","name":"...","project":"..."}
  {"type":"events","session_key":"...","events":[{"type":"message","payload":{}}]}
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect

from ...auth.domain.entities.user import User
from ...auth.interface.fastapi_auth import get_current_user
from ...auth.unified_token_validator import validate_token_universal
from ...session_stream import repository as repo
from ...session_stream.hub import hub
from .websocket_routes import validate_websocket_token

logger = logging.getLogger(__name__)

router = APIRouter(tags=["session-stream"])

WRITE_SCOPE = "sessions:write"
MAX_MESSAGE_CHARS = 1024 * 1024
_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")

# Close codes: 4001 auth required, 4003 missing scope, 4004 not found
_AUTH = 4001
_FORBIDDEN = 4003
_NOT_FOUND = 4004
_TRY_AGAIN = 1013

# Open connector sockets per (user_id, connector_id). A reconnect opens the new
# socket before the old one is noticed closed; sessions may only go offline when
# the last socket for that connector closes.
_open_connectors: dict[tuple[str, str], int] = {}


async def _authenticate_connector(websocket: WebSocket) -> tuple[str, list[str]] | None:
    token = websocket.query_params.get("token")
    if not token:
        header = websocket.headers.get("authorization", "")
        if header.lower().startswith("bearer "):
            token = header[7:].strip()
    if not token:
        return None
    result = await validate_token_universal(token)
    if not result.valid or not result.user_id:
        return None
    return result.user_id, list(result.scopes or [])


@router.websocket("/ws/connector")
async def connector_ingest(websocket: WebSocket) -> None:
    auth = await _authenticate_connector(websocket)
    if auth is None:
        await websocket.close(code=_AUTH, reason="Authentication required")
        return
    user_id, scopes = auth
    if WRITE_SCOPE not in scopes:
        await websocket.close(code=_FORBIDDEN, reason=f"Missing scope {WRITE_SCOPE}")
        return

    await websocket.accept()
    connector_id: str | None = None
    # session_key -> session_id, only for sessions this connection registered
    known: dict[str, str] = {}

    try:
        while True:
            raw = await websocket.receive_text()
            if len(raw) > MAX_MESSAGE_CHARS:
                await websocket.send_json(
                    {"type": "error", "error": "message too large"}
                )
                continue
            try:
                msg: dict[str, Any] = json.loads(raw)
                kind = msg.get("type")
            except (json.JSONDecodeError, AttributeError):
                await websocket.send_json({"type": "error", "error": "invalid json"})
                continue

            if kind == "hello":
                cid = str(msg.get("connector_id", ""))
                if not _ID_RE.match(cid):
                    await websocket.send_json(
                        {"type": "error", "error": "bad connector_id"}
                    )
                    continue
                if connector_id is not None and connector_id != cid:
                    await websocket.send_json(
                        {"type": "error", "error": "connector_id already set"}
                    )
                    continue
                if connector_id is None:
                    connector_id = cid
                    key_ = (user_id, cid)
                    _open_connectors[key_] = _open_connectors.get(key_, 0) + 1
                await websocket.send_json({"type": "ready", "connector_id": cid})
                continue

            if connector_id is None:
                await websocket.send_json(
                    {"type": "error", "error": "send hello first"}
                )
                continue

            if kind == "session":
                key = str(msg.get("session_key", ""))
                if not key or len(key) > 255:
                    await websocket.send_json(
                        {"type": "error", "error": "bad session_key"}
                    )
                    continue
                try:
                    row = await asyncio.to_thread(
                        repo.upsert_session,
                        user_id,
                        connector_id,
                        key,
                        str(msg.get("name") or key),
                        msg.get("project"),
                    )
                except Exception:
                    logger.exception("session upsert failed")
                    await websocket.send_json(
                        {"type": "error", "error": "internal error"}
                    )
                    continue
                known[key] = row["id"]
                await websocket.send_json(
                    {
                        "type": "session_ack",
                        "session_key": key,
                        "session_id": row["id"],
                        "last_seq": row["last_seq"],
                    }
                )
            elif kind == "events":
                sid = known.get(str(msg.get("session_key", "")))
                events = msg.get("events")
                if sid is None or not isinstance(events, list):
                    await websocket.send_json(
                        {"type": "error", "error": "unknown session"}
                    )
                    continue
                try:
                    stored = await asyncio.to_thread(
                        repo.append_events, user_id, sid, events
                    )
                except (ValueError, PermissionError) as e:
                    await websocket.send_json({"type": "error", "error": str(e)})
                    continue
                except Exception:
                    logger.exception("event append failed")
                    await websocket.send_json(
                        {"type": "error", "error": "internal error"}
                    )
                    continue
                hub.publish(sid, stored)
                await websocket.send_json(
                    {
                        "type": "events_ack",
                        "session_id": sid,
                        "last_seq": stored[-1]["seq"] if stored else 0,
                    }
                )
            else:
                await websocket.send_json({"type": "error", "error": "unknown type"})
    except WebSocketDisconnect:
        pass
    finally:
        if connector_id:
            key_ = (user_id, connector_id)
            left = _open_connectors.get(key_, 1) - 1
            if left > 0:
                _open_connectors[key_] = left
            else:
                _open_connectors.pop(key_, None)
                try:
                    await asyncio.to_thread(repo.mark_offline, user_id, connector_id)
                except Exception:
                    logger.exception("mark_offline failed")


async def _wait_disconnect(websocket: WebSocket) -> None:
    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                return
    except (WebSocketDisconnect, RuntimeError):
        return


@router.websocket("/ws/sessions/{session_id}")
async def session_viewer(websocket: WebSocket, session_id: str) -> None:
    user = await validate_websocket_token(websocket.query_params.get("token", ""))
    if user is None:
        await websocket.close(code=_AUTH, reason="Authentication required")
        return
    # Same response for "missing" and "not yours" so ids can't be probed.
    if await asyncio.to_thread(repo.get_session_for_user, user.id, session_id) is None:
        await websocket.close(code=_NOT_FOUND, reason="Session not found")
        return

    await websocket.accept()
    try:
        after = int(websocket.query_params.get("after_seq", "0"))
    except ValueError:
        after = 0

    q = hub.subscribe(session_id)  # subscribe before replay so nothing is missed
    try:
        last = after
        while True:
            batch = await asyncio.to_thread(
                repo.list_events, user.id, session_id, last, 500
            )
            for ev in batch:
                await websocket.send_json(ev)
                last = ev["seq"]
            if len(batch) < 500:
                break
        # Watch the socket too: without a pending receive, an idle viewer
        # would never notice the browser closing and would leak its queue.
        # Anything the browser sends (e.g. a ping) is ignored, not a close.
        closed = asyncio.create_task(_wait_disconnect(websocket))
        try:
            while True:
                nxt = asyncio.create_task(q.get())
                done, _ = await asyncio.wait(
                    {nxt, closed}, return_when=asyncio.FIRST_COMPLETED
                )
                if closed in done:
                    nxt.cancel()
                    break
                ev = nxt.result()
                if ev.get("_overflow"):
                    # Too slow: close so the browser reconnects with after_seq.
                    await websocket.close(code=_TRY_AGAIN, reason="Too slow, reconnect")
                    break
                if ev["seq"] <= last:  # already replayed
                    continue
                await websocket.send_json(ev)
                last = ev["seq"]
        finally:
            closed.cancel()
    except WebSocketDisconnect:
        pass
    finally:
        hub.unsubscribe(session_id, q)


@router.get("/api/v2/sessions")
async def list_my_sessions(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return {"sessions": await asyncio.to_thread(repo.list_sessions, current_user.id)}


@router.get("/api/v2/sessions/{session_id}/events")
async def list_my_session_events(
    session_id: str,
    after_seq: int = 0,
    limit: int = 500,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    if (
        await asyncio.to_thread(repo.get_session_for_user, current_user.id, session_id)
        is None
    ):
        raise HTTPException(status_code=404, detail="Session not found")
    events = await asyncio.to_thread(
        repo.list_events, current_user.id, session_id, after_seq, limit
    )
    return {"events": events}
