#!/usr/bin/env python3
"""Create the 4genthub development team as an OpenRig room through the 4genthub API.

The team definition (room, seats, links, context modules, overlays) is data in
``scripts/team/4genthub/team.json``; the module texts are the files next to it.
``apply`` pushes that definition in a fixed order and is idempotent::

    1. seat types        POST /api/v2/openrig/seat-types/seed        (the seats need them;
                         idempotent, the server needs AGENTHUB_PUBLIC_URL)
    2. context modules   PUT  /api/v2/openrig/modules/{slug}/versions/{version}
    3. room              POST /api/v2/openrig/rooms                  (409 exists: ok)
    4. seats             POST /api/v2/openrig/rooms/{room}/seats     (409 exists: ok)
    5. links             PUT  /api/v2/openrig/rooms/{room}/seats/{seat}/links
    6. company overlay   PUT  /api/v2/openrig/overlay
    7. seat overlays     PUT  /api/v2/openrig/rooms/{room}/seats/{seat}/overlay

Overlay PUTs replace the previous overlay of their scope, so the full op list is
sent every time. Any other HTTP error stops the run.

``import-project`` reads the current project's local Claude configuration and pushes
it as module versions through the same ``PUT`` call ``apply`` uses::

  1. .mcp.json         one ``mcp`` module per server entry (name, type http|stdio,
                       url, or command + args, headers/env)
  2. .claude/skills/*  one ``skill`` module per directory, content = SKILL.md

The project root is the one the Claude-code hooks derive, imported from
``utils/env_loader.get_project_root`` (never re-derived here). A block never carries a
secret value: a credential-shaped literal is refused with a clear message, while a value
that names ``${ENV_VAR}`` is stored verbatim for the client runtime to expand.

Environment:
  AGENTHUB_URL    base URL of the 4genthub server, e.g. https://api.4genthub.com
  AGENTHUB_TOKEN  bearer token; sent as an Authorization header, never printed.

Usage:
  openrig_team_setup.py apply [--dry-run] [--team DIR]
  openrig_team_setup.py import-project [--dry-run] [--version X.Y.Z]

``--dry-run`` prints the plan without calling the API and needs no environment.

Exit codes:
  0  success
  1  network or HTTP error
  2  usage or configuration error
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Sibling client-side helpers live next to this script; the Claude-code hooks live under the
# repository's .claude. The hooks' env_loader owns the one project-root derivation, so this
# script imports it instead of computing a second "project root" of its own.
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
from openrig_scrub import scrub  # noqa: E402

_HOOKS_DIR = _SCRIPTS_DIR.parent / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))
from utils.env_loader import get_project_root  # noqa: E402

DEFAULT_TEAM_DIR = Path(__file__).resolve().parent / "team" / "4genthub"
API = "/api/v2/openrig"

EXIT_OK = 0
EXIT_REMOTE = 1
EXIT_USAGE = 2

IMPORT_VERSION = "1.0.0"
MCP_CONFIG = ".mcp.json"
SKILLS_DIR = Path(".claude") / "skills"
SKILL_FILE = "SKILL.md"

# A ${ENV_VAR} reference is expanded by the client runtime and is never a stored secret.
_ENV_REFERENCE = re.compile(r"\$\{[A-Za-z_][A-Za-z0-9_]*\}")
_MODULE_SLUG = re.compile(r"[a-z][a-z0-9-]*")


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


def module_step(slug: str, kind: str, version: str, content: str) -> tuple:
    """One module-version PUT: the single shape both apply and import-project push."""
    return (
        f"module {slug}@{version}", "PUT",
        f"{API}/modules/{slug}/versions/{version}",
        {"kind": kind, "content": content}, False,
    )


def module_steps(modules: list, version: str) -> list:
    """The ordered module-version PUT steps for slug/kind/content records."""
    return [module_step(m["slug"], m["kind"], version, m["content"]) for m in modules]


def _refuse_secret(label: str, value: str) -> None:
    """Fail on a credential-shaped literal; ${ENV_VAR} references are allowed through."""
    if scrub(_ENV_REFERENCE.sub("", value), {})[1]:
        raise SetupError(
            f"{label}: carries a credential-shaped value; reference the secret as "
            "${ENV_VAR} instead of writing it into the module",
            EXIT_USAGE,
        )


def _module_slug(name: str, what: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not _MODULE_SLUG.fullmatch(slug):
        raise SetupError(
            f"{what} {name!r} does not yield a module slug matching ^[a-z][a-z0-9-]*$ "
            f"(got {slug!r})",
            EXIT_USAGE,
        )
    return slug


def _refuse_block_secrets(name: str, block: dict) -> None:
    def check(field: str, value: str) -> None:
        _refuse_secret(f"mcp server {name!r} {field}", value)

    for field in ("url", "command"):
        if field in block:
            check(field, block[field])
    for index, arg in enumerate(block.get("args", [])):
        check(f"args[{index}]", arg)
    for field in ("headers", "env"):
        for key, value in block.get(field, {}).items():
            check(f"{field}.{key}", value)


def _mcp_block(name: str, entry) -> dict:
    """One .mcp.json server entry as the backend's mcp block payload."""
    if not isinstance(entry, dict):
        raise SetupError(f"mcp server {name!r} must be an object", EXIT_USAGE)
    server_type = entry.get("type")
    if server_type not in ("http", "stdio"):
        if "url" in entry and "command" not in entry:
            server_type = "http"
        elif "command" in entry and "url" not in entry:
            server_type = "stdio"
        else:
            raise SetupError(
                f"mcp server {name!r}: type must be \"http\" or \"stdio\", or be "
                "inferable from url / command",
                EXIT_USAGE,
            )
    block = {"name": name, "type": server_type}
    if server_type == "http":
        url = entry.get("url")
        if not isinstance(url, str) or not url:
            raise SetupError(f"mcp server {name!r}: an http server needs a url", EXIT_USAGE)
        block["url"] = url
    else:
        command = entry.get("command")
        if not isinstance(command, str) or not command:
            raise SetupError(f"mcp server {name!r}: a stdio server needs a command", EXIT_USAGE)
        block["command"] = command
        args = entry.get("args")
        if args:
            if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
                raise SetupError(f"mcp server {name!r}: args must be an array of strings", EXIT_USAGE)
            block["args"] = args
    for field in ("headers", "env"):
        values = entry.get(field)
        if not values:
            continue
        if not isinstance(values, dict) or not all(isinstance(v, str) for v in values.values()):
            raise SetupError(f"mcp server {name!r}: {field} must be an object of strings", EXIT_USAGE)
        if server_type == "http" and field == "env":
            raise SetupError(f"mcp server {name!r}: an http server takes headers, not env", EXIT_USAGE)
        if server_type == "stdio" and field == "headers":
            raise SetupError(f"mcp server {name!r}: a stdio server takes env, not headers", EXIT_USAGE)
        block[field] = values
    _refuse_block_secrets(name, block)
    return block


def mcp_modules(project_root: Path) -> list:
    """One mcp module per .mcp.json server entry; [] when there is no config."""
    config_path = project_root / MCP_CONFIG
    if not config_path.exists():
        return []
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        raise SetupError(f"cannot read {config_path}: {err}", EXIT_USAGE)
    servers = config.get("mcpServers") if isinstance(config, dict) else None
    if servers is None:
        return []
    if not isinstance(servers, dict):
        raise SetupError(f"{config_path}: mcpServers must be an object", EXIT_USAGE)
    modules = []
    for name in sorted(servers):
        block = _mcp_block(name, servers[name])
        modules.append({
            "slug": _module_slug(name, "mcp server"),
            "kind": "mcp",
            "content": json.dumps(block, indent=2),
        })
    return modules


def skill_modules(project_root: Path) -> list:
    """One skill module per .claude/skills directory, content = its SKILL.md."""
    skills_dir = project_root / SKILLS_DIR
    if not skills_dir.is_dir():
        return []
    modules = []
    for entry in sorted(skills_dir.iterdir()):
        if not entry.is_dir():
            continue
        skill_file = entry / SKILL_FILE
        if not skill_file.is_file():
            raise SetupError(f"skill {entry.name!r}: {skill_file} is missing", EXIT_USAGE)
        try:
            content = skill_file.read_text(encoding="utf-8")
        except OSError as err:
            raise SetupError(f"cannot read {skill_file}: {err}", EXIT_USAGE)
        _refuse_secret(f"skill {entry.name!r}", content)
        modules.append({
            "slug": _module_slug(entry.name, "skill"),
            "kind": "skill",
            "content": content,
        })
    return modules


def project_modules(project_root: Path) -> list:
    """Every module the project's local Claude configuration imports."""
    modules = mcp_modules(project_root) + skill_modules(project_root)
    slugs = [m["slug"] for m in modules]
    duplicates = sorted({slug for slug in slugs if slugs.count(slug) > 1})
    if duplicates:
        raise SetupError(
            f"module slug(s) {', '.join(duplicates)} are produced by more than one import entry",
            EXIT_USAGE,
        )
    return modules


def build_plan(team: dict) -> list:
    """Return the ordered steps: (label, method, path, body, tolerate_exists)."""
    room = team["room"]["slug"]
    seats_path = f"{API}/rooms/{room}/seats"
    plan = [("seat types (seed)", "POST", f"{API}/seat-types/seed", {}, False)]
    for m in team["modules"]:
        plan.append(module_step(m["slug"], m["kind"], m["version"], m["content"]))
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


def run_steps(steps: list, dry_run: bool) -> None:
    """Print a dry-run plan, or send every step in order and report each outcome."""
    if dry_run:
        for label, method, path, _, _ in steps:
            print(f"plan: {label} ({method} {path})")
        return
    base_url = os.environ.get("AGENTHUB_URL", "")
    token = os.environ.get("AGENTHUB_TOKEN", "")
    for name, value in (("AGENTHUB_URL", base_url), ("AGENTHUB_TOKEN", token)):
        if not value:
            raise SetupError(f"{name} is not set", EXIT_USAGE)
    for label, method, path, body, tolerate_exists in steps:
        status, text = send(base_url, token, method, path, body)
        try:
            result = outcome(method, status, text, tolerate_exists)
        except SetupError as err:
            raise SetupError(f"{label}: {method} {path}: {err}", err.code)
        print(f"{label}: {result}")


def cmd_apply(args) -> None:
    run_steps(build_plan(load_team(args.team)), args.dry_run)


def cmd_import_project(args) -> None:
    root = get_project_root()  # the Claude-code hooks' derivation, not a second one
    modules = project_modules(root)
    steps = module_steps(modules, args.version)
    if args.dry_run:
        print(f"plan: import-project from {root} ({len(steps)} module(s))")
    else:
        print(f"importing {len(steps)} module(s) from {root}")
    run_steps(steps, args.dry_run)


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
    import_project = subparsers.add_parser(
        "import-project",
        help="push .mcp.json servers and .claude/skills as module versions",
    )
    import_project.add_argument("--dry-run", action="store_true", help="print the plan, call nothing")
    import_project.add_argument(
        "--version", default=IMPORT_VERSION, help="module version to publish (default 1.0.0)"
    )
    import_project.set_defaults(func=cmd_import_project)

    args = parser.parse_args(argv)
    try:
        args.func(args)
    except SetupError as err:
        print(f"error: {err}", file=sys.stderr)
        return err.code
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
