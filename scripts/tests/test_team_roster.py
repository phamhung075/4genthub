"""The room definition must name the roster the rig runs.

`team.json` rebuilds the room, and a room definition is not the roster - but it must name the
roster. `team.json` kept declaring `go-dev2` after that seat was removed on 2026-10-08, and never
declared the `architect` running beside it, so a first `apply` of that stale definition would have
built a team that does not exist. The cases here are what stop the definition drifting from the rig
again.

The roster below is MEASURED, not copied from any file: `rig ps --json` gives `nodeCount` 10 for this
rig, and the names and runtimes come from its exported spec.

THE COMPARISON AGAINST `SEAT_ROLES` IS GONE, and it is not a loss of coverage: that table lived in
the client package's Python `seat_policy.py`, which the client repository deleted in `1eca7de`, and
its live home is that repository's Go policy writer. The case that compared the two files opened the
deleted path directly, so it failed with `FileNotFoundError` on every run in this tree; what it
asserted - the omp seats are exactly the seats the policy writer emits - belongs where the writer
lives, and is covered there.
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
TEAM_JSON = REPO_ROOT / "scripts" / "team" / "4genthub-min" / "team.json"

# The team the rig is RUNNING, measured 2026-10-08. `go-dev2` was removed that day; `architect`
# runs on claude-code and every other seat on omp.
LIVE_SEATS = [
    "architect",
    "context-dev",
    "fe-dev",
    "feedback-dev",
    "go-dev",
    "lead",
    "reviewer",
    "skills-dev",
    "web-dev",
    "writer",
]


def team() -> dict:
    return json.loads(TEAM_JSON.read_text())


def test_the_declared_seats_are_the_live_ten():
    declared = sorted(seat["seat_key"] for seat in team()["seats"])
    assert declared == sorted(LIVE_SEATS)


def test_the_architect_runs_claude_code():
    seats = {seat["seat_key"]: seat for seat in team()["seats"]}
    assert "architect" in seats, "the live rig runs an architect seat"
    assert seats["architect"]["runtime"] == "claude-code"


def test_every_overlay_key_is_a_declared_seat_and_every_module_file_exists():
    doc = team()
    declared = {seat["seat_key"] for seat in doc["seats"]}
    assert set(doc["seat_overlays"]) <= declared
    for module in doc["modules"]:
        assert (TEAM_JSON.parent / module["file"]).is_file(), module["slug"]
