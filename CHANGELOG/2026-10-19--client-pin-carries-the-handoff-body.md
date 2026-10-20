# The pin carries the handoff body

The hub's gitlink moves `ad28da4 -> 02eac84` (client main). A `room queue close --reason handed_off_to
--note <text>` now hands the receiver a row whose BODY is the note — the fresh account — instead of a copy
of the source body, which handed it the stale question the note had just answered. An empty note is no
account, so the source body is carried unchanged.

Where: `rust/agenthub-runtime/src/queue/mod.rs`, `QueueStore::close` computes `successor_body` and feeds it
to the successor INSERT; the Go client already sent the note, so no Go edit.

Evidence: reviewer gate PASS at `f3c064a` (row `qitem-20261018234500-7388e26e8999`); task `1d8a8171` closed
through the gate (0.97 / 0.99); rebased onto `ad28da4` as `02eac84`, where `cargo test --offline` in
`rust/agenthub-runtime` is 185 + 1 + 19 + 1 passed, 0 failed, and `go test ./...` rc 0. Red-first: the
round-trip test fails on the note assertion when the successor body is forced back to the source body,
while the empty-note case stays green both ways.
