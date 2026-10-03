"""Tests for scripts/openrig_bridge.py using fake tool runners and a local HTTP server."""

import importlib.util
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

MODULE_PATH = Path(__file__).resolve().parents[4] / "scripts" / "openrig_bridge.py"

FAKE_TOKEN = "sk-FAKEFAKEFAKEFAKEFAKE12345678"


def _load_module():
    spec = importlib.util.spec_from_file_location("openrig_bridge", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bridge_mod = _load_module()


def rig_output(*extra_nodes):
    nodes = [
        {
            "rigName": "eng",
            "logicalId": "dev.coder",
            "runtime": "claude-code",
            "sessionStatus": "running",
            "lifecycleState": "running",
            "agentActivity": {"state": "running", "reason": "busy"},
            "cwd": f"/work/{FAKE_TOKEN}",
            "canonicalSessionName": f"dev-coder@eng-{FAKE_TOKEN}",
            "resumeToken": FAKE_TOKEN,
        },
        {
            "rigName": "eng",
            "logicalId": "dev.reviewer",
            "runtime": "weird-runtime",
            "sessionStatus": "running",
            "agentActivity": {"state": "needs_input"},
            "latestError": f"auth failed token={FAKE_TOKEN}",
        },
        *extra_nodes,
    ]
    return json.dumps(nodes)


def herdr_output(*agents):
    agents = agents or (
        {
            "agent": "claude",
            "agent_status": "working",
            "pane_id": "w5:p3",
            "cwd": f"/home/{FAKE_TOKEN}",
            "terminal_title": f"user@host: {FAKE_TOKEN}",
            "terminal_title_stripped": FAKE_TOKEN,
            "agent_session": {"value": FAKE_TOKEN},
        },
    )
    return json.dumps({"result": {"snapshot": {"agents": list(agents)}}})


def fake_runner(rig=None, herdr=None):
    def runner(argv):
        out = rig if argv[0] == "rig" else herdr
        if out is None:
            raise FileNotFoundError(argv[0])
        if isinstance(out, Exception):
            raise out
        return out

    return runner


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def make_bridge(tmp_path, runner, send, **kwargs):
    kwargs.setdefault("secrets", {"AGENTHUB_TOKEN": FAKE_TOKEN})
    return bridge_mod.Bridge(
        "pc-1", 20.0, send, runner=runner, pins_dir=tmp_path, **kwargs
    )


def test_payload_shape_state_and_runtime_mapping(tmp_path):
    bridge = make_bridge(
        tmp_path, fake_runner(rig_output(), herdr_output()), lambda b: 200
    )
    payload = bridge.build_payload()
    assert set(payload) == {"machine_id", "reported_at", "seats", "agents"}
    coder, reviewer = payload["seats"]
    assert (coder["room"], coder["seat"], coder["state"], coder["runtime"]) == (
        "eng",
        "coder",
        "running",
        "claude-code",
    )
    assert (reviewer["seat"], reviewer["state"], reviewer["runtime"]) == (
        "reviewer",
        "blocked",
        "unknown",
    )
    assert payload["agents"] == [
        {"agent": "claude", "status": "working", "pane_id": "w5:p3"}
    ]


@pytest.mark.parametrize(
    "node,expected",
    [
        (
            {"sessionStatus": "stopped", "agentActivity": {"state": "running"}},
            "stopped",
        ),
        ({"lifecycleState": "recoverable"}, "stopped"),
        ({"lifecycleState": "attention_required"}, "blocked"),
        ({"startupStatus": "failed"}, "blocked"),
        ({"agentActivity": {"state": "idle"}}, "idle"),
        ({"agentActivity": {"state": "bogus"}}, "unknown"),
        ({}, "unknown"),
    ],
)
def test_seat_state_mapping(node, expected):
    assert bridge_mod.seat_state(node) == expected


def test_allow_list_never_sends_foreign_fields_or_secrets(tmp_path):
    sent = []
    bridge = make_bridge(
        tmp_path,
        fake_runner(rig_output(), herdr_output()),
        lambda b: sent.append(b) or 200,
    )
    bridge.cycle()
    body = sent[0].decode()
    assert FAKE_TOKEN not in body
    for leaked in (
        "cwd",
        "terminal_title",
        "agent_session",
        "resumeToken",
        "canonicalSessionName",
    ):
        assert leaked not in body
    payload = json.loads(body)
    assert set(payload["seats"][0]) == {
        "room",
        "seat",
        "state",
        "runtime",
        "hash",
        "detail",
        "redacted",
    }
    assert payload["seats"][1]["redacted"] is True
    assert "[REDACTED" in payload["seats"][1]["detail"]


def test_bad_names_are_skipped(tmp_path):
    bad = [
        {"rigName": "bad room", "logicalId": "x"},
        {"rigName": "eng", "logicalId": "../etc"},
        {"rigName": "eng", "logicalId": "dev.coder"},
        {"rigName": "ok", "logicalId": 7},
    ]
    agents = [
        {"agent": "bad name", "agent_status": "idle", "pane_id": "w1:p1"},
        {"agent": "claude", "agent_status": "idle", "pane_id": "../x"},
        {"agent": "codex", "agent_status": "weird", "pane_id": "w1:p2"},
    ]
    bridge = make_bridge(
        tmp_path, fake_runner(json.dumps(bad), herdr_output(*agents)), lambda b: 200
    )
    payload = bridge.build_payload()
    assert [(s["room"], s["seat"]) for s in payload["seats"]] == [("eng", "coder")]
    assert payload["agents"] == [
        {"agent": "codex", "status": "unknown", "pane_id": "w1:p2"}
    ]


def _payload_and_stderr(tmp_path, capsys, nodes):
    bridge = make_bridge(tmp_path, fake_runner(json.dumps(nodes), None), lambda b: 200)
    payload = bridge.build_payload()
    return payload, capsys.readouterr().err


def test_same_member_in_two_pods_of_one_rig_is_a_named_duplicate(tmp_path, capsys):
    nodes = [
        {"rigName": "4genthub-go", "logicalId": "dev.check"},
        {"rigName": "4genthub-go", "logicalId": "agy.check"},
    ]
    payload, err = _payload_and_stderr(tmp_path, capsys, nodes)
    assert [(s["room"], s["seat"]) for s in payload["seats"]] == [
        ("4genthub-go", "check")
    ]
    assert (
        "seat 'check' in rig 4genthub-go exists in pods agy and dev; rename one" in err
    )
    assert "invalid" not in err


def test_invalid_names_have_their_own_message(tmp_path, capsys):
    nodes = [
        {"rigName": "eng", "logicalId": "dev.coder"},
        {"rigName": "bad room", "logicalId": "dev.x"},
        {"rigName": "eng", "logicalId": "dev.../etc"},
    ]
    payload, err = _payload_and_stderr(tmp_path, capsys, nodes)
    assert [(s["room"], s["seat"]) for s in payload["seats"]] == [("eng", "coder")]
    assert "skipped 2 seat(s) with invalid names" in err
    assert "rename one" not in err


def test_duplicate_message_wording():
    msg = bridge_mod.duplicate_message
    assert msg("r", "check", ["dev", "agy", "ops"]) == (
        "seat 'check' in rig r exists in pods agy, dev and ops; rename one"
    )
    assert msg("r", "check", ["dev", "dev"]) == (
        "seat 'check' in rig r is listed twice in pod dev; rename one"
    )


def test_same_member_in_two_rigs_is_not_a_duplicate(tmp_path, capsys):
    nodes = [
        {"rigName": "a", "logicalId": "dev.check"},
        {"rigName": "b", "logicalId": "dev.check"},
    ]
    payload, err = _payload_and_stderr(tmp_path, capsys, nodes)
    assert [(s["room"], s["seat"]) for s in payload["seats"]] == [
        ("a", "check"),
        ("b", "check"),
    ]
    assert "skipped" not in err and "rename one" not in err


def test_pinned_hash_used_when_valid(tmp_path):
    pin = tmp_path / "eng" / "coder"
    pin.mkdir(parents=True)
    (pin / "pinned.json").write_text(json.dumps({"hash": "ab12"}))
    other = tmp_path / "eng" / "reviewer"
    other.mkdir(parents=True)
    (other / "pinned.json").write_text(json.dumps({"hash": "../evil"}))
    bridge = make_bridge(tmp_path, fake_runner(rig_output(), None), lambda b: 200)
    seats = bridge.build_payload()["seats"]
    assert [s["hash"] for s in seats] == ["ab12", ""]


def test_absent_tools_yield_empty_sources_and_log_once(tmp_path, capsys):
    bridge = make_bridge(tmp_path, fake_runner(None, None), lambda b: 200)
    for _ in range(3):
        payload = bridge.build_payload()
    assert payload["seats"] == [] and payload["agents"] == []
    err = capsys.readouterr().err
    assert err.count("rig not installed") == 1
    assert err.count("herdr not installed") == 1


def test_failing_tool_is_absent_not_fatal(tmp_path):
    bridge = make_bridge(
        tmp_path, fake_runner(RuntimeError("exit 1"), "not json"), lambda b: 200
    )
    payload = bridge.build_payload()
    assert payload["seats"] == [] and payload["agents"] == []


def test_send_on_change_and_heartbeat(tmp_path):
    sent = []
    clock = FakeClock()
    runner_state = {"rig": rig_output()}

    def runner(argv):
        return runner_state["rig"] if argv[0] == "rig" else herdr_output()

    bridge = make_bridge(tmp_path, runner, lambda b: sent.append(b) or 200, clock=clock)
    bridge.cycle()
    assert len(sent) == 1
    clock.now += 20
    bridge.cycle()
    assert len(sent) == 1
    runner_state["rig"] = rig_output({"rigName": "eng", "logicalId": "dev.qa"})
    clock.now += 20
    bridge.cycle()
    assert len(sent) == 2
    clock.now += 61
    bridge.cycle()
    assert len(sent) == 3


def test_422_drops_detail_next_cycle_then_recovers(tmp_path):
    statuses = iter([422, 200, 200])
    sent = []

    def send(body):
        sent.append(json.loads(body))
        return next(statuses)

    bridge = make_bridge(tmp_path, fake_runner(rig_output(), herdr_output()), send)
    assert bridge.cycle() == 20.0
    assert bridge.strip_detail is True
    bridge.cycle()
    assert all(s["detail"] == "" and s["redacted"] is True for s in sent[1]["seats"])
    assert bridge.strip_detail is False
    assert sent[0]["seats"][1]["detail"] != ""


def test_backoff_doubles_to_cap_and_resets(tmp_path):
    results = [OSError("down")] * 6 + [200]

    def send(body):
        result = results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    bridge = make_bridge(tmp_path, fake_runner(rig_output(), None), send)
    delays = [bridge.cycle() for _ in range(6)]
    assert delays == [20.0, 40.0, 80.0, 120.0, 120.0, 120.0]
    assert bridge.cycle() == 20.0
    assert bridge.backoff == 0.0


@pytest.mark.parametrize("status", [400, 401, 500])
def test_other_http_errors_back_off_without_crashing(tmp_path, status):
    bridge = make_bridge(tmp_path, fake_runner(rig_output(), None), lambda b: status)
    assert bridge.cycle() == 20.0
    assert bridge.cycle() == 40.0


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        self.server.requests.append(
            (self.path, self.headers.get("Authorization"), self.rfile.read(length))
        )
        time.sleep(self.server.delay)
        self.send_response(self.server.status)
        self.end_headers()

    def log_message(self, *args):
        pass


@pytest.fixture
def server():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    srv.requests, srv.status, srv.delay = [], 200, 0.0
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield srv
    srv.shutdown()
    srv.server_close()


def test_sender_posts_to_status_path_with_bearer(server, tmp_path):
    send = bridge_mod.make_sender(f"http://127.0.0.1:{server.server_port}/", "tok-abc")
    bridge = make_bridge(tmp_path, fake_runner(rig_output(), herdr_output()), send)
    bridge.cycle()
    path, auth, body = server.requests[0]
    assert path == "/api/v2/openrig/seat-status"
    assert auth == "Bearer tok-abc"
    assert FAKE_TOKEN not in body.decode()


def test_sender_reports_422_status_code(server, tmp_path):
    server.status = 422
    send = bridge_mod.make_sender(f"http://127.0.0.1:{server.server_port}", "t")
    bridge = make_bridge(tmp_path, fake_runner(rig_output(), None), send)
    bridge.cycle()
    assert bridge.strip_detail is True


def test_run_once_exit_codes(tmp_path):
    stop = threading.Event()
    ok = make_bridge(tmp_path, fake_runner(rig_output(), None), lambda b: 200)
    assert ok.run(stop, once=True) == bridge_mod.EXIT_OK
    bad = make_bridge(tmp_path, fake_runner(rig_output(), None), lambda b: 500)
    assert bad.run(stop, once=True) == bridge_mod.EXIT_REMOTE


def test_run_stops_on_event(tmp_path):
    stop = threading.Event()

    def send(body):
        stop.set()
        return 200

    bridge = make_bridge(tmp_path, fake_runner(rig_output(), None), send)
    assert bridge.run(stop) == bridge_mod.EXIT_OK


def test_machine_id_sanitized():
    assert bridge_mod.sanitize_machine_id("my host.local") == "my-host-local"
    assert bridge_mod.sanitize_machine_id("..") == "machine"


def test_usage_errors_exit_2(monkeypatch):
    monkeypatch.delenv("AGENTHUB_URL", raising=False)
    monkeypatch.delenv("AGENTHUB_TOKEN", raising=False)
    with pytest.raises(SystemExit) as err:
        bridge_mod.main(["run", "--once"])
    assert err.value.code == 2
    with pytest.raises(SystemExit) as err:
        bridge_mod.main(["run", "--interval", "0"])
    assert err.value.code == 2
    with pytest.raises(SystemExit) as err:
        bridge_mod.main(["once", "--print", "--machine-id", "bad id"])
    assert err.value.code == 2


def test_install_service_prints_unit(capsys):
    assert bridge_mod.main(["install-service"]) == 0
    out = capsys.readouterr().out
    assert "Restart=on-failure" in out
    assert "EnvironmentFile=%h/.config/agenthub-bridge.env" in out
    assert str(MODULE_PATH) in out


class _RecordingStop(threading.Event):
    """Stop event that records every wait the run loop asks for and stops after `limit` waits."""

    def __init__(self, limit):
        super().__init__()
        self.limit, self.waits = limit, []

    def wait(self, timeout=None):
        self.waits.append(timeout)
        if len(self.waits) >= self.limit:
            self.set()
        return self.is_set()


def _run_against(server, tmp_path, monkeypatch, steps):
    """Run the loop over one real HTTP exchange per step; a step is (status, delay_seconds)."""
    monkeypatch.setattr(bridge_mod, "SEND_TIMEOUT", 0.2)
    send = bridge_mod.make_sender(f"http://127.0.0.1:{server.server_port}", FAKE_TOKEN)
    bridge = make_bridge(tmp_path, fake_runner(rig_output(), None), send)
    stop = _RecordingStop(len(steps))
    original = server.RequestHandlerClass.do_POST

    def stepped(handler):
        server.status, server.delay = steps[len(server.requests)]
        original(handler)

    monkeypatch.setattr(server.RequestHandlerClass, "do_POST", stepped)
    bridge.run(stop)
    return bridge, stop.waits


def test_run_loop_backs_off_on_401_500_and_timeout_then_resets(
    server, tmp_path, monkeypatch
):
    steps = [(401, 0.0), (500, 0.0), (200, 0.5), (200, 0.0), (200, 0.0)]
    bridge, waits = _run_against(server, tmp_path, monkeypatch, steps)
    # 401 -> 20, 500 -> 40, timeout (slow 200) -> 80, success resets -> 20; the unchanged
    # payload is not resent, so the last cycle just waits one interval.
    assert waits == [20.0, 40.0, 80.0, 20.0, 20.0]
    assert bridge.backoff == 0.0
    assert all(
        w >= bridge.interval for w in waits
    ), "the loop must never wait less than one interval"
    assert len(server.requests) == 4


def test_run_loop_failures_never_leak_the_token(server, tmp_path, monkeypatch, capsys):
    steps = [(401, 0.0), (500, 0.0), (200, 0.5)]
    _run_against(server, tmp_path, monkeypatch, steps)
    err = capsys.readouterr()
    output = err.out + err.err
    assert "HTTP 401" in output or "HTTP 500" in output
    assert "timed out" in output
    assert FAKE_TOKEN not in output


def test_run_loop_backoff_stops_at_the_cap(tmp_path):
    stop = _RecordingStop(8)
    bridge = make_bridge(tmp_path, fake_runner(rig_output(), None), lambda b: 500)
    bridge.run(stop)
    assert stop.waits == [20.0, 40.0, 80.0, 120.0, 120.0, 120.0, 120.0, 120.0]
