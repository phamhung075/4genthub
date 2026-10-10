# scripts/team/4genthub-min — what this directory is, and the two things it does not settle

The room definition for the minimum team, applied by `4genteam team apply` (the module is
`agenthub_client/src/agenthub_client/team_setup.py`; this named `scripts/openrig_team_setup.py`
until the 2026-10-09 client relocation moved the scripts into the installed client). It mirrors the
SHAPE of `scripts/team/4genthub/team.json` and **inherits nothing from it**: that room is nine seats
on `claude-code` with an empty model, this one is nine seats on `omp` with
`deepseek/deepseek-flash` plus an architect on `claude-code`, and `seat_type`, `runtime` and `model`
are stated **per seat** here — a room definition copied from the other file would describe a fleet
that does not exist, and it would do it silently because every field would be filled in.

## The ten modules

`guide-common` is carried by the **seat types**, not by a room overlay: `seedlibrary.go`'s
`sharedModuleFiles` (`:45-64`) mounts it on every seat type. The ten `guide-<seat>` modules are in each
seat's own overlay (slug lists — `4genteam team apply` builds the ops). The texts are a **pure copy**
of the seed-library blocks, verified byte-identical to the digests recorded in
`seedlibrary/guides.lock.json`, 10 of 10.

*Corrected 2026-10-09 (row `2458e090`): the company overlay is EMPTY — `team.json:200` reads
`"company_overlay": []` — and `grep -rn guide-common scripts/team/` matches no line of `team.json` at
all, because `f8d3eaab` dropped it. `guide-common` reaches every seat through the seat types'
shared-module list, which is what the delivered renders show: every installed seat's `AGENTS.md` opens
with `## Working procedure (every seat)`. The count of per-seat guides is TEN, not nine — `guide-architect`
is the one the earlier count missed.*

*Measured 2026-10-06: the sha256 of each text file compared with its entry in that lock — 11 of 11 — at
the commit that created this directory (`10e5222b`), and again after the note edits. The count is now
ten because the second backend seat's guide retired with that seat on 2026-10-08, and the
roster alignment that removed them is the change that carries this line.*

## The seat types: seven clean, three flagged (7 + 3 = 10)

| seats | seat_type | why |
|---|---|---|
| `lead`, `reviewer`, `writer`, `architect` | `lead`, `reviewer`, `writer`, `architect` | match by name |
| `go-dev`, `fe-dev`, `web-dev` | `developer` | match by name |
| `skills-dev`, `context-dev`, `feedback-dev` | `developer` **(flagged)** | they resolve the **orchestrator** spec today, and `orchestrator` is not one of the nine seeded types |

Seven seats match a seeded type by name — `lead`, `reviewer`, `writer`, `architect`, `go-dev`,
`fe-dev`, `web-dev` — and three do not: `skills-dev`, `context-dev`, `feedback-dev`. Seven plus three
is the ten seats in `team.json`, which is the check to run on this paragraph rather than counting
table rows.

*Measured 2026-10-08: `resolved_spec_name` per seat from the OpenRig ledger (`nodes`, rig
`01M447FRCC0P2WBKPA45R21M8N`) compared against the nine files in `seedlibrary/seat-types/`. NOT from
`team.json` — that file states `developer` for the three, so a check reading it would be comparing the
file with itself, which is how a first version of this check answered ten and zero and looked right.
The architect resolves `architect`, which is a seeded type, so putting it in the retired seat's place
keeps the split at seven clean: the three flagged seats are the `orchestrator` ones.*

The three flagged seats are a **product choice still open with the owner**: either `orchestrator`
becomes a tenth seed type — which means a new `seat-types/orchestrator.yaml` in the seed library, and
then this file changes by three lines — or they keep `developer`, whose context describes
implementation rather than coordination. `developer` is what the file states because it is the only
value executable against the nine seeded types. The divergence is not created here; it is recorded:
those three already carry `resolved_spec_name: orchestrator` at one shared spec hash in the ledger,
while their local `agent.yaml` says developer.

## Not settled here, deliberately

- **`apply` has not been run.** The `4genthub-min` room does not exist, and creating a room and ten
  seats in production is the owner's decision, not a data change.

  > **CORRECTED 2026-10-10 (web-dev, row `qitem-20261007162529-198e75cb265f3ba1`) — THIS BULLET IS FALSE, NOT EARLY, AND IT IS KEPT ABOVE AS WHAT IT SAID.** The room **exists in production**, written by **`b553b586` at 2026-10-07 17:18:49Z** — the principal's own run. Its commit subject reads *"The 4genthub-min room is created in production"* and its `CHANGELOG/` entry reads *"the room, its 10 seats and the 10 seat overlays were written … run by the principal, who holds the token"*. Measured read-only 2026-10-10: `GET /api/v2/openrig/rooms` -> `4genthub-dev`, **`4genthub-min` · "4genthub minimum team"**, `smoke`; `GET /api/v2/openrig/rooms/4genthub-min/seats` -> HTTP 200, **10 seats**; `4genteam seat status 4genthub-min` -> the ten with resolved snapshot hashes (`lead` `7ac2237e0d0e`, `web-dev` `ebff3c29104d`). **This paragraph was written BEFORE that run and never revisited.** What an `apply` would change *today* is the smaller, different thing: the live room carries `guide-go-dev2` and `policy-go-dev2` (a seat since retired) and **lacks `guide-architect` and `policy-architect`**, and it has `go-dev2` and **no `architect`** — so the architect pair added to `team.json` on 2026-10-09 has never reached the room, and publishing it is a production write and the owner's decision in precisely the sense this bullet meant.
  >
  > **ROW RELATIONSHIP, SAID OUT LOUD RATHER THAN IMPLIED: this is not a line row `2458e090` missed.** That row — landed by `27f27267` (2026-10-09 23:04:26Z), this file's last touch — covered the `guide-common`/overlay lines (`:14`, `:58`) and is **closed**; this bullet and the links bullet below are **new lines that were never in its scope.**
- **The three-home deletion waits** on a live-seat observation that a seat's `AGENTS.md` came from a
  module rather than from the notice generator.
- **The company overlay is EMPTY** (`team.json:200` reads `"company_overlay": []`, corrected 2026-10-09: `guide-common` is carried by the seat types — see above). Porting `project-*`, `mission-*` and
  `delegate-deepseek` from the other room is a named follow-on, not part of a guide move.
- **The 26 links are derived from `rig-omp.yaml`**, so they describe the team that is running rather
  than a team somebody imagined; a room without them would describe ten seats that do not know each
  other.

  > **CORRECTED 2026-10-10 — THERE ARE NO LINKS, AND THAT IS A DECISION RATHER THAN A GAP; the line above is kept as what it said.** `team.json:199` reads `"links": []`, and the client emits one link step per entry (`agenthub_client/src/agenthub_client/team_setup.py:573`), so the credential-free dry run of 2026-10-10 reproduces **42 steps = 1 seat-types seed + 20 modules + 1 room + 10 seats + 10 overlays, and ZERO link steps**. `b553b586` removed them deliberately, in its own words: *"allowing links are refused for omp seats (rule G3), so the min team defines none."* The 26 ported links it deleted are gone from the tree — `26` at `10e5222b`, `0` from `b553b586` on — while `rig-omp.yaml` still carries the running team's edges, **28 of them under `pods[0].edges` (lines 78–105)**. So the "ten seats that do not know each other" this bullet warns of is the state the room was deliberately created in, not one still pending.
