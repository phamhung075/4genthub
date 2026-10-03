#!/usr/bin/env python3
"""Report OpenRig seat status and herdr agent status up to 4genthub.

A background daemon for each PC. Status goes UP only: it reads local tools and
POSTs to ``{AGENTHUB_URL}/api/v2/openrig/seat-status``. It never receives
commands and never reads terminal content.

Every outgoing object is built by copying named fields (allow-list). Nothing
from a tool's JSON is passed through, enums are clamped to ``unknown``, names
are validated, and the only free text (``detail``) comes from a few short
fields and goes through ``openrig_scrub.scrub``.

OpenRig source: ``rig ps --json --nodes -A`` (local daemon, all rigs) -> a bare
list of nodes (an ``{"items": [...]}`` envelope is also accepted). Per node:
  rigName                       -> room
  logicalId (minus "<podId>.")  -> seat
  runtime                       -> runtime  (claude-code|codex|terminal else unknown)
  state, first match wins:
    sessionStatus stopped|exited, or lifecycleState detached|recoverable -> stopped
    agentActivity.state needs_input, lifecycleState attention_required,
      or startupStatus attention_required|failed                         -> blocked
    agentActivity.state running                                          -> running
    agentActivity.state idle                                             -> idle
    anything else                                                        -> unknown
  detail  <- latestError, heldReason, agentActivity.reason (scrubbed, <=200)
  hash    <- ~/.openrig/agenthub-seats/<room>/<seat>/pinned.json "hash", else ""

herdr source: ``herdr api snapshot`` -> result.snapshot.agents[]. Only
agent, agent_status and pane_id are kept. agent_status maps to
idle|working|blocked|done, anything else unknown.

If a tool is missing or fails, that source is reported as empty and the loop
continues; the condition is logged to stderr once per change.

Environment:
  AGENTHUB_URL    base URL of the 4genthub server
  AGENTHUB_TOKEN  bearer token (sent as a header, never logged or written)

Usage:
  openrig_bridge.py run [--interval 20] [--machine-id ID] [--once]
  openrig_bridge.py once [--print] [--machine-id ID]
  openrig_bridge.py install-service

Exit codes: 0 success, 1 send failure (--once), 2 usage error.
"""

import argparse
import json
import os
import re
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import openrig_scrub  # noqa: E402

STATUS_PATH = "/api/v2/openrig/seat-status"
DEFAULT_PINS = Path.home() / ".openrig" / "agenthub-seats"
HEARTBEAT_SECONDS = 60.0
MAX_BACKOFF = 120.0
TOOL_TIMEOUT = 15
SEND_TIMEOUT = 15

EXIT_OK = 0
EXIT_REMOTE = 1
EXIT_USAGE = 2

NAME_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]*")
HASH_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
PANE_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9:_-]{0,31}")

SEAT_STATES = {"running", "idle", "blocked", "stopped", "unknown"}
RUNTIMES = {"claude-code", "codex", "terminal", "unknown"}
AGENT_STATUSES = {"idle", "working", "blocked", "done", "unknown"}

Runner = Callable[[list[str]], str]
Sender = Callable[[bytes], int]


def run_command(argv: list[str]) -> str:
    """Run a local tool and return stdout; raise on absence, failure or timeout."""
    result = subprocess.run(
        argv, capture_output=True, text=True, timeout=TOOL_TIMEOUT, check=False
    )
    if result.returncode != 0:
        first = (result.stderr or "").strip().splitlines()[:1]
        raise RuntimeError(f"exit {result.returncode}: {first[0][:80] if first else ''}")
    return result.stdout


def _str(value) -> str:
    return value if isinstance(value, str) else ""


def _dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _valid(pattern: re.Pattern[str], value) -> bool:
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def seat_state(node: dict) -> str:
    session = _str(node.get("sessionStatus"))
    life = _str(node.get("lifecycleState"))
    startup = _str(node.get("startupStatus"))
    activity = _str(_dict(node.get("agentActivity")).get("state"))
    if session in ("stopped", "exited") or life in ("detached", "recoverable"):
        return "stopped"
    if activity == "needs_input" or life == "attention_required" or startup in (
        "attention_required",
        "failed",
    ):
        return "blocked"
    if activity in ("running", "idle"):
        return activity
    return "unknown"


def seat_name(node: dict) -> str:
    logical = _str(node.get("logicalId"))
    pod = _str(node.get("podId"))
    prefix = f"{pod}."
    return logical[len(prefix):] if pod and logical.startswith(prefix) else logical


def pinned_hash(pins_dir: Path, room: str, seat: str) -> str:
    try:
        data = json.loads((pins_dir / room / seat / "pinned.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    value = _dict(data).get("hash")
    return value if _valid(HASH_RE, value) else ""


def seat_detail(node: dict) -> str:
    parts = [
        _str(node.get("latestError")),
        _str(node.get("heldReason")),
        _str(_dict(node.get("agentActivity")).get("reason")),
    ]
    return "; ".join(p for p in parts if p)


def build_seats(
    nodes: list, secrets: dict[str, str], pins_dir: Path, strip_detail: bool
) -> tuple[list[dict], int]:
    seats: list[dict] = []
    seen: set[tuple[str, str]] = set()
    skipped = 0
    for node in nodes:
        node = _dict(node)
        room, seat = _str(node.get("rigName")), seat_name(node)
        if not (_valid(NAME_RE, room) and _valid(NAME_RE, seat)) or (room, seat) in seen:
            skipped += 1
            continue
        seen.add((room, seat))
        if strip_detail:
            detail, redacted = "", True
        else:
            detail, redacted = openrig_scrub.scrub(seat_detail(node), secrets)
        runtime = _str(node.get("runtime"))
        seats.append(
            {
                "room": room,
                "seat": seat,
                "state": seat_state(node),
                "runtime": runtime if runtime in RUNTIMES else "unknown",
                "hash": pinned_hash(pins_dir, room, seat),
                "detail": detail,
                "redacted": redacted,
            }
        )
    return seats, skipped


def build_agents(raw_agents: list) -> list[dict]:
    agents: list[dict] = []
    for raw in raw_agents:
        raw = _dict(raw)
        name, pane = raw.get("agent"), raw.get("pane_id")
        if not (_valid(NAME_RE, name) and _valid(PANE_RE, pane)):
            continue
        status = _str(raw.get("agent_status"))
        agents.append(
            {
                "agent": name,
                "status": status if status in AGENT_STATUSES else "unknown",
                "pane_id": pane,
            }
        )
    return agents


def parse_rig_nodes(output: str) -> list:
    data = json.loads(output)
    items = data.get("items") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ValueError("unexpected rig ps JSON shape")
    return items


def parse_herdr_agents(output: str) -> list:
    agents = _dict(_dict(_dict(json.loads(output)).get("result")).get("snapshot")).get("agents")
    if not isinstance(agents, list):
        raise ValueError("unexpected herdr snapshot JSON shape")
    return agents


def sanitize_machine_id(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "-", name).lstrip("-_")
    return cleaned or "machine"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_sender(base_url: str, token: str) -> Sender:
    url = base_url.rstrip("/") + STATUS_PATH

    def send(body: bytes) -> int:
        request = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=SEND_TIMEOUT) as response:
                return response.status
        except urllib.error.HTTPError as err:
            return err.code

    return send


class Bridge:
    """Builds payloads and decides when to send them."""

    def __init__(
        self,
        machine_id: str,
        interval: float,
        send: Sender,
        runner: Runner = run_command,
        secrets: dict[str, str] | None = None,
        pins_dir: Path = DEFAULT_PINS,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.machine_id = machine_id
        self.interval = interval
        self.send = send
        self.runner = runner
        self.secrets = secrets or {}
        self.pins_dir = pins_dir
        self.clock = clock
        self.strip_detail = False
        self.backoff = 0.0
        self._last_key: str | None = None
        self._last_sent: float | None = None
        self._notes: dict[str, str] = {}

    def note(self, key: str, message: str) -> None:
        if self._notes.get(key) != message:
            self._notes[key] = message
            print(f"openrig-bridge: {message}", file=sys.stderr, flush=True)

    def _read(self, key: str, argv: list[str], parse: Callable[[str], list]) -> list:
        try:
            items = parse(self.runner(argv))
        except FileNotFoundError:
            self.note(key, f"{argv[0]} not installed; source absent")
        except Exception as err:
            self.note(key, f"{argv[0]} unavailable: {type(err).__name__}: {err}")
        else:
            self.note(key, f"{argv[0]} ok")
            return items
        return []

    def build_payload(self) -> dict:
        nodes = self._read("rig", ["rig", "ps", "--json", "--nodes", "-A"], parse_rig_nodes)
        raw_agents = self._read("herdr", ["herdr", "api", "snapshot"], parse_herdr_agents)
        seats, skipped = build_seats(nodes, self.secrets, self.pins_dir, self.strip_detail)
        if skipped:
            self.note("skipped", f"skipped {skipped} seat(s) with invalid names")
        return {
            "machine_id": self.machine_id,
            "reported_at": utc_now(),
            "seats": seats,
            "agents": build_agents(raw_agents),
        }

    def cycle(self) -> float:
        """Run one cycle; return seconds to wait before the next one."""
        try:
            payload = self.build_payload()
            key = json.dumps(
                {k: v for k, v in payload.items() if k != "reported_at"}, sort_keys=True
            )
            now = self.clock()
            due = self._last_sent is None or now - self._last_sent >= HEARTBEAT_SECONDS
            if key == self._last_key and not due:
                return self.interval
            status = self.send(json.dumps(payload).encode("utf-8"))
        except Exception as err:
            return self._fail(f"cycle failed: {type(err).__name__}: {err}")
        if 200 <= status < 300:
            self._last_key, self._last_sent = key, now
            self.strip_detail = False
            self.backoff = 0.0
            self.note("send", "sent")
            return self.interval
        if status == 422:
            self.strip_detail = True
            self.note("send", "server rejected text as secret-bearing (422); dropping detail next cycle")
            return self.interval
        return self._fail(f"server answered HTTP {status}")

    def _fail(self, message: str) -> float:
        self.note("send", message)
        self.backoff = min(MAX_BACKOFF, self.backoff * 2 if self.backoff else self.interval)
        return self.backoff

    def run(self, stop: threading.Event, once: bool = False) -> int:
        while not stop.is_set():
            delay = self.cycle()
            if once:
                return EXIT_OK if self.backoff == 0.0 and not self.strip_detail else EXIT_REMOTE
            stop.wait(delay)
        return EXIT_OK


SERVICE_UNIT = """[Unit]
Description=4genthub OpenRig status bridge
After=network-online.target

[Service]
EnvironmentFile=%h/.config/agenthub-bridge.env
ExecStart={python} {script} run
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
"""


def service_unit() -> str:
    return SERVICE_UNIT.format(python=sys.executable, script=Path(__file__).resolve())


def build_bridge(args, send: Sender) -> Bridge:
    machine_id = args.machine_id or sanitize_machine_id(socket.gethostname())
    if not NAME_RE.fullmatch(machine_id):
        print(f"invalid machine id: {machine_id!r}", file=sys.stderr)
        raise SystemExit(EXIT_USAGE)
    return Bridge(
        machine_id,
        getattr(args, "interval", 20.0),
        send,
        secrets=openrig_scrub.secret_values_from_env(os.environ),
    )


def sender_from_env() -> Sender:
    url, token = os.environ.get("AGENTHUB_URL", ""), os.environ.get("AGENTHUB_TOKEN", "")
    if not url or not token:
        print("AGENTHUB_URL and AGENTHUB_TOKEN must be set", file=sys.stderr)
        raise SystemExit(EXIT_USAGE)
    return make_sender(url, token)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="openrig_bridge.py")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--interval", type=float, default=20.0)
    run.add_argument("--machine-id")
    run.add_argument("--once", action="store_true")
    once = sub.add_parser("once")
    once.add_argument("--print", action="store_true", dest="print_only")
    once.add_argument("--machine-id")
    sub.add_parser("install-service")
    args = parser.parse_args(argv)
    if args.command == "run" and args.interval <= 0:
        parser.error("--interval must be positive")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.command == "install-service":
        print(service_unit(), end="")
        return EXIT_OK
    if args.command == "once" and args.print_only:
        bridge = build_bridge(args, lambda body: 200)
        print(json.dumps(bridge.build_payload(), indent=2))
        return EXIT_OK
    bridge = build_bridge(args, sender_from_env())
    stop = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    return bridge.run(stop, once=args.command == "once" or args.once)


if __name__ == "__main__":
    sys.exit(main())
