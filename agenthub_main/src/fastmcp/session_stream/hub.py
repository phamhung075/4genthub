"""In-process fan-out of stored session events to connected browsers."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

QUEUE_SIZE = 1000
OVERFLOW: dict[str, Any] = {"_overflow": True}


class SessionHub:
    def __init__(self) -> None:
        self._subs: dict[str, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)

    def subscribe(self, session_id: str) -> asyncio.Queue[dict[str, Any]]:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=QUEUE_SIZE)
        self._subs[session_id].add(q)
        return q

    def unsubscribe(self, session_id: str, q: asyncio.Queue[dict[str, Any]]) -> None:
        subs = self._subs.get(session_id)
        if subs:
            subs.discard(q)
            if not subs:
                del self._subs[session_id]

    def publish(self, session_id: str, events: list[dict[str, Any]]) -> None:
        """Non-blocking. A slow viewer that overflows is dropped, not waited on.

        The dropped viewer gets an OVERFLOW marker so its handler can close the
        socket and let the browser reconnect with after_seq, instead of
        waiting forever on a queue that is no longer fed.
        """
        for q in list(self._subs.get(session_id, ())):
            for ev in events:
                try:
                    q.put_nowait(ev)
                except asyncio.QueueFull:
                    self.unsubscribe(session_id, q)
                    while not q.empty():
                        q.get_nowait()
                    q.put_nowait(OVERFLOW)
                    break


hub = SessionHub()
