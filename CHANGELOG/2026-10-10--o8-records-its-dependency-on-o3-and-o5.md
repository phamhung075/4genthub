## O8 records its dependency on O3 and O5 instead of implying event kinds the ledger does not accept

### Changed

- `agenthub_go/NEXT_GEN.md` — O8's box carries a dated dependency clause. Its `Check` names "a TEST-fail → FIX →
  TEST-pass → ACCEPT sequence", but O1a's kind CHECK — what the ledger accepts today — is `created`, `updated`,
  `status_changed`, `completed`, `deleted`, with `actor_kind` `user`, `system`, `agent`
  (`fastmcp/task_management/infrastructure/database/task_event_tables.go:33`): **nothing in that vocabulary is
  evidence or a verdict.**
- The two missing names belong to later items rather than to a gap: `TEST-fail`/`TEST-pass` are **O3's
  `evidence_submitted`** and `ACCEPT` is **O5's `gate_verdict`** (the event O6 consumes when it enforces).
  **Neither is built:** at this HEAD both names occur in `NEXT_GEN.md`'s own plan prose (O3, O5, P3) and nowhere
  in `agenthub_go` — pattern `evidence_submitted|gate_verdict|/evidence` over that subtree — and **P1**
  schedules the widening of the kind CHECK.
- **Until O3 and O5 land, the timeline is built over the five kinds that exist**, with `phase` still derived from
  events and never stored, and the four-step case is marked NOT IMPLEMENTED. The other half of the check (the
  panel's numbers equal the backend query's on a seeded database) is unaffected. **O8 keeps its `[ ]`** — this
  clause records a dependency and ticks nothing.
- **No Go source, test, route or table is touched by this commit.** The pin-conditional held edit inside the same
  file (`NEXT_GEN.md:240-241`) is deliberately not included, so the commit is built from a temporary index
  against HEAD rather than from the working-tree path.
