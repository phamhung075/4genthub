# Seat limits and customising a seat

Every omp seat runs in `yolo` (OpenRig offers nothing between yolo and "no tools at all"), so a seat's
limits land in two files that have **two different writers** since 2026-10-07:

| File (per seat, in `~/.openrig/state/omp/<rig>-<seat>@<rig>/agent/`) | Writer | What it does |
|---|---|---|
| `config.yml` | `scripts/openrig_seat_policy.py apply` **and**, after a client install, the render's `runtime/omp-config.yml` merged in (`openrig_seat_sync.py`) | **enforces**: refused shell patterns, refused tools, the MCP startup wait |
| `AGENTS.md` | **the render**, via the seat's policy module and its guide modules | tells the seat its limits in words, how it works (4genthub task loop, deepseek offload) and its own guide |

**The generator's `notice` verb is gone.** It wrote `AGENTS.md` from `ai_docs/operations/seat-guides/` and the
`render_notice` table until 2026-10-07; the limits words now come from the render, whose source is the per-seat
policy module at `scripts/team/4genthub-min/policy-<seat>.json` (kind `policy`: role, the refused patterns with
their siblings, the tool denials, `mcp.startupTimeoutMs: 0`). The files already on disk were **left in place**:
a seat that has not re-installed still shows the generator's text, which is a known state rather than drift, and
the next client install replaces it.

They are a guard rail against accidents, not a sandbox: a seat that can write files can still reach around them.

omp reads both at every launch, including a fresh session after `rig up --fresh`. A running seat keeps what it
loaded, so a change needs a relaunch of that seat (or a `rig send` for the meantime).

## Commands

```bash
python3 scripts/openrig_seat_policy.py show <seat> --rig 4genthub-min     # one seat's config.yml
python3 scripts/openrig_seat_policy.py apply --rig 4genthub-min           # write config.yml
python3 scripts/openrig_seat_policy.py apply --rig 4genthub-min --check   # write nothing; exit 1 on drift
```

To change what a seat is **told** (its `AGENTS.md`), publish the module and let the render carry it — the
`apply` command no longer touches that file.

## Customising

| Want | Do | Takes effect |
|---|---|---|
| Change what a seat may run — the words it reads | edit `scripts/team/4genthub-min/policy-<seat>.json` (kind `policy`), publish it, then the seat's next render | next render + launch |
| Change what a seat may run — the rule that ENFORCES it | edit the deny lists (`COMMON_BASH_DENY`, `NON_LEAD_BASH_DENY`, `NON_LEAD_TOOL_DENY`, `REVIEWER_TOOL_DENY`) or `SEAT_ROLES` in `scripts/openrig_seat_policy.py`, then `apply` | next launch of that seat |
| Add a seat or a role | add it to `SEAT_ROLES` (an unlisted seat has no policy and is an error) and give it a policy module; a new role is handled in `policy_for` | after `apply`, a publish and a launch |
| Change how one seat works | edit its guide block `scripts/team/4genthub-min/guide-<seat>.md` and publish; the shared procedure is `guide-common.md`. Text added by hand to a seat's `AGENTS.md` is overwritten by the next render | next render + launch |
| Instructions for every seat of the rig | the rig directory's `AGENTS.md` (the seats' working directory) | next launch |
| A one-off instruction now | `rig send <rig>-<seat>@<rig> "..."` | immediately |

**Until the config half retires, the two `config.yml` writers must agree**: the script's tables and the policy
modules carry the same rules, and `--check` compares the policy's own keys rather than the whole file, because a
client install MERGES the render's document into the runtime's own file.

Changing a limit is a decision about risk, so state it in the commit and keep `--check` clean.
