## A failed dependent unblock is no longer reported as success

`CompleteTaskUseCase.updateSingleDependentTask` ends a dependent task's unblock with a status write of its own,
and that write's error was **discarded** — `_ = uc.ledger.SaveStatus(...)` — so when the save failed, `Execute`
returned success to its caller and the completion was reported as done with the dependent task still blocked.
That is the same shape as the rest of tonight's findings: the failure happened, was known, and was dropped on the
floor by the one line that had it.

**The file's own convention settled the form.** Of the four `SaveStatus` call sites in the use-case package, three
propagate the error — `update_task.go:152`, `complete_task.go:138` and `:389` — and only this one discarded it. The
error now travels the whole chain inside `complete_task.go`: `updateSingleDependentTask` returns it,
`updateDependentTasks` returns it, and `Execute` turns it into `return nil, err` at `:146-148`.

**A deliberate divergence from the ported behaviour, stated rather than implied.** The old comment recorded the
choice: Python logs the failure and continues, so a failure to *record* the unblock could not fail the completion.
That trade is what made a failed write indistinguishable from a successful one at the API boundary, and a caller
cannot retry or report what it is never told. The comment now says so.

**What I deliberately left alone**: the `FindAll` failure at the top of `updateDependentTasks` is still skipped. It
reads nothing and writes nothing, so it has nothing to report to the caller, and changing it is not part of this
ask — named here so a reviewer sees it is a decision rather than an oversight.

**Evidence.** New test `TestCompleteTaskReportsAFailedDependentUnblock` drives `Execute` with a blocked dependent
task whose unblock write fails, failing **only** that task's save (the fake gained a `saveErrOn` seam so the
completed task's own earlier write still succeeds). Red before the fix, with the source stashed and the test left in
place: *"a dependent task whose unblock failed to save was reported as success"*. Green after. `gofmt` clean,
`go vet ./fastmcp/task_management/application/use_cases/` clean, module-wide `go test ./... -count=1` green.
Nothing was pushed.
