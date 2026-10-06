#!/usr/bin/env python3
"""Live tool-call feed for the omp seats of an OpenRig rig. Read-only.

    openrig_watch_tools.py feed [--rig R] [--seat S ...] [--back N] [--width W]
        one merged stream: a line per tool call and per result, coloured by tool kind
    openrig_watch_tools.py grid [--rig R] [--cols 2] [--back N] [--width W]
        a new herdr workspace with one pane per seat, each running its own ``feed``

The feed reads each seat's newest session jsonl under ~/.openrig/state/omp and follows it.
A policy refusal is shown white-on-red. See ai_docs/operations/watching-openrig-seats.md.
"""

import argparse
import json
import os
import subprocess
import time
from pathlib import Path

ROOT = Path.home() / ".openrig" / "state" / "omp"
COLORS = [31, 32, 33, 34, 35, 36, 91, 92, 93, 94]
RESET = "\033[0m"
# tool name -> colour: reads blue, writes yellow, shell green, MCP magenta, anything else white
TOOL_COLORS = {
    "read": 34,
    "grep": 34,
    "find": 34,
    "ls": 34,
    "search": 34,
    "write": 33,
    "edit": 33,
    "ast_edit": 33,
    "bash": 32,
    "eval": 32,
}


def newest_session(seat_dir: Path):
    files = list((seat_dir / "sessions").glob("*.jsonl"))
    return max(files, key=lambda f: f.stat().st_mtime, default=None)


def brief(args, width: int) -> str:
    if not isinstance(args, dict):
        return str(args)[:width]
    for key in ("command", "path", "intent", "prompt", "code"):
        if key in args:
            text = str(args[key]).replace("\n", " ⏎ ")
            extra = (
                ""
                if len(args) == 1
                else f" (+{', '.join(k for k in args if k != key)})"
            )
            return f"{key}={text[:width]}{extra}"
    return json.dumps(args)[:width]


def events(line: str, width: int):
    try:
        msg = json.loads(line).get("message") or {}
    except json.JSONDecodeError:
        return
    content = msg.get("content")
    if msg.get("role") == "toolResult":
        text = " ".join(p.get("text", "") for p in content or [] if isinstance(p, dict))
        body = text.replace(chr(10), " ⏎ ")[:width]
        if text.startswith("Tool ") and "is blocked by tool policy" in text[:120]:
            yield f"\033[1;97;41m ✗ BLOCKED {RESET} \033[91m{body}{RESET}"
        elif msg.get("isError"):
            yield f"\033[1;91m✗ {body}{RESET}"
        else:
            yield f"\033[2m← {body}{RESET}"
    elif isinstance(content, list):
        for part in content:
            if isinstance(part, dict) and part.get("type") == "toolCall":
                name = part.get("name") or "?"
                code = 35 if name.startswith("mcp__") else TOOL_COLORS.get(name, 97)
                yield f"\033[1;{code}m→ {name}{RESET} {brief(part.get('arguments'), width)}"


def rig_seats(rig: str) -> list[str]:
    return sorted(
        d.name.removeprefix(f"{rig}-").removesuffix(f"@{rig}")
        for d in ROOT.glob(f"{rig}-*@{rig}")
    )


def herdr(*args: str) -> dict:
    """Run a herdr API command; send-text and send-keys print nothing."""
    out = subprocess.run(
        ["herdr", *args], capture_output=True, text=True, check=True
    ).stdout
    return json.loads(out)["result"] if out.strip() else {}


def pane_id(result: dict) -> str:
    return (result.get("pane") or result["root_pane"])["pane_id"]


def grid(a: argparse.Namespace) -> None:
    """One pane per seat. Columns are split first, then each column into equal rows."""
    seats = rig_seats(a.rig)
    cwd = str(Path(__file__).resolve().parent)
    root = herdr("workspace", "create", "--cwd", cwd, "--label", f"{a.rig} grid")[
        "root_pane"
    ]["pane_id"]

    def split(pane: str, direction: str, ratio: float) -> str:
        return pane_id(
            herdr(
                "pane",
                "split",
                "--pane",
                pane,
                "--direction",
                direction,
                "--ratio",
                f"{ratio:.3f}",
                "--cwd",
                cwd,
            )
        )

    heads = [root]
    for left in range(a.cols - 1, 0, -1):
        heads.append(split(heads[-1], "right", 1 / (left + 1)))
    per_col = -(-len(seats) // a.cols)
    panes = []
    for head in heads:
        cur = head
        panes.append(cur)
        for left in range(per_col - 1, 0, -1):
            cur = split(cur, "down", 1 / (left + 1))
            panes.append(cur)
    me = Path(__file__).resolve()
    for pane, seat in zip(panes, seats):
        cmd = f"python3 {me} feed --rig {a.rig} --seat {seat} --back {a.back} --width {a.width}"
        herdr("pane", "send-text", pane, cmd)
        herdr("pane", "send-keys", pane, "Enter")
    herdr("workspace", "focus", root.split(":")[0])
    print(f"grid: {len(seats)} seats in {a.cols} columns")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    for name, fn in (("feed", feed), ("grid", grid)):
        p = sub.add_parser(name)
        p.add_argument("--rig", default="4genthub-min")
        p.add_argument("--back", type=int, default=3 if name == "feed" else 4)
        p.add_argument("--width", type=int, default=170 if name == "feed" else 110)
        if name == "feed":
            p.add_argument("--seat", nargs="*")
        else:
            p.add_argument("--cols", type=int, default=2)
        p.set_defaults(func=fn)
    a = ap.parse_args()
    a.func(a)


def feed(a: argparse.Namespace) -> None:
    seats = rig_seats(a.rig)
    if a.seat:
        seats = [s for s in seats if s in a.seat]
    color = {s: COLORS[i % len(COLORS)] for i, s in enumerate(seats)}
    pos: dict[str, tuple[Path, int]] = {}

    def show(seat, line):
        stamp = time.strftime("%H:%M:%S")
        for text in events(line, a.width):
            print(
                f"\033[2m{stamp}\033[0m \033[1;{color[seat]}m{seat:<12}{RESET} {text}",
                flush=True,
            )

    for seat in seats:
        f = newest_session(ROOT / f"{a.rig}-{seat}@{a.rig}")
        if f is None:
            continue
        lines = f.read_text().splitlines()
        shown = [ln for ln in lines if any(True for _ in events(ln, 1))][-a.back * 2 :]
        for ln in shown:
            show(seat, ln)
        pos[seat] = (f, f.stat().st_size)
    print(f"-- following {len(seats)} seats; Ctrl-C to stop", flush=True)
    while True:
        for seat in seats:
            f = newest_session(ROOT / f"{a.rig}-{seat}@{a.rig}")
            if f is None:
                continue
            old, off = pos.get(seat, (f, 0))
            if f != old:
                off = 0
            size = f.stat().st_size
            if size > off:
                with open(f, "rb") as fh:
                    fh.seek(off)
                    chunk = fh.read(size - off).decode(errors="replace")
                for ln in chunk.splitlines():
                    show(seat, ln)
            pos[seat] = (f, size)
        time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        os._exit(0)
