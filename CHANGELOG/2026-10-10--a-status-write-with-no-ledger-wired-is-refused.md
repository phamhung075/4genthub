# A status write with no ledger wired is refused instead of silently saving

## The defect

`StatusLedger.SaveStatus` opened with `if !l.Enabled() { return save(ctx) }`. With the ledger unwired
the status committed, **no** `status_changed` entry was written, the call returned **success**, and the
updated websocket frame still went out — a clean success over an event that does not exist. It needed no
database breakage and produced no error anywhere: any composition site that forgot `.WithLedger(...)`
had it, and the seam's own comment described the behaviour as a feature ("leaves the save exactly as it
was").

## The fix

`ErrLedgerNotWired`, returned instead of the bare save. A status write is a write that must record its
entry; an unwired composition fails **where it is written**, not where its events are missed. `Enabled()`
stays for reading the state; the silent path is gone.

## What it touched

The unit cases that built either use case without a ledger now wire a **pass-through** ledger — a
recorder that reports the same status before and after the save, so the unit of work runs and no entry
is recorded. That is right for them: their subject is the use case's own behaviour (fields updated,
hooks notified, save errors propagating), not what the ledger records. What the ledger records is
measured in `status_ledger_test.go` and in the real-Postgres cases.

The refusal has its own acceptance case, asserted with `errors.Is` so that a different error cannot pass
as it.

## Evidence

- `go test -count=1 ./fastmcp/task_management/application/use_cases/` — ok.
- `go test -count=1 ./fastmcp/task_management/interface/mcp_controllers/task_mcp_controller/handlers/`
  — ok.
- `go test -count=1 ./fastmcp/server/httpapp/` with `AGENTHUB_TEST_PG_URL` set — ok, so the
  database-backed boot path is unaffected.
