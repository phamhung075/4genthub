"""Persistence for streamed sessions.

Every function takes user_id and filters on it. That is the only tenant
boundary (PostgreSQL here has no row-level security), so routes must never
query the session tables directly.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..task_management.infrastructure.database.models import (
    AgentSession,
    AgentSessionEvent,
)

_NAMESPACE = uuid.UUID("6f1c2d3e-4a5b-4c6d-8e7f-0a1b2c3d4e5f")

MAX_EVENTS_PER_BATCH = 200
MAX_PAYLOAD_CHARS = 64 * 1024

SessionFactory = Callable[[], Session]


def _default_factory() -> Session:
    from ..task_management.infrastructure.database.database_config import get_session

    return get_session()


def session_id_for(user_id: str, connector_id: str, session_key: str) -> str:
    """Deterministic id so a reconnecting connector resumes the same session."""
    return str(uuid.uuid5(_NAMESPACE, f"{user_id}:{connector_id}:{session_key}"))


def _clip(value: Any) -> str | None:
    """Coerce an untrusted optional field to a short string."""
    if value is None or value == "":
        return None
    return str(value)[:255]


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _row(s: AgentSession) -> dict[str, Any]:
    return {
        "id": s.id,
        "name": s.name,
        "project": s.project,
        "status": s.status,
        "connector_id": s.connector_id,
        "last_seq": s.last_seq,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "last_seen": s.last_seen.isoformat() if s.last_seen else None,
    }


def upsert_session(
    user_id: str,
    connector_id: str,
    session_key: str,
    name: str,
    project: str | None = None,
    factory: SessionFactory | None = None,
) -> dict[str, Any]:
    sid = session_id_for(user_id, connector_id, session_key)
    db = (factory or _default_factory)()
    try:
        row = db.get(AgentSession, sid)
        if row is not None and row.user_id != user_id:
            raise PermissionError("session belongs to another user")
        if row is None:
            row = AgentSession(
                id=sid,
                user_id=user_id,
                connector_id=connector_id,
                session_key=session_key,
                name=name[:255],
                project=_clip(project),
                status="active",
                last_seq=0,
            )
            db.add(row)
        else:
            row.name = name[:255]
            row.project = _clip(project) or row.project
            row.status = "active"
        row.last_seen = _now()
        db.commit()
        return _row(row)
    finally:
        db.close()


def append_events(
    user_id: str,
    session_id: str,
    events: list[dict[str, Any]],
    factory: SessionFactory | None = None,
) -> list[dict[str, Any]]:
    """Append events, assigning seq on the server. Returns the stored events."""
    if len(events) > MAX_EVENTS_PER_BATCH:
        raise ValueError(f"at most {MAX_EVENTS_PER_BATCH} events per batch")
    db = (factory or _default_factory)()
    try:
        if not all(isinstance(ev, dict) for ev in events):
            raise ValueError("each event must be an object")
        # FOR UPDATE serializes writers on one session so last_seq (and the
        # unique (session_id, seq) key) cannot collide. SQLite ignores it.
        row = db.execute(
            select(AgentSession)
            .where(AgentSession.id == session_id, AgentSession.user_id == user_id)
            .with_for_update()
        ).scalar_one_or_none()
        if row is None:
            raise PermissionError("unknown session")
        stored = []
        for ev in events:
            payload = ev.get("payload") or {}
            if len(json.dumps(payload, default=str)) > MAX_PAYLOAD_CHARS:
                payload = {"truncated": True}
            row.last_seq += 1
            rec = AgentSessionEvent(
                session_id=session_id,
                user_id=user_id,
                seq=row.last_seq,
                type=str(ev.get("type", "message"))[:32],
                payload=payload,
            )
            db.add(rec)
            stored.append(
                {
                    "seq": rec.seq,
                    "type": rec.type,
                    "payload": payload,
                }
            )
        row.last_seen = _now()
        db.commit()
        return stored
    finally:
        db.close()


def list_sessions(
    user_id: str, factory: SessionFactory | None = None
) -> list[dict[str, Any]]:
    db = (factory or _default_factory)()
    try:
        rows = (
            db.execute(
                select(AgentSession)
                .where(AgentSession.user_id == user_id)
                .order_by(AgentSession.last_seen.desc())
            )
            .scalars()
            .all()
        )
        return [_row(r) for r in rows]
    finally:
        db.close()


def get_session_for_user(
    user_id: str, session_id: str, factory: SessionFactory | None = None
) -> dict[str, Any] | None:
    db = (factory or _default_factory)()
    try:
        row = db.execute(
            select(AgentSession).where(
                AgentSession.id == session_id, AgentSession.user_id == user_id
            )
        ).scalar_one_or_none()
        return _row(row) if row else None
    finally:
        db.close()


def list_events(
    user_id: str,
    session_id: str,
    after_seq: int = 0,
    limit: int = 500,
    factory: SessionFactory | None = None,
) -> list[dict[str, Any]]:
    db = (factory or _default_factory)()
    try:
        rows = (
            db.execute(
                select(AgentSessionEvent)
                .where(
                    AgentSessionEvent.user_id == user_id,
                    AgentSessionEvent.session_id == session_id,
                    AgentSessionEvent.seq > after_seq,
                )
                .order_by(AgentSessionEvent.seq)
                .limit(min(limit, 1000))
            )
            .scalars()
            .all()
        )
        return [
            {
                "seq": r.seq,
                "type": r.type,
                "payload": r.payload,
                "ts": r.ts.isoformat() if r.ts else None,
            }
            for r in rows
        ]
    finally:
        db.close()


def mark_offline(
    user_id: str, connector_id: str, factory: SessionFactory | None = None
) -> None:
    from sqlalchemy import update

    db = (factory or _default_factory)()
    try:
        db.execute(
            update(AgentSession)
            .where(
                AgentSession.user_id == user_id,
                AgentSession.connector_id == connector_id,
            )
            .values(status="offline", last_seen=_now())
        )
        db.commit()
    finally:
        db.close()


__all__ = [
    "MAX_EVENTS_PER_BATCH",
    "append_events",
    "get_session_for_user",
    "list_events",
    "list_sessions",
    "mark_offline",
    "session_id_for",
    "upsert_session",
]
