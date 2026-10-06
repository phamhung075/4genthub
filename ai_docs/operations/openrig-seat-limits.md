# Seat limits and customising a seat

Every omp seat runs in `yolo` (OpenRig offers nothing between yolo and "no tools at all"), so each
seat's limits live in two files that `scripts/openrig_seat_policy.py` generates from one table.
They are a guard rail against accidents, not a sandbox: a seat that can write files can still reach
around them, so the notice also tells the seat not to try.

| File (per seat, in `~/.openrig/state/omp/<rig>-<seat>@<rig>/agent/`) | What it does |
|---|---|
| `config.yml` | enforces: refused shell patterns, refused tools, MCP startup wait |
| `AGENTS.md` | tells the seat its limits in words, how it works (4genthub task loop, deepseek offload), and its own guide |

omp reads both at every launch, including a fresh session after `rig up --fresh`. A running seat
keeps what it loaded, so a change needs a relaunch of that seat (or a `rig send` for the meantime).

## Commands

```bash
python3 scripts/openrig_seat_policy.py show <seat> --rig 4genthub-min     # one seat's config.yml
python3 scripts/openrig_seat_policy.py apply --rig 4genthub-min           # write config.yml and AGENTS.md
python3 scripts/openrig_seat_policy.py apply --rig 4genthub-min --check   # exit 1 if any seat drifted
python3 scripts/openrig_seat_policy.py notice --rig 4genthub-min          # AGENTS.md only
```

## Customising

| Want | Do | Takes effect |
|---|---|---|
| Change what a seat may run | edit the deny lists (`COMMON_BASH_DENY`, `NON_LEAD_BASH_DENY`, `NON_LEAD_TOOL_DENY`, `REVIEWER_TOOL_DENY`) or `SEAT_ROLES` in the script, then `apply` | next launch of that seat |
| Add a seat or a role | add it to `SEAT_ROLES` (an unlisted seat has no policy and is an error); a new role is handled in `policy_for` | after `apply` and a launch |
| Change how one seat works | edit its guide `ai_docs/operations/seat-guides/<seat>.md` (tools it uses, workflow, checks, don'ts), then `apply`; the shared procedure is `seat-guides/_common.md`. A seat with no guide file is an error. Text added by hand to a seat's `AGENTS.md` is overwritten by the next `apply` | next launch |
| Instructions for every seat of the rig | the rig directory's `AGENTS.md` (the seats' working directory) | next launch |
| A one-off instruction now | `rig send <rig>-<seat>@<rig> "..."` | immediately |

Changing a limit is a decision about risk, so state it in the commit and keep `--check` clean.
