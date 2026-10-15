# The architecture doc prints the post-ruling transition table

**What this changes.** Three things the ruling `2b75d092` made untrue, in the lane that owns them:

1. `ai_docs/core-architecture/agenthub-system-architecture.md` printed the pre-ruling transition
   block — `todo`, `review` and `testing` with no `blocked` edge — directly beneath a citation of the
   file the ruling changed. The block gains the three edges and a dated note that says what changed
   and what did **not**.
2. Its citation `value_objects/task_status.go:12-37` pointed at the status constants, not the map it
   describes; repointed to the map's own range at this tip.
3. The entity comment claimed "the inconsistency this closes" without saying which one. It now says
   the **`blocked` column** is what the ruling closes, and names what still differs.

**Why the doc block mattered.** It is the one place outside the Go tree that prints the rule as a
table, and it carried no instrument that would notice the ruling — the same "prose class" the board's
T14 opens for `surface-inventory.md`, here with the copy living two directories away from the source.
Found by the reviewer's gate of `2b75d092` (`ai_docs/reports-status/GATE-status-block-edges-2b75d092-2026-10-15.md`,
"Corrections and residuals", items 2 and 3), which named the architect as owner.

**The divergence that is NOT closed, so no reader takes the two tables as one:**

| Edge | entity `taskStatusTransitions` | service `transitionRules` |
|---|---|---|
| `todo -> done` | yes | no |
| `review -> cancelled` | yes | no |
| `testing -> cancelled` | yes | no |
| `cancelled -> todo` | yes | no |
| `in_progress -> todo` | no | yes |
| `blocked -> todo` | no | yes |
| `archived` | a state with no out-edges | absent from the map |

Only the `blocked` column (the ruling's subject) was closed.

**Also corrected in this lane.** The landed entry `CHANGELOG/2026-10-15--every-open-task-state-can-reach-blocked.md`
named the sweeper's tip as `4662fe65` (that branch has since been rebased; identity is a ref, not a
sha quoted in prose) and the row that asked for this gate claimed the lane "touches no file
task-sweeper touches" — both lanes share `TEST-CHANGELOG.md`. Corrected in place, dated.

**The five live cites into this doc, and what the edit owes them.** Adding two lines at `:136` moved
every line below it by **+2**, and five files cite this doc by line. Shifted, in this commit:
`agenthub_go/fastmcp/server/routes/ledger_routes.go:9` (`:613` → `:615`),
`agenthub_go/fastmcp/server/httpapp/task_wiring.go:127` (`:612` → `:614`),
`agenthub_go/fastmcp/ledger/application/services/ledger_service.go:6` (`:595-:615` → `:597-:617` and
`:599`, `:606` → `:601`, `:608`),
`agenthub_go/fastmcp/ledger/domain/entities/intent.go:7` (`:595-:615` → `:597-:617`), and
`agenthub-frontend/src/lib/taskTimeline.ts:4` (`:173`, `:389` → `:175`, `:393` — the second one
verified rather than shifted: the sentence it quotes verbatim, "Phases are derived from events and
never stored as a second status", is at `:393`, and `:389` was a blank line before this commit too).

**Measured while doing it, and left alone:** three of those cites do not resolve to a sentence that
carries their claim, before or after this commit. `ledger_routes.go` cites this doc for a
"the reason both exist" sentence about O1a and the ledger read; `task_wiring.go` cites it for the
recorder's single-writer/transaction decision; `ledger_service.go` cites `:599`/`:606` for the
one-sentence rule. The document contains no occurrence of `O1a`, and its D9 body has no recorder or
transaction sentence — measured: `grep -nc 'O1a\|P2\b'` → **0**, `grep -n 'recorder\|one writer'` →
`:405`, `:599` only, neither being the claim. The +2 shift keeps them as precise as they were; naming
them here because a cite that cannot bear its claim is the "prose class" the board's T14 opens, and
these three live in Go comments where no instrument would ever notice them.

**Verified at this tip:** `gofmt -l` clean on the touched file, `go build ./...` rc 0,
`go test -count=1 ./fastmcp/task_management/...` rc 0 (a comment moved, no rule did), and
`CI= python3 scripts/CITATION-AUDIT.py` → `rows 148  stale 0  unresolved 0` — the doc this commit
fixes is still read by no instrument, which is why it took a gate to find.

**Not in this change.** No rule change, no test change, no instrument.
