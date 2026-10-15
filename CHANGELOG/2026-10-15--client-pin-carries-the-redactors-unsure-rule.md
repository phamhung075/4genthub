# The client pin carries the redactor's unsure rule

The client main is `8c8233b` ("fix(clientsync): the unsure rule stops withholding paths and tool-call
ids"), and the parent's pin records it: `e41d827` -> `8c8233b`. The client's own entry for that commit is
`CHANGELOG/2026-10-15--redactor-unsure-rule-stops-withholding-paths-and-ids.md`.

What moved in the client: `internal/clientsync/redaction.go` (`+34/-1`) stops withholding paths,
queue-item ids and tool-call ids that the secret scanner cannot classify, while a random secret over the
same alphabet is still withheld as `unsure`; `internal/clientsync/redaction_test.go` (`+24`) adds
`TestEventKeepsPathsAndIdsButWithholdsSecrets`.

Measured before writing this, in the client tree: `git -C agenthub_client rev-parse HEAD` ->
`8c8233b8b508d591a5a954824bf94ad827b35926`; `git diff agenthub_client` in the parent ->
`-Subproject commit e41d827913cc...` / `+Subproject commit 8c8233b8b508...`; `go test
./internal/clientsync` -> `ok  github.com/phamhung075/4genthub-client/internal/clientsync  1.341s`.

CARRIED IN THIS COMMIT, NOT WRITTEN HERE: `TEST-CHANGELOG.md` held five uncommitted lines in the shared
working tree at 17:05:43Z — the entry "2026-10-15 - redactor unsure rule", naming the same test and the
same `go test` line. It is the test record of the revision this pin names, so it rides this commit
instead of staying loose in a shared tree; if its author wanted it in another commit, it is one file and
one entry.

## Not in this change

No parent code, no parent test and no parent document: the pin, that test-changelog entry and this file
are the whole commit.
