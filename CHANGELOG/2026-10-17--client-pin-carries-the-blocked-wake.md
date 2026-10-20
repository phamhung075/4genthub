# The pin carries the blocked-wake fix, and its record awaits a carrier

The hub's gitlink moves `7e01b65 -> db06fed`: the blocked-wake lane (`e901f22`, gated PASS as
`qitem-20261017064412-2af19fb84ce2`, 3 files +320) merged as `db06fed`. Two halves: `supervisor::waiting_rows`
filters `state != "blocked"`, so neither the alert nor the nudge pass treats a blocked row as work waiting on
its destination; and `queue::unblock_dependents` runs inside the closing transaction (both roads: `close` and
`update --state done`), returning every row whose `blocked_on` is that qitem id to `pending` with one
transition naming the closure. Wake-on-close did not exist before this.

Rulings the entry records: a row blocked with no `blocked_on` (the two hand-parked owner rows) wakes nobody
and nothing wakes it automatically — it stays blocked until a seat moves it to pending; a free-text
`blocked_on` is a label, not an edge; `in-progress` still counts as work for its seat.

Measured at the merged tip: `go test -count=1 ./...` 32 packages rc 0; `cargo test --offline` 161 + 1 + 15 + 1
green (178/178). The live proof needs the rebuilt binary installed and the seats reseated — on the running
01:01Z daemon the defect is still live (this pin changes nothing until then): the lead's own rail woke it for
the hand-parked row `qitem-20261017023905-7e2b46059c7c` at 06:52Z, after the row had been blocked since
03:07Z.

This commit is the gitlink alone; the router's docs and records wait in the worktree for the carrier commit
the architect's order routes them to.
