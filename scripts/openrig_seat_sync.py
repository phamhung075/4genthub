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
  openrig_seat_sync.py bundle ROOM SEAT --rig-yaml PATH --rig-root DIR [--out-dir DIR]

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

EXIT_OK = 0
EXIT_REMOTE = 1
EXIT_USAGE = 2

NAME_RE = re.compile(r"[a-z0-9][a-z0-9_-]*")
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
            f"invalid {kind} name: {value!r} (expected [a-z0-9][a-z0-9_-]*)",
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


def fetch_seat(base_url: str, token: str, room: str, seat: str) -> dict:
    path = f"{SEATS_PATH}/{room}/{seat}"
    request = urllib.request.Request(
        base_url.rstrip("/") + path,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.load(response)
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", "replace")[:300]
        raise SyncError(f"GET {path} failed: HTTP {err.code} {detail}", EXIT_REMOTE)
    except urllib.error.URLError as err:
        raise SyncError(f"GET {path} failed: {err.reason}", EXIT_REMOTE)
    except (TimeoutError, OSError) as err:
        raise SyncError(f"GET {path} failed: {err}", EXIT_REMOTE)
    except json.JSONDecodeError as err:
        raise SyncError(f"GET {path} returned invalid JSON: {err}", EXIT_REMOTE)

    if not isinstance(body, dict) or body.get("success") is not True:
        raise SyncError(f"GET {path} returned an error response", EXIT_REMOTE)
    resolved = body.get("resolved_seat")
    if not isinstance(resolved, dict):
        raise SyncError(f"GET {path} response has no resolved_seat", EXIT_REMOTE)
    return resolved


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


def cmd_pull(args: argparse.Namespace) -> None:
    room = validate_name("room", args.room)
    seat = validate_name("seat", args.seat)
    base_url = require_env("AGENTHUB_URL")
    token = require_env("AGENTHUB_TOKEN")

    resolved = fetch_seat(base_url, token, room, seat)
    if resolved.get("room") != room or resolved.get("seat") != seat:
        raise SyncError("server returned a snapshot for a different room/seat", EXIT_REMOTE)
    fetched_hash = validate_hash(resolved.get("hash"))
    entries = extract_files(resolved)
    policy = resolved.get("policy", {})

    out = (args.out or DEFAULT_OUT).expanduser().resolve()
    seat_dir = out / room / seat
    seat_dir.mkdir(parents=True, exist_ok=True)
    lock_path = seat_dir / "pinned.json"
    lock = read_lock(lock_path)

    if lock is not None and not args.update and fetched_hash != lock["hash"]:
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
        print(f"path:{pinned_dir}")
        return

    hash_dir = seat_dir / fetched_hash
    materialize(hash_dir, entries)
    write_json_atomic(seat_dir / "policy.json", policy)
    if lock is None or lock["hash"] != fetched_hash or args.update:
        write_json_atomic(lock_path, {"hash": fetched_hash, "path": str(hash_dir)})
    print(f"path:{hash_dir}")


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

    args = parser.parse_args(argv)
    try:
        args.func(args)
    except SyncError as err:
        print(f"error: {err}", file=sys.stderr)
        return err.code
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
