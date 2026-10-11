## The database-gated replay case now says what it did not run, and it was run

### Changed
- `agenthub_go/fastmcp/server/httpapp/missed_notification_replay_test.go`: the shared bring-up `newMissedNotificationAppEnv` - three cases in this package depend on it - skips with `SKIPPED, NOT PASSED: AGENTHUB_TEST_PG_URL is unset, so this case did NOT run - and .github/workflows/ci.yml provides no database either; the comment above names the two commands that run it`, and its doc comment names the three dependent cases, the CI job that runs none of them (`go vet ./... && go test ./...`, no service, no `AGENTHUB_TEST_PG_URL`), and the two commands that do. The old message, `AGENTHUB_TEST_PG_URL not set`, read as coverage for the offline store and its replay, which has no other guard.

### Verified
- The gated case RUNS and passes: `bash tools/testpg/start.sh` (the shipped throwaway PostgreSQL 16.4 on 55432), then `AGENTHUB_TEST_PG_URL=postgresql://agenthub_user@127.0.0.1:55432/postgres go test -count=1 -v ./fastmcp/server/httpapp/ -run 'TestMissedNotificationStoredOfflineAndReplayedOnce|TestBroadcastNotifyIsAuthedAndIgnoresBodyUser'` -> **both PASS**, the replay case in 1.97s. The whole package with the database: `ok` in 14.3s.
- This is the first actual run of that case. The entry `2026-10-10--anyone-could-forge-a-notification-for-any-user-through-post-api-v2-broadcast.md` records its edit as "compile-verified only and has not been run against a database"; it now has been, at HEAD, with the token supplying the user and the body naming another user.
- Without the database, 15 cases in this package print SKIP (measured) - that is the condition CI runs in.

### Not changed, and why
- CI is untouched. Setting `AGENTHUB_TEST_PG_URL` in the `go` job would turn on every database-gated test in the repository at once (15 in this package alone) and none of that was measured here, so it is a separate change for the lead to route, not a rider on this row.
