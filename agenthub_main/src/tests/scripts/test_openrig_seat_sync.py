"""Tests for scripts/openrig_seat_sync.py.

These exercise the client against a local HTTP server serving canned resolved
seats and rigspecs, so no real 4genthub server or `rig` binary is needed.
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

RIG_YAML = (
    "name: room1\n"
    "pods:\n"
    "  - id: main\n"
    "    members:\n"
    "      - id: seat1\n"
    "        agent_ref: local:agents/seat1\n"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("openrig_seat_sync", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


seat_sync = _load_module()


class _SeatHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.gets.append(self.path)
        route = self.server.routes.get(self.path.partition("?")[0])
        if route is None:
            self.send_error(404)
            return
        status, body = route
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_PUT(self):
        length = int(self.headers.get("Content-Length", "0"))
        self.server.puts.append(
            (
                self.path,
                json.loads(self.rfile.read(length)),
                self.headers.get("Authorization"),
            )
        )
        route = self.server.routes.get(("PUT", self.path))
        if route is None:
            self.send_error(404)
            return
        status, body = route
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):  # keep test output clean
        pass


class SeatServer:
    def __init__(self):
        self.routes = {}
        self.httpd = HTTPServer(("127.0.0.1", 0), _SeatHandler)
        self.httpd.routes = self.routes
        self.puts = []
        self.httpd.puts = self.puts
        self.gets = []
        self.httpd.gets = self.gets
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    @property
    def url(self):
        return f"http://127.0.0.1:{self.httpd.server_port}"

    def set_seat(
        self,
        hash_value,
        files=None,
        policy=None,
        status=200,
        room="room1",
        seat="seat1",
    ):
        path = f"/api/v2/openrig/seats/{room}/{seat}"
        if status == 200:
            body = {
                "success": True,
                "resolved_seat": {
                    "room": room,
                    "seat": seat,
                    "hash": hash_value,
                    "runtime": "claude",
                    "files": FILES if files is None else files,
                    "policy": POLICY if policy is None else policy,
                },
            }
        else:
            body = {"success": False, "error": "boom"}
        self.routes[path] = (status, body)

    def set_rigspec(
        self,
        yaml_text=None,
        seats=None,
        status=200,
        room="room1",
        error="room has no active seats",
    ):
        path = f"/api/v2/openrig/rooms/{room}/rigspec"
        if status == 200:
            body = {
                "success": True,
                "rigspec": {
                    "name": room,
                    "yaml": RIG_YAML if yaml_text is None else yaml_text,
                    "seats": (
                        [{"seat": "seat1", "hash": HASH_A}] if seats is None else seats
                    ),
                },
            }
        else:
            body = {"success": False, "error": error}
        self.routes[path] = (status, body)

    def set_occupants(self, seats, room="room1"):
        self.routes[f"/api/v2/openrig/rooms/{room}/seats"] = (
            200,
            {"success": True, "seats": seats},
        )

    def set_put(self, status=200, room="room1", seat="seat1"):
        path = f"/api/v2/openrig/rooms/{room}/seats/{seat}/occupant"
        body = (
            {"success": True, "seat": {}}
            if status == 200
            else {"success": False, "error": "no"}
        )
        self.routes[("PUT", path)] = (status, body)

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


@pytest.mark.parametrize("bad_name", ["../etc", "_x", "", "a/b", "room.1", "room name"])
def test_unsafe_room_name_rejected(env, tmp_path, capsys, bad_name):
    code = run_cli(["pull", bad_name, "seat1", "--out", str(tmp_path)])
    out, err = capsys.readouterr()

    assert code == 2
    assert out == ""
    assert "invalid room name" in err


def test_unsafe_seat_name_rejected(env, tmp_path, capsys):
    code = run_cli(["pull", "room1", "seat.1", "--out", str(tmp_path)])
    _, err = capsys.readouterr()

    assert code == 2
    assert "invalid seat name" in err


def test_uppercase_room_and_seat_names_accepted(env, tmp_path, capsys):
    env.set_seat(HASH_A, room="Room1", seat="Seat1")

    code = run_cli(["pull", "Room1", "Seat1", "--out", str(tmp_path)])
    out, err = capsys.readouterr()

    seat_dir = tmp_path / "Room1" / "Seat1"
    assert code == 0
    assert out.strip().splitlines() == [f"path:{seat_dir / HASH_A}"]
    assert err == ""
    assert (seat_dir / HASH_A / "docs" / "readme.md").read_text() == "hello"


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


def test_rig_writes_yaml_verbatim_and_links_every_seat(env, tmp_path, capsys):
    yaml_text = (
        "name: room1\n"
        "pods:\n"
        "  - id: main\n"
        "    members:\n"
        "      - id: coder\n"
        "        agent_ref: local:agents/coder\n"
        "      - id: checker\n"
        "        agent_ref: local:agents/checker\n"
    )
    env.set_rigspec(
        yaml_text,
        [{"seat": "coder", "hash": HASH_A}, {"seat": "checker", "hash": HASH_B}],
    )
    env.set_seat(HASH_A, room="room1", seat="coder")
    env.set_seat(HASH_B, room="room1", seat="checker")

    code = run_cli(["rig", "room1", "--out", str(tmp_path)])
    out, err = capsys.readouterr()

    rig_dir = tmp_path / "room1" / "rig"
    assert code == 0
    assert out.strip().splitlines() == [f"rig:{rig_dir / 'rig.yaml'}"]
    assert err == ""
    # The server's YAML is written verbatim, byte for byte.
    assert (rig_dir / "rig.yaml").read_text() == yaml_text

    coder = rig_dir / "agents" / "coder"
    checker = rig_dir / "agents" / "checker"
    assert coder.is_symlink()
    assert checker.is_symlink()
    assert coder.resolve() == (tmp_path / "room1" / "coder" / HASH_A).resolve()
    assert checker.resolve() == (tmp_path / "room1" / "checker" / HASH_B).resolve()
    assert (
        json.loads((tmp_path / "room1" / "coder" / "pinned.json").read_text())["hash"]
        == HASH_A
    )


def test_rig_accepts_uppercase_names(env, tmp_path, capsys):
    env.set_seat(HASH_A, room="Room1", seat="Coder")
    env.set_rigspec(RIG_YAML, [{"seat": "Coder", "hash": HASH_A}], room="Room1")

    code = run_cli(["rig", "Room1", "--out", str(tmp_path)])
    out, err = capsys.readouterr()

    rig_dir = tmp_path / "Room1" / "rig"
    assert code == 0
    assert out.strip().splitlines() == [f"rig:{rig_dir / 'rig.yaml'}"]
    assert err == ""
    assert (rig_dir / "agents" / "Coder").resolve() == (
        tmp_path / "Room1" / "Coder" / HASH_A
    ).resolve()


def test_rig_second_run_keeps_pin_and_prints_notice(env, tmp_path, capsys):
    env.set_rigspec(RIG_YAML, [{"seat": "seat1", "hash": HASH_A}])
    env.set_seat(HASH_A)
    assert run_cli(["rig", "room1", "--out", str(tmp_path)]) == 0
    capsys.readouterr()

    shifted_yaml = RIG_YAML + "# shifted\n"
    env.set_rigspec(shifted_yaml, [{"seat": "seat1", "hash": HASH_B}])
    env.set_seat(HASH_B, files=[{"path": "docs/readme.md", "content": "newer"}])
    code = run_cli(["rig", "room1", "--out", str(tmp_path)])
    out, err = capsys.readouterr()

    seat_dir = tmp_path / "room1" / "seat1"
    rig_dir = tmp_path / "room1" / "rig"
    assert code == 0
    assert out.strip().splitlines() == [f"rig:{rig_dir / 'rig.yaml'}"]
    assert f"newer snapshot available: {HASH_B} (run with --update to adopt)" in err
    assert json.loads((seat_dir / "pinned.json").read_text())["hash"] == HASH_A
    # The link still points at the pinned directory, not the newer one.
    link = rig_dir / "agents" / "seat1"
    assert link.is_symlink()
    assert link.resolve() == (seat_dir / HASH_A).resolve()
    assert not (seat_dir / HASH_B).exists()
    # rig.yaml always comes from the current server response.
    assert (rig_dir / "rig.yaml").read_text() == shifted_yaml


def test_rig_update_moves_pin_and_link(env, tmp_path, capsys):
    env.set_rigspec(RIG_YAML, [{"seat": "seat1", "hash": HASH_A}])
    env.set_seat(HASH_A)
    assert run_cli(["rig", "room1", "--out", str(tmp_path)]) == 0
    capsys.readouterr()

    env.set_rigspec(RIG_YAML, [{"seat": "seat1", "hash": HASH_B}])
    env.set_seat(HASH_B, files=[{"path": "docs/readme.md", "content": "newer"}])
    code = run_cli(["rig", "room1", "--out", str(tmp_path), "--update"])
    out, err = capsys.readouterr()

    seat_dir = tmp_path / "room1" / "seat1"
    rig_dir = tmp_path / "room1" / "rig"
    assert code == 0
    assert err == ""
    assert json.loads((seat_dir / "pinned.json").read_text())["hash"] == HASH_B
    assert (rig_dir / "agents" / "seat1").resolve() == (seat_dir / HASH_B).resolve()
    assert out.strip().splitlines() == [f"rig:{rig_dir / 'rig.yaml'}"]


def test_rig_missing_pinned_dir_exits_1(env, tmp_path, capsys):
    seat_dir = tmp_path / "room1" / "seat1"
    seat_dir.mkdir(parents=True)
    (seat_dir / "pinned.json").write_text(
        json.dumps({"hash": HASH_A, "path": str(seat_dir / HASH_A)})
    )
    env.set_rigspec(RIG_YAML, [{"seat": "seat1", "hash": HASH_B}])
    env.set_seat(HASH_B)

    code = run_cli(["rig", "room1", "--out", str(tmp_path)])
    out, err = capsys.readouterr()

    assert code == 1
    assert out == ""
    assert "seat seat1 could not be pulled" in err
    assert "pinned seat directory is missing" in err
    assert not (tmp_path / "room1" / "rig").exists()


def test_rig_empty_room_409_exits_1_with_server_message(env, tmp_path, capsys):
    env.set_rigspec(status=409, error="room has no active seats")

    code = run_cli(["rig", "room1", "--out", str(tmp_path)])
    out, err = capsys.readouterr()

    assert code == 1
    assert out == ""
    assert "HTTP 409" in err
    assert "room has no active seats" in err
    assert not (tmp_path / "room1" / "rig").exists()


@pytest.mark.parametrize("bad_name", ["../etc", "_x", "", "a/b", "room.1", "room name"])
def test_rig_unsafe_room_name_rejected(env, tmp_path, capsys, bad_name):
    env.set_rigspec()

    code = run_cli(["rig", bad_name, "--out", str(tmp_path)])
    out, err = capsys.readouterr()

    assert code == 2
    assert out == ""
    assert "invalid room name" in err


def test_rig_unsafe_seat_name_rejected(env, tmp_path, capsys):
    env.set_rigspec(RIG_YAML, [{"seat": "seat.1", "hash": HASH_A}])

    code = run_cli(["rig", "room1", "--out", str(tmp_path)])
    out, err = capsys.readouterr()

    assert code == 2
    assert out == ""
    assert "invalid seat name" in err
    assert not (tmp_path / "room1" / "rig").exists()


def test_rig_failed_seat_pull_leaves_previous_rig_untouched(env, tmp_path, capsys):
    env.set_rigspec(RIG_YAML, [{"seat": "seat1", "hash": HASH_A}])
    env.set_seat(HASH_A)
    assert run_cli(["rig", "room1", "--out", str(tmp_path)]) == 0
    capsys.readouterr()

    rig_dir = tmp_path / "room1" / "rig"
    old_yaml = (rig_dir / "rig.yaml").read_text()

    env.set_rigspec(RIG_YAML + "# changed\n", [{"seat": "seat1", "hash": HASH_B}])
    env.set_seat(HASH_B, status=500)
    code = run_cli(["rig", "room1", "--out", str(tmp_path)])
    out, err = capsys.readouterr()

    assert code == 1
    assert out == ""
    assert "seat seat1 could not be pulled" in err
    # The previous rig directory was not touched or partially overwritten.
    assert (rig_dir / "rig.yaml").read_text() == old_yaml
    assert (rig_dir / "agents" / "seat1").resolve() == (
        tmp_path / "room1" / "seat1" / HASH_A
    ).resolve()
    leftovers = [
        p.name for p in (tmp_path / "room1").iterdir() if p.name.startswith(".rig.")
    ]
    assert leftovers == []


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


# --- switch -----------------------------------------------------------------

PS_NODES = [
    {
        "rigName": "room1",
        "logicalId": "main.other",
        "canonicalSessionName": "other-1@room1",
    },
    {
        "rigName": "room1",
        "logicalId": "main.seat1",
        "canonicalSessionName": "seat1-2@room1",
    },
]


class FakeRig:
    """Stands in for subprocess.run; records every rig command in order."""

    def __init__(self, nodes=None, missing=False):
        self.nodes = PS_NODES if nodes is None else nodes
        self.missing = missing
        self.calls = []

    def __call__(self, command, **kwargs):
        self.calls.append(list(command))
        if self.missing:
            raise FileNotFoundError("rig")
        stdout = json.dumps(self.nodes) if command[1] == "ps" else ""
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

    def seat_calls(self):
        return [c for c in self.calls if c[1] == "seat"]


@pytest.fixture
def rig(monkeypatch):
    fake = FakeRig()
    monkeypatch.setattr(seat_sync.subprocess, "run", fake)
    return fake


def occupant(runtime="claude-code", model="old-model"):
    return {"seat_key": "seat1", "runtime": runtime, "model": model}


def setup_switch(env, **kwargs):
    env.set_occupants([occupant(**kwargs)])
    env.set_put()


def test_switch_model_puts_body_keeps_runtime_and_sets_model(env, rig, capsys):
    setup_switch(env)

    code = run_cli(
        ["switch", "room1", "seat1", "--model", "new-model", "--reason", "why"]
    )
    out, err = capsys.readouterr()

    assert code == 0
    assert env.puts == [
        (
            "/api/v2/openrig/rooms/room1/seats/seat1/occupant",
            {"runtime": "claude-code", "model": "new-model"},
            "Bearer test-token",
        )
    ]
    assert rig.seat_calls() == [
        [
            "rig",
            "seat",
            "set-model",
            "seat1-2@room1",
            "--model",
            "new-model",
            "--reason",
            "why",
        ]
    ]
    assert (
        out.strip()
        == "switched:room1/seat1 runtime=claude-code model=new-model applied=set-model"
    )
    assert "test-token" not in out + err


def test_switch_runtime_only_keeps_current_model_and_prints_manual_steps(
    env, rig, capsys
):
    setup_switch(env)

    code = run_cli(["switch", "room1", "seat1", "--runtime", "codex"])
    out, err = capsys.readouterr()

    assert code == 0
    assert env.puts[0][1] == {"runtime": "codex", "model": "old-model"}
    assert rig.calls == []
    assert "rig down room1" in err
    assert (
        out.strip()
        == "switched:room1/seat1 runtime=codex model=old-model applied=manual"
    )


def test_switch_explicit_apply_none_with_runtime_change_skips_manual(env, rig, capsys):
    setup_switch(env)

    code = run_cli(
        ["switch", "room1", "seat1", "--runtime", "codex", "--apply", "none"]
    )
    out, err = capsys.readouterr()

    assert code == 0
    assert rig.calls == []
    assert err == ""
    assert out.strip().endswith("applied=none")


def test_switch_restart_stops_then_launches_fresh_with_warning(env, rig, capsys):
    setup_switch(env)

    code = run_cli(
        [
            "switch",
            "room1",
            "seat1",
            "--model",
            "new-model",
            "--apply",
            "restart",
            "--reason",
            "r",
        ]
    )
    out, err = capsys.readouterr()

    assert code == 0
    assert [c[2] for c in rig.seat_calls()] == ["set-model", "stop", "launch"]
    assert rig.seat_calls()[1] == [
        "rig",
        "seat",
        "stop",
        "seat1-2@room1",
        "--reason",
        "r",
    ]
    assert rig.seat_calls()[2] == [
        "rig",
        "seat",
        "launch",
        "seat1-2@room1",
        "--fresh",
        "--reason",
        "r",
    ]
    assert "warning" in err and "loses its live context" in err
    assert out.strip().endswith("applied=restart")


def test_switch_runtime_change_prints_manual_steps_and_skips_rig(env, rig, capsys):
    setup_switch(env)

    code = run_cli(["switch", "room1", "seat1", "--runtime", "codex", "--model", "m2"])
    out, err = capsys.readouterr()

    assert code == 0
    assert rig.calls == []
    assert "openrig_seat_sync.py rig room1 --update" in err
    assert "rig down room1" in err
    assert "rig up" in err
    assert out.strip() == "switched:room1/seat1 runtime=codex model=m2 applied=manual"


def test_switch_apply_none_never_calls_rig(env, rig, capsys):
    setup_switch(env)

    code = run_cli(
        ["switch", "room1", "seat1", "--model", "new-model", "--apply", "none"]
    )
    out, _ = capsys.readouterr()

    assert code == 0
    assert rig.calls == []
    assert out.strip().endswith("applied=none")


def test_switch_missing_rig_binary_records_cloud_and_exits_0(env, monkeypatch, capsys):
    setup_switch(env)
    monkeypatch.setattr(seat_sync.subprocess, "run", FakeRig(missing=True))

    code = run_cli(["switch", "room1", "seat1", "--model", "new-model"])
    out, err = capsys.readouterr()

    assert code == 0
    assert len(env.puts) == 1
    assert "`rig` not found" in err
    assert out.strip().endswith("applied=none")


def test_switch_seat_not_in_rig_ps_exits_0(env, monkeypatch, capsys):
    setup_switch(env)
    fake = FakeRig(nodes=[])
    monkeypatch.setattr(seat_sync.subprocess, "run", fake)

    code = run_cli(["switch", "room1", "seat1", "--model", "new-model"])
    out, err = capsys.readouterr()

    assert code == 0
    assert "not in `rig ps`" in err
    assert fake.seat_calls() == []
    assert out.strip().endswith("applied=none")


def test_switch_rig_command_failure_exits_1(env, monkeypatch, capsys):
    setup_switch(env)

    def failing(command, **kwargs):
        if command[1] == "seat":
            raise subprocess.CalledProcessError(3, command)
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(PS_NODES))

    monkeypatch.setattr(seat_sync.subprocess, "run", failing)

    code = run_cli(["switch", "room1", "seat1", "--model", "new-model"])
    out, err = capsys.readouterr()

    assert code == 1
    assert out == ""
    assert "exit code 3" in err


@pytest.mark.parametrize("status", [404, 409])
def test_switch_put_error_exits_1(env, rig, capsys, status):
    env.set_occupants([occupant()])
    env.set_put(status=status)

    code = run_cli(["switch", "room1", "seat1", "--model", "new-model"])
    out, err = capsys.readouterr()

    assert code == 1
    assert out == ""
    assert f"HTTP {status}" in err
    assert rig.calls == []
    assert "test-token" not in err


def test_switch_unknown_seat_in_cloud_exits_1(env, rig, capsys):
    env.set_occupants([])

    code = run_cli(["switch", "room1", "seat1", "--model", "new-model"])
    _, err = capsys.readouterr()

    assert code == 1
    assert "not found in the cloud" in err
    assert env.puts == []


@pytest.mark.parametrize(
    "argv, message",
    [
        (["switch", "room1", "seat1"], "at least one of"),
        (["switch", "room1", "seat1", "--runtime", "gpt"], "invalid runtime"),
        (["switch", "room1", "seat1", "--model=-bad"], "invalid model"),
        (["switch", "room1", "seat1", "--model", ""], "invalid model"),
        (["switch", "../x", "seat1", "--model", "m"], "invalid room name"),
        (["switch", "room1", "se.at", "--model", "m"], "invalid seat name"),
    ],
)
def test_switch_usage_errors_exit_2(env, rig, capsys, argv, message):
    code = run_cli(argv)
    out, err = capsys.readouterr()

    assert code == 2
    assert out == ""
    assert message in err
    assert env.puts == [] and rig.calls == []


def test_switch_invalid_apply_choice_exits_2(env, rig, capsys):
    code = run_cli(["switch", "room1", "seat1", "--model", "m", "--apply", "bogus"])

    assert code == 2


# --- rig --permission-policy --------------------------------------------------

RIGSPEC_PATH = "/api/v2/openrig/rooms/room1/rigspec"


def test_rig_permission_policy_adds_query(env, tmp_path):
    env.set_rigspec()
    env.set_seat(HASH_A)

    code = run_cli(
        ["rig", "room1", "--out", str(tmp_path), "--permission-policy", "yolo"]
    )

    assert code == 0
    assert f"{RIGSPEC_PATH}?permission_policy=yolo" in env.gets


def test_rig_without_permission_policy_requests_plain_path(env, tmp_path):
    env.set_rigspec()
    env.set_seat(HASH_A)

    code = run_cli(["rig", "room1", "--out", str(tmp_path)])

    assert code == 0
    assert RIGSPEC_PATH in env.gets
    assert not any("permission_policy" in g for g in env.gets)


def test_rig_invalid_permission_policy_exits_2(env, tmp_path, capsys):
    code = run_cli(
        ["rig", "room1", "--out", str(tmp_path), "--permission-policy", "bogus"]
    )
    _, err = capsys.readouterr()

    assert code == 2
    assert "invalid choice" in err
    assert env.gets == []
