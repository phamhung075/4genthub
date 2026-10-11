## No discarded error on the completion path reads as success

The companion to the dependent-unblock fix, and the lead's extension of it: a discarded error on this path is a
discarded error whether it hides a write or a scan. `updateDependentTasks` opened by loading every task so it could
find the dependents of the one being completed, and a failed load was **skipped** — the pass never ran, `Execute`
returned success, and the caller was told a task was completed with its dependents untouched. That is the same
class as the write it sits beside: a failure that the code knew about and did not pass on.

The error is now returned, so the use case reports a dependent scan it could not perform instead of a completion it
did not fully make.

**Deliberate divergence, same as its sibling.** The old behaviour matched the Python port, which logged both
failures and continued. Python's logging is what made the two indistinguishable to a caller — a retry or a report
needs the error, not a line in a log the caller cannot see.

**Evidence.** New test `TestCompleteTaskReportsAFailedDependentLookup` drives `Execute` with a failing
`FindAll` (the fake's existing `findAllErr` seam). Red before the fix, with the source stashed and the test left in
place: *"a dependent scan whose lookup failed was reported as success"*. Green after. `gofmt` clean, `go vet
./fastmcp/task_management/application/use_cases/` clean, module-wide `go test ./... -count=1` green. Nothing pushed.
