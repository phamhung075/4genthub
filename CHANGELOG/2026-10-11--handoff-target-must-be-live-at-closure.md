## A handoff target must be live at closure time

### Added
- `ai_docs/core-architecture/rigd-boundaries.md` §7.11, the architect's ruling on the reviewer's GATE `f541f2f5`, requested in the lead's `qitem-20261010233502-641a56880b826f98`.
  - **The rule:** a `handed_off_to` closure resolves its destination from the live set (`rig ps --nodes`, `rig whoami`), never from a commit trailer, the identity hint or memory. A destination that is not live is re-routed with `rig queue fallback`.
  - **The guard:** `seatcheck send` refuses a destination that is not live (reason `not_live`), and `doctor` gets an `orphan_handoffs` row. Both go with the team-prune item `00f2e9cf`.

### Verified
- On 2026-10-11 the architect ran `rig ps --nodes --rig 4genthub-min`. It listed five running seats: lead, go-dev, reviewer, fe-dev and architect. Neither writer nor web-dev was among them.
- No code changed in this commit, so no tests apply.
