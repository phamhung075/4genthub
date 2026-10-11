"""What THIS repository ships, checked without the retired Python client.

The apply-and-plan cases this file used to hold drove `agenthub_client.team_setup`, the client's
Python planner, which the client repository deleted in `1eca7de`. Their live home is that
repository's Go `internal/clientteam` (`plan.go`, `publish.go`, `team.go`, `drift.go`, with
`apply_test.go`, `publish_test.go` and `drift_test.go`), and the pin-archive loader that briefly
kept them collectable went with them: a test whose only way to run is an archive of deleted code
covers nothing in this repository.

What is left is this repository's own data - the rooms under `scripts/team`, the word bands their
instruction files are held to, and the skill inventory's curation - checked against files that live
HERE. The eight data cases the split keeps are the whole file: seven about the rooms, one about the
curation, and none of them reads the client or any other tree.

WHAT LEFT THIS FILE, so it is not quietly missing: the case that digested each recorded `sha256`
against the OpenRig revision the inventory's `generated_from` names. The rule it checked is
implemented by the live Go `team publish-skills` verb, so the case belongs where that verb is,
driven through it, rather than as a second copy of the rule in Python. It is port row 25 in
DISPOSITION-retired-python-client-tests-2026-10-10.md, and until that port lands this repository has
no check that the committed inventory describes the revision it names.
"""


import json
import subprocess


from pathlib import Path


import pytest


# These tests are self-contained and must not spin up the test database.
pytestmark = pytest.mark.unit


REPO_ROOT = Path(__file__).resolve().parents[2]


TEAM_ROOT = REPO_ROOT / "scripts" / "team"


# The dev room: whose module text the wording cases at the bottom of this file read directly.
TEAM_DIR = TEAM_ROOT / "4genthub"


def _tracked_rooms():
    """The rooms THIS REPOSITORY ships: the ones whose `team.json` is in the index.

    Read with git rather than by walking the directory, and the difference is the point:
    `scripts/team` is where a room definition is written before it is committed, so an untracked
    directory there is somebody's work in progress rather than part of the release. A stray
    directory must be able to make this suite neither red nor green - which is why `4genthub-ab`,
    untracked in this tree and a live rig besides, is an owner row (`f465d5df`) instead of a red
    guard here.
    """
    listed = subprocess.run(
        ["git", "ls-files", "--", "scripts/team/*/team.json"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    ).stdout.split()
    return sorted(Path(p).parts[2] for p in listed)


# Every room shipped under scripts/team, discovered rather than listed. This file used to hard-code
# the single directory above as the only room, so a room added beside it - which is how
# 4genthub-client arrived - was gated by nothing at all.
ROOMS = _tracked_rooms()
INVENTORY = REPO_ROOT / "ai_docs" / "agent-system" / "skill-library.json"


SEAT_TYPES = {
    "lead",
    "planner",
    "architect",
    "developer",
    "reviewer",
    "tester",
    "debugger",
    "researcher",
    "writer",
}


# Every instruction file a room keeps in its OWN directory gets a word band: the file is pasted
# into a seat's context, so the band is how "this stays short" is written down and how a truncated
# file is caught. A room-local instruction file with no band FAILS the guard rather than passing
# unnoticed, and a band no file uses is stale. A file a room points at outside its own directory
# (the Go seed library's blocks) only has to resolve here; its content is the Go seed's to check.
#
# HOW THE NUMBERS ARE SET, because four of these bands were once within five words of their
# ceiling - at two, three, four and five words - and a bound that close catches nothing: the file
# cannot grow and cannot be truncated: the ceiling is a round number above the file's own length
# with room for about two sentences of honest editing, and the floor is the truncation check rather
# than a style bound.
# Both ends bite, which is the point: a band states the room a file is allowed, not what it happens
# to weigh today.
#
# THE MIN ROOM'S TABLE IS EMPTY ON PURPOSE rather than unfilled: every instruction module it names
# lives in the Go seed library, whose content the seed owns, so it has no room-local file to band
# and an empty table is the honest form there. An empty table copied as a convention would be
# copying an absence.
ROOM_WORD_LIMITS = {
    "4genthub": {
        "project-4genthub": (350, 500),
        "delegate-deepseek": (100, 230),
        "area-go-backend": (120, 250),
        "area-web-frontend": (100, 200),
        "area-quality": (100, 240),
        "area-docs": (80, 190),
        "mission-4genthub": (350, 560),
    },
    "4genthub-ab": {"ab-terse": (25, 60), "ab-verify": (30, 70)},
    "4genthub-client": {"client-go-mission": (350, 560)},
    "4genthub-min": {},  # every instruction module it names lives in the Go seed library
}


# Which runtimes a room's seats are launched on. Written down per room rather than recomputed:
# moving a room onto another runtime is a decision somebody makes, and this is the value the room
# ships. An omp seat must name the model it runs and the seat-type version it pinned (the
# min-room convention the newer rooms follow); a claude-code seat names neither.
ROOM_RUNTIMES = {
    "4genthub": {"claude-code"},
    "4genthub-ab": {"omp"},
    "4genthub-client": {"omp"},
    "4genthub-min": {"claude-code", "omp"},
}


def _definition(room):
    """A room's team.json as written, with nothing read on its behalf.

    Read as JSON rather than through any loader, and the difference matters to the case that HAS to
    fail: the guard wants to name the module and its path rather than report that a room could not
    be loaded at all.
    """
    return json.loads((TEAM_ROOT / room / "team.json").read_text(encoding="utf-8"))


def _team():
    """The dev room's own definition, as written."""
    return _definition("4genthub")


# --- the definition guard: every room under scripts/team, not just the one above ---------------
def test_the_per_room_tables_cover_every_shipped_room():
    # One direction only: a room that EXISTS must have an expectation, so it cannot arrive ungated.
    # The reverse would tie this file to how many rooms a given checkout happens to have (a room
    # can sit in a working tree before it is committed), and an entry for an absent room costs
    # nothing. Both directions are still enforced by the cases below, per room.
    assert set(ROOMS) <= set(ROOM_RUNTIMES), (
        f"a room with no runtime expectation would be ungated: {sorted(set(ROOMS) - set(ROOM_RUNTIMES))}"
    )
    assert set(ROOMS) <= set(ROOM_WORD_LIMITS), (
        f"a room with no band table would be ungated: {sorted(set(ROOMS) - set(ROOM_WORD_LIMITS))}"
    )


@pytest.mark.parametrize("room", ROOMS)
def test_every_room_names_files_that_resolve(room):
    room_dir = (TEAM_ROOT / room).resolve()
    for module in _definition(room)["modules"]:
        path = TEAM_ROOT / room / module["file"]
        assert path.is_file(), f"{room}/{module['slug']}: {module['file']} does not resolve"
        text = path.read_text(encoding="utf-8")
        assert text.strip(), f"{room}/{module['slug']}: {module['file']} is empty"
        if module["kind"] == "policy":
            assert isinstance(json.loads(text), dict), (
                f"{room}/{module['slug']}: a policy module is one JSON object"
            )
            # A POLICY IS THE ROOM'S OWN RULES, so it lives in the room that declares it. A `..`
            # out of the directory makes the room depend on a sibling's file and break silently
            # the moment that sibling renames or edits one - the defect b4ca5c68 fixed for
            # 4genthub-client. Instruction modules may point at the Go seed library's blocks, which
            # is why the bound is on the policy kind rather than on every module.
            assert room_dir in path.resolve().parents, (
                f"{room}/{module['slug']}: its policy resolves to {path.resolve()}, outside "
                f"{room_dir} - a room's policies live in the room that declares them"
            )


@pytest.mark.parametrize("room", ROOMS)
def test_every_room_defines_what_its_overlays_use_and_covers_its_seats(room):
    team = _definition(room)
    created = {m["slug"] for m in team["modules"]}
    referenced = set(team["company_overlay"])
    for slugs in team["seat_overlays"].values():
        referenced.update(slugs)
    assert referenced <= created, "an overlay references a module the room does not define"
    assert created <= referenced, "a module no overlay uses is dead weight"
    seat_keys = {s["seat_key"] for s in team["seats"]}
    assert set(team["seat_overlays"]) == seat_keys, (
        "a seat with no overlay would start with no context at all"
    )
    for link in team["links"]:
        assert {link["from"], link["to"]} <= seat_keys


@pytest.mark.parametrize("room", ROOMS)
def test_every_room_seat_is_a_known_type_on_the_declared_runtimes(room):
    runtimes = set()
    for seat in _definition(room)["seats"]:
        assert seat["seat_type"] in SEAT_TYPES
        runtimes.add(seat["runtime"])
        if seat["runtime"] == "omp":
            assert seat["model"], f"{room}/{seat['seat_key']}: an omp seat names its model"
            assert seat.get("pinned_version"), (
                f"{room}/{seat['seat_key']}: an omp seat pins the seat-type version it runs"
            )
    expected = ROOM_RUNTIMES.get(room, set())
    assert runtimes == expected, (
        f"{room} ships {sorted(runtimes)}, the expectation says {sorted(expected)}"
    )


@pytest.mark.parametrize("room", ROOMS)
def test_every_room_local_context_file_has_a_band_it_respects(room):
    room_dir = (TEAM_ROOT / room).resolve()
    local = {}
    for module in _definition(room)["modules"]:
        path = (room_dir / module["file"]).resolve()
        if module["kind"] == "instruction" and room_dir in path.parents:
            local[module["slug"]] = path
    bands = ROOM_WORD_LIMITS.get(room, {})
    assert set(local) == set(bands), (
        f"{room}: the bands and the room's own instruction files disagree - a file with no band "
        f"would pass unnoticed, and a band with no file is stale"
    )
    for slug, path in sorted(local.items()):
        low, high = bands[slug]
        words = len(path.read_text(encoding="utf-8").split())
        assert low <= words <= high, f"{room}/{slug}: {words} words, expected {low}-{high}"


def test_delegate_module_carries_the_chef_and_worker_wording():
    text = (TEAM_DIR / "delegate-deepseek.txt").read_text(encoding="utf-8")
    assert "Each seat's session is the chef" in text
    assert "accountable for the result" in text
    assert "never forwarded unreviewed" in text
    versions = {m["slug"]: m["version"] for m in _team()["modules"]}
    assert versions["delegate-deepseek"] == "1.1.0"


def test_project_brief_starts_with_the_safety_rule():
    text = (TEAM_DIR / "project-4genthub.txt").read_text(encoding="utf-8")
    assert text.startswith("SAFETY.")
    assert "Never git push" in text.split("\n")[0]


# --- the skill inventory's curation, checked where it can always run ----------------------------
#
# WHAT IS NOT HERE, so it is not quietly missing: the case that materialised the revision
# `generated_from` names and digested each recorded `sha256` against it. That rule is the live Go
# `team publish-skills` verb's, so the case is port row 25 in
# DISPOSITION-retired-python-client-tests-2026-10-10.md and belongs on that verb, driven through it,
# rather than re-implemented here. The curation case below is a different invariant, and it needs no
# checkout at all: it reads only the inventory.


def _curation_gaps(inventory: dict) -> list:
    """Every way the curation fails to account for the skills, as sentences. Empty means none.

    The inventory is hand-maintained, so a row added without a home and a name typed into
    ``unused_by_default`` are the two edits that are quiet everywhere else. The Go seed test
    checks that curated refs resolve and that each unused name reaches no seed - and a MISSPELLED
    unused name passes that second check by reaching no seed either. This is the check that
    closes it, and the arithmetic that says all 52 are accounted for exactly once.
    """
    names = {row["name"] for row in inventory["skills"]}
    curated = {
        entry["skill"] for entries in inventory["seat_curation"].values() for entry in entries
    }
    unused = set(inventory["unused_by_default"])
    gaps = [f"curated skill {name!r} is not a row" for name in sorted(curated - names)]
    gaps += [f"unused_by_default name {name!r} is not a row" for name in sorted(unused - names)]
    gaps += [
        f"skill {name!r} is neither curated nor unused_by_default" for name in sorted(names - curated - unused)
    ]
    gaps += [f"skill {name!r} is both curated and unused_by_default" for name in sorted(curated & unused)]
    return gaps


def test_the_inventory_curation_accounts_for_every_skill():
    """Every row has exactly one home, and every curated and unused name resolves to a row.

    No checkout is needed - the inventory documents its own curation - so this case runs wherever
    the suite runs, including on a machine that has never cloned OpenRig.
    """
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))

    gaps = _curation_gaps(inventory)

    assert not gaps, "the curation does not account for the inventory:\n  " + "\n  ".join(gaps)
