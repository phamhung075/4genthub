# Seat limits and customising a seat

A seat's limits have one source: the hub's seat render. The hub folds the seat's policy modules into
`runtime/omp-config.yml` (`agenthub_go/fastmcp/seat_management/domain/seatrenderer/`); the client fetches the render
and hands it to the runtime in the seat spec, and the runtime writes it as the seat's `config.yml` before the
seat starts. The client keeps no policy table of its own (`agenthub_client/internal/clientpolicy/policy.go`).

The limits are a guard rail against accidents, not a sandbox: a seat that can write files can reach around them.

## Commands

```bash
4genteam policy render --room <room> --seat <seat>           # what would be installed as that seat's config.yml
4genteam policy render --room <room> --seat <seat> --check   # compare the installed file with the render; exit 1 on drift
```

## Customising

| Want | Do | Takes effect |
|---|---|---|
| Change what a seat may run | edit its policy module `scripts/team/<room>/policy-<seat>.json`, publish it, check with `policy render --check` | the seat's next start |
| Change how one seat works | edit its workflow or role skill under `agenthub_client/skills/rooms/<room>/<seat>/`, or its guide block in `agenthub_go/fastmcp/seat_management/domain/seedlibrary/blocks/guide-<seat>.md` (shared: `shared-modules/guide-common.md`) | the seat's next start |
| Add a seat | add it to `scripts/team/<room>/team.json` with a policy module; an unlisted seat has no policy and is an error | after `4genteam team apply` and a start |
| A one-off instruction now | `4genteam send` to the seat | immediately |

A running seat keeps what it loaded: restart it with `4genteam room reseat <room> <seat>`, or the whole room
with `agenthub_client/scripts/respawn.sh <room>`. Changing a limit is a decision about risk, so state it in the
commit body and keep `--check` clean.
