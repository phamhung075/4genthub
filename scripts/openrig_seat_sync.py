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
untouched. **The build owns exactly ``rig.yaml`` and ``agents/``**: anything else
found in the rig directory was placed there by the operator — a credential link,
a delegation file, notes — and is carried over to the rebuilt directory, named on
stderr, rather than deleted. Print only ``rig:<path to rig.yaml>`` on stdout so the
operator can run ``rig up <that path>``.

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
  openrig_seat_sync.py bundle ROOM SEAT --rig-yaml PATH --rig-root DIR [--out-dir DIR]
  openrig_seat_sync.py install-checker [--out DIR]
  openrig_seat_sync.py switch ROOM SEAT [--runtime R] [--model M]
                       [--apply none|set-model|restart] [--reason TEXT]

``install-checker`` builds ``agenthub_go/cmd/seatcheck`` to ``<DIR>/bin/seatcheck`` (DIR is the
seat store) and links ``~/.local/bin/seatcheck`` to it. Seats run the bare name
``seatcheck send ...``, so it must resolve on the PATH the seats inherit; ``pull`` and ``rig``
fail until it resolves to the store's binary. The check reads the PATH the seats inherit: while
a tmux server runs that is its global PATH, and at cold start it reads the running rig daemon's
PATH from ``/proc/<pid>/environ`` (the daemon starts the first tmux server, so the first seat
inherits the daemon's environment). Only when neither is available does it fall back to the
operator's shell PATH and say so. If the daemon's PATH does not resolve ``seatcheck``, restart
the daemon from a shell where it resolves (``rig daemon stop``, ``rig daemon start``).

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
import time
import urllib.error
import urllib.request
from pathlib import Path, PurePosixPath

DEFAULT_OUT = Path.home() / ".openrig" / "agenthub-seats"
AGENTHUB_GO_DIR = Path(__file__).resolve().parent.parent / "agenthub_go"
CHECKER_NAME = "seatcheck"
SEATS_PATH = "/api/v2/openrig/seats"
ROOMS_PATH = "/api/v2/openrig/rooms"

EXIT_OK = 0
EXIT_REMOTE = 1
EXIT_USAGE = 2

NAME_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]*")
MODEL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}")
RUNTIMES = ("claude-code", "codex", "agy", "omp")
APPLY_MODES = ("none", "set-model", "restart")
HASH_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
# How often `respawn` re-reads the seat while waiting for the dead reading to hold.
RESPAWN_POLL_SECONDS = 5.0
# Default hold before respawning. The reason field is the only discriminator, and it is
# RUNTIME-DEPENDENT: a just-launched agy seat reads exactly like a dead one (`unknown` +
# `no_runtime_hook`) until its hook attaches (observed ~15s), while an omp seat with no activity
# yet reports reason null and stays unknown. So one reading is never enough, and this hold must
# not be shortened without re-measuring per runtime.
DEFAULT_RESPAWN_AFTER_SECONDS = 30.0


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
        raise SyncError(
            f"{method} {path} failed: HTTP {err.code} {detail}", EXIT_REMOTE
        )
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


def fetch_rigspec(base_url: str, token: str, room: str) -> dict:
    path = f"{ROOMS_PATH}/{room}/rigspec"
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
            raise SyncError(
                "resolved_seat contains a malformed file entry", EXIT_REMOTE
            )
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
        raise SyncError(
            "server returned a snapshot for a different room/seat", EXIT_REMOTE
        )
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


def checker_binary(out: Path) -> Path:
    return out / "bin" / CHECKER_NAME


def checker_link() -> Path:
    return Path.home() / ".local" / "bin" / CHECKER_NAME


TMUX_TIMEOUT_SECONDS = 5


def tmux_global_path() -> str | None:
    """The PATH new seats inherit (tmux's global environment); None without a tmux server."""
    try:
        result = subprocess.run(
            ["tmux", "show-environment", "-g", "PATH"],
            capture_output=True,
            text=True,
            timeout=TMUX_TIMEOUT_SECONDS,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0 or not result.stdout.startswith("PATH="):
        return None
    return result.stdout.strip()[len("PATH=") :]


def openrig_daemon_port() -> str | None:
    """The rig daemon port from OPENRIG_PORT, else the port in OPENRIG_URL."""
    port = os.environ.get("OPENRIG_PORT", "").strip()
    if port.isdigit():
        return port
    match = re.search(r":(\d+)(?:/|$)", os.environ.get("OPENRIG_URL", ""))
    return match.group(1) if match else None


def openrig_daemon_pid() -> int | None:
    """The rig daemon pid listening on the OpenRig port, or None when it cannot be found.

    The daemon starts the first tmux server, so at cold start the first seat inherits the
    daemon's environment; its PATH is readable from /proc while the daemon runs.
    """
    port = openrig_daemon_port()
    if port is None:
        return None
    try:
        result = subprocess.run(
            ["ss", "-ltnp"],
            capture_output=True,
            text=True,
            timeout=TMUX_TIMEOUT_SECONDS,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    for line in result.stdout.splitlines():
        if f":{port} " in line or f":{port}\t" in line:
            match = re.search(r"pid=(\d+)", line)
            if match:
                return int(match.group(1))
    return None


def proc_env_path(pid: int) -> str | None:
    """The PATH of process pid from /proc/<pid>/environ, or None when unreadable."""
    try:
        raw = Path(f"/proc/{pid}/environ").read_bytes()
    except OSError:
        return None
    for entry in raw.split(b"\0"):
        if entry.startswith(b"PATH="):
            return entry[len(b"PATH=") :].decode("utf-8", "surrogateescape")
    return None


SHELL_PATH_SOURCE = (
    "shell PATH (no tmux server and no readable rig daemon PATH were found, so no seat "
    "exists yet)"
)
DAEMON_PATH_SOURCE = "rig daemon PATH (the daemon starts the first tmux server, so the first seat inherits it)"


def seat_path() -> tuple[str, str]:
    """The PATH to check and its source: tmux global, else the daemon's, else this shell's.

    At cold start (no tmux server) the first seat inherits the rig daemon's environment, so
    the daemon's PATH is read from its /proc entry instead of assuming the operator's shell.
    """
    tmux_path = tmux_global_path()
    if tmux_path is not None:
        return tmux_path, "tmux global PATH"
    pid = openrig_daemon_pid()
    if pid is not None:
        daemon_path = proc_env_path(pid)
        if daemon_path:
            return daemon_path, DAEMON_PATH_SOURCE
    return os.environ.get("PATH", ""), SHELL_PATH_SOURCE


def resolve_checker(out: Path) -> bool:
    """True when the bare name ``seatcheck`` resolves to the seat store's binary."""
    path, source = seat_path()
    if source == SHELL_PATH_SOURCE:
        print(f"note: checked {CHECKER_NAME} on the {source}", file=sys.stderr)
    found = shutil.which(CHECKER_NAME, path=path)
    return found is not None and os.path.realpath(found) == os.path.realpath(
        checker_binary(out)
    )


PATH_LIMIT = (
    "seats inherit the tmux global PATH, which is what this checks while a tmux server "
    "runs (only the default tmux socket is queried); at cold start it reads the PATH of "
    "the running rig daemon (the daemon starts the first tmux server, so the first seat "
    "inherits the daemon's environment). If the daemon's PATH does not resolve "
    f"{CHECKER_NAME}, restart the daemon from a shell where it resolves "
    "(`rig daemon stop`, `rig daemon start`)"
)


def describe_found() -> str:
    path, source = seat_path()
    found = shutil.which(CHECKER_NAME, path=path)
    where = f"{found} -> {os.path.realpath(found)}" if found else "not on PATH"
    return f"{where}, on the {source}"


def require_checker(out: Path) -> None:
    if not resolve_checker(out):
        raise SyncError(
            f"{CHECKER_NAME} does not resolve to {checker_binary(out)} on PATH "
            f"(found: {describe_found()}); "
            "run `openrig_seat_sync.py install-checker` and put "
            f"{checker_link().parent} on PATH ({PATH_LIMIT})",
            EXIT_USAGE,
        )


def cmd_install_checker(args: argparse.Namespace) -> None:
    out = (args.out or DEFAULT_OUT).expanduser().resolve()
    binary = checker_binary(out)
    binary.parent.mkdir(parents=True, exist_ok=True)
    cache, tmp = AGENTHUB_GO_DIR / ".gocache", AGENTHUB_GO_DIR / ".gotmp"
    for directory in (cache, tmp):
        directory.mkdir(exist_ok=True)
    try:
        subprocess.run(
            ["go", "build", "-o", str(binary), "./cmd/seatcheck"],
            cwd=AGENTHUB_GO_DIR,
            env={**os.environ, "GOCACHE": str(cache), "TMPDIR": str(tmp)},
            check=True,
        )
    except FileNotFoundError:
        raise SyncError(
            "go is not installed; cannot build the seat checker", EXIT_USAGE
        )
    except subprocess.CalledProcessError as err:
        raise SyncError(f"go build failed with exit code {err.returncode}", EXIT_REMOTE)
    place_agent(binary, checker_link())
    if not resolve_checker(out):
        raise SyncError(
            f"installed {binary} and linked {checker_link()}, but {CHECKER_NAME} does not "
            f"resolve to it on PATH (found: {describe_found()}); "
            f"add {checker_link().parent} to PATH ({PATH_LIMIT})",
            EXIT_USAGE,
        )
    print(f"checker:{binary}")


def cmd_pull(args: argparse.Namespace) -> None:
    room = validate_name("room", args.room)
    seat = validate_name("seat", args.seat)
    out = (args.out or DEFAULT_OUT).expanduser().resolve()
    require_checker(out)
    base_url = require_env("AGENTHUB_URL")
    token = require_env("AGENTHUB_TOKEN")

    hash_dir = pull_seat(base_url, token, room, seat, out, args.update)
    print(f"path:{hash_dir}")


def remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def place_agent(source: Path, target: Path) -> None:
    """Point ``target`` at ``source`` (a file or a directory) with a relative symlink."""
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.parent / f".{target.name}.{os.getpid()}.tmp"
    remove_path(temporary)
    try:
        os.symlink(os.path.relpath(source, target.parent), temporary)
    except OSError as err:
        raise SyncError(f"cannot link {target} to {source}: {err}", EXIT_USAGE) from err
    if target.is_dir() and not target.is_symlink():
        remove_path(target)
    os.replace(temporary, target)


def materialize_agent(source: Path, seat_dir: Path, target: Path) -> None:
    """Materialize the seat's agent directory at ``target`` from the pinned snapshot.

    The snapshot (``source``) holds only the rendered files. A bundle built from this rig
    root copies what sits here, so the seat's ``policy.json`` and ``pinned.json`` are
    copied in from ``seat_dir``: ``policy.json`` is the file ``seatcheck`` reads at runtime
    (``<pins>/<rig>/<member>/policy.json``), and without it an offline bundle seat cannot
    decide or audit (G4).
    """
    remove_path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target, symlinks=False)
    for name in ("policy.json", "pinned.json"):
        candidate = seat_dir / name
        if candidate.is_file():
            shutil.copy2(candidate, target / name)


# The entries a rig build writes into the rig directory. Everything else found there was placed
# by the operator and is preserved across a rebuild: the swap replaces what the build RENDERS, and
# an operator's file was never the build's to delete.
RIG_BUILD_ENTRIES = frozenset({"rig.yaml", "agents"})


def operator_entries(rig_dir: Path) -> list[str]:
    """The names in a rig directory that the build does not own.

    A credential link, a delegation file, an operator's notes — anything that is not
    ``rig.yaml`` or ``agents`` — lives here, and a rebuild must carry it over rather than
    remove it silently.
    """
    if not rig_dir.is_dir():
        return []
    return sorted(
        entry.name for entry in rig_dir.iterdir() if entry.name not in RIG_BUILD_ENTRIES
    )


def swap_dir(staging: Path, target: Path, preserve: list[str] | None = None) -> list[str]:
    """Move ``staging`` onto ``target``, restoring ``target`` if the move fails.

    ``preserve`` names entries of the old ``target`` that the caller does not own: after the swap
    they are moved back into the new directory, and their names are returned so the caller can say
    what it kept. A name the new directory already has is left alone — the build's own content
    wins. Entries are moved rather than copied, so a symlink stays a symlink.
    """
    kept: list[str] = []
    backup = None
    if target.exists() or target.is_symlink():
        backup = Path(
            tempfile.mkdtemp(prefix=f".{target.name}.old.", dir=target.parent)
        )
        backup.rmdir()
        target.rename(backup)
    try:
        staging.rename(target)
    except BaseException:
        if backup is not None:
            backup.rename(target)
        raise
    if backup is not None:
        for name in preserve or []:
            candidate = backup / name
            if not candidate.exists() and not candidate.is_symlink():
                continue
            if (target / name).exists() or (target / name).is_symlink():
                continue
            candidate.rename(target / name)
            kept.append(name)
        shutil.rmtree(backup, ignore_errors=True)
    return kept


def cmd_rig(args: argparse.Namespace) -> None:
    room = validate_name("room", args.room)
    out = (args.out or DEFAULT_OUT).expanduser().resolve()
    require_checker(out)
    base_url = require_env("AGENTHUB_URL")
    token = require_env("AGENTHUB_TOKEN")

    rigspec = fetch_rigspec(base_url, token, room)
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

    pinned: dict[str, Path] = {}
    for seat in seats:
        try:
            pinned[seat] = pull_seat(base_url, token, room, seat, out, args.update)
        except SyncError as err:
            raise SyncError(
                f"seat {seat} could not be pulled: {err}", EXIT_REMOTE
            ) from err

    room_dir = out / room
    room_dir.mkdir(parents=True, exist_ok=True)
    rig_dir = room_dir / "rig"
    # Whatever the operator put in the rig directory survives this build; the swap below only
    # ever replaces what the build itself renders.
    operator_files = operator_entries(rig_dir)
    staging = Path(tempfile.mkdtemp(prefix=".rig.", dir=room_dir))
    try:
        (staging / "rig.yaml").write_text(yaml_text, encoding="utf-8")
        agents = staging / "agents"
        agents.mkdir()
        for seat in seats:
            materialize_agent(pinned[seat], out / room / seat, agents / seat)
        kept = swap_dir(staging, rig_dir, preserve=operator_files)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    if kept:
        print(
            f"kept {len(kept)} file(s) the build did not create in {rig_dir}: "
            f"{', '.join(kept)}",
            file=sys.stderr,
        )
    print(f"rig:{rig_dir / 'rig.yaml'}")


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


def cmd_offline_install(args: argparse.Namespace) -> None:
    """Install a materialized bundle's pinned policy into the seat store.

    ``seatcheck`` resolves its policy as
    ``<home>/.openrig/agenthub-seats/<rig>/<member>/policy.json`` (it is deliberately not a
    flag, so the guard cannot choose where its policy and audit live). A bundle
    materializes to ``<target>/agents/<agent>/``, so this copies the pinned
    ``policy.json``/``pinned.json`` that travel inside the bundle into that store path —
    without it an offline seat's allowed path cannot decide or audit (G4).
    """
    try:
        import yaml  # lazy: the other subcommands stay dependency-free
    except ImportError as err:  # pragma: no cover - environment dependent
        raise SyncError(f"PyYAML is required for offline-install: {err}", EXIT_USAGE)

    target = Path(args.target).expanduser().resolve()
    spec_path = target / "rig.yaml"
    try:
        spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    except OSError as err:
        raise SyncError(f"cannot read {spec_path}: {err}", EXIT_USAGE) from err
    except yaml.YAMLError as err:
        raise SyncError(f"{spec_path} is not valid YAML: {err}", EXIT_USAGE) from err
    if not isinstance(spec, dict):
        raise SyncError(f"{spec_path} is not a rig spec", EXIT_USAGE)
    rig = validate_name("room", str(spec.get("name") or ""))
    home = Path(args.home).expanduser().resolve() if args.home else Path.home()
    store = home / ".openrig" / "agenthub-seats"

    installed: list[str] = []
    for pod in spec.get("pods") or []:
        for member in (pod or {}).get("members") or []:
            seat = validate_name("seat", str((member or {}).get("id") or ""))
            ref = str((member or {}).get("agent_ref") or "")
            agent = ref.partition("local:agents/")[2]
            if not agent or not safe_relative(agent):
                print(f"skipped {rig}/{seat}: no local agent ref", file=sys.stderr)
                continue
            agent_dir = target / "agents" / agent
            policy = agent_dir / "policy.json"
            if not policy.is_file():
                print(
                    f"skipped {rig}/{seat}: no pinned policy in the bundle "
                    f"({policy} is missing)",
                    file=sys.stderr,
                )
                continue
            # Two members that share one seat type share one agent directory in the bundle,
            # so only one of their policies can ride there. Refuse to install a policy that
            # names a different seat instead of silently giving this seat the wrong links.
            try:
                claimed = json.loads(policy.read_text(encoding="utf-8")).get("Seat")
            except (OSError, ValueError) as err:
                raise SyncError(f"cannot read {policy}: {err}", EXIT_USAGE) from err
            if isinstance(claimed, str) and claimed != seat:
                print(
                    f"skipped {rig}/{seat}: the bundle's {agent} policy belongs to seat "
                    f"{claimed!r} (members sharing one seat type share one agent directory "
                    "in a bundle; per-seat policy needs distinct seat types)",
                    file=sys.stderr,
                )
                continue
            seat_dir = store / rig / seat
            seat_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(policy, seat_dir / "policy.json")
            pinned = agent_dir / "pinned.json"
            if pinned.is_file():
                shutil.copy2(pinned, seat_dir / "pinned.json")
            installed.append(f"{rig}/{seat}")
    if not installed:
        raise SyncError(
            f"no pinned policy found under {target}/agents; build the bundle from a rig "
            "root that carries it (openrig_seat_sync.py rig / bundle does since 2026-10-05)",
            EXIT_USAGE,
        )
    for name in installed:
        print(f"installed {name} -> {store / name}")


def _seat_node(room: str, seat: str) -> dict | None:
    """The ``rig ps`` node for ``room.seat``, or None when OpenRig does not list it."""
    result = run_rig(["rig", "ps", "--json", "--nodes", "--rig", room])
    try:
        nodes = json.loads(result.stdout)
    except json.JSONDecodeError as err:
        raise SyncError(f"rig ps returned invalid JSON: {err}", EXIT_REMOTE)
    if isinstance(nodes, dict):
        nodes = nodes.get("items")
    for node in nodes if isinstance(nodes, list) else []:
        if isinstance(node, dict) and (node.get("logicalId") or "").partition(".")[2] == seat:
            return node
    return None


def _agent_is_gone(node: dict) -> bool:
    """The reading a dead agent leaves: the tmux session is up, the runtime hook is not."""
    activity = node.get("agentActivity") or {}
    return (
        node.get("sessionStatus") not in ("stopped", "exited")
        and activity.get("state") == "unknown"
        and activity.get("reason") == "no_runtime_hook"
    )


def cmd_respawn(args: argparse.Namespace) -> None:
    """Respawn a seat whose agent died outside `rig seat stop`.

    OpenRig has no automatic trigger for this: its installed CLI carries no respawn or
    auto-restart path (grep over `@openrig/cli/dist` for respawn/autoRestart/restartPolicy is
    empty); it offers only the deliberate primitive `rig seat launch <seat> [--fresh] [--stop]
    --reason <text>` (registered at `@openrig/cli/dist/commands/seat.js:419`), which creates a
    blank native occupant with a new session id and generation. This runs that primitive, and
    only for a seat that really reads dead: a just-launched agy seat produces the SAME reading
    (`agentActivity` unknown + `no_runtime_hook`) until its runtime hook attaches (~15s; an omp
    seat with no activity yet reports reason null instead), so the reading must hold for
    `--after-seconds` before anything is launched.
    """
    room = validate_name("room", args.room)
    seat = validate_name("seat", args.seat)
    deadline = time.monotonic() + args.after_seconds
    while True:
        node = _seat_node(room, seat)
        if node is None:
            raise SyncError(f"OpenRig lists no node {room}.{seat}", EXIT_USAGE)
        if not _agent_is_gone(node):
            raise SyncError(
                f"{room}.{seat} is not in the dead-agent state "
                f"(sessionStatus={node.get('sessionStatus')!r}, "
                f"agentActivity={node.get('agentActivity')!r}); refusing to respawn",
                EXIT_USAGE,
            )
        if time.monotonic() >= deadline:
            break
        time.sleep(RESPAWN_POLL_SECONDS)
    session = canonical_session(room, seat) or f"{room}.{seat}"
    command = [
        "rig",
        "seat",
        "launch",
        session,
        "--fresh",
        "--stop",
        "--reason",
        args.reason,
    ]
    try:
        result = run_rig(command)
    except subprocess.CalledProcessError as err:
        # `rig seat launch` can start the occupant and still exit non-zero (for example "Fresh
        # occupant started but runtime identity requires attention"), so decide on the seat's
        # actual state, not the exit code: an automated caller must not read a successful respawn
        # as a failure. Still dead -> error; running now -> success with the caveat on stderr.
        detail = (err.stderr or err.stdout or "").strip().splitlines()
        message = detail[-1] if detail else f"exit {err.returncode}"
        node = _seat_node(room, seat) or {}
        if _agent_is_gone(node):
            raise SyncError(f"rig seat launch reported: {message}", EXIT_REMOTE) from err
        print(f"respawned {room}.{seat}; rig seat launch warned: {message}", file=sys.stderr)
        return
    if result.stdout.strip():
        print(result.stdout.strip())


def validate_choice(
    kind: str, value: str, pattern: re.Pattern | None, allowed=None
) -> str:
    if allowed is not None and value not in allowed:
        raise SyncError(
            f"invalid {kind}: {value!r} (expected one of {', '.join(allowed)})",
            EXIT_USAGE,
        )
    if pattern is not None and not pattern.fullmatch(value):
        raise SyncError(
            f"invalid {kind}: {value!r} (expected {pattern.pattern})", EXIT_USAGE
        )
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
        print(
            "note: `rig` not found on PATH; the cloud change is recorded only",
            file=sys.stderr,
        )
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
        commands.append(
            ["rig", "seat", "set-model", session, "--model", model, "--reason", reason]
        )
    if restart:
        print(
            f"warning: restarting {session} interrupts it and loses its live context",
            file=sys.stderr,
        )
        commands.append(["rig", "seat", "stop", session, "--reason", reason])
        commands.append(
            ["rig", "seat", "launch", session, "--fresh", "--reason", reason]
        )
    for command in commands:
        try:
            run_rig(command)
        except FileNotFoundError:
            raise SyncError("`rig` executable not found on PATH", EXIT_REMOTE)
        except subprocess.CalledProcessError as err:
            raise SyncError(
                f"`rig seat {command[2]}` failed with exit code {err.returncode}",
                EXIT_REMOTE,
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
    body = request_json(
        "PUT", base_url, token, path, {"runtime": runtime, "model": model}
    )
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
        applied = apply_to_rig(
            room, seat, model if model_changed else "", mode == "restart", reason
        )
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

    offline = subparsers.add_parser(
        "offline-install",
        help="install a materialized bundle's pinned policy into the seat store",
    )
    offline.add_argument(
        "target", type=Path, help="the directory a .rigbundle was materialized into"
    )
    offline.add_argument(
        "--home",
        type=Path,
        default=None,
        help="home whose .openrig/agenthub-seats is written (default: the real home)",
    )
    offline.set_defaults(func=cmd_offline_install)

    respawn = subparsers.add_parser(
        "respawn",
        help="respawn a seat whose agent died outside `rig seat stop`",
    )
    respawn.add_argument("room")
    respawn.add_argument("seat")
    respawn.add_argument(
        "--after-seconds",
        type=float,
        default=DEFAULT_RESPAWN_AFTER_SECONDS,
        help=(
            "how long the dead reading must hold before launching "
            f"(default {DEFAULT_RESPAWN_AFTER_SECONDS:g}s: a just-launched seat reads the same)"
        ),
    )
    respawn.add_argument(
        "--reason",
        default="agent died outside `rig seat stop` (respawn)",
        help="audit reason recorded on the seat.fresh_launched event",
    )
    respawn.set_defaults(func=cmd_respawn)

    install = subparsers.add_parser(
        "install-checker",
        help="build seatcheck into the seat store and link it on PATH",
    )
    install.add_argument(
        "--out", type=Path, default=None, help=f"seat store (default {DEFAULT_OUT})"
    )
    install.set_defaults(func=cmd_install_checker)

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
