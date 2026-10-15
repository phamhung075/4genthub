## The seat-message deliverer is now a supervised safeguard

### Fixed
- The frontend's "send request to lead" message never reached the lead. The owner typed
  "give me all selectif decision for i can valid because i will sleep for 3h" in the RoomDecisionPanel at
  2026-10-12T22:00:26.854Z; it landed in the cloud `seat_messages` store (row
  `8df26eb8-9526-420b-9dad-e04ff4d59bd1`, room `4genthub-min`, seat `lead`) and stopped there. Root cause:
  that store's only consumer was the manual `4genteam sync messages <room> <seat>` verb — nothing
  scheduled it, the `delivered/` ledger directory had never existed, and the supervising rigd tree had
  died at ~2026-10-12T21:57:39Z (every safeguard row's last beat between 21:56:48Z and 21:57:39Z), ~2.7
  minutes before the POST. A message could be sent, answered `ok`, and never read.
- The stranded row was delivered by hand as part of the same work: `sync messages --rig 4genthub-min
  --dry-run` showed the full text, one pass printed `4genthub-min/lead: 1 delivered, 0 re-acked,
  0 failed` (exit 0), the ledger `~/.config/4genthub/agenthub-seats/delivered/4genthub-min-lead.ids` holds the
  row id, a re-peek is empty (the cloud was acked), and the lead's pane shows the full text with its
  `From: human@kernel` envelope.
- SURFACED, NOT FIXED — the one-word `status` the lead's pane showed is NOT a truncated rendering of the
  frontend message: it is a separate, earlier local send (outbox `outbox-20261012220025-5adad102`,
  stamped 22:00:25.034Z, 1.8 s before the cloud row) whose body was wrapped as
  `From owner session: status`. The wrapper's only producer in the tree is
  `internal/clientseat/reseat.go`; which process sent it is unexplained and recorded here so the next
  reader does not mistake it for the bug's remnant.

### Added
- `sync messages --rig R [--watch]` (`agenthub_client/internal/clientsync/messagesverb.go`): the rig shape
  derives each seat's session from `rig ps --nodes --rig R --json` (running seats only, by canonical
  session name, room = the rig), and `--watch` runs one pass every 10 s until cancelled — a pass that
  fails is logged and the loop goes on, because a deliverer that exits is how the message reached the
  cloud and stopped there. Sends are stamped `AGENTHUB_SESSION_NAME=human@kernel`, so the receiving seat
  sees the human as the sender (the envelope — From/To/Sent — stays on).
- `MessagesLogPath` (`agenthub_client/internal/clientlifecycle/paths.go`): `messages-<rig>.log`, what
  every pass printed, so a message that would not land stays readable after the fact.

### Changed
- The `messages` safeguard joins the five health tables in
  `agenthub_client/internal/clientservices/services.go` — `Safeguards()`, `RigScoped()`,
  `DefaultSilentAfter()`, `Pattern()` (`4genteam sync messages --rig <rig> --watch`) and `Verify()`'s
  capacity — with `MessagesEvery` = 10 s, so its silence threshold is 30 s (three passes). The five
  move together or the report and the process table start disagreeing about which process is the
  deliverer.
- `rigd` supervises it as each rig's third child (`agenthub_client/internal/clientlifecycle/rigd.go`,
  argv `sync messages --rig R --watch`), beside compact-run and the watchdog, so delivery restarts with
  the machine's other safeguards rather than by hand. `doctor` and `lifecycle`'s summaries name it
  (`doctor.go`, `lifecycle.go`).
- `~/.config/4genthub/agenthub-seats/rigd.json` was found carrying a junk `RIG` entry plus stale safeguard rows
  beating 21:56:48–21:57:39Z; it was rewritten clean (`{"rigs":["4genthub-min"],"safeguards":[]}`) and
  rigd now repopulates it each pass. This is operational state, named because a frozen `safeguards` list
  is part of why the outage was not visible in the report.

### Testing
- `gofmt` clean, `go vet` clean, and the WHOLE client module green: `go test ./...` (no package fails;
  the four new cases in `messagesverb_test.go` cover the rig pass over a mixed node fixture, per-seat
  failure isolation, the watch loop's heartbeat-and-continue, and the shape refusals; the fixture-driven
  updates landed in `services_test.go`, `rigd_test.go`, `doctor_test.go`).
- `scripts/build.sh` ran vet + tests + build and installed `~/.local/bin/4genteam`; `4genteam up
  4genthub-min` exit 0; `doctor` exits 0 with all five rows running; `pgrep` shows rigd 9466 and the
  child `4genteam sync messages --rig 4genthub-min --watch` 9515, and the orphaned compact-run 24593 was
  ADOPTED (same pid, not duplicated).
- End-to-end through the production path: the stranded row was typed into the lead's real session and
  acked — the first live proof of the fixed loop.
- The change is client commit `7cefd9b` on branch `human/messages-safeguard`; the superproject pin stays
  at `9f84728`. The bump is the architect's per the standing rule — recorded in TEST-CHANGELOG.md.
