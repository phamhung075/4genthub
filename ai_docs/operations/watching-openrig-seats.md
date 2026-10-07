# Watching OpenRig seats

How to see what each seat of a rig is doing: every tool call and its result, per seat, live.
Read-only. It reads the seats' session logs and never talks to a seat.

Tool: `scripts/openrig_watch_tools.py`. Needs `herdr` for the grid view.

**Standing choice (owner, 2026-10-07):** after restoring or spawning a team, watch it with `grid`
(below), not with `rig terminal open` tiles. The `spawn-team` skill records the same rule.

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

Each pane is named after its seat (herdr pane title) and starts with a `== seat ==` header; its lines carry no seat name, to save width. The merged `feed` (several seats in one stream) still puts the seat name on every line.

Options: `--rig <name>` (default `4genthub-min`), `--cols N`, `--back N` (events replayed per seat
at start, default 40; a pane holds only what was printed since it started, so raise this to see older work), `--width N` (characters kept of each line, default 200), `--lines N` (lines shown of each call, result or message, default 25).

Run it again for a fresh grid. It does not reuse or close an earlier one; close the old workspace
in herdr (`herdr workspace close <id>`).

## Input panes: type to a seat from the grid (optional)

The grid panes are read-only. To talk to a seat from the grid, open a small input pane under each seat pane:

```bash
python3 scripts/openrig_watch_tools.py inputs open    # one "<seat> > input" pane under every seat pane
python3 scripts/openrig_watch_tools.py inputs open --seat lead   # only the lead gets one
python3 scripts/openrig_watch_tools.py inputs hide    # close them again; the grid is back to watch-only
```

A line typed in an input pane is sent to that seat with `rig send <rig>-<seat>@<rig>`; `/hide` or Ctrl-D leaves the loop.
Opening twice adds nothing. Keep backticks, apostrophes and `$` out of a message: `rig send` mangles them.
The inputs are off by default; the grid itself never writes to a seat.

## Feed: one merged stream

```bash
python3 scripts/openrig_watch_tools.py feed [--seat go-dev reviewer] [--back 5] [--width 170] [--lines 25]
```

All seats interleaved in one terminal; `--seat` limits it. Useful over ssh or without herdr.

## Scrolling back

herdr keeps 10 MB of scrollback per pane. Scroll with the mouse wheel (3 lines a notch) or the scrollbar; or press `prefix+[` for copy mode and use `PageUp`/`PageDown`, `q` or `Esc` to leave. Output stays live and follows the bottom. Settings (`~/.config/herdr/config.toml`): `[ui] mouse_scroll_lines`, `mouse_capture`, `pane_scrollbars`; `[advanced] scrollback_limit_bytes`. Older work than the replay is not in the pane: start the grid with a larger `--back`.

## Detail: reasoning, what the agent says, what it is told

`grid` shows it by default; for `feed` add `--detail`. Three more kinds of line:

| Mark | Meaning |
|---|---|
| `~ think` (light purple italic) | the agent's reasoning before it acts |
| `▸ say` (bold) | what the agent writes back (single-character replies are skipped) |
| `◂ in` (light cyan) | a message the agent received: the owner, another seat, a system notice |

**What OpenRig already shows, and what this adds.** OpenRig's own views (`rig transcript`, `rig ask`, `rig terminal open`, the UI's transcript drill-in) read the seat's pane, which the omp runner fills with the assistant's text, one-line tool summaries, incoming messages, compaction and errors. They do not carry the reasoning or a tool's full arguments and result; those exist only in the seat's session log, which this tool reads. Use OpenRig's views for the conversation, this one for the reasoning and tool detail.

## Reading a line

```
21:01:20 lead   → bash (+cwd, timeout) command=cd /home/daihu/…
                rig queue list --json
21:01:20 lead   ← {
                  "success": true,
                  …
21:01:20 lead   ← Sent to 4genthub-min-reviewer@4genthub-min
```

| Mark | Meaning |
|---|---|
| `→ tool key=value` | a tool call; `(+a, b)` lists arguments that are not shown |
| `← text` | the tool's result, dim |
| `✗ text` | an error result, red |
| `✗ BLOCKED` (white on a red block) | the seat's policy refused the call (`scripts/openrig_seat_policy.py`) |
| indented lines below a mark | the rest of that call, result or message, as real lines; a compact JSON result is shown indented |
| `… +N more lines` | N lines beyond `--lines` were not shown (nothing is dropped silently) |

All colours are light 256-colour tones chosen for a black terminal background; none uses the dim style or the dark ANSI blues and magentas (change the palette at the top of the script).

Tool colours: read, grep, find, ls light blue; write, edit yellow; bash, eval green; `mcp__*` (4genthub,
deepseek) pink. The timestamp is when the viewer printed the line, not when the seat ran it, so
the replayed lines at start all share one time.

## Notes

- The viewer follows each seat's newest file in `~/.openrig/state/omp/<rig>-<seat>@<rig>/sessions/`.
  A seat that restarts starts a new file and the viewer switches to it.
- A seat's own screen (not its tool calls) is a different tool: `rig terminal open <rig>` opens one
  tile per seat in herdr.
- Seats other than omp seats have no such log, so they do not appear.

## One command: grid plus lead window

```bash
python3 scripts/openrig_watch_tools.py watch --rig 4genthub-min
```

Opens the seat grid and a `<rig> lead` workspace: the lead's detailed feed on top, a `lead > input` pane below
(a line typed there goes to the lead with `rig send`). Never type or press Ctrl-C in a raw `tmux attach` pane of a seat.
