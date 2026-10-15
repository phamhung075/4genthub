# The comm-guard points at the audited send path

Date: 2026-10-15
Owner ruling (2026-10-15, verbatim anchors): *"remove 'seatcheck send'. It refuses every send,
policy.json is written by nothing, and 4genteam send already decides and audits. Delete the verb, the
`Bash(seatcheck send:*)` allow rule and the README lines; clean break, no compat layer."* … *"The deny
list beside it (`Bash(4genteam send:*)`, input, tmux send-keys, tmux paste-buffer) is the guard that
STAYS - do not touch it, and keep the whoami allow."*

## What was wrong

The `comm-guard` module is what a seat reads before it sends anything, and it still sent the seat to
the retired checker:

- `shared-modules/comm-guard-skill.md` taught `seatcheck send --to <seat> --intent …` as **the only
  way to message another seat**, and taught exit codes 3 (denied), 2 (unreadable policy) and 5
  (delivery failure). Measured against the client's own error mapping (see "Instruments"), the numbers
  it gave were wrong for the route that survives: a policy denial is 2, not 3, and there is no 5.
- `seatrenderer/renderer.go:393` wrote the same retired verb into every codex seat's execpolicy
  justification.

## Changed

- **`shared-modules/comm-guard-skill.md`** — body replaced (front matter untouched). It names
  `4genteam send <rig> <seat> "<message>" [--intent <task|escalation|report|question|notice>]` alone,
  says what the audited path does (builds the room's policy at send time, records the decision,
  delivers, records the outcome), states that `--intent` defaults to `notice`, and replaces the wrong
  code list with the four refusals and their real codes — 2 for a policy refusal, 3 for an unreadable
  link source or audit log, 1 for a runtime delivery refusal, 3 again for a delivery whose outcome
  line could not be written — telling the reader to read the words rather than the number, because two
  failures share a code. The command spelling was checked against the client's own usage
  (`go run ./cmd/4genteam send --help`) and matches it.
- **`seatrenderer/renderer.go:393`** — the codex justification now reads ``Use `4genteam send`, the
  audited send path, instead of a direct command.`` (one string, no test asserted its text).
- **`seedmap/seedmap.go`** — `seedVersion` 1.4.4 → 1.4.5, with the version comment covering both
  changes under it.
- **`seedlibrary/seedcontent.lock.json`** — the appended 1.4.5 record (26 files, content_sha256
  `08c8b22c38e0…`), recorded with the package's own instrument
  (`go test ./fastmcp/seat_management/domain/seedlibrary/ -run TestSeedVersionNamesOneContentSet -args
  -update-seedcontent-lock`). The record is an append: `git diff --numstat` on the lock is 32
  insertions, 0 deletions, so the 1.4.4 record is untouched.
- **`commpolicy/policy.go`** — `AuditRecord.Outcome`'s comment no longer names the retired checker as
  the process that can stop between delivery and recording; the sender is the process that does both
  now. Nothing else in the comment changed.
- Test expectations updated to the surviving route, not weakened: `seatrenderer/renderer_test.go`
  (the four runtime skill assertions, and the two guards whose fixtures modelled the retired allow
  entry) and `seedlibrary/seedlibrary_test.go` (the skill's command spelling, and its exit-code
  expectation, which the old text could not satisfy once the codes were corrected).

## Not in this change

- **The deny list is untouched, and it is byte-identical to HEAD's**: `Bash(4genteam send:*)`,
  `Bash(4genteam input:*)`, `Bash(tmux send-keys:*)`, `Bash(tmux paste-buffer:*)` — and
  `Bash(4genteam whoami:*)` stays the allow entry (see "Instruments" for the byte comparison).
- No source change beyond the two strings and the version comment above: this is a module-text and
  comment change, and no send path moved. The client half of the ruling (the verb itself, the README
  lines) is the client lane's commit; this repo carries the server-side half only.

## Instruments

- `python3` byte comparison of the `deny` array against
  `git show HEAD:agenthub_go/fastmcp/seat_management/domain/seedlibrary/shared-modules/comm-guard.json`
  → identical.
- Client exit codes read at the source: `internal/clientcmd/command.go` (2 usage, 3 unavailable, 1
  remote), `internal/clientseat/seat.go:34` (`ExitFailed = 3`), `internal/clientseat/reseat.go:270-417`
  and `internal/clientseat/sendpolicy.go:143-179` (a policy denial is `clientcmd.ExitUsage` = 2).
- End-to-end read of the policy-denial code, one self-message (refused by the policy, so nothing was
  delivered and nothing could be): `4genteam send 4genthub-min go-dev "probe"` →
  `error: refused by 4genthub-min's communication policy: go-dev may not send a notice to go-dev (self message). The room's own declared links are what license a send; nothing was sent`
  exit 2.
- `gofmt -l agenthub_go` empty; `go build ./...` and `go test ./...` in `agenthub_go` exit 0.
