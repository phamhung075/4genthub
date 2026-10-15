# The MCP tools are mounted, and a relaunch is what fixed it

**What this changes.** §3's measured state, item 8 of the 2026-10-14 20:2xZ block, said no seat has
the MCP tools, that `manage_task`/`manage_context` are unreachable from every seat and that "a
relaunch alone cannot fix it". The line is corrected in place, dated, with the re-measurement: the
nine `agenthub_http` tools **are** mounted, and a relaunch is what fixed it.

**Why it is not a cosmetic correction.** That sentence carries a live premise: §5's item 2 (the
overlays / `config.yml` unit) rests on it — "the seats run without their guide/policy skills *and*
without the MCP tools, which makes AGENTS.md §5's record-work duty unsatisfiable from every seat".
The tools leg of that premise is now false, which changes what the open unit is about.

**Measured 2026-10-15 18:0xZ, in the architect's own session:**

| Reading | Result |
|---|---|
| `find ~/.config/4genthub/rooms/4genthub-min/seats -maxdepth 3 -name mcp.json \| wc -l` | **5** — one per seat, each an `mcpServers` entry `agenthub_http` with a `url` |
| `find … -name config.yml` | **0**, unchanged — and not what the mount needs |
| `manage_task list` in this session | **30 rows returned** |
| `manage_task create`/`update` | two tasks live in the store (`096a3c36`, `01f75907`) |
| `manage_context add_insight`/`add_progress` | accepted |
| `manage_git_branch list` (no `project_id`) | a validation error — the server answered |
| `seats/<seat>/skills/` | **14** shared skills per seat (guide/policy blocks are not among them) |
| `seats/<seat>/hooks/pre/` | `seat-guard.ts` per seat, and enforced: a `bash` command of this seat was refused today with `seat guard (env-secret)` |

**What still stands:** `config.yml` is 0 and `spec.json` carries `agent_dir: null` for all five seats,
so the open part of the unit is the guide/policy materialisation as seat files — not the tools, and
not the shared skills.

**Mechanism, not inference.** AGENTS.md §5, dated 2026-10-15: the runtime gives each seat the
state-root env file and writes `<seat dir>/mcp.json`; a running seat never re-reads either, so the
mount arrives with a relaunch. This session is that relaunch.

**Not in this change.** No ruling on the overlays unit and no edit outside `NEXT-GEN2.md` and this
entry.
