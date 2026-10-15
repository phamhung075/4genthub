## The plan's enumeration gets its missing P1 row, and the unit mapping is stated once

### Added

- `NEXT-GEN2.md`, Group P: the **P1** item the rig has been talking about while the enumeration skipped it
  (the group began at P2). P1 = **the client's reaches go native** — the client-runtime cutover unit: every
  reach answers over the runtime's socket and the exec of the installed CLI disappears. It closes only when all
  **three reaches** are native, and both named commits were resolved before the row was written:
  - the **read** — `55597e2 refactor(messages): the message pass reads its seats from the runtime`;
  - the **delivery** — `9e392ae refactor(messages): the delivery goes to the daemon, and the envelope keeps the
    human's name`;
  - the `firstRigSession` reach — `agenthub_client/internal/clientsync/connectorverb.go:103`, behaviour
    unchanged, ruled (i).
- The same row states the **unit mapping once**, so a next session cannot re-derive it: **P1** = the client's
  reaches native (client-runtime cutover unit); **U1** = room hosting and materialisation (the `spec.json` leg,
  satisfied 2026-10-13 by the `cutover-lab` room); **U2** = the native runner plus the room-lifecycle wiring
  for `up`.

### Notes

- **The P1 remainder is measured, not estimated:** 18 exec call sites in `agenthub_client/internal/` non-test
  sources — 15 as `rig.Run(` and 5 as a `.Run(ctx` on another receiver, the two overlapping — across 9 files,
  over the primitive `func (r *Rig) Run(ctx context.Context, args ...string)` at
  `internal/clientcmd/command.go:83`. An earlier note in §1 of the same document said *eleven* and recorded no
  pattern; the row says so and asks for both counts to be re-run before either number is quoted again.
- Docs only; no code path changed.
