# The peak gate covers both restart verbs: `room reseat` and `heal`

Architect ruling, 2026-10-20, on the lead's question (`qitem-20261020172030-5e6bda1c2fa8`, board
`ebfa8f33`): a restart path starts a DeepSeek seat, so does it take the peak gate, refuse or warn?
- **Client work:** `f743a64` (`agenthub_client`, `room reseat` + `heal`, with tests).
- **Hub work:** `59c7e635` (register row 54, the changelog, the client pin).
- **Ruling row:** `qitem-20261020172112-6afa8631ad81`; implementation row
  `qitem-20261020172112-03824441b55a`.
- **Composes with:** `nfr-register.md` row `COST-03`, and the schedule the gate reads in
  `agenthub_client/internal/clientoffpeak/schedule.go`.

**The rule.** A stop and restart is a launch: it starts a turn, and on a `deepseek/` seat it bills at
whatever rate the clock is on. Every verb and automatic resume that starts a seat already asks
`clientlifecycle.PeakGate`; `room reseat` and `heal` stopped and restarted seats without asking, so the
gate was one command away from useless. Both now **refuse at peak unless `--allow-peak`**, and **neither
warns and proceeds**.

**Why refusal, not a warning.** Three options were weighed. Keeping both ungated was rejected because
the register records the hole, it does not license it. Warning for `heal` was rejected because it bills
the same rate as the verb that refuses: a warn-and-proceed path is the silent spend the gate exists to
stop, and it would be the only one. Refusal is right for both because both are human-run: `heal`'s only
entry point is `cmd/4genteam/main.go:112` (no package calls `clientheal.`), it has no timer and no
autostart, and its report names what it left - so a refusal is visible, waitable, and overridable with
`--allow-peak`.

**What would change this ruling.** If `heal` or `room reseat` gains a caller with no operator - a timer,
the watchdog, an autostart - a refusal would stop repairs silently and repeatedly. That verb then flips
to a warning: proceed, and report the spend it could not stop. Until such a caller exists, refuse.

**`room reseat` as landed** (`clientroom/room.go`): `ModeFromFlags` reads `--allow-peak` before the
sub-verb's own parser, which refuses any flag it does not own (`:432` `runReseat`); the usage line and
help name the flag (`:113`). The gate is `clientlifecycle.PeakGate` (`:49`, a variable so the suite can
watch it) called with the verb string `room reseat` at `:445`, **before** the runtime document is fetched
and before `StopSeat` (`:453`) - so a refusal leaves the seat exactly as it was - and its exit code
returns unchanged: 3 on a refusal, 3 when the room's node records cannot be read, 2 for an unreadable
schedule. Tests: `room_test.go:349` (refused at peak, no `StopSeat` reached) and `:382` (proceeds with
the flag).

**`heal` as landed** (`clientheal/command.go`): usage gains `ModeFlagUsage` (`:23`), the flag is read the
same way (`:67`), and the gate runs inside the `Reseat` repair before the stop (`:131` before `:134`)
through `gateRestart` (`:179`), which passes verb `heal` to the same `PeakGate` and returns its refusal
**both** to stderr and as the repair's error - `apply` turns that into an `unfixed` finding on that
seat's own target, so the run exits 3 ("something is left") instead of reporting a repaired room over a
seat left down. `--check` never reaches the repair, so it never asks the gate. `heal` restarts from the
room's own record, no fresh render (`:140`), because a fresh render is what `room reseat` is for.

**`PeakGate`, not `clientoffpeak.Check`, for a room.** `PeakGate` is the one home for the room-level
semantics: an unreadable reading refuses in words, and a room with no node records proceeds while saying
the gate did NOT run. `seat reseat` keeps `Check` because it gates per-seat targets, not a room.

**What this ruling does not cover.** A seat that is already running is not stopped: the gate prices
starts and resumes, not the turn a live seat takes. That residual is stated in register row `COST-03` and
is unchanged by this ruling.

**Provenance.** The rail note this document replaces is
`rooms/4genthub-min/seats/architect/RULING-peak-gate-restart-verbs-2026-10-20.md`; this file is the
record. Anchors were read at client `bb30cb0` before the work and at `f743a64` after it.
