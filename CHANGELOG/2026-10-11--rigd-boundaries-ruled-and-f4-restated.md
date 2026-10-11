## rigd boundaries ruled, F4 restated, and the G3 and P-chain rulings recorded in their boxes

### Added
- `ai_docs/core-architecture/rigd-boundaries.md`: the architect's ruling on the three rigd boundaries the lead asked for (`qitem-20261010222721-557596c2630798bc`), each comparing two options and recommending one:
  - **Socket frames:** the existing `/ws/connector` names are kept. New fields: `protocol`, `capabilities`, `heartbeat_s`, `session.state`/`source`, `events.cursor`, `ping`/`pong`, `error.code`/`fatal`. The cursor is stored with the events in a new `agent_sessions.client_cursor` column, which gives exact resume after a lost ack. Capability-gated frame kinds are the forward-compatibility rule. The phase-2 command frames are designed and NOT built.
  - **Command authorization:** `sessions:write` does NOT authorize inbound commands. Phase 2 needs a human-only issuer, a new `sessions:command` scope, local opt-in plus an allowlist the cloud cannot widen, argv exec with no shell, a 5-minute expiry, and a server row plus a local audit line.
  - **Redaction:** rules are compiled into the client and may be extended locally (add-only); they are never cloud-pushed. Redaction FAILS CLOSED per event: a withheld event uploads only a `redaction_withheld {reason, bytes}` placeholder.
  - **First shippable slice:** server frames and cursor, then the client loop and redaction, then frontend rendering. No chat input.

### Changed
- `agenthub_go/NEXT_GEN.md`:
  - **F4:** `[x]` -> `[~]`. The tick cited `scripts/openrig_seat_sync.py` and `scripts/openrig_bridge.py`, which are no longer in the tree. The box now names the remaining scope (rigd phase 1 and phase 2) and points to the ruling.
  - **P4:** `ledger_tip` is sent only to a client that advertised the `ledger` capability.
  - **G3:** records the boundary ruling. `eedc1a4` is a C4 precondition, followed by the sequence: review, pin bump, operator install, A0-A4.
  - **P2:** records that "after P1" is met, not removed.
  - **P7:** records that P7 stands minus its CHECK.

### Verified
- `git ls-files scripts | grep openrig_` prints nothing (architect ran, 2026-10-11).
- No code changed in this commit, so no tests apply. The ruling rows were read back: `87c58552` (rigd), `f1bb7614` (G3) and `aa8d172e` (P-chain).
