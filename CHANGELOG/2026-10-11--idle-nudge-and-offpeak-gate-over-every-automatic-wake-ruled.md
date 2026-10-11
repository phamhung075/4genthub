## Idle nudge ruled, and the off-peak gate now covers every automatic wake

### Added
- `ai_docs/core-architecture/rigd-boundaries.md` §7.9 (lead's `qitem-20261010230121-aba9ffb6153fb3fa`, ruling row `002e9f44`).
  - **What the nudge is:** a rigd loop. When every seat of a room is running and idle for `IDLE_NUDGE_MINUTES` (new setting, default 5, 0 means off), it sends the room's lead ONE continue message.
  - **Activity source:** the nudge reuses the §7.7 seat activity, read from the transcript tail. It adds no second source.
  - **Latch:** keyed on the idle period's identity, `T` (newest seat activity). At most one nudge fires per period. A nudge deferred at peak fires at the first open minute only if no seat worked in between.
  - **"Stopped on purpose":** a room absent from the `rigd.json` `rigs` list. A new `4genteam down RIG` verb removes it.
  - **Event:** each nudge is logged and sent upstream as an `idle_nudge` events item.
  - **Off-peak gate:** every automatic wake goes through the existing `clientoffpeak` gate via `clientlifecycle.PeakGate`. `--allow-peak` never reaches an automatic path.
  - **Defect named:** the compaction supervisor's post-compaction resume message (`agenthub_client` `supervisor.go`) calls no gate, so it can wake a DeepSeek seat at peak.

### Verified
- The architect read `agenthub_client` at `63fd184`: `clientoffpeak/gate.go:31,43,109`, `schedule.go:111`, `lifecycle.go:176,251`, `restore.go:204`. Grepping `supervisor.go` for `clientoffpeak|PeakGate` counts 0.
- No code changed, so no tests apply. Ruling row `002e9f44` was read back.
