## The all-refused batch is pinned: the ledger nudge's `tip > 0` guard has a case

Row `qitem-20261011064850-9a7d432406b46f12`, the reviewer's M2 on the P4 verdict (gate row
`qitem-20261011064809`, `GATE-fcc8a2fc-ledger-tip-nudge-2026-10-11.md`). A coverage gap, not a defect:
the guard was right, and nothing held it.

### What was missing

`ledgerIntentsWriterAdapter.SubmitIntents` nudges only when `ledgerAcceptedTip` answered `(tip, true)`,
and the comment beside it states the property: *a batch that committed nothing nudges nobody*. The
reviewer falsified it: with `return tip, tip > 0` changed to `return tip, true` the whole Ledger set
stayed GREEN (`ok 21.762s`), because every other case in the file commits at least one accepted item. A
later refactor could therefore have deleted the branch and left the suite green - the failure mode a
guard exists to prevent.

### The case, and what it asserts

`ledger_pg_test.go::TestALedgerBatchThatAcceptedNothingNudgesNobody` (PostgreSQL; skips loudly without
`AGENTHUB_TEST_PG_URL`). It drives the OUTCOME rather than the expression:

- A first decision commits so the task has a seq a later one can be stale against. It is posted
  **before** the socket opens, because it nudges too and a buffered frame would be misread as the
  refused batch's own - the mistake the first draft of this case made, and it is why the ordering is
  commented in the case.
- An entitled connector socket (hello advertises `ledger`, `ready` echoes it) opens after that commit.
- A decision on a STALE `base_seq`: the request answers 200, the item is refused, and the case asserts
  the tip did not move and no row was written - so "accepted nothing" is measured, not assumed.
- Then the assertion: **no frame at all arrives** within a 700ms read window.
- Then the positive contrast on the SAME socket: the next batch that commits IS nudged, carrying its
  own `user_seq`. Without this half, a socket that simply cannot hear would pass the case.

Observed on a green run: `OBSERVED refused batch: rows 1 tip 1 unchanged and no frame -> then the
commit's user_seq=2 arrived as 2`.

### Red first, and both runs

The reviewer's own mutation, applied alone:

    ledgerAcceptedTip:  return tip, tip > 0   ->   return tip, true

    RED:   ledger_pg_test.go:996: an entitled socket received opcode=1
           payload="{\"type\":\"ledger_tip\",\"user_seq\":0}" when the batch accepted nothing, want nothing
           --- FAIL: TestALedgerBatchThatAcceptedNothingNudgesNobody (1.42s)
    GREEN: --- PASS: TestALedgerBatchThatAcceptedNothingNudgesNobody (2.14s)

The red names the frame the mutation invents - `user_seq: 0`, the tip of a batch that accepted nothing -
which is exactly the payload a client would have been sent to pull nothing for. The guard is restored in
the committed tree; no production code changed in this commit.

### The Ledger set

    AGENTHUB_TEST_PG_URL=postgresql://agenthub_user@127.0.0.1:55995/postgres \
      go test -count=1 -run 'Ledger' ./fastmcp/server/httpapp/
    -> ok agenthub/fastmcp/server/httpapp 22.468s   (verbose: every case PASS, none skipped)

`gofmt -l` on the touched file prints nothing. Scope: the P4 connector's ledger-tip guard and its case -
`SendTextWithin` and the capability slice are untouched, and M1 (the 2s bound per entitled socket) stays
a known accepted cost rather than something to change here.
