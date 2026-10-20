## Changed

- `agenthub_client` pin moves `02bffb1` -> `c3f5a7e` (1 commit).

### Fixed

- The register gate's fourth verdict now has its first consumer. `4genteam activity --problems` kept `reject`
  and dropped `unjudgeable`, so a task the enforced gate had refused was invisible in the one view an operator
  reads to ask why a task did not close (`internal/clientactivity/activity.go`; the reviewer's finding F1 on the
  register lane). `uncertain` stays out of `--problems`, which is the reviewer's ruling rather than an omission:
  its "the task has no acceptance criteria" branch is a task-shape fact, not a refusal.
- `TestProblemsKeepsAnUnjudgeableGateAndDropsAnAcceptingOne` serialises its three rows from `clientjev.LogEntry`
  - the writer's own type, so the fixture cannot drift from what the completion appends - and asserts that both
  refusing verdicts are kept, that an acceptance is not, and that a kept row renders as one line naming the
  verdict and the task. Red at the lane's base via `-overlay` (only the rejecting row survives).

### Measured, so the filter is checkable

- `TestTheRegisterFindsAWholeNumberAndNotASubstring` pins `containsInteger`'s precision - the helper the
  reviewer's mutation M3 showed no test bound: `0` is not found inside `10` or inside `0.98`, while the
  trailing dot of "exit code 0." still counts as this run's exit code.
- The gate was verified end to end through the real writer and the real flag path: `unjudgeable` and `reject`
  are kept, `accept` and `uncertain` are dropped.

Validated: gated by the reviewer at `c3f5a7e` (client main fast-forwarded `02bffb1` -> `c3f5a7e`):
`go build ./...`, `go vet ./...` and `gofmt -l` clean, 32 packages ok / 0 FAIL, and the red-first reproduction
at the base. This pin's hub entry and the parked `TEST-CHANGELOG.md` section for the lane both sit in the
working tree, owed to the next non-doc carrier commit - `docs-only-guard` cannot see a gitlink, so a pin commit
carrying its own docs is refused for a seat (`qitem-20261017002819`).
