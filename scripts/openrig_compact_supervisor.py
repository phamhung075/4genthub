#!/usr/bin/env python3
"""Keep every seat of a rig under the per-session context limit without cutting a job short.

A seat may run past the limit, up to ``HARD_LIMIT`` where it is compacted whatever it is doing. When its context crosses ``COMPACT_LIMIT`` the supervisor tells the
seat once, in its terminal, that the limit is reached and how to compact itself. When the seat then
finishes (its session log is silent for ``--quiet`` seconds) and is still over the limit, the
supervisor sends ``/compact`` for it. A compaction counts only when a new compaction record appears
(omp) or the context drops (Claude Code); a send with no such witness is logged as a failure.
Run it from the host, not inside a seat pane: a loop in a seat dies with the seats it watches.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import openrig_watch_tools as watch  # noqa: E402

TAIL_BYTES = 2_000_000
COOLDOWN = 900  # seconds after a /compact before the same seat is considered again


def last_context(log: Path) -> int | None:
    """Tokens of the newest reading in the log; the tail is enough because it is a last reading."""
    with open(log, "rb") as fh:
        fh.seek(max(log.stat().st_size - TAIL_BYTES, 0))
        lines = fh.read().decode(errors="replace").splitlines()
    return next((t for t in map(watch.context_tokens, reversed(lines)) if t), None)


def compactions(log: Path) -> int:
    with open(log, "rb") as fh:
        return fh.read().decode(errors="replace").count('"type":"compaction"')


def say(rig: str, seat: str, text: str) -> None:
    subprocess.run(
        ["rig", "send", f"{rig}-{seat}@{rig}", text, "--wait-for-idle", "120"],
        capture_output=True,
        text=True,
    )


def log(text: str) -> None:
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {text}", flush=True)


def notice(rig: str, seat: str) -> str:
    return (
        "Context limit reached: your session is past "
        f"{watch.kilo(watch.COMPACT_LIMIT)} tokens. You may finish the job you are on. "
        "When it is finished, compact your own session: run this and nothing else: "
        f"rig send {rig}-{seat}@{rig} /compact --wait-for-idle 120. "
        f"If you do not, the supervisor sends /compact for you once you have been quiet for a while, "
        f"or at once at {watch.kilo(watch.HARD_LIMIT)} tokens."
    )


def step(rig: str, state: dict, quiet: int) -> None:
    now = time.time()
    for seat in watch.rig_seats(rig):
        path, runtime = watch.seat_log(rig, seat)
        if path is None:
            continue
        used = last_context(path)
        s = state.setdefault(seat, {"told": False, "sent": 0.0, "before": None, "count": 0})
        if used is None or used < watch.COMPACT_LIMIT:
            s["told"] = False
            continue
        if s["before"] is not None and now - s["sent"] > 180:
            done = compactions(path) > s["count"] or used < s["before"] * 0.6
            log(f"{seat}: /compact {'WITNESSED' if done else 'NOT witnessed'} ({watch.kilo(s['before'])} -> {watch.kilo(used)})")
            s["before"] = None
        if not s["told"]:
            say(rig, seat, notice(rig, seat))
            s["told"] = True
            log(f"{seat}: told, {watch.kilo(used)} of {watch.kilo(watch.COMPACT_LIMIT)} ({runtime})")
        silent = now - path.stat().st_mtime
        if (silent >= quiet or used >= watch.HARD_LIMIT) and now - s["sent"] > COOLDOWN:
            s.update(sent=now, before=used, count=compactions(path))
            say(rig, seat, "/compact")
            log(f"{seat}: quiet {silent:.0f}s at {watch.kilo(used)}, sent /compact{' (hard limit)' if used >= watch.HARD_LIMIT else ''}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rig", default="4genthub-min")
    ap.add_argument("--quiet", type=int, default=180, help="seconds of log silence that mean the job is finished")
    ap.add_argument("--every", type=int, default=30)
    ap.add_argument("--once", action="store_true")
    a = ap.parse_args()
    state: dict = {}
    log(f"supervising {a.rig}: limit {watch.kilo(watch.COMPACT_LIMIT)}, quiet {a.quiet}s")
    while True:
        step(a.rig, state, a.quiet)
        if a.once:
            return
        time.sleep(a.every)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
