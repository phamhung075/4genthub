"""Tests for scripts/openrig_team_setup.py.

The script runs against a local HTTP server that records every request, so no
real 4genthub server is needed.
"""

import importlib.util
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

# These tests are self-contained and must not spin up the test database.
pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = REPO_ROOT / "scripts" / "openrig_team_setup.py"
TEAM_DIR = REPO_ROOT / "scripts" / "team" / "4genthub"

TOKEN = "tok-secret-1234567890"
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
    "delegate-deepseek": (100, 180),
    "area-go-backend": (120, 250),
    "area-web-frontend": (100, 200),
    "area-quality": (100, 200),
    "area-docs": (80, 150),
    "mission-4genthub": (350, 520),
}
MODULE_FILES = {"mission-4genthub": "mission.md"}


def _load_module():
    spec = importlib.util.spec_from_file_location("openrig_team_setup", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


team_setup = _load_module()


class _Handler(BaseHTTPRequestHandler):
    def _handle(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"null")
        server = self.server
        server.requests.append(
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

    def log_message(self, *args):
        pass


class TeamServer:
    def __init__(self):
        self.requests = []
        self.overrides = {}  # (method, path) -> (status, text)
        self.httpd = HTTPServer(("127.0.0.1", 0), _Handler)
        self.httpd.requests = self.requests
        self.httpd.respond = self.respond
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    @property
    def url(self):
        return f"http://127.0.0.1:{self.httpd.server_port}"

    def respond(self, method, path, body):
        if (method, path) in self.overrides:
            return self.overrides[(method, path)]
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
    code = team_setup.main(["apply", *extra])
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
        {"kind": "add", "slug": "delegate-deepseek", "version": "1.0.0", "content": ""},
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


def test_project_brief_starts_with_the_safety_rule():
    text = (TEAM_DIR / "project-4genthub.txt").read_text(encoding="utf-8")
    assert text.startswith("SAFETY.")
    assert "Never git push" in text.split("\n")[0]
