#!/usr/bin/env python3
"""Materialize 4genthub resolved seats for the OpenRig client.

OpenRig is the client and 4genthub is the cloud. A *resolved seat* is an
immutable snapshot of a seat's files plus its runtime and policy metadata,
addressed by the hash the cloud assigns to it. This script downloads that
snapshot and lays it out on disk for OpenRig::

    <out>/<room>/<seat>/<hash>/...    immutable files for that snapshot
    <out>/<room>/<seat>/policy.json   policy of the adopted snapshot
    <out>/<room>/<seat>/pinned.json   {"hash": ..., "path": ...} pin

Each hash gets its own directory, so pinned versions coexist. ``pull`` is
pinned by default: once a lock exists it keeps serving that directory and only
prints a notice when the cloud has a newer snapshot. Pass ``--update`` to adopt
the newer snapshot and move the pin. A pin whose directory is missing on disk
is an error; the script never silently falls back to another snapshot.

``rig`` materializes a whole room in one command. It fetches the room's rigspec,
pulls every listed seat with the same pinning rules as ``pull``, then builds::

    <out>/<room>/rig/rig.yaml         the server's RigSpec, written verbatim
    <out>/<room>/rig/agents/<seat>    link to that seat's pinned hash directory

The ``agents/<seat>`` link makes the ``local:agents/<seat>`` references in the
YAML resolve. The rig directory is built in a staging directory and swapped in
only after every seat is pinned, so a failed run leaves a previous rig directory
untouched. Print only ``rig:<path to rig.yaml>`` so the operator can run
``rig up <that path>``.

Offline use is an explicit operator choice. ``bundle`` produces a self-contained
``.rigbundle`` from the pinned snapshot; it is never used automatically as a
fallback. To run a seat offline, operate the bundle yourself::

    rig up <bundle> --target <dir>

Environment:
  AGENTHUB_URL    base URL of the 4genthub server, e.g. https://api.4genthub.com
  AGENTHUB_TOKEN  bearer token. It is sent as an Authorization header and is
                  never written to disk or printed.

Usage:
  openrig_seat_sync.py pull ROOM SEAT [--out DIR] [--update]
  openrig_seat_sync.py rig ROOM [--out DIR] [--update]
                       [--permission-policy locked|standard|open|yolo|none]
  openrig_seat_sync.py bundle ROOM SEAT --rig-yaml PATH --rig-root DIR [--out-dir DIR]
  openrig_seat_sync.py switch ROOM SEAT [--runtime R] [--model M]
                       [--apply none|set-model|restart] [--reason TEXT]

``switch`` changes the LLM of one seat: 4genthub records the occupant, then
OpenRig applies it. Fields not given keep their current cloud value. A model
change is applied with ``rig seat set-model``; ``--apply restart`` also stops and
freshly launches the seat (interrupts it and loses live context). OpenRig cannot
change a runtime in place, so a runtime change prints the manual steps instead.

Exit codes:
  0  success
  1  network, HTTP or response/JSON error
  2  usage or validation error
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path, PurePosixPath

DEFAULT_OUT = Path.home() / ".openrig" / "agenthub-seats"
SEATS_PATH = "/api/v2/openrig/seats"
ROOMS_PATH = "/api/v2/openrig/rooms"

EXIT_OK = 0
EXIT_REMOTE = 1
EXIT_USAGE = 2

NAME_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]*")
MODEL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}")
RUNTIMES = ("claude-code", "codex")
APPLY_MODES = ("none", "set-model", "restart")
PERMISSION_POLICIES = ("locked", "standard", "open", "yolo", "none")
HASH_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


class SyncError(Exception):
    """A failure that maps to one of the documented process exit codes."""

    def __init__(self, message: str, code: int):
        super().__init__(message)
        self.code = code


def require_env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise SyncError(f"{name} is not set", EXIT_USAGE)
    return value


def validate_name(kind: str, value: str) -> str:
    if not isinstance(value, str) or not NAME_RE.fullmatch(value):
        raise SyncError(
            f"invalid {kind} name: {value!r} (expected [a-zA-Z0-9][a-zA-Z0-9_-]*)",
            EXIT_USAGE,
        )
    return value


def validate_hash(value: str) -> str:
    """A hash becomes a directory name, so it must not escape the seat store."""
    if not isinstance(value, str) or not HASH_RE.fullmatch(value) or ".." in value:
        raise SyncError(f"server returned an unsafe seat hash: {value!r}", EXIT_USAGE)
    return value


def safe_relative(path: str) -> PurePosixPath:
    """Reject file paths that could escape the snapshot directory."""
    if (
        not isinstance(path, str)
        or not path
        or path.startswith("/")
        or path.startswith("\\")
        or "\\" in path
    ):
        raise SyncError(f"server returned an unsafe file path: {path!r}", EXIT_USAGE)
    parts = path.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise SyncError(f"server returned an unsafe file path: {path!r}", EXIT_USAGE)
    return PurePosixPath(*parts)


def request_json(
    method: str, base_url: str, token: str, path: str, payload: dict | None = None
) -> dict:
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        base_url.rstrip("/") + path, data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.load(response)
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", "replace")[:300]
        raise SyncError(f"{method} {path} failed: HTTP {err.code} {detail}", EXIT_REMOTE)
    except urllib.error.URLError as err:
        raise SyncError(f"{method} {path} failed: {err.reason}", EXIT_REMOTE)
    except (TimeoutError, OSError) as err:
        raise SyncError(f"{method} {path} failed: {err}", EXIT_REMOTE)
    except json.JSONDecodeError as err:
        raise SyncError(f"{method} {path} returned invalid JSON: {err}", EXIT_REMOTE)

    if not isinstance(body, dict):
        raise SyncError(f"{method} {path} returned a malformed response", EXIT_REMOTE)
    return body


def get_json(base_url: str, token: str, path: str) -> dict:
    return request_json("GET", base_url, token, path)


def fetch_seat(base_url: str, token: str, room: str, seat: str) -> dict:
    path = f"{SEATS_PATH}/{room}/{seat}"
    body = get_json(base_url, token, path)
    if body.get("success") is not True:
        raise SyncError(f"GET {path} returned an error response", EXIT_REMOTE)
    resolved = body.get("resolved_seat")
    if not isinstance(resolved, dict):
        raise SyncError(f"GET {path} response has no resolved_seat", EXIT_REMOTE)
    return resolved


def fetch_rigspec(
    base_url: str, token: str, room: str, permission_policy: str | None = None
) -> dict:
    path = f"{ROOMS_PATH}/{room}/rigspec"
    if permission_policy is not None:
        path += f"?permission_policy={permission_policy}"
    body = get_json(base_url, token, path)
    if body.get("success") is not True:
        raise SyncError(f"GET {path} returned an error response", EXIT_REMOTE)
    rigspec = body.get("rigspec")
    if not isinstance(rigspec, dict):
        raise SyncError(f"GET {path} response has no rigspec", EXIT_REMOTE)
    return rigspec


def extract_files(resolved: dict) -> list[tuple[PurePosixPath, str]]:
    files = resolved.get("files")
    if not isinstance(files, list):
        raise SyncError("resolved_seat has no files list", EXIT_REMOTE)
    entries: list[tuple[PurePosixPath, str]] = []
    for file in files:
        if (
            not isinstance(file, dict)
            or not isinstance(file.get("path"), str)
            or not isinstance(file.get("content"), str)
        ):
            raise SyncError("resolved_seat contains a malformed file entry", EXIT_REMOTE)
        entries.append((safe_relative(file["path"]), file["content"]))
    return entries


def read_lock(lock_path: Path) -> dict | None:
    if not lock_path.is_file():
        return None
    try:
        data = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        raise SyncError(f"cannot read lock file {lock_path}: {err}", EXIT_USAGE)
    if (
        not isinstance(data, dict)
        or not isinstance(data.get("hash"), str)
        or not isinstance(data.get("path"), str)
    ):
        raise SyncError(f"lock file {lock_path} is malformed", EXIT_USAGE)
    return data


def write_json_atomic(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def materialize(hash_dir: Path, entries: list[tuple[PurePosixPath, str]]) -> None:
    """Write a snapshot through a staging directory, then move it into place."""
    if hash_dir.is_dir():
        return
    hash_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{hash_dir.name}.", dir=hash_dir.parent))
    try:
        for relative, content in entries:
            destination = staging.joinpath(*relative.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8")
        staging.rename(hash_dir)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def pull_seat(
    base_url: str, token: str, room: str, seat: str, out: Path, update: bool
) -> Path:
    """Pin one seat and return the directory of the adopted snapshot.

    The lock is the pin: without ``update`` a newer cloud snapshot only prints a
    notice, and a pin whose directory is missing is a loud failure.
    """
    resolved = fetch_seat(base_url, token, room, seat)
    if resolved.get("room") != room or resolved.get("seat") != seat:
        raise SyncError("server returned a snapshot for a different room/seat", EXIT_REMOTE)
    fetched_hash = validate_hash(resolved.get("hash"))
    entries = extract_files(resolved)
    policy = resolved.get("policy", {})

    seat_dir = out / room / seat
    seat_dir.mkdir(parents=True, exist_ok=True)
    lock_path = seat_dir / "pinned.json"
    lock = read_lock(lock_path)

    if lock is not None and not update and fetched_hash != lock["hash"]:
        pinned_hash = validate_hash(lock["hash"])
        pinned_dir = seat_dir / pinned_hash
        if not pinned_dir.is_dir():
            raise SyncError(
                f"pinned seat directory is missing: {pinned_dir} "
                f"(refusing silent fallback; fix the store or remove {lock_path})",
                EXIT_USAGE,
            )
        print(
            f"newer snapshot available: {fetched_hash} (run with --update to adopt)",
            file=sys.stderr,
        )
        return pinned_dir

    hash_dir = seat_dir / fetched_hash
    materialize(hash_dir, entries)
    write_json_atomic(seat_dir / "policy.json", policy)
    if lock is None or lock["hash"] != fetched_hash or update:
        write_json_atomic(lock_path, {"hash": fetched_hash, "path": str(hash_dir)})
    return hash_dir


def cmd_pull(args: argparse.Namespace) -> None:
    room = validate_name("room", args.room)
    seat = validate_name("seat", args.seat)
    base_url = require_env("AGENTHUB_URL")
    token = require_env("AGENTHUB_TOKEN")

    out = (args.out or DEFAULT_OUT).expanduser().resolve()
    hash_dir = pull_seat(base_url, token, room, seat, out, args.update)
    print(f"path:{hash_dir}")


def remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def place_agent(source: Path, target: Path) -> None:
    """Point ``target`` at ``source``, copying if this OS has no symlinks."""
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.parent / f".{target.name}.{os.getpid()}.tmp"
    remove_path(temporary)
    try:
        os.symlink(os.path.relpath(source, target.parent), temporary)
    except OSError:
        remove_path(temporary)
        shutil.copytree(source, temporary, symlinks=True)
    try:
        os.replace(temporary, target)
    except OSError:
        remove_path(target)
        os.replace(temporary, target)


def swap_dir(staging: Path, target: Path) -> None:
    """Move ``staging`` onto ``target``, restoring ``target`` if the move fails."""
    backup = None
    if target.exists() or target.is_symlink():
        backup = Path(tempfile.mkdtemp(prefix=f".{target.name}.old.", dir=target.parent))
        backup.rmdir()
        target.rename(backup)
    try:
        staging.rename(target)
    except BaseException:
        if backup is not None:
            backup.rename(target)
        raise
    if backup is not None:
        shutil.rmtree(backup, ignore_errors=True)


def cmd_rig(args: argparse.Namespace) -> None:
    room = validate_name("room", args.room)
    base_url = require_env("AGENTHUB_URL")
    token = require_env("AGENTHUB_TOKEN")

    rigspec = fetch_rigspec(base_url, token, room, args.permission_policy)
    if rigspec.get("name") != room:
        raise SyncError("server returned a rigspec for a different room", EXIT_REMOTE)
    yaml_text = rigspec.get("yaml")
    if not isinstance(yaml_text, str):
        raise SyncError("rigspec has no yaml text", EXIT_REMOTE)
    listed = rigspec.get("seats")
    if not isinstance(listed, list) or not listed:
        raise SyncError("rigspec has no seats", EXIT_REMOTE)

    seats: list[str] = []
    for entry in listed:
        if not isinstance(entry, dict) or not isinstance(entry.get("seat"), str):
            raise SyncError("rigspec contains a malformed seat entry", EXIT_REMOTE)
        if not isinstance(entry.get("hash"), str):
            raise SyncError("rigspec seat entry has no hash", EXIT_REMOTE)
        seat = validate_name("seat", entry["seat"])
        if seat in seats:
            raise SyncError(f"rigspec lists seat {seat!r} twice", EXIT_REMOTE)
        seats.append(seat)

    out = (args.out or DEFAULT_OUT).expanduser().resolve()
    pinned: dict[str, Path] = {}
    for seat in seats:
        try:
            pinned[seat] = pull_seat(base_url, token, room, seat, out, args.update)
        except SyncError as err:
            raise SyncError(f"seat {seat} could not be pulled: {err}", EXIT_REMOTE) from err

    room_dir = out / room
    room_dir.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".rig.", dir=room_dir))
    try:
        (staging / "rig.yaml").write_text(yaml_text, encoding="utf-8")
        agents = staging / "agents"
        agents.mkdir()
        for seat in seats:
            place_agent(pinned[seat], agents / seat)
        swap_dir(staging, room_dir / "rig")
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    print(f"rig:{room_dir / 'rig' / 'rig.yaml'}")


def cmd_bundle(args: argparse.Namespace) -> None:
    room = validate_name("room", args.room)
    seat = validate_name("seat", args.seat)

    seat_dir = DEFAULT_OUT.expanduser().resolve() / room / seat
    lock = read_lock(seat_dir / "pinned.json")
    if lock is None:
        raise SyncError(
            f"no pinned snapshot for {room}/{seat}; run "
            f"`openrig_seat_sync.py pull {room} {seat}` first",
            EXIT_USAGE,
        )
    pinned_hash = validate_hash(lock["hash"])

    out_dir = (args.out_dir or Path.cwd()).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = out_dir / f"{room}-{seat}-{pinned_hash[:8]}.rigbundle"

    command = [
        "rig",
        "bundle",
        "create",
        str(args.rig_yaml),
        "--rig-root",
        str(args.rig_root),
        "-o",
        str(bundle_path),
        "--name",
        f"{room}-{seat}",
        "--bundle-version",
        "1.0.0",
        "--notes",
        f"resolved_sha256={pinned_hash} source=4genthub",
    ]
    try:
        subprocess.run(command, check=True)
    except FileNotFoundError:
        raise SyncError("`rig` executable not found on PATH", EXIT_REMOTE)
    except subprocess.CalledProcessError as err:
        raise SyncError(
            f"rig bundle create failed with exit code {err.returncode}", EXIT_REMOTE
        )
    print(str(bundle_path))


def validate_choice(kind: str, value: str, pattern: re.Pattern | None, allowed=None) -> str:
    if allowed is not None and value not in allowed:
        raise SyncError(f"invalid {kind}: {value!r} (expected one of {', '.join(allowed)})", EXIT_USAGE)
    if pattern is not None and not pattern.fullmatch(value):
        raise SyncError(f"invalid {kind}: {value!r} (expected {pattern.pattern})", EXIT_USAGE)
    return value


def current_occupant(base_url: str, token: str, room: str, seat: str) -> dict:
    path = f"{ROOMS_PATH}/{room}/seats"
    body = get_json(base_url, token, path)
    seats = body.get("seats")
    if body.get("success") is not True or not isinstance(seats, list):
        raise SyncError(f"GET {path} returned an error response", EXIT_REMOTE)
    for entry in seats:
        if isinstance(entry, dict) and entry.get("seat_key") == seat:
            return entry
    raise SyncError(f"seat {room}/{seat} not found in the cloud", EXIT_REMOTE)


def run_rig(command: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(command, check=True, capture_output=True, text=True)


def canonical_session(room: str, seat: str) -> str | None:
    """Find the live canonical session name of a seat, or None if OpenRig lacks it."""
    result = run_rig(["rig", "ps", "--json", "--nodes", "--rig", room])
    try:
        nodes = json.loads(result.stdout)
    except json.JSONDecodeError as err:
        raise SyncError(f"rig ps returned invalid JSON: {err}", EXIT_REMOTE)
    if isinstance(nodes, dict):
        nodes = nodes.get("items")
    for node in nodes if isinstance(nodes, list) else []:
        if not isinstance(node, dict):
            continue
        logical = node.get("logicalId")
        name = node.get("canonicalSessionName")
        if (
            isinstance(logical, str)
            and isinstance(name, str)
            and name
            and node.get("rigName", room) == room
            and logical.partition(".")[2] == seat
        ):
            return name
    return None


def apply_to_rig(room: str, seat: str, model: str, restart: bool, reason: str) -> str:
    """Apply the model through OpenRig; return the applied mode actually reached."""
    try:
        session = canonical_session(room, seat)
    except FileNotFoundError:
        print("note: `rig` not found on PATH; the cloud change is recorded only", file=sys.stderr)
        return "none"
    except subprocess.CalledProcessError as err:
        raise SyncError(f"rig ps failed with exit code {err.returncode}", EXIT_REMOTE)
    if session is None:
        print(
            f"note: seat {room}/{seat} is not in `rig ps`; the cloud change is recorded only",
            file=sys.stderr,
        )
        return "none"

    commands = []
    if model:
        commands.append(["rig", "seat", "set-model", session, "--model", model, "--reason", reason])
    if restart:
        print(
            f"warning: restarting {session} interrupts it and loses its live context",
            file=sys.stderr,
        )
        commands.append(["rig", "seat", "stop", session, "--reason", reason])
        commands.append(["rig", "seat", "launch", session, "--fresh", "--reason", reason])
    for command in commands:
        try:
            run_rig(command)
        except FileNotFoundError:
            raise SyncError("`rig` executable not found on PATH", EXIT_REMOTE)
        except subprocess.CalledProcessError as err:
            raise SyncError(
                f"`rig seat {command[2]}` failed with exit code {err.returncode}", EXIT_REMOTE
            )
    if restart:
        return "restart"
    return "set-model" if commands else "none"


def cmd_switch(args: argparse.Namespace) -> None:
    room = validate_name("room", args.room)
    seat = validate_name("seat", args.seat)
    if args.runtime is None and args.model is None:
        raise SyncError("at least one of --runtime or --model is required", EXIT_USAGE)
    if args.runtime is not None:
        validate_choice("runtime", args.runtime, None, RUNTIMES)
    if args.model is not None:
        validate_choice("model", args.model, MODEL_RE)
    base_url = require_env("AGENTHUB_URL")
    token = require_env("AGENTHUB_TOKEN")

    current = current_occupant(base_url, token, room, seat)
    runtime = args.runtime if args.runtime is not None else current.get("runtime") or ""
    model = args.model if args.model is not None else current.get("model") or ""
    path = f"{ROOMS_PATH}/{room}/seats/{seat}/occupant"
    body = request_json("PUT", base_url, token, path, {"runtime": runtime, "model": model})
    if body.get("success") is not True:
        raise SyncError(f"PUT {path} returned an error response", EXIT_REMOTE)

    runtime_changed = runtime != (current.get("runtime") or "")
    model_changed = model != (current.get("model") or "")
    reason = args.reason or f"4genthub switch {room}/{seat}"
    if args.apply is not None:
        mode = args.apply
    elif runtime_changed:
        mode = "manual"
    else:
        mode = "set-model" if model_changed else "none"

    applied = "none"
    if mode != "none" and runtime_changed:
        applied = "manual"
        print(
            f"runtime changed: OpenRig cannot switch a runtime in place. Run:\n"
            f"  openrig_seat_sync.py rig {room} --update\n"
            f"  rig down {room}\n"
            f"  rig up <path of the rig.yaml printed by the first command>",
            file=sys.stderr,
        )
    elif mode != "none":
        applied = apply_to_rig(room, seat, model if model_changed else "", mode == "restart", reason)
    print(f"switched:{room}/{seat} runtime={runtime} model={model} applied={applied}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="openrig_seat_sync.py",
        description="Download and pin 4genthub resolved seats for OpenRig.",
        epilog=(
            "Offline use is an explicit operator choice: after `bundle` produces a "
            ".rigbundle, run it yourself with `rig up <bundle> --target <dir>`. This "
            "script never falls back to a bundle automatically."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    pull = subparsers.add_parser("pull", help="download a resolved seat and pin it")
    pull.add_argument("room")
    pull.add_argument("seat")
    pull.add_argument(
        "--out", type=Path, default=None, help=f"seat store (default {DEFAULT_OUT})"
    )
    pull.add_argument(
        "--update",
        action="store_true",
        help="adopt the fetched snapshot even if a different pin exists",
    )
    pull.set_defaults(func=cmd_pull)

    rig = subparsers.add_parser(
        "rig", help="materialize a whole room: rig.yaml plus agent links"
    )
    rig.add_argument("room")
    rig.add_argument(
        "--out", type=Path, default=None, help=f"seat store (default {DEFAULT_OUT})"
    )
    rig.add_argument(
        "--update",
        action="store_true",
        help="adopt fetched snapshots even if different pins exist",
    )
    rig.add_argument(
        "--permission-policy",
        choices=PERMISSION_POLICIES,
        default=None,
        help="ask the server to render the rigspec with this permission policy",
    )
    rig.set_defaults(func=cmd_rig)

    bundle = subparsers.add_parser(
        "bundle", help="build a .rigbundle from the pinned snapshot"
    )
    bundle.add_argument("room")
    bundle.add_argument("seat")
    bundle.add_argument("--rig-yaml", type=Path, required=True)
    bundle.add_argument("--rig-root", type=Path, required=True)
    bundle.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="where to write the .rigbundle (default: current directory)",
    )
    bundle.set_defaults(func=cmd_bundle)

    switch = subparsers.add_parser(
        "switch", help="change the LLM of a seat: cloud records it, OpenRig applies it"
    )
    switch.add_argument("room")
    switch.add_argument("seat")
    switch.add_argument("--runtime", default=None)
    switch.add_argument("--model", default=None)
    switch.add_argument(
        "--apply",
        choices=APPLY_MODES,
        default=None,
        help="default: manual steps when the runtime changed, else set-model when "
        "the model changed, else none; "
        "restart also stops and relaunches the seat fresh",
    )
    switch.add_argument("--reason", default=None, help="audit reason passed to rig")
    switch.set_defaults(func=cmd_switch)

    args = parser.parse_args(argv)
    try:
        args.func(args)
    except SyncError as err:
        print(f"error: {err}", file=sys.stderr)
        return err.code
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
