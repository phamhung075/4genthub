# COST-03 goes GATE: the peak gate's boundaries are pinned by tests

The register recorded COST-03 as a GAP while the enforcement existed: `clientoffpeak` holds the two
Mon-Fri UTC windows the vendor publishes, `01:00-04:00` and `06:00-10:00`, as
`peakBlocks = [2][2]int{{60, 240}, {360, 600}}` (`schedule.go:43`), a holiday file named by
`DEEPSEEK_HOLIDAYS` makes those days off-peak in full, and only seats whose model starts `deepseek/`
are gated (`gate.go:145`). GATE is the status that asks a test to fail when the property stops
holding, and four do:

- `TestTheBoundariesMatchTheShellGate` (`schedule_test.go:117`) walks each window edge - 00:59, 01:00,
  03:59, 04:00, 05:59, 06:00, 09:59, 10:00 - against the verdict the retired shell gate printed.
- `TestDecideRefusesOnThePeakBlockItSitsIn` (`gate_test.go:222`) and
  `TestCheckRefusesOnlyWhenTheSettingIsOnTheRoomIsDeepSeekAndItIsPeak` (`gate_test.go:155`) pin the
  three conditions (peak, setting on, a DeepSeek seat) and their negations: `--allow-peak`, the
  setting off, a non-DeepSeek seat, no seat at all.
- `TestUpRefusesAtPeakWhenTheRoomRunsADeepSeekSeat` (`offpeak_gate_test.go:79`) proves `up` refuses
  before it resumes a seat.

Run in `agenthub_client` at `bb30cb0`, `go test ./internal/clientoffpeak ./internal/clientlifecycle
-run 'TestTheBoundariesMatchTheShellGate|TestDecideRefusesOnThePeakBlockItSitsIn|TestCheckRefusesOnlyWhenTheSettingIsOnTheRoomIsDeepSeekAndItIsPeak|TestUpRefusesAtPeakWhenTheRoomRunsADeepSeekSeat'
-count=1` is green, and the register row now names that command as its verification cell.

Every gate reads the room's node records through one decision (`peakGate`, `lifecycle.go:838`): a
reading that cannot be taken is a refusal in words, and a room with no records proceeds and says the
gate did not decide. The paths it gates, each opened at HEAD:

| Path | Site |
|---|---|
| `4genteam up` | `lifecycle.go:353` (the definition's own seats stand in when the room has no records) |
| `4genteam compact` | `lifecycle.go:949` |
| `4genteam continue` | `restore/continue.go:155`, `:184` |
| `4genteam watchdog` | `restore/watchdog.go:293` (its refusal is logged, so a room left stopped for billing says so) |
| `4genteam sync respawn` | `respawnverb.go:165` |
| `4genteam seat reseat` | `clientseat/reseat.go:126` |
| the idle guard's wake | `idleguard.go:103` (automatic) |
| the compaction supervisor's held resume | `supervisor.go:229` (automatic; re-asks each pass, sends at the first open minute) |

**What it does not do:** it gates starts and resumes only. A seat already running when peak begins is
not stopped - no call site stops one, and the supervisor's hold covers a *resume*, not a live turn. And
two restarts never ask it at all: `4genteam room reseat` stops a seat and restarts it from a fresh
runtime render, and `4genteam heal` restarts a seat that died, both from the room's own record, at
whatever the clock says (`clientroom/room.go:437`, `clientheal/command.go:119`) - neither package
imports `clientoffpeak`, so neither prints a word about the peak rate. On a peak hour `room reseat` is
the verb that installs a policy change and takes the seats down and back up ungated.

**One published window still says 01:00-15:00.** `ai_docs/reports-status/NFR-analysis-2026-10-19.md:57`
catalogues the wrong span. That path is frozen for seats (the seat guard's `frozen-paths` rule refuses
the write: `ai_docs/reports-status/`), so the correction is not a seat's to make; its own header
already marks the file superseded by the register, and this entry records the contradiction rather
than leaving it silent. Check: `grep -rn '01:00.15:00' ai_docs/` answers that one line.
