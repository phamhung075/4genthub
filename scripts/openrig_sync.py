#!/usr/bin/env python3
"""Download 4genthub agents as OpenRig AgentSpec directories.

OpenRig is the client and 4genthub is the cloud. OpenRig resolves `agent_ref` only
from local:/path: directories, so this script materializes the cloud agents on disk.
Reference the result from a rig spec with `agent_ref: "path:<out>/<slug>"`.

Environment:
  AGENTHUB_URL    base URL of the 4genthub server, e.g. https://api.4genthub.com
  AGENTHUB_TOKEN  bearer token. Rendered specs read the same variable from the seat's
                  environment (Claude Code expands ${AGENTHUB_TOKEN} in .mcp.json), so
                  export it before `rig up` / `rig start`. It is never written to disk.

Usage:
  openrig_sync.py [--out DIR] [slug ...]

Each synced slug directory is replaced wholesale. Directories of agents removed from
the cloud are left alone; use a dedicated --out directory and delete them yourself.
"""

import argparse
import json
import os
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path, PurePosixPath

DEFAULT_OUT = Path.home() / ".openrig" / "agenthub-agents"
AGENTS_PATH = "/api/v2/openrig/agents"


def require_env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        sys.exit(f"{name} is not set")
    return value


def fetch(base_url: str, token: str, slug: str | None) -> list[dict]:
    path = f"{AGENTS_PATH}/{slug}" if slug else AGENTS_PATH
    request = urllib.request.Request(
        base_url.rstrip("/") + path,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.load(response)
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", "replace")[:300]
        sys.exit(f"GET {path} failed: HTTP {err.code} {detail}")
    except urllib.error.URLError as err:
        sys.exit(f"GET {path} failed: {err.reason}")
    return [body["agent"]] if slug else body["agents"]


def safe_relative(path: str) -> PurePosixPath:
    """Reject paths that could escape the spec directory."""
    rel = PurePosixPath(path)
    if rel.is_absolute() or ".." in rel.parts or not rel.parts:
        sys.exit(f"server returned an unsafe file path: {path!r}")
    return rel


def write_spec(out: Path, spec: dict) -> Path:
    slug = spec["slug"]
    if "/" in slug or slug in ("", ".", ".."):
        sys.exit(f"server returned an unsafe slug: {slug!r}")
    target = out / slug
    out.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{slug}.", dir=out))
    try:
        for file in spec["files"]:
            destination = staging.joinpath(*safe_relative(file["path"]).parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(file["content"], encoding="utf-8")
        if target.exists():
            shutil.rmtree(target)
        staging.rename(target)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"output directory (default {DEFAULT_OUT})")
    parser.add_argument("slugs", nargs="*", help="agent slugs to sync (default: all)")
    args = parser.parse_args()

    base_url = require_env("AGENTHUB_URL")
    token = require_env("AGENTHUB_TOKEN")

    specs: list[dict] = []
    for slug in args.slugs or [None]:
        specs.extend(fetch(base_url, token, slug))

    out = args.out.expanduser().resolve()
    for spec in specs:
        target = write_spec(out, spec)
        print(f'{spec["slug"]}\tpath:{target}')
    print(f"synced {len(specs)} agent(s) to {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
