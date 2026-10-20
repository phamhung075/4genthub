The evidence writer answers an identical replay with the stored entry

The evidence route refused EVERY second submission for a task's latest head_sha, comparing only the
head (`task_event_controller.go`, `ErrEvidenceDuplicate` -> 409). A client retrying an evidence POST
whose answer was lost therefore got a 409 for a submission that was already stored, and a client
submitting a DIFFERENT account of the same head got the same 409 - so a completion could be computed
on one account and judged on another.

The writer now decides with the entry's content, not only its head:

- It reads the task's latest `evidence_submitted` entry (event and payload) under the same ledger
  append lock the decision was already taken under, and compares `base_sha`, `head_sha`, `numstat`
  and `test.command` / `exit_code` / `failed` in order (`sameEvidence`).
- Equal -> a REPLAY: the stored event is returned with `created=false` and nothing is appended. The
  route answers **200** with the stored entry.
- Different -> `ErrEvidenceDuplicate` -> **409** "Evidence for this head_sha has already been
  submitted with different content".
- A new head, or a task with no evidence, is appended as before -> **201**.

`TaskEvidenceWriter.RecordEvidence` now returns `(*TaskEvent, created bool, error)`, and
`routes.SubmitTaskEvidence` carries the flag to the handler, which picks 201 or 200. The stored side
arrives from JSONB (`float64`, `[]any`) and the submitted side from the route (`int`, `[]string`), so
both are normalized before comparing; a list whose order differs is a different account.

The client follows in `agenthub_client cb7e81f`: the 409 continuation is deleted, so a 409 stops the
completion, and the retry path is the hub's 200 - already the stored path.
