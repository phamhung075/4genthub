# Watching OpenRig seats

How to see what each seat of a rig is doing: every tool call and its result, per seat, live.
Read-only. It reads the seats' session logs and never talks to a seat.

Tool: `scripts/openrig_watch_tools.py`. Needs `herdr` for the grid view.

## Grid: one pane per seat (the usual way)

```bash
python3 scripts/openrig_watch_tools.py grid
```

Creates a herdr workspace named `<rig> grid` and focuses it. Seats are sorted by name and fill the
columns top to bottom, left to right. With the default 2 columns for `4genthub-min`:

| Left | Right |
|---|---|
| context-dev | lead |
| fe-dev | reviewer |
| feedback-dev | skills-dev |
| go-dev | web-dev |
| go-dev2 | writer |

Every line carries the seat name, so the position never matters.

Options: `--rig <name>` (default `4genthub-min`), `--cols N`, `--back N` (events replayed per seat
at start, default 4), `--width N` (characters of each command or result, default 110).

Run it again for a fresh grid. It does not reuse or close an earlier one; close the old workspace
in herdr (`herdr workspace close <id>`).

## Feed: one merged stream

```bash
python3 scripts/openrig_watch_tools.py feed [--seat go-dev reviewer] [--back 5] [--width 170]
```

All seats interleaved in one terminal; `--seat` limits it. Useful over ssh or without herdr.

## Reading a line

```
21:01:20 lead   → bash command=cd … ⏎ rig queue … (+cwd, timeout)
21:01:20 lead   ← Sent to 4genthub-min-reviewer@4genthub-min
```

| Mark | Meaning |
|---|---|
| `→ tool key=value` | a tool call; `(+a, b)` lists arguments that are not shown |
| `← text` | the tool's result, dim |
| `✗ text` | an error result, red |
| `✗ BLOCKED` (white on red) | the seat's policy refused the call (`scripts/openrig_seat_policy.py`) |
| `⏎` | a line break inside a command or result |

Tool colours: read, grep, find, ls blue; write, edit yellow; bash, eval green; `mcp__*` (4genthub,
deepseek) magenta. The timestamp is when the viewer printed the line, not when the seat ran it, so
the replayed lines at start all share one time.

## Notes

- The viewer follows each seat's newest file in `~/.openrig/state/omp/<rig>-<seat>@<rig>/sessions/`.
  A seat that restarts starts a new file and the viewer switches to it.
- A seat's own screen (not its tool calls) is a different tool: `rig terminal open <rig>` opens one
  tile per seat in herdr.
- Seats other than omp seats have no such log, so they do not appear.
