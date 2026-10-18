# The pin carries the verdict-line fix, and its record awaits a carrier

The hub's gitlink moves `84bcd8c9 -> 858abf2e` (hub `2682cfa3`, gitlink only). Client main took
`4genthub-min/send-reply-race` as a fast-forward: `84bcd8c -> 858abf2` (one commit).

## Changed (client)

The gate's finding (`qitem-20261017034501`) measured the two layers disagreeing: at `84bcd8c` the
printed line refused to claim a delivery for every runtime answer except `submitted`, while the audit
line wrote `delivered` for EVERY accepted answer. A relayed send was told unconfirmed on stdout and
recorded as delivered in the decision log.

- `internal/clientruntime/transport.go`: `SendVerdict` is the one reader of the answer document -
  `VerdictSubmitted` / `VerdictRelayed` / `VerdictPastedUnconfirmed`, plus the readable flag.
- `internal/clientseat/reseat.go`: audits `delivered` only for `VerdictSubmitted`; relayed, no-verdict
  and unreadable answers audit `delivery_unconfirmed`; the audit-failure sentence no longer claims
  the message was delivered. `RuntimeSendLine`'s branches and sentences are unchanged.
- `internal/clientseat/sendfailure_test.go`: `TestASuccessfulSendAuditsTheVerdictItPrints`, three
  subtests each pinning exit code, printed line and audit line.

## Evidence

- Reviewer gate PASS at `858abf2` (row `qitem-20261017035321`): `go test` rc 0 over 32 packages; the
  three subtests pass; the three `sendline_test.go` tests pass by name.
- The mutation was RUN, not read: the `858abf2` test file dropped into the `84bcd8c` parent (its
  `reseat.go:437` writes unconditional `OutcomeDelivered`) failed exactly on the relayed and
  no-verdict subtests while `submitted` passed.
- Full U3 lab, fresh root: 137 pass / 0 fail / 4 skip (the same four known skips); B1 green, which
  confirms the earlier single red was the harness's pane-text patience, not the lane.
- Lead at the merged tip: ff clean, hub pin `2682cfa3` is a bare gitlink bump (`numstat` 1 file
  `+1 -1`).

## Held

Held record: a pin commit cannot carry its docs from a seat (pre-commit drops the gitlink, so a
pin+docs commit arrives as docs-only and the docs-only guard refuses it; no hook was bypassed). It
rides any commit that touches a non-doc file, or the owner's `types_or: [file, directory]` one-liner
(`qitem-20261017002819-8e1c6aff25f2`).

The push is not authorized and waits for the owner's word (`qitem-20261017030506`).
