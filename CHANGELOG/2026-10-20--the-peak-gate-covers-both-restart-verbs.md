# The peak gate covers both restart verbs

A restart is a launch: it starts a DeepSeek seat on whatever rate the clock is on. Two verbs did it with no
gate at all - `4genteam room reseat` (`clientroom/room.go`) stopped a seat and restarted it from a fresh
runtime render, and `4genteam heal` restarted a seat that had died - so the gate `up`, `compact`, `continue`,
`watchdog`, `sync respawn` and `seat reseat` all call was one command away from being skipped. Ruling:
`ai_docs/core-architecture/peak-gate-restart-verbs.md` (both refuse unless `--allow-peak`; neither warns
and proceeds).

**`room reseat`** reads `clientoffpeak.ModeFromFlags` before its own parser (which refuses a flag it does not
own), and calls the exported `clientlifecycle.PeakGate(room, "room reseat", …)` BEFORE the stop, returning its
code unchanged. A refusal leaves the seat running. Its usage line and help name the flag.

**`heal`** gains `[--allow-peak]`, read the same way. The gate runs inside its `Reseat` repair, before
`StopSeat`, through `gateRestart` → `PeakGate(room, "heal", …)`; the refusal is written to stderr AND returned
as the repair's error, which `apply` turns into an `unfixed` finding on that seat's own target - so the verb
exits 3 ("something is left") instead of reporting a repaired room over a seat left down. `--check` never
reaches the repair, so it never asks the gate.

`PeakGate`, not `Check`: the room-record semantics (an unreadable reading refuses in words; a room with no
records proceeds and says the gate did not run) belong to one function. `seat reseat` keeps `Check` because it
gates per-seat targets.

Tests, all with the clock pinned through `OFFPEAK_UTC` and a real fake daemon / fake repairs:

- `go test ./internal/clientroom -run 'TestRoomReseatRefusesAtPeakBeforeTheSeatIsStopped|TestRoomReseatProceedsAtPeakWithTheFlag'`
  - the refusal's recorded frames are exactly the one `GetRoomStatus` the gate decides on: NO `StopSeat`, no
    `RestartSeat`; and the flag passes the same peak room through all three.
- `go test ./internal/clientheal -run 'TestHealsGateRefusesBeforeTheStop|TestTheFlagIsWhatHealsGateSees|TestARefusedRestartIsAnUnfixedFindingNamingTheSeat'`
  - the client points at a socket nothing listens on, so an error naming that path would be the stop having
    run; the refusal comes back instead. With the flag the dial error does come back, which is how the run
    moved past the gate.
- `go test ./...` in `agenthub_client` is green at client `bb30cb0`.

`nfr-register.md` COST-03: the gated list grows to eight verbs with both restarts, and the residual now says
they ask the gate before the stop rather than that they skip it.
