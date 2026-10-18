# The gate wire carries per-path counts

The `agenthub_client` gitlink moves from `2ced214` to `4c8f18e` - the merge of
`4genthub-min/gate-wire` (`6b5abb0`), which the reviewer passed twice (once on
`b6a8f5e`, then on the case-insensitive tip `6b5abb0`).

Why: a criterion that names a file count ("`files_changed` = 3") could not be
settled from the evidence the completion gate hands its judge. The wire now
carries the numstat rows as anonymous changes, and the count key is a register
fact:

- `internal/clientevidence/numstat.go` - one line per path from `git show --numstat`.
- `internal/clientjev/countsonly.go` - a count criterion matches on the register
  only; the branch is inferred from the window it was measured in.
- `internal/clientjev/jev.go` - the count key match is case-insensitive, as names
  already normalises the criterion.
- `internal/clientcomplete/gate.go` - the ten-key state and the per-path rows.

No path text is admitted to the wire beyond the anonymous rows the count needs.

Tests at the merge: client `go vet ./...` rc 0 and `go test ./...` rc 0
(35 packages). Reviewer: `go vet ./...` and `go test ./...` rc 0 across 31
client packages at the branch tip.

Task: 86e4d618 (board), reviewer rows `qitem-20261018215122-4a7610689c4d`
(PASS `b6a8f5e`) and `qitem-20261018215811-807a618be919` (PASS `6b5abb0`).
