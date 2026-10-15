# The boundaries doc reports the six safeguards and the agent scope

`ai_docs/core-architecture/rigd-boundaries.md` is the doc-of-record for the safeguard report, and six of
its clauses stated the vocabulary the server used to accept rather than the one the client sends. These
are the doc half of the architect's item-4 ruling, whose server half landed as
`feat(safeguards): the six names the client reports, and the error frame says message`.

## Changed

- **7.2's row list** is the six names with the scope split spelled out: the four rig-scoped ones carry
  the rig the row is about, and `bridge`/`agent` carry an EMPTY rig. It also records why: these are the
  names the client reports (`internal/clientservices/services.go:79-83`) and `rigd` is deleted rather
  than aliased, `bc725e6` (2026-10-15) having renamed the machine-level supervisor to `agent`.
- **7.3's dead-man paragraph** raises `safeguard_alert` for `agent`, and names a dead agent.
- **7.4's silence table** gains the two rows it was missing - `messages` 10 s/30 s and `roomguard`
  30 s/90 s - and its `rigd` row becomes `agent` 25 s/75 s. Every value is the client's own default
  (`internal/clientservices/services.go:60-70`, `DefaultSilentAfter`), which is what `doctor` uses.
- **7.6's "Names a failing test may assert" table** lists the six safeguards in the client's order.
- **The `4genteam up RIG` addendum** calls the machine-level supervisor `agent` wherever it names it:
  the service table's row and every `RestartBy` cell, the start order, the three sentences that rule what
  starts what, the "a room started by hand with `rig up` has no `agent` row" clause, and the row-name
  table that mirrors the service rows.

## Not in this change

- **The doc's title and file name still say `rigd`**, which the ruling parks as a separate decision, and
  so do the sections outside the six deltas it lists (7.1, 7.2's heartbeat paragraph, 7.4's owner line,
  7.5, 7.9). Naming this is the point: a reader who greps `rigd` finds a doc whose subject is the
  supervisor it is about, and the vocabulary the wire and the table use is the six names above.
- **The service table's row list is not extended to `messages` and `roomguard`.** It is a different list
  from the report vocabulary - the ruling's own §7 flags the reconciliation as a 7.7 decision - and this
  change renames what was there rather than ruling a new row set.
- **No code, no test and no pin**: the diff is this doc plus this entry.
