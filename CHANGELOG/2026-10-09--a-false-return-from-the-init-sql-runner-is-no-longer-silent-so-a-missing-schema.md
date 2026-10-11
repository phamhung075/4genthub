## A false return from the init SQL runner is no longer silent, so a missing schema cannot pass for a completed run

### Fixed
- `agenthub_go/fastmcp/task_management/infrastructure/database/db_initializer.go` — `ExecuteInitSQLFile` returned `false` on four paths having written **nothing anywhere**. That is why a fresh database in the distroless image failed with no line naming the SQL file (row `b231a84b`): the read of `init_schema_postgresql.sql` resolved through `runtime.Caller`, found nothing, and the caller saw only a bool. All four paths now log — the read failure with the asset name, **the resolved path** and the error; the `BeginTx` failure; the failing statement with its error after the rollback; and the commit failure. The resolved path is the line the container needs: it prints what the binary actually looked for, which is the wrong-path evidence rather than a restatement of it.
- The shape follows the package: `log.Printf("database: could not ...: %v")`, as `missing_tables.go:131`.

### Verified
- **SEEN RED FIRST, on the not-a-directory case rather than a reconstruction.** `TestExecuteInitSQLFileLogsTheUnreadableAsset` resolves a path whose PARENT IS A FILE — the shape the distroless image has for `/agenthub`, where the binary itself is the file — and before the change it failed with `the read failure is silent: log=""`; after it, PASS. `TestExecuteInitSQLFileLogsAFailedStatement` covers the execution path through the scripted fake driver's `failExec`.
- `go test -count=1 ./fastmcp/task_management/infrastructure/database/` → **ok**; `go vet` on the package clean; `gofmt -l` on both files prints nothing; `go build ./...` clean.
