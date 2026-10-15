# The list does not query an id that is not an id

The reviewer's MINOR on `95c60881`, and a regression that commit introduced.

## What was wrong

`TaskListResponseFromDomainList` builds one id slice for its two batch reads, and it built it with
`taskIDString(task)` - which renders a row whose `ID` is nil as the literal string `"None"`, because
that is what the row *displays*. Both queries cast that slice `::uuid`:
`GetCompletedSubtaskCounts` and `ProgressEventsByTask`.

The two reads then differ in exactly the way that turns a tolerance into an outage: the counts read
**swallows** its error (`if err != nil { return map[string]int{}, nil }`), and the notes read - the one
this commit added - returns it. So before `95c60881` a page holding such a row rendered with empty
counts; after it, the same page failed the whole list with `invalid input syntax for type uuid: "None"`.

## The fix

The ids that are ids are the ones queried. `task.ID == nil` or an empty value is skipped once, before
either read, so neither query can see a value that is not a uuid, and the row renders what it has: no
count and no notes. `taskIDString` keeps its one job - the display value the row lookups use - and the
two sides no longer disagree about what an id is.

## Verified

- `go test -count=1 ./fastmcp/task_management/application/dtos/task/ ./fastmcp/task_management/application/use_cases/ ./fastmcp/task_management/application/facades/ ./fastmcp/task_management/application/services/ ./fastmcp/task_management/interface/mcp_controllers/task_mcp_controller/...`
  green; `go build ./...` and `go vet ./fastmcp/task_management/...` rc 0; `gofmt -l` over the tracked
  files empty.
- **Measured red FIRST**, and it reproduces the reviewer's report word for word: with the id slice built
  from `taskIDString` again, `TestTaskListResponseDoesNotQueryRowsWithNoID` fails
  `a row with no id failed the whole list: invalid input syntax for type uuid: "None"`. The case's
  ledger fake refuses a non-uuid the way the cast does, so it fails for the same reason the query does.
