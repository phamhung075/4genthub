## Changed

- `agenthub_client` pin moves `a2c1df3` -> `02bffb1` (1 commit).

### Added

- The completion gate now refuses a criterion its own four-field bundle carries no fact about - the
  `gate` command name, its exit code, a numstat path and a base/head sha prefix of 7+ characters
  (`internal/clientcomplete/gate.go`, `internal/clientjev/jev.go`). Such a criterion is answered
  `unjudgeable` deterministically, with NO call to the judge route; one such criterion refuses the task;
  the enforced CLI exit stays 6. This closes the defect task `283fb358` records: the bundle carries no
  file contents and no command output, so a behaviour-shaped criterion was previously scored low by a
  judge that could never see it, however the criterion was worded.
- Five cases in `internal/clientcomplete/complete_test.go` pin the refusal, including Outcome 1's own
  three criteria: `unjudgeable`, each refused criterion named in the reply, the register printed, and
  zero calls to the judge route. Three existing cases moved to criteria that carry register facts, and
  `TestCriteriaVerdicts` likewise - their subject is the flow and the verdict mapping, neither of which
  changed.

### Measured, so the refusal is checkable

- Red first: run against the base `a2c1df3`'s `gate.go` through `go test -overlay`, four of the five new
  cases fail on their assertions - Outcome 1's criteria answered `accept` at 0.99/0.99/0.99 with the
  judge called, a numstat path the bundle does not carry judged, a sha the bundle does not name judged,
  and one refused criterion scored `uncertain` ("Jev answered 2 of 3 criteria") instead of refusing the
  task.
- The enforced CLI on Outcome 1's real criteria: exit 6, `{"verdict":"unjudgeable",...}`, zero calls to
  the judge route, and no other write; the measured register's own shape: exit 0 after one judge call,
  evidence and completion posted.

Validated: gated by the reviewer at `02bffb1` - fresh worktrees, `go build`/`go vet`/`gofmt -l` clean,
`go test -count=1 ./...` = 32 packages ok / 0 FAIL, the five named tests pass, the base is red 4/5 by
`-overlay`, and five mutations are caught by their own tests. The parked `TEST-CHANGELOG.md` section for
this lane rides in this commit, as its parked note asked.
