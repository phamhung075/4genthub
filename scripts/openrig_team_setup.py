#!/usr/bin/env python3
"""Create the 4genthub development team as an OpenRig room through the 4genthub API.

The team definition (room, seats, links, context modules, overlays) is data in
``scripts/team/4genthub/team.json``; the module texts are the files next to it.
``apply`` pushes that definition in a fixed order and is idempotent::

    1. context modules   PUT  /api/v2/openrig/modules/{slug}/versions/{version}
    2. room              POST /api/v2/openrig/rooms                  (409 exists: ok)
    3. seats             POST /api/v2/openrig/rooms/{room}/seats     (409 exists: ok)
    4. links             PUT  /api/v2/openrig/rooms/{room}/seats/{seat}/links
    5. company overlay   PUT  /api/v2/openrig/overlay
    6. seat overlays     PUT  /api/v2/openrig/rooms/{room}/seats/{seat}/overlay

Overlay PUTs replace the previous overlay of their scope, so the full op list is
sent every time. Any other HTTP error stops the run.

Environment:
  AGENTHUB_URL    base URL of the 4genthub server, e.g. https://api.4genthub.com
  AGENTHUB_TOKEN  bearer token; sent as an Authorization header, never printed.

Usage:
  openrig_team_setup.py apply [--dry-run] [--team DIR]

``--dry-run`` prints the plan without calling the API and needs no environment.

Exit codes:
  0  success
  1  network or HTTP error
  2  usage or configuration error
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_TEAM_DIR = Path(__file__).resolve().parent / "team" / "4genthub"
API = "/api/v2/openrig"

EXIT_OK = 0
EXIT_REMOTE = 1
EXIT_USAGE = 2


class SetupError(Exception):
    """A failure that maps to one of the documented process exit codes."""

    def __init__(self, message: str, code: int):
        super().__init__(message)
        self.code = code


def load_team(team_dir: Path) -> dict:
    """Read team.json and attach each module's text from its file."""
    try:
        team = json.loads((team_dir / "team.json").read_text(encoding="utf-8"))
        for module in team["modules"]:
            module["content"] = (team_dir / module["file"]).read_text(encoding="utf-8")
    except (OSError, ValueError, KeyError) as err:
        raise SetupError(f"cannot load team definition from {team_dir}: {err}", EXIT_USAGE)
    return team


def module_versions(team: dict) -> dict:
    return {m["slug"]: m["version"] for m in team["modules"]}


def overlay_body(team: dict, slugs: list) -> dict:
    versions = module_versions(team)
    try:
        ops = [{"kind": "add", "slug": s, "version": versions[s], "content": ""} for s in slugs]
    except KeyError as err:
        raise SetupError(f"overlay references unknown module {err}", EXIT_USAGE)
    return {"ops": ops}


def build_plan(team: dict) -> list:
    """Return the ordered steps: (label, method, path, body, tolerate_exists)."""
    room = team["room"]["slug"]
    seats_path = f"{API}/rooms/{room}/seats"
    plan = []
    for m in team["modules"]:
        plan.append((
            f"module {m['slug']}@{m['version']}", "PUT",
            f"{API}/modules/{m['slug']}/versions/{m['version']}",
            {"kind": m["kind"], "content": m["content"]}, False,
        ))
    plan.append((f"room {room}", "POST", f"{API}/rooms", dict(team["room"]), True))
    for seat in team["seats"]:
        plan.append((f"seat {seat['seat_key']}", "POST", seats_path, dict(seat), True))
    for link in team["links"]:
        plan.append((
            f"link {link['from']} {link['kind']} {link['to']}", "PUT",
            f"{seats_path}/{link['from']}/links",
            {"to_seat": link["to"], "kind": link["kind"], "allow": True}, False,
        ))
    plan.append((
        "overlay company", "PUT", f"{API}/overlay",
        overlay_body(team, team["company_overlay"]), False,
    ))
    for seat, slugs in team["seat_overlays"].items():
        plan.append((
            f"overlay seat {seat}", "PUT", f"{seats_path}/{seat}/overlay",
            overlay_body(team, slugs), False,
        ))
    return plan


def send(base_url: str, token: str, method: str, path: str, body: dict) -> tuple:
    """Return (status, response text); raise SetupError on network failure."""
    request = urllib.request.Request(
        base_url.rstrip("/") + path,
        data=json.dumps(body).encode("utf-8"),
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as err:
        return err.code, err.read().decode("utf-8", "replace")
    except urllib.error.URLError as err:
        raise SetupError(f"{method} {path} failed: {err.reason}", EXIT_REMOTE)
    except OSError as err:
        raise SetupError(f"{method} {path} failed: {err}", EXIT_REMOTE)


def outcome(method: str, status: int, text: str, tolerate_exists: bool) -> str:
    if status in (200, 201):
        return "created" if method == "POST" else "applied"
    if status == 409 and tolerate_exists and "already exists" in text.lower():
        return "exists"
    raise SetupError(f"HTTP {status} {text[:300]}", EXIT_REMOTE)


def cmd_apply(args) -> None:
    plan = build_plan(load_team(args.team))
    if args.dry_run:
        for label, method, path, _, _ in plan:
            print(f"plan: {label} ({method} {path})")
        return
    base_url = os.environ.get("AGENTHUB_URL", "")
    token = os.environ.get("AGENTHUB_TOKEN", "")
    for name, value in (("AGENTHUB_URL", base_url), ("AGENTHUB_TOKEN", token)):
        if not value:
            raise SetupError(f"{name} is not set", EXIT_USAGE)
    for label, method, path, body, tolerate_exists in plan:
        status, text = send(base_url, token, method, path, body)
        try:
            result = outcome(method, status, text, tolerate_exists)
        except SetupError as err:
            raise SetupError(f"{label}: {method} {path}: {err}", err.code)
        print(f"{label}: {result}")


def main(argv: list = None) -> int:
    parser = argparse.ArgumentParser(
        prog="openrig_team_setup.py",
        description="Create the 4genthub development team as an OpenRig room.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    apply = subparsers.add_parser("apply", help="create modules, room, seats, links, overlays")
    apply.add_argument("--dry-run", action="store_true", help="print the plan, call nothing")
    apply.add_argument("--team", type=Path, default=DEFAULT_TEAM_DIR, help="team definition directory")
    apply.set_defaults(func=cmd_apply)

    args = parser.parse_args(argv)
    try:
        args.func(args)
    except SetupError as err:
        print(f"error: {err}", file=sys.stderr)
        return err.code
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
