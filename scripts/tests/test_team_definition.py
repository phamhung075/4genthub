"""The shipped team definition (`scripts/team/4genthub`) and skill inventory, applied through the client.

The client is a separate repository with no knowledge of this one, so what is checked HERE is this
repository's data: the team files, their word limits and the skill inventory. The client's own
logic is tested in its repository. A local HTTP server records every request, so no real server is
needed.
"""




import importlib.util


import json


import os




import threading


from http.server import BaseHTTPRequestHandler, HTTPServer


from pathlib import Path


import pytest


# These tests are self-contained and must not spin up the test database.
pytestmark = pytest.mark.unit


REPO_ROOT = Path(__file__).resolve().parents[2]


TEAM_DIR = REPO_ROOT / "scripts" / "team" / "4genthub"
INVENTORY = REPO_ROOT / "ai_docs" / "agent-system" / "skill-library.json"


TOKEN = "tok-secret-1234567890"


SEAT_TYPES_PATH = "/api/v2/openrig/seat-types"


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


WORD_LIMITS = {
    "project-4genthub": (350, 500),
    "delegate-deepseek": (100, 230),
    "area-go-backend": (120, 250),
    "area-web-frontend": (100, 200),
    "area-quality": (100, 200),
    "area-docs": (80, 150),
    "mission-4genthub": (350, 520),
}


MODULE_FILES = {"mission-4genthub": "mission.md"}


def _load_module():
    return importlib.import_module("agenthub_client.team_setup")


team_setup = _load_module()


class _Handler(BaseHTTPRequestHandler):
    def _handle(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"null")
        server = self.server
        # apply's read of the stored seat types is counted apart, so the write-sequence
        # assertions below stay about writes
        record = (
            server.seat_type_reads
            if (self.command, self.path) == ("GET", SEAT_TYPES_PATH)
            else server.requests
        )
        record.append(
            {
                "method": self.command,
                "path": self.path,
                "body": body,
                "auth": self.headers.get("Authorization"),
            }
        )
        status, text = server.respond(self.command, self.path, body)
        payload = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    do_PUT = _handle
    do_POST = _handle
    do_GET = _handle

    def log_message(self, *args):
        pass


class TeamServer:
    def __init__(self):
        self.requests = []
        self.seat_type_reads = []
        self.overrides = {}  # (method, path) -> (status, text)
        self.httpd = HTTPServer(("127.0.0.1", 0), _Handler)
        self.httpd.requests = self.requests
        self.httpd.seat_type_reads = self.seat_type_reads
        self.httpd.respond = self.respond
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    @property
    def url(self):
        return f"http://127.0.0.1:{self.httpd.server_port}"

    def respond(self, method, path, body):
        if (method, path) in self.overrides:
            return self.overrides[(method, path)]
        if (method, path) == ("GET", SEAT_TYPES_PATH):
            return 200, '{"seat_types": []}'  # nothing stored: the seed runs
        if method == "GET":
            return 404, '{"detail": "not found"}'
        return (201 if method == "POST" else 200), '{"success": true}'

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=5)


@pytest.fixture
def server():
    team_server = TeamServer()
    yield team_server
    team_server.close()


@pytest.fixture
def env(server, monkeypatch):
    monkeypatch.setenv("AGENTHUB_URL", server.url)
    monkeypatch.setenv("AGENTHUB_TOKEN", TOKEN)


def _run(capsys, *extra):
    code = team_setup.main(["apply", "--team", str(TEAM_DIR), *extra])
    out = capsys.readouterr()
    return code, out.out, out.err


def _context_file(slug):
    return TEAM_DIR / MODULE_FILES.get(slug, f"{slug}.txt")


def _team():
    return team_setup.load_team(TEAM_DIR)


def test_calls_follow_the_documented_order(server, env, capsys):
    code, out, _ = _run(capsys)
    assert code == 0
    kinds = []
    for req in server.requests:
        path = req["path"]
        if path.endswith("/seat-types/seed"):
            kind = "seed"
        elif "/modules/" in path:
            kind = "module"
        elif path.endswith("/rooms"):
            kind = "room"
        elif path.endswith("/links"):
            kind = "link"
        elif path.endswith("/overlay") and "/seats/" not in path:
            kind = "company-overlay"
        elif path.endswith("/overlay"):
            kind = "seat-overlay"
        else:
            kind = "seat"
        if not kinds or kinds[-1] != kind:
            kinds.append(kind)
    assert kinds == [
        "seed",
        "module",
        "room",
        "seat",
        "link",
        "company-overlay",
        "seat-overlay",
    ]
    assert len(out.strip().splitlines()) == len(server.requests)
    assert all(r["auth"] == f"Bearer {TOKEN}" for r in server.requests)


def test_module_content_comes_from_the_files(server, env, capsys):
    assert _run(capsys)[0] == 0
    puts = {
        r["path"].split("/")[5]: r["body"]
        for r in server.requests
        if "/modules/" in r["path"]
    }
    assert set(puts) == set(WORD_LIMITS)
    for slug, body in puts.items():
        assert body["kind"] == "instruction"
        assert body["content"] == _context_file(slug).read_text(encoding="utf-8")


def test_overlays_send_full_op_lists(server, env, capsys):
    assert _run(capsys)[0] == 0
    overlays = {
        r["path"]: r["body"] for r in server.requests if r["path"].endswith("/overlay")
    }
    company = overlays["/api/v2/openrig/overlay"]
    assert company["ops"] == [
        {"kind": "add", "slug": "project-4genthub", "version": "1.0.0", "content": ""},
        {"kind": "add", "slug": "delegate-deepseek", "version": "1.1.0", "content": ""},
    ]
    room = "/api/v2/openrig/rooms/4genthub-dev/seats"

    def slugs(seat):
        return [o["slug"] for o in overlays[f"{room}/{seat}/overlay"]["ops"]]

    assert slugs("go-dev") == ["area-go-backend"]
    assert slugs("web-dev") == ["area-web-frontend"]
    assert slugs("planner") == [
        "area-go-backend",
        "area-web-frontend",
        "mission-4genthub",
    ]
    assert slugs("architect") == ["area-go-backend", "area-web-frontend"]
    for seat in ("tester", "reviewer", "debugger"):
        assert slugs(seat) == ["area-quality"]
    assert slugs("writer") == ["area-docs"]
    assert slugs("lead") == ["mission-4genthub"]
    mission_seats = {
        seat
        for seat in team_setup.load_team(TEAM_DIR)["seat_overlays"]
        if "mission-4genthub" in slugs(seat)
    }
    assert mission_seats == {"lead", "planner"}


def test_links_match_the_team_topology(server, env, capsys):
    assert _run(capsys)[0] == 0
    prefix = "/api/v2/openrig/rooms/4genthub-dev/seats/"
    links = {
        (
            r["path"][len(prefix) :].split("/")[0],
            r["body"]["kind"],
            r["body"]["to_seat"],
        )
        for r in server.requests
        if r["path"].endswith("/links")
    }
    others = {
        "planner",
        "architect",
        "go-dev",
        "web-dev",
        "reviewer",
        "tester",
        "debugger",
        "writer",
    }
    expected = {("lead", "delegates_to", s) for s in others}
    expected |= {(s, "escalates_to", "lead") for s in others}
    expected |= {
        (d, "collaborates_with", t)
        for d in ("go-dev", "web-dev")
        for t in ("reviewer", "tester")
    }
    expected.add(("reviewer", "collaborates_with", "tester"))
    assert links == expected
    assert all(
        r["body"]["allow"] is True
        for r in server.requests
        if r["path"].endswith("/links")
    )


def test_rerun_tolerates_existing_room_and_seats(server, env, capsys):
    server.overrides[("POST", "/api/v2/openrig/rooms")] = (
        409,
        '{"detail":"room already exists"}',
    )
    for seat in _team()["seats"]:
        path = "/api/v2/openrig/rooms/4genthub-dev/seats"
        server.overrides[("POST", path)] = (409, '{"detail":"seat already exists"}')
    code, out, _ = _run(capsys)
    assert code == 0
    assert "room 4genthub-dev: exists" in out
    assert "seat lead: exists" in out
    assert "link lead delegates_to planner: applied" in out
    assert len(server.requests) == len(team_setup.build_plan(_team()))


def test_409_on_a_module_is_an_error(server, env, capsys):
    path = "/api/v2/openrig/modules/project-4genthub/versions/1.0.0"
    server.overrides[("PUT", path)] = (
        409,
        '{"detail":"already exists with different content"}',
    )
    code, _, err = _run(capsys)
    assert code == 1
    assert "project-4genthub" in err
    assert len(server.requests) == 2  # the seed, then the failing module


def test_seed_failure_stops_before_any_other_call(server, env, capsys):
    server.overrides[("POST", "/api/v2/openrig/seat-types/seed")] = (
        500,
        '{"detail":"AGENTHUB_PUBLIC_URL is not set"}',
    )
    code, _, err = _run(capsys)
    assert code == 1
    assert "seat types (seed)" in err and "AGENTHUB_PUBLIC_URL" in err
    assert len(server.requests) == 1


def test_the_seed_is_skipped_when_every_needed_seat_type_is_stored(server, env, capsys):
    stored = [{"slug": slug} for slug in SEAT_TYPES]
    server.overrides[("GET", SEAT_TYPES_PATH)] = (
        200,
        json.dumps({"seat_types": stored}),
    )
    code, out, _ = _run(capsys)
    assert code == 0
    assert not any(r["path"].endswith("/seat-types/seed") for r in server.requests)
    assert "seat types (seed)" not in out
    assert len(server.requests) == len(team_setup.build_plan(_team(), SEAT_TYPES))


def test_the_seed_runs_when_a_needed_seat_type_is_missing(server, env, capsys):
    stored = [{"slug": slug} for slug in SEAT_TYPES - {"writer"}]
    server.overrides[("GET", SEAT_TYPES_PATH)] = (
        200,
        json.dumps({"seat_types": stored}),
    )
    code, out, _ = _run(capsys)
    assert code == 0
    assert server.requests[0]["path"] == "/api/v2/openrig/seat-types/seed"


def test_an_empty_company_overlay_sends_no_company_overlay(server, env, capsys):
    team = _team()
    team[
        "company_overlay"
    ] = []  # the company overlay is account-wide: a PUT would replace it
    labels = [step[0] for step in team_setup.build_plan(team, SEAT_TYPES)]
    assert "overlay company" not in labels
    assert any(label.startswith("overlay seat ") for label in labels)


def test_an_unreadable_seat_type_list_stops_before_any_write(server, env, capsys):
    server.overrides[("GET", SEAT_TYPES_PATH)] = (500, '{"detail":"boom"}')
    code, _, err = _run(capsys)
    assert code == 1
    assert "GET /api/v2/openrig/seat-types failed: HTTP 500" in err
    assert server.requests == []


def test_409_without_already_exists_is_an_error(server, env, capsys):
    server.overrides[("POST", "/api/v2/openrig/rooms")] = (409, '{"detail":"conflict"}')
    code, _, _ = _run(capsys)
    assert code == 1


def test_other_4xx_stops_the_run(server, env, capsys):
    server.overrides[("POST", "/api/v2/openrig/rooms")] = (422, '{"detail":"bad slug"}')
    code, _, err = _run(capsys)
    assert code == 1
    assert "422" in err
    assert server.requests[-1]["path"] == "/api/v2/openrig/rooms"


def test_dry_run_makes_no_requests_and_needs_no_env(server, monkeypatch, capsys):
    monkeypatch.delenv("AGENTHUB_URL", raising=False)
    monkeypatch.delenv("AGENTHUB_TOKEN", raising=False)
    code, out, _ = _run(capsys, "--dry-run")
    assert code == 0
    assert server.requests == []
    assert len(out.strip().splitlines()) == len(team_setup.build_plan(_team()))


def test_token_is_never_printed(server, env, capsys):
    server.overrides[("POST", "/api/v2/openrig/rooms")] = (500, "boom")
    _, fail_out, fail_err = _run(capsys)
    assert TOKEN not in fail_out + fail_err
    server.overrides.clear()
    ok_code, ok_out, ok_err = _run(capsys)
    assert ok_code == 0
    assert TOKEN not in ok_out + ok_err
    _, dry_out, dry_err = _run(capsys, "--dry-run")
    assert TOKEN not in dry_out + dry_err


def test_missing_config_is_a_usage_error(monkeypatch, capsys):
    monkeypatch.delenv("AGENTHUB_URL", raising=False)
    monkeypatch.setenv("AGENTHUB_TOKEN", TOKEN)
    code, _, err = _run(capsys)
    assert code == 2
    assert "AGENTHUB_URL" in err


def test_unreachable_server_is_exit_1(monkeypatch, capsys):
    monkeypatch.setenv("AGENTHUB_URL", "http://127.0.0.1:1")
    monkeypatch.setenv("AGENTHUB_TOKEN", TOKEN)
    code, _, err = _run(capsys)
    assert code == 1
    assert TOKEN not in err


def test_every_overlay_module_is_created_by_the_script():
    team = _team()
    created = {m["slug"] for m in team["modules"]}
    referenced = set(team["company_overlay"])
    for slugs in team["seat_overlays"].values():
        referenced.update(slugs)
    assert referenced <= created
    assert created <= referenced, "a module no overlay uses is dead weight"
    seat_keys = {s["seat_key"] for s in team["seats"]}
    assert set(team["seat_overlays"]) <= seat_keys
    for link in team["links"]:
        assert {link["from"], link["to"]} <= seat_keys


def test_seat_types_are_among_the_nine():
    for seat in _team()["seats"]:
        assert seat["seat_type"] in SEAT_TYPES
        assert seat["runtime"] == "claude-code"


@pytest.mark.parametrize("slug", sorted(WORD_LIMITS))
def test_context_files_respect_word_limits(slug):
    low, high = WORD_LIMITS[slug]
    words = len(_context_file(slug).read_text(encoding="utf-8").split())
    assert low <= words <= high, f"{slug}: {words} words, expected {low}-{high}"


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


# OPENRIG_SKILLS_ROOT is set nowhere committed, so the root is DERIVED when it is absent: the
# checkout beside this repository. A guard whose default state is skip reports on its own baseline -
# it would have stayed quiet on the stale digest this file was written for - so the derived root is
# used whenever it can satisfy the inventory, and the skip is kept for a path that is not there.
OPENRIG_CHECKOUT_DEFAULT = REPO_ROOT.parent / "openrig"


# The two committed skill edges the inventory's recorded paths live under: all 35 canonical rows
# under the first, all 19 plugin rows under the second. Both must be present, or a half-cloned tree
# would be digested as if it were a checkout and fail on a path rather than report itself absent.
OPENRIG_SKILL_EDGES = (
    Path("skills") / "_canonical",
    Path("packages") / "daemon" / "assets" / "plugins" / "openrig-core" / "skills",
)


def _openrig_root_or_skip() -> Path:
    """The real OpenRig checkout, or a skip that says so LOUDLY.

    A skip that reads as a pass is the same silence this guard exists to end, one level down, so
    the reason names the variable, the value it holds and what to set instead.

    The configured root wins when it is a usable checkout; otherwise the derived root is tried, so
    an ordinary checkout runs these cases with no environment set at all. Every candidate that was
    unusable is named in the skip, so the reason a reader sees is the path that was actually tried.
    """
    configured = os.environ.get(team_setup.LIBRARY_ROOT_ENV)
    candidates = [Path(configured)] if configured else []
    candidates.append(OPENRIG_CHECKOUT_DEFAULT)
    unusable = []
    for candidate in candidates:
        absent = [edge for edge in OPENRIG_SKILL_EDGES if not (candidate / edge).is_dir()]
        if not absent:
            return candidate
        unusable.append(f"{candidate} has no {', '.join(str(edge) for edge in absent)}")
    state = (
        f"{team_setup.LIBRARY_ROOT_ENV}={configured!r}"
        if configured
        else f"{team_setup.LIBRARY_ROOT_ENV} is not set"
    )
    pytest.skip(
        f"SKIPPED, NOT PASSED ({state}): the inventory's digests can only be verified against a real "
        f"OpenRig checkout, and none of these is one - {'; '.join(unusable)}. Set "
        f"{team_setup.LIBRARY_ROOT_ENV}=/path/to/openrig - the variable publish-skills "
        "--source-root and drift-check --library-root already read - to run it."
    )


def _inventory_guard(inventory_path: Path, source_root: Path) -> list:
    """The check itself: the publish path's own verifier, fed the inventory it publishes from."""
    return team_setup.skill_library_modules(
        team_setup.load_skill_inventory(inventory_path), source_root
    )


def test_the_shipped_inventory_digests_match_the_committed_openrig_checkout():
    """Every recorded digest still describes the file at its committed path."""
    source_root = _openrig_root_or_skip()
    inventory_path = INVENTORY

    modules = _inventory_guard(inventory_path, source_root)

    inventory = team_setup.load_skill_inventory(inventory_path)
    assert inventory["count"] == len(inventory["skills"]), "the count disagrees with the rows"
    assert len(modules) == inventory["count"], "one block per skill, so a short list is a lost skill"
    sides = sum(1 for entry in inventory["skills"] for edge in ("canonical", "plugin") if edge in entry)
    assert sides == 54, (
        f"{sides} recorded sides: 52 skills with 2 mirrored pairs is what this inventory documents. "
        "Every recorded side must be read, so confirm the new count deliberately before changing it."
    )


def test_the_inventory_guard_names_the_skill_and_both_digests(tmp_path):
    """A perturbed digest must fail, naming WHICH side moved - the case that must not be vacuous.

    Hermetic: it perturbs a COPY of the inventory under tmp_path and leaves the shipped file alone,
    so the guard is seen to fail without the shared tree being touched.
    """
    source_root = _openrig_root_or_skip()
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    row = next(entry for entry in inventory["skills"] if "canonical" in entry)
    recomputed = row["canonical"]["sha256"]
    row["canonical"]["sha256"] = "0" * 64
    perturbed = tmp_path / "skill-library.json"
    perturbed.write_text(json.dumps(inventory), encoding="utf-8")

    with pytest.raises(team_setup.SetupError) as refused:
        _inventory_guard(perturbed, source_root)

    message = str(refused.value)
    assert row["name"] in message, "the failing skill must be named"
    assert "0" * 64 in message, "the RECORDED digest must be named"
    assert recomputed in message, (
        "the RECOMPUTED digest must be named too, or the reader cannot tell which side moved"
    )


def test_the_inventory_guard_reads_the_mirror_too(tmp_path):
    """The same red, one side further out: the MIRROR's file is read and digested as well.

    A mirrored skill records two digests. Verifying only the source leaves the mirror free to rot:
    its digest was recorded, never checked, so a stale mirror stayed green. This case is the one
    that goes red the moment the module stops reading the mirror's file.
    """
    source_root = _openrig_root_or_skip()
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    row = next(
        entry for entry in inventory["skills"] if "canonical" in entry and "plugin" in entry
    )
    recomputed = row["plugin"]["sha256"]
    row["plugin"]["sha256"] = "0" * 64
    perturbed = tmp_path / "skill-library.json"
    perturbed.write_text(json.dumps(inventory), encoding="utf-8")

    with pytest.raises(team_setup.SetupError) as refused:
        _inventory_guard(perturbed, source_root)

    message = str(refused.value)
    assert row["name"] in message, "the failing skill must be named"
    assert "0" * 64 in message, "the RECORDED mirror digest must be named"
    assert recomputed in message, "the RECOMPUTED mirror digest must be named too"


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
    inventory = team_setup.load_skill_inventory(INVENTORY)

    gaps = _curation_gaps(inventory)

    assert not gaps, "the curation does not account for the inventory:\n  " + "\n  ".join(gaps)
