# Watching OpenRig seats

How to see what each seat of a rig is doing: every tool call and its result, per seat, live.
Read-only. It reads the seats' session logs and never talks to a seat.

Tool: the watch view in the `agenthub_client` package (`agenthub_client/src/agenthub_client/watch.py`), run through the console script as `4genteam watch`. Needs `herdr` for the grid view.

**Standing choice (owner, 2026-10-07):** after restoring or spawning a team, watch it with `grid`
(below), not with `rig terminal open` tiles. The `spawn-team` skill records the same rule.

## Grid: one pane per seat (the usual way)

```bash
4genteam grid
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

Run it again for a fresh grid: it closes the rig's earlier `<rig> grid` workspace first, then rebuilds it.

## Input panes: type to a seat from the grid (optional)

The grid panes are read-only. To talk to a seat from the grid, open a small input pane under each seat pane:

```bash
4genteam inputs open    # one "<seat> > input" pane under every seat pane
4genteam inputs open --seat lead   # only the lead gets one
4genteam inputs hide    # close them again; the grid is back to watch-only
```

A line typed in an input pane is sent to that seat with `rig send <rig>-<seat>@<rig>`; `/hide` or Ctrl-D leaves the loop.
Opening twice adds nothing. Keep backticks, apostrophes and `$` out of a message: `rig send` mangles them.
The inputs are off by default; the grid itself never writes to a seat.

## Feed: one merged stream

```bash
4genteam feed [--seat go-dev reviewer] [--back 5] [--width 170] [--lines 25]
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
| `✗ BLOCKED` (white on a red block) | the seat's policy refused the call (`agenthub_client/src/agenthub_client/seat_policy.py`) |
| indented lines below a mark | the rest of that call, result or message, as real lines; a compact JSON result is shown indented |
| `… +N more lines` | N lines beyond `--lines` were not shown (nothing is dropped silently) |

All colours are light 256-colour tones chosen for a black terminal background; none uses the dim style or the dark ANSI blues and magentas (change the palette at the top of the module).

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
4genteam watch --rig 4genthub-min
```

Opens the seat grid and a `<rig> lead` workspace: the lead's detailed feed on top, a `lead > input` pane below
(a line typed there goes to the lead with `rig send`). Never type or press Ctrl-C in a raw `tmux attach` pane of a seat.

## Same style on every relaunch, resume or runtime switch

`watch` is the one entry point and it is idempotent: it closes the rig's earlier `<rig> grid` and `<rig> lead` workspaces, then rebuilds both with the same layout (2 columns, `--back 40 --width 200 --lines 60 --detail`, seat name + model + token bar in each pane, the lead window with its input pane). The layout lives in the module, not in a saved herdr state, so it cannot drift.

- `~/.openrig/bin/rig-continue.sh <rig>` opens it at the end of every restore, as `4genteam watch watch --rig <rig>` (skip the wall with `RIG_CONTINUE_WATCH=0`).
- After `rig up` or a runtime switch (`rig-runtime-switch` skill, step 10) run it by hand: `4genteam watch --rig <rig>`.
- **A running pane never picks up a code change.** Each pane is a Python process that read `agenthub_client/src/agenthub_client/watch.py` when it started, so an edited constant (for example `COMPACT_LIMIT`, the `/150k` in each token bar) shows only after the panes are rebuilt: run `4genteam watch --rig <rig>` again. The compaction supervisor (`agenthub_client/src/agenthub_client/compact.py`, run as `4genteam compact-run`) has the same property: restart it after editing the limit or its `--quiet` default.
- Panes are matched to seats by tmux session name (`<rig>-<seat>@<rig>`), so a seat that changes LLM keeps its pane; the model in the header follows the seat's newest log. A runtime with no log reader (Codex, agy) keeps the pane and header but shows no events.

**2026-10-09: every command above was rewritten from the `scripts/openrig_*.py` form.** Those eight scripts were relocated into the `agenthub_client` package and no longer exist on disk; the invocation is the console script `4genteam` (a symlink at `~/.local/bin/4genteam` to the installed client), whose verbs this document now uses (`4genteam grid`, `feed`, `inputs …`, `watch`). The old `WATCH_TOOL` override the previous version of this bullet named was removed from `rig-continue.sh` at the same time, so the bullet now states what that launcher does instead of naming a variable it no longer has.
