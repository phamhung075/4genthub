"""Tests for scripts/openrig_compact_supervisor.py: tell once past the limit, compact only after the job ends."""

import importlib.util
import json
import os
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[4] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location(
    "openrig_compact_supervisor", SCRIPTS / "openrig_compact_supervisor.py"
)
sup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sup)


def seat_log(tmp_path, tokens, age):
    path = tmp_path / "s.jsonl"
    path.write_text(json.dumps({"message": {"usage": {"totalTokens": tokens}}}) + "\n")
    stamp = time.time() - age
    os.utime(path, (stamp, stamp))
    return path


def run_step(monkeypatch, path, state, working=False):
    sent = []
    monkeypatch.setattr(sup.watch, "rig_seats", lambda rig: ["lead"])
    monkeypatch.setattr(sup.watch, "seat_log", lambda rig, seat: (path, "omp"))
    monkeypatch.setattr(sup, "idle", lambda rig, seat: not working)
    monkeypatch.setattr(
        sup,
        "say",
        lambda rig, seat, text, raw=False: sent.append(
            text if not raw else "/compact RAW"
        ),
    )
    sup.step("r", state, quiet=180)
    return sent


def test_a_seat_under_the_limit_is_left_alone(monkeypatch, tmp_path):
    assert run_step(monkeypatch, seat_log(tmp_path, 150_000, 999), {}) == []


def test_a_seat_past_the_limit_still_working_is_told_once_and_not_compacted(
    monkeypatch, tmp_path
):
    state = {}
    path = seat_log(tmp_path, 250_000, 5)
    first = run_step(monkeypatch, path, state)
    assert len(first) == 1 and "Context limit reached" in first[0]
    assert "rig send r-lead@r /compact" in first[0]
    assert run_step(monkeypatch, path, state) == []


def test_a_quiet_seat_past_the_limit_is_compacted_after_the_notice(
    monkeypatch, tmp_path
):
    sent = run_step(monkeypatch, seat_log(tmp_path, 250_000, 600), {})
    assert [t[:5] for t in sent] == ["Conte", "/comp"]


def test_a_seat_that_dropped_below_the_limit_is_told_again_next_time(
    monkeypatch, tmp_path
):
    state = {}
    run_step(monkeypatch, seat_log(tmp_path, 250_000, 5), state)
    run_step(monkeypatch, seat_log(tmp_path, 40_000, 5), state)
    assert state["lead"]["told"] is False


def test_a_seat_at_the_hard_limit_is_compacted_without_waiting_for_quiet(
    monkeypatch, tmp_path
):
    sent = run_step(monkeypatch, seat_log(tmp_path, 420_000, 5), {})
    assert [t[:5] for t in sent] == ["Conte", "/comp"]


def test_a_working_seat_is_never_sent_compact_even_at_the_hard_limit(
    monkeypatch, tmp_path
):
    sent = run_step(monkeypatch, seat_log(tmp_path, 420_000, 600), {}, working=True)
    assert [t[:5] for t in sent] == ["Conte"]
