## The status surface says WHICH hash it shows: pinned (resolved) versus expected (intended)

- **What was ambiguous:** the bridge reports a per-seat hash that **is** the resolved-seat snapshot the seat has
  **pinned** — it reads the seat's own `pinned.json` — but it travelled as `hash` on the wire and in the status
  response, beside the cloud's `expected_hash`. An operator could see both numbers and not know which one said
  what the seat was **actually on**, which is the same intended-versus-resolved confusion as tonight's vacuous
  `/health` check.
- **The rename is end to end now, AND THE FIRST ATTEMPT WAS NOT — recorded because the failures are the proof.**
  The writer side was mechanical: the bridge's payload key (`openrig_bridge.py:260`), the Go ingest struct
  (`seat_status_mount.go:79-86`, typed `PinnedHash`), its length guard and message, the mapping to the stored
  `RunningHash` (`:283`), the served response key (`:330`), and the frontend's type. **The READER was missed**:
  `openrig_bridge.py:568` read `seat.get("hash")`, so the verdict fell to `unknown` and **three** script-suite
  tests failed. **A second type-position reference was missed too** — `Pick<MachineSeatStatus, 'sync' | 'hash' |
  'expected_hash'>` in `MachinesPanel.tsx:39`, which alone produced **four** tsc errors across two files. Both
  are the same shape: **a rename counted over writers and not over readers.**
- **THE ASSERTION THAT MAKES IT AN INSTRUMENT, which is the point of the change:**
  `TestSeatStatusPostStoresAndGetServes` posts a pinned hash and sets the fake's stored expected hash to a
  **different** value, then asserts the served pair is `pinned_hash:abc123` and `expected_hash:cloud999`. A
  wiring that served the intended hash under `pinned_hash` satisfies every earlier check in that test and fails
  this one — so the field cannot silently mean the wrong thing.
- Files: `scripts/openrig_bridge.py`, `seat_management/**/seat_status_mount.go` and its test,
  `agenthub-frontend` types + panel, the two script test files, both changelogs.
