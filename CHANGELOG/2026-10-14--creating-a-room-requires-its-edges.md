## Creating a room requires its edges

### Changed
- `agenthub_client/docs/AGENT-SETUP.md` (2.2 c, 2.3): all five link kinds are listed; a room is created with its links, with a stated minimum (lead delegates to every seat, each worker delegates to the reviewer, every non-lead seat escalates to the lead); the dry run's `link` lines are counted against the agreed edges; after apply the links are read back from the cloud and written to the local `spec.json`.
- `agenthub_client/skills/client/spawn-team/SKILL.md` (spawning a new team, step 1): `edges` are required, with the five kinds, the same minimum, and how to check them.

- `agenthub_client/internal/clientteam/plan.go` (`loadTeam`): a team of more than one seat with no `links` is refused with "a room of N seats needs its links", so `team apply` and its `--dry-run` stop before anything is sent. A one-seat room needs none.

### Tested
New `internal/clientteam/links_required_test.go` (3 cases); `go vet` clean and `go test ./...` passes in the client. The worked example in 2.7 already satisfies the minimum. Not committed: the client repo has these files modified on `feat/support-agy-watch`.
