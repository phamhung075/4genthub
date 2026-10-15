"""The room definition must name the roster the rig runs.

`team.json` rebuilds the room, and a room definition is not the roster - but it must name the
roster. `team.json` kept declaring `go-dev2` after that seat was removed on 2026-10-08, and never
declared the `architect` running beside it, so a first `apply` of that stale definition would have
built a team that does not exist. The cases here are what stop the definition drifting from the rig
again.

The roster below is MEASURED, not copied from any file: `rig ps --json` gives `nodeCount` 10 for this
rig, and the names and runtimes come from its exported spec.

THE COMPARISON AGAINST `SEAT_ROLES` IS REPLACED, NOT DROPPED. That table lived in the client
package's Python `seat_policy.py`, which the client repository deleted in `1eca7de`, and the case
that opened it failed with `FileNotFoundError` on every run in this tree. What it was really about
was never that table: it was the AGREEMENT between the two writes for one team - `team.json` rebuilds
the room, the policy writer emits an omp `config.yml` for every seat the room declares on omp, and
nothing else compared them, which is how `team.json` kept declaring `go-dev2` after the rig stopped
running it. The repo-side half of that agreement is asserted here, against the measured split; the
half that drives the writer itself (`4genteam policy show SEAT --rig RIG --team FILE`) waits for the
pin bump and is owed to task `fe6ebedc`, not to this file.
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
TEAM_JSON = REPO_ROOT / "scripts" / "team" / "4genthub-min" / "team.json"

# The team the rig is RUNNING. RE-MEASURED 2026-10-15: ALL FIVE SEATS RUN `omp` - the owner replaced
# the architect seat on 2026-10-14 20:21Z, and the room's `spec.json`, `4genteam ps --nodes --json` and
# the cloud now all report `omp` for every seat - and the room's `team.json` declares exactly those
# five, so the two writes agree at five. The 2026-10-11 reading this comment used to carry (one
# `claude-code` architect and four `omp`) was true when taken and is exactly what the definition
# drifted from: the file went on saying `claude-code`/`opus` for two more days, and the case that
# asserted that runtime string from memory is DELETED rather than re-pointed - asserting a runtime
# string is how it drifted, and the pair of set comparisons below already carries its intent.
LIVE_SEATS = [
    "architect",
    "fe-dev",
    "go-dev",
    "lead",
    "reviewer",
]

# WHICH of those seats run omp, measured the same way and on the same day as `LIVE_SEATS` above: all
# five, since 2026-10-15. Recorded rather than recomputed for the reason the pair exists - a set
# derived from `team.json` agrees with `team.json` by construction, and this pair exists because the
# room and the rig disagreed for two days.
OMP_SEATS = [
    "architect",
    "fe-dev",
    "go-dev",
    "lead",
    "reviewer",
]


def team() -> dict:
    return json.loads(TEAM_JSON.read_text())


def test_the_declared_seats_are_the_live_roster():
    declared = sorted(seat["seat_key"] for seat in team()["seats"])
    assert declared == sorted(LIVE_SEATS)


def test_the_rooms_omp_seats_are_the_rigs_omp_seats():
    """The room's omp seats and the rig's omp seats are the SAME SET, in both directions.

    `LIVE_SEATS` says WHICH seats exist; this says WHICH RUNTIME each one runs, which is the half the
    two writes disagree about. `team.json` rebuilds the room, and the policy writer emits an omp
    `config.yml` for every seat the room declares on omp - so a seat moved onto omp in the room while
    the rig still runs it on claude-code, or the reverse, is a room describing a team nobody runs.
    `go-dev2` is what that looks like after the fact: declared in the room, with no seat behind it.

    Both sides are named when this fails, because the reader has to know WHICH file moved: the seats
    the room declares on omp that the rig does not run there, and the omp seats the room leaves off
    omp. The comparison is against the measured `OMP_SEATS`, never against the file under test.

    THIS CASE ALSO CARRIES WHAT `test_the_architect_runs_claude_code` USED TO SAY, and it says it
    better: that case asserted ONE seat's runtime string from memory, and a hard-coded string is
    exactly what drifted - the definition went on declaring `claude-code`/`opus` for two days after
    the owner had moved that seat to `omp`. The property the room needs is the one asserted here (the
    definition names no seat whose declared runtime disagrees with the roster the rig runs, in either
    direction), so the old case is DELETED rather than re-pointed to the new string.
    """
    declared = {seat["seat_key"]: seat["runtime"] for seat in team()["seats"]}
    room_omp = {key for key, runtime in declared.items() if runtime == "omp"}
    rig_omp = set(OMP_SEATS)
    assert room_omp == rig_omp, (
        f"the room declares {sorted(room_omp - rig_omp)} on omp but the rig does not run them "
        f"there, and the rig runs {sorted(rig_omp - room_omp)} on omp but the room does not declare "
        f"them that way"
    )
    # AND THE SPLIT IS A SPLIT OF THE LIVE ROSTER, not of a list that merely happens to agree: every
    # omp seat is a seat that exists, and the seats declared on something else are exactly the roster
    # minus the omp half. Without this second pair, a runtime string nobody runs - a typo, or a third
    # runtime added to one file alone - leaves both sets looking right while the room describes a
    # seat that launches nowhere.
    assert rig_omp <= set(LIVE_SEATS), (
        f"{sorted(rig_omp - set(LIVE_SEATS))} are recorded as omp seats but are not on the roster"
    )
    off_omp = {key for key, runtime in declared.items() if runtime != "omp"}
    assert off_omp == set(LIVE_SEATS) - rig_omp, (
        f"the room declares {sorted(off_omp)} off omp; the roster says the off-omp half is "
        f"{sorted(set(LIVE_SEATS) - rig_omp)}"
    )


def test_every_overlay_key_is_a_declared_seat_and_every_module_file_exists():
    doc = team()
    declared = {seat["seat_key"] for seat in doc["seats"]}
    assert set(doc["seat_overlays"]) <= declared
    for module in doc["modules"]:
        assert (TEAM_JSON.parent / module["file"]).is_file(), module["slug"]
