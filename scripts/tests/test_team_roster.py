"""The room definition and the omp policy table must name the same team the rig runs.

`team.json` rebuilds the room; `SEAT_ROLES` writes the omp policy for the seats in it. Two files,
two writes, one team - and nothing compared them, so `team.json` kept declaring `go-dev2` after that
seat was removed on 2026-10-08, and never declared the `architect` running beside it. The comparison
is the point: it is what stops the two writes drifting apart again. A room definition is not the
roster, but it must name the roster.

The roster below is MEASURED, not copied from either file: `rig ps --json` gives `nodeCount` 10 for
this rig, and the names and runtimes come from its exported spec. A first `apply` of the stale
definition would have built `go-dev2` and never created the architect, so the cloud room would have
described a team that does not exist.
"""

import importlib.util
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
TEAM_JSON = REPO_ROOT / "scripts" / "team" / "4genthub-min" / "team.json"
# `SEAT_ROLES` moved with the client relocation (2026-10-09): it was
# `scripts/openrig_seat_policy.py`, and the file is now part of the installed client package. This
# path is a string, not an import, so nothing but a grep finds it - and this test failed with
# `FileNotFoundError` from the moment the old file was deleted until the path was repointed here.
POLICY_PATH = REPO_ROOT / "agenthub_client" / "src" / "agenthub_client" / "seat_policy.py"
RIG = "4genthub-min"

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


def load_policy():
    spec = importlib.util.spec_from_file_location("seat_policy", POLICY_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def test_the_omp_seats_are_exactly_the_seat_roles_table():
    """The invariant that keeps the two writes together.

    The architect is deliberately absent from `SEAT_ROLES`: the script writes omp `config.yml`
    under the omp state root, an architect has no directory there, and listing it would make
    `apply` exit at the architect.
    """
    omp_seats = {
        seat["seat_key"] for seat in team()["seats"] if seat["runtime"] == "omp"
    }
    assert omp_seats == set(load_policy().SEAT_ROLES[RIG])
