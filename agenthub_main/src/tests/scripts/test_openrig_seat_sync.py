"""Tests for scripts/openrig_seat_sync.py.

These exercise the client against a local HTTP server serving a canned resolved
seat, so no real 4genthub server or `rig` binary is needed.
"""

import importlib.util
import json
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

# These tests are self-contained and must not spin up the test database.
pytestmark = pytest.mark.unit

MODULE_PATH = Path(__file__).resolve().parents[4] / "scripts" / "openrig_seat_sync.py"

HASH_A = "a1" * 32
HASH_B = "b2" * 32
HASH_LONG = "c3d4e5f6" + "0" * 56

FILES = [
    {"path": "docs/readme.md", "content": "hello"},
    {"path": "nested/deeper/notes.txt", "content": "notes"},
]
POLICY = {"max_turns": 5, "runtime": "claude"}


def _load_module():
    spec = importlib.util.spec_from_file_location("openrig_seat_sync", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


seat_sync = _load_module()


class _SeatHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        canned = self.server.canned
        if self.path != canned["path"]:
            self.send_error(404)
            return
        status = canned.get("status", 200)
        if status != 200:
            body = b'{"error":"boom"}'
            self.send_response(status)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        payload = json.dumps(canned["body"]).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):  # keep test output clean
        pass


class SeatServer:
    def __init__(self):
        self.canned = {"path": "/api/v2/openrig/seats/room1/seat1", "status": 200}
        self.httpd = HTTPServer(("127.0.0.1", 0), _SeatHandler)
        self.httpd.canned = self.canned
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    @property
    def url(self):
        return f"http://127.0.0.1:{self.httpd.server_port}"

    def set_seat(self, hash_value, files=None, policy=None, status=200):
        self.canned["path"] = "/api/v2/openrig/seats/room1/seat1"
        self.canned["status"] = status
        self.canned["body"] = {
            "success": True,
            "resolved_seat": {
                "room": "room1",
                "seat": "seat1",
                "hash": hash_value,
                "runtime": "claude",
                "files": FILES if files is None else files,
                "policy": POLICY if policy is None else policy,
            },
        }

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=5)


@pytest.fixture
def server():
    seat_server = SeatServer()
    yield seat_server
    seat_server.close()


@pytest.fixture
def env(monkeypatch, server):
    monkeypatch.setenv("AGENTHUB_URL", server.url)
    monkeypatch.setenv("AGENTHUB_TOKEN", "test-token")
    return server


def run_cli(argv):
    try:
        return seat_sync.main(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1


def test_pull_writes_files_and_creates_lock(env, tmp_path, capsys):
    env.set_seat(HASH_A)

    code = run_cli(["pull", "room1", "seat1", "--out", str(tmp_path)])
    out, err = capsys.readouterr()

    seat_dir = tmp_path / "room1" / "seat1"
    assert code == 0
    assert out.strip().splitlines() == [f"path:{seat_dir / HASH_A}"]
    assert err == ""

    assert (seat_dir / HASH_A / "docs" / "readme.md").read_text() == "hello"
    assert (
        seat_dir / HASH_A / "nested" / "deeper" / "notes.txt"
    ).read_text() == "notes"

    lock = json.loads((seat_dir / "pinned.json").read_text())
    assert lock == {"hash": HASH_A, "path": str(seat_dir / HASH_A)}
    assert json.loads((seat_dir / "policy.json").read_text()) == POLICY


def test_second_pull_keeps_lock_and_prints_notice(env, tmp_path, capsys):
    env.set_seat(HASH_A)
    assert run_cli(["pull", "room1", "seat1", "--out", str(tmp_path)]) == 0
    capsys.readouterr()

    env.set_seat(HASH_B, files=[{"path": "docs/readme.md", "content": "newer"}])
    code = run_cli(["pull", "room1", "seat1", "--out", str(tmp_path)])
    out, err = capsys.readouterr()

    seat_dir = tmp_path / "room1" / "seat1"
    assert code == 0
    assert out.strip().splitlines() == [f"path:{seat_dir / HASH_A}"]
    assert f"newer snapshot available: {HASH_B} (run with --update to adopt)" in err
    assert json.loads((seat_dir / "pinned.json").read_text())["hash"] == HASH_A
    assert not (seat_dir / HASH_B).exists()
    assert (seat_dir / HASH_A / "docs" / "readme.md").read_text() == "hello"


def test_update_moves_lock_and_materializes_new_hash(env, tmp_path, capsys):
    env.set_seat(HASH_A)
    assert run_cli(["pull", "room1", "seat1", "--out", str(tmp_path)]) == 0
    capsys.readouterr()

    env.set_seat(HASH_B, files=[{"path": "docs/readme.md", "content": "newer"}])
    code = run_cli(["pull", "room1", "seat1", "--out", str(tmp_path), "--update"])
    out, err = capsys.readouterr()

    seat_dir = tmp_path / "room1" / "seat1"
    assert code == 0
    assert out.strip().splitlines() == [f"path:{seat_dir / HASH_B}"]
    assert err == ""
    assert json.loads((seat_dir / "pinned.json").read_text())["hash"] == HASH_B
    assert (seat_dir / HASH_B / "docs" / "readme.md").read_text() == "newer"
    # The previous pinned snapshot is immutable and survives.
    assert (seat_dir / HASH_A / "docs" / "readme.md").read_text() == "hello"


@pytest.mark.parametrize(
    "bad_path",
    ["../evil.txt", "/etc/passwd", "a\\b.txt", "a//b.txt", "", "./x.txt", ".."],
)
def test_unsafe_file_path_rejected(env, tmp_path, capsys, bad_path):
    env.set_seat(HASH_A, files=[{"path": bad_path, "content": "x"}])

    code = run_cli(["pull", "room1", "seat1", "--out", str(tmp_path)])
    out, err = capsys.readouterr()

    assert code == 2
    assert out == ""
    assert "unsafe file path" in err
    assert not (tmp_path / "evil.txt").exists()


@pytest.mark.parametrize("bad_name", ["../etc", "Room", "_x", "", "a/b"])
def test_unsafe_room_name_rejected(env, tmp_path, capsys, bad_name):
    code = run_cli(["pull", bad_name, "seat1", "--out", str(tmp_path)])
    out, err = capsys.readouterr()

    assert code == 2
    assert out == ""
    assert "invalid room name" in err


def test_unsafe_seat_name_rejected(env, tmp_path, capsys):
    code = run_cli(["pull", "room1", "Seat", "--out", str(tmp_path)])
    _, err = capsys.readouterr()

    assert code == 2
    assert "invalid seat name" in err


def test_missing_pinned_dir_fails_loudly(env, tmp_path, capsys):
    seat_dir = tmp_path / "room1" / "seat1"
    seat_dir.mkdir(parents=True)
    (seat_dir / "pinned.json").write_text(
        json.dumps({"hash": HASH_A, "path": str(seat_dir / HASH_A)})
    )
    env.set_seat(HASH_B)

    code = run_cli(["pull", "room1", "seat1", "--out", str(tmp_path)])
    out, err = capsys.readouterr()

    assert code == 2
    assert out == ""
    assert "pinned seat directory is missing" in err
    assert HASH_A in err
    # No silent fallback to the fetched snapshot.
    assert not (seat_dir / HASH_B).exists()
    assert json.loads((seat_dir / "pinned.json").read_text())["hash"] == HASH_A


def test_http_error_exits_1(env, tmp_path, capsys):
    env.set_seat(HASH_A, status=500)

    code = run_cli(["pull", "room1", "seat1", "--out", str(tmp_path)])
    out, err = capsys.readouterr()

    assert code == 1
    assert out == ""
    assert "HTTP 500" in err


def test_invalid_json_exits_1(monkeypatch, tmp_path, capsys):
    class _BadHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = b"not json"
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    httpd = HTTPServer(("127.0.0.1", 0), _BadHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        monkeypatch.setenv("AGENTHUB_URL", f"http://127.0.0.1:{httpd.server_port}")
        monkeypatch.setenv("AGENTHUB_TOKEN", "test-token")
        code = run_cli(["pull", "room1", "seat1", "--out", str(tmp_path)])
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)

    out, err = capsys.readouterr()
    assert code == 1
    assert out == ""
    assert "invalid JSON" in err


def test_bundle_without_lock_exits_2(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(seat_sync, "DEFAULT_OUT", tmp_path / "seats")

    code = run_cli(
        [
            "bundle",
            "room1",
            "seat1",
            "--rig-yaml",
            str(tmp_path / "rig.yaml"),
            "--rig-root",
            str(tmp_path),
            "--out-dir",
            str(tmp_path / "bundles"),
        ]
    )
    out, err = capsys.readouterr()

    assert code == 2
    assert out == ""
    assert "no pinned snapshot" in err


def test_bundle_uses_pinned_hash_and_argument_list(monkeypatch, tmp_path, capsys):
    seats = tmp_path / "seats"
    seat_dir = seats / "room1" / "seat1"
    seat_dir.mkdir(parents=True)
    (seat_dir / "pinned.json").write_text(
        json.dumps({"hash": HASH_LONG, "path": str(seat_dir / HASH_LONG)})
    )
    monkeypatch.setattr(seat_sync, "DEFAULT_OUT", seats)

    calls = []

    def fake_run(command, **kwargs):
        calls.append((list(command), dict(kwargs)))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(seat_sync.subprocess, "run", fake_run)

    rig_yaml = tmp_path / "rig.yaml"
    rig_root = tmp_path / "rig-root"
    out_dir = tmp_path / "bundles"
    code = run_cli(
        [
            "bundle",
            "room1",
            "seat1",
            "--rig-yaml",
            str(rig_yaml),
            "--rig-root",
            str(rig_root),
            "--out-dir",
            str(out_dir),
        ]
    )
    out, err = capsys.readouterr()

    bundle_path = out_dir / f"room1-seat1-{HASH_LONG[:8]}.rigbundle"
    assert code == 0
    assert err == ""
    assert out.strip() == str(bundle_path)
    assert calls == [
        (
            [
                "rig",
                "bundle",
                "create",
                str(rig_yaml),
                "--rig-root",
                str(rig_root),
                "-o",
                str(bundle_path),
                "--name",
                "room1-seat1",
                "--bundle-version",
                "1.0.0",
                "--notes",
                f"resolved_sha256={HASH_LONG} source=4genthub",
            ],
            {"check": True},
        )
    ]


def test_help_states_offline_use_is_manual(capsys):
    code = run_cli(["--help"])
    out, _ = capsys.readouterr()

    assert code == 0
    assert "rig up <bundle> --target <dir>" in out
    assert "never falls back" in out
