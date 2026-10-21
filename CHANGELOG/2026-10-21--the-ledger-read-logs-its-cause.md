# The ledger's read failure is logged, so a flat 500 stops being the whole record

`GET /api/v2/tasks/{id}/events` answers `{"detail":"Failed to load task events"}` for any failure of the read,
and `routes.GetTaskEvents` dropped the error there. The adapter that performs the read,
`taskEventReaderAdapter.ListTaskEvents`, logged nothing either, so a broken statement left no trace: on
2026-10-21 every task's events answered 500 on the deployed hub - the four measured were all older than the
22:59Z restart, while a task created after it answered 200 with its own row - and the only record anywhere was
the flat body. The write half of the same ledger does log (`evidence: task %s: RecordEvidence failed: %v`), which
is why its failure was diagnosable from the host's stdout at all.

The fix is that line's sibling, in the same reader: when the repository read returns an error,
`ListTaskEvents` logs `events: task <id>: ListTaskEvents failed: <cause>`. The next occurrence names the failing
statement in the log rather than only its symptom in the response, which is the whole difference between a
five-minute read and this one.

Verified: `go test ./fastmcp/server/httpapp/ ./fastmcp/server/routes/` exits 0, and the new
`TestTheEventsReadLogsWhyItFailed` fails without the line (it asserts the task id and the returned cause are both
in the log) and passes with it.
