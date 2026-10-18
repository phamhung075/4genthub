# The pin carries the held-send audit fix, and its record awaits a carrier

The hub's gitlink moves `dae76a98 -> 84bcd8c9` (hub `7fef4b8f`, gitlink only). Client main took
`4genthub-min/send-reply-race` as a fast-forward: `dae76a9 -> 84bcd8c` (four commits, 5d0cc8e /
efa83bd / e7df9fe / 84bcd8c).

## Changed (client)

The U3 gate caught `send` printing `refused it: …; nothing was sent` against a delivery the runner
had HELD for the next turn. The lane makes the transport row say which of three things happened -
nothing left the client, the frame reached the runner (the text may be held), or the answer cannot
be read - and each side fixes its own defect:

- `rust/agenthub-runtime/src/runner/mod.rs`: the reply socket is unique per call
  (`{seat}.reply-{pid}-{seq}.sock`), so two overlapping deliveries to one seat each get their own
  answer; `REPLY_TIMEOUT = 8 s` bounds the accept and the read, and a timeout is the runner's own
  named sentence. The reply file is removed on every path.
- `internal/commpolicy/policy.go`: `delivery_unconfirmed` is a third outcome - it does not claim a
  loss nobody measured. `internal/clientseat/reseat.go` audits `delivery_unconfirmed` when
  `!nothingWasSent(err)` and `delivery_failed` otherwise, and the sentence carries the runner's own
  words for a hold. `internal/clientruntime/ipc.go` exports `CallDeadline` and `IsNoAnswer`.

## Evidence

- Reviewer gate PASS at `84bcd8c` (row `qitem-20261017034246`): `go test` rc 0 over 32 packages;
  `TestAHeldSendIsAuditedUnconfirmedAndARefusalFailed` passes both subtests (held ->
  `delivery_unconfirmed`, refusal -> `delivery_failed`); `cargo --bins` 154/0 with the seam test
  `send_to_a_mailbox_that_never_answers_ends_in_the_named_sentence` (real 8 s); a full fresh lab at
  the tip = 136/1/4, the one red being B1's pane-visibility precondition (harness patience: the
  kill landed 89 s into a 300 s window), not this lane; C2's leg green.
- Lead at the merged tip: ff clean, `go build ./...` rc 0, `internal/clientseat` and
  `internal/commpolicy` tests ok.
- The held-sentence end-to-end against a live daemon is NOT MEASURED (a forced hold needs a seat
  mid-turn); both string ends and the audit mapping are test-pinned.

## Held

Held record: a pin commit cannot carry its docs from a seat (pre-commit drops the gitlink, so a
pin+docs commit arrives as docs-only and the docs-only guard refuses it; no hook was bypassed). It
rides any commit that touches a non-doc file, or the owner's `types_or: [file, directory]` one-liner
(`qitem-20261017002819-8e1c6aff25f2`).

The push is not authorized and waits for the owner's word.
