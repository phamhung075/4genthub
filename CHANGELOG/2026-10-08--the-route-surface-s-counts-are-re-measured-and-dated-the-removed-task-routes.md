## The route surface's counts are re-measured and dated, the removed task routes are struck, and apirefgen replaces a hand-written resolver

### Changed
- `ai_docs/api-integration/surface-inventory.md`: the Reproduce line now reads **143** (httpapp 123 + auth 20) at `db9d2bc3`, where it carried 145 — it contradicted line 30 of the same file. The acceptance block's own count read **121 + 20 = 141** and now reads **123 + 20 = 143** as a **snapshot at `62b734ec`**, with the stale figure named and the instruction to re-run its two commands rather than quote the line, because a count inside a fenced block is outside what `COUNTS-AUDIT.py` reads. The "How to read the route table" section now names `cd agenthub_go && go run ./cmd/apirefgen` (143 routes, 10 tools at that HEAD) instead of leaving the reader to hand-write a resolver for the function-scoped `const base` that the same paragraph describes — three such attempts produced junk path keys while reporting plausible counts.
- `ai_docs/architecture-design/Architecture_Technique.md`: the row for the removed `GET /api/v2/tasks/stats/summary` is struck and marked **REMOVED by `e6829b32`**, with the command that proves its absence. **The table's check mark is the Auth Required column, not a liveness mark** — the row was live-looking because nothing dated it, and that file carries no staleness marker of its own, so the fleet's convention (name the removal commit plus a proving command, from `surface-inventory.md:545`) was used rather than a new one.
- `ai_docs/architecture-design/decision-task-stats-endpoint.md`: the two `file:line` cites are anchored to **`e6829b32^`**, the revision at which they are correct, rather than renumbered — the removal commit moved both lines onto different routes.

### Tested
- `python3 <seat-area>/COUNTS-AUDIT.py` at `62b734ec`: **exit 0**, eleven rows matching.
- `cd agenthub_go && go run ./cmd/apirefgen -out /tmp/apiref.ts` at `db9d2bc3`: **143 routes, 10 tools**; neither removed route present. The same negative holds by grep: exit 1 at `db9d2bc3`, count 1 each at `e6829b32^`.
- The acceptance block's two commands, re-run after the edit: 123 and 20.

Commits `bc5db276`, `ee71488b`, `894d4b2c`, `3fe918cb`.
