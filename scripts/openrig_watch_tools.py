#!/usr/bin/env python3
"""Live tool-call feed for the omp seats of an OpenRig rig. The feed is read-only.

    openrig_watch_tools.py feed [--rig R] [--seat S ...] [--back N] [--width W] [--lines L]
        one merged stream: a line per tool call and per result, coloured by tool kind
    openrig_watch_tools.py grid [--rig R] [--cols 2] [--back N] [--width W] [--lines L]
        a new herdr workspace with one pane per seat, each running its own ``feed``
    openrig_watch_tools.py inputs open|hide [--rig R] [--seat S ...]
        open or hide a small input pane under each seat pane of the grid; a line typed
        there is sent to that seat with ``rig send`` (the grid itself stays read-only)

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
RESET = "\033[0m"
BOLD = "\033[1m"


def fg(code: int) -> str:
    """256-colour foreground. Every colour below is a light one: readable on a black background."""
    return f"\033[38;5;{code}m"


SEAT_COLORS = [203, 114, 221, 75, 213, 87, 215, 183, 120, 229]
MCP_COLOR = 213
DEFAULT_TOOL_COLOR = 255
RESULT_COLOR = 249
STAMP_COLOR = 245
# tool name -> colour: reads blue, writes yellow, shell green, MCP magenta, anything else white
TOOL_COLORS = {
    "read": 117,
    "grep": 117,
    "find": 117,
    "ls": 117,
    "search": 117,
    "write": 221,
    "edit": 221,
    "ast_edit": 221,
    "bash": 120,
    "eval": 120,
}


def newest_session(seat_dir: Path):
    files = list((seat_dir / "sessions").glob("*.jsonl"))
    return max(files, key=lambda f: f.stat().st_mtime, default=None)


def pretty(text: str) -> str:
    """A result that is JSON (compact or not) is shown indented; anything else as it is."""
    stripped = text.strip()
    if stripped[:1] in "{[":
        try:
            return json.dumps(json.loads(stripped), indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            pass
    return text


def block(head: str, style: str, text: str, width: int, lines: int) -> str:
    """``head`` then ``text`` as real lines: the first beside the head, the rest indented.

    Each line is cut at ``width`` characters and at most ``lines`` lines are shown; what is hidden
    is counted, never silently dropped.
    """
    rows = text.rstrip().splitlines() or [""]
    out = [f"{head}{style}{rows[0][:width]}{RESET}"]
    out += [f"    {style}{row[:width]}{RESET}" for row in rows[1:lines]]
    if len(rows) > lines:
        out.append(f"    {fg(STAMP_COLOR)}… +{len(rows) - lines} more lines{RESET}")
    return "\n".join(out)


def call_body(args) -> tuple[str, str]:
    """(names of the arguments not shown, the main argument as text)."""
    if not isinstance(args, dict):
        return "", str(args)
    for key in ("command", "path", "intent", "prompt", "code"):
        if key in args:
            others = [k for k in args if k != key]
            extra = f" (+{', '.join(others)})" if others else ""
            return extra, f"{key}={args[key]}"
    return "", json.dumps(args, indent=2, ensure_ascii=False)


def detail_lines(role: str | None, part: dict, width: int, lines: int):
    """Reasoning, what the agent says, and what it is told: the parts OpenRig's own view omits."""
    kind = part.get("type")
    if role == "assistant" and kind == "thinking":
        text = str(part.get("thinking", "")).strip()
        if text:
            yield block(
                f"{BOLD}{fg(183)}~ think {RESET}",
                f"{fg(183)}\033[3m",
                text,
                width,
                lines,
            )
    elif role == "assistant" and kind == "text":
        text = str(part.get("text", "")).strip()
        if len(text) > 1:
            yield block(f"{BOLD}{fg(231)}▸ say {RESET}", fg(255), text, width, lines)
    elif role == "user" and kind == "text":
        text = str(part.get("text", "")).strip()
        if text:
            yield block(f"{BOLD}{fg(87)}◂ in {RESET}", fg(123), text, width, lines)


def events(line: str, width: int, detail: bool = False, lines: int = 25):
    try:
        msg = json.loads(line).get("message") or {}
    except json.JSONDecodeError:
        return
    content = msg.get("content")
    if msg.get("role") == "toolResult":
        text = " ".join(p.get("text", "") for p in content or [] if isinstance(p, dict))
        body = pretty(text)
        if text.startswith("Tool ") and "is blocked by tool policy" in text[:120]:
            head = f"\033[1;38;5;231;48;5;160m ✗ BLOCKED {RESET} "
            yield block(head, fg(210), body, width, lines)
        elif msg.get("isError"):
            yield block(f"{BOLD}{fg(203)}✗ {RESET}", fg(203), body, width, lines)
        else:
            yield block(
                f"{fg(RESULT_COLOR)}← {RESET}", fg(RESULT_COLOR), body, width, lines
            )
    elif isinstance(content, list):
        for part in content:
            if detail and isinstance(part, dict):
                yield from detail_lines(msg.get("role"), part, width, lines)
            if isinstance(part, dict) and part.get("type") == "toolCall":
                name = part.get("name") or "?"
                code = (
                    MCP_COLOR
                    if name.startswith("mcp__")
                    else TOOL_COLORS.get(name, DEFAULT_TOOL_COLOR)
                )
                extra, body = call_body(part.get("arguments"))
                head = f"{BOLD}{fg(code)}→ {name}{extra}{RESET} "
                yield block(head, fg(255), body, width, lines)


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
        cmd = (
            f"python3 {me} feed --rig {a.rig} --seat {seat} --back {a.back} --width {a.width}"
            + f" --lines {a.lines}"
            + (" --detail" if a.detail else "")
        )
        herdr("pane", "rename", pane, seat)
        herdr("pane", "send-text", pane, cmd)
        herdr("pane", "send-keys", pane, "Enter")
    herdr("workspace", "focus", root.split(":")[0])
    print(f"grid: {len(seats)} seats in {a.cols} columns")


INPUT_SUFFIX = " > input"
INPUT_ROWS_RATIO = 0.65  # share of the seat pane that stays with the feed; the input needs rows to click on


def grid_workspace(rig: str) -> str:
    """The id of the newest ``<rig> grid`` workspace."""
    found = [
        w["workspace_id"]
        for w in herdr("workspace", "list")["workspaces"]
        if w["label"] == f"{rig} grid"
    ]
    if not found:
        raise SystemExit(f"no '{rig} grid' workspace: run grid first")
    return found[-1]


def grid_panes(rig: str) -> list[dict]:
    ws = grid_workspace(rig)
    return [p for p in herdr("pane", "list")["panes"] if p["workspace_id"] == ws]


def inputs(a: argparse.Namespace) -> None:
    """Open or hide the input pane under every seat pane of the grid."""
    panes = grid_panes(a.rig)
    seats = set(a.seat or rig_seats(a.rig))
    if a.action == "hide":
        closing = [p for p in panes if (p.get("label") or "").endswith(INPUT_SUFFIX)]
        for p in closing:
            herdr("pane", "close", p["pane_id"])
        print(f"inputs: hid {len(closing)}")
        return
    open_for = {p["label"] for p in panes if (p.get("label") or "").endswith(INPUT_SUFFIX)}
    me = Path(__file__).resolve()
    opened = 0
    for p in panes:
        seat = p.get("label")
        if seat not in seats or seat + INPUT_SUFFIX in open_for:
            continue
        new = pane_id(
            herdr(
                "pane", "split", "--pane", p["pane_id"], "--direction", "down",
                "--ratio", f"{INPUT_ROWS_RATIO:.3f}", "--cwd", str(me.parent),
            )
        )
        herdr("pane", "rename", new, seat + INPUT_SUFFIX)
        herdr("pane", "send-text", new, f"clear; exec python3 {me} input --rig {a.rig} --seat {seat}")
        herdr("pane", "send-keys", new, "Enter")
        opened += 1
    print(f"inputs: opened {opened}")


def input_loop(a: argparse.Namespace) -> None:
    """Read lines and send each to the seat. Empty line skips; Ctrl-D or /hide leaves."""
    target = f"{a.rig}-{a.seat}@{a.rig}"
    while True:
        try:
            line = input(f"{a.seat} > ").strip()
        except EOFError:
            return
        if line == "/hide":
            return
        if not line:
            continue
        done = subprocess.run(["rig", "send", target, line], capture_output=True, text=True)
        print("sent" if done.returncode == 0 else f"failed: {done.stderr.strip()[:200]}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    for name, fn in (("feed", feed), ("grid", grid)):
        p = sub.add_parser(name)
        p.add_argument("--rig", default="4genthub-min")
        p.add_argument("--back", type=int, default=3 if name == "feed" else 40)
        p.add_argument("--width", type=int, default=170 if name == "feed" else 200)
        p.add_argument("--lines", type=int, default=25)
        p.add_argument(
            "--detail",
            action="store_true",
            default=name == "grid",
            help="also show the agent's reasoning, what it says and what it is told (on for grid)",
        )
        if name == "feed":
            p.add_argument("--seat", nargs="*")
        else:
            p.add_argument("--cols", type=int, default=2)
        p.set_defaults(func=fn)
    p = sub.add_parser("inputs")
    p.add_argument("action", choices=("open", "hide"))
    p.add_argument("--rig", default="4genthub-min")
    p.add_argument("--seat", nargs="*", help="open: only these seats (default all)")
    p.set_defaults(func=inputs)
    p = sub.add_parser("input")
    p.add_argument("--rig", default="4genthub-min")
    p.add_argument("--seat", required=True)
    p.set_defaults(func=input_loop)
    a = ap.parse_args()
    a.func(a)


def feed(a: argparse.Namespace) -> None:
    seats = rig_seats(a.rig)
    if a.seat:
        seats = [s for s in seats if s in a.seat]
    color = {s: SEAT_COLORS[i % len(SEAT_COLORS)] for i, s in enumerate(seats)}
    pos: dict[str, tuple[Path, int]] = {}

    def show(seat, line):
        stamp = time.strftime("%H:%M:%S")
        # One seat in view (a grid pane): its name is the pane's title, not a column on every line.
        name = "" if len(seats) == 1 else f"{BOLD}{fg(color[seat])}{seat:<12}{RESET} "
        for text in events(line, a.width, a.detail, a.lines):
            print(f"{fg(STAMP_COLOR)}{stamp}{RESET} {name}{text}", flush=True)

    if len(seats) == 1:
        print(f"{BOLD}{fg(color[seats[0]])}== {seats[0]} =={RESET}", flush=True)
    else:
        print(f"-- following {len(seats)} seats; Ctrl-C to stop", flush=True)
    for seat in seats:
        f = newest_session(ROOT / f"{a.rig}-{seat}@{a.rig}")
        if f is None:
            continue
        lines = f.read_text().splitlines()
        shown = [
            ln for ln in lines if any(True for _ in events(ln, 1, a.detail, a.lines))
        ][-a.back * 2 :]
        for ln in shown:
            show(seat, ln)
        pos[seat] = (f, f.stat().st_size)
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
