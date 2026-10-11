# The init SQL could never run to completion — 13 names created twice, and the whole asset rolled back

Found while landing the T12 fold: the boot arm of the schema comparison came out at 41 tables when the
registry alone implies 41 **plus** the production tables the asset adds. The reason was not the fold.

## What was wrong, measured

`init_schema_postgresql.sql` creates **13 names twice**: a `CREATE UNIQUE INDEX <name>` in the index
sections (`:521`–`:601`) and, later, an `ALTER TABLE ... ADD CONSTRAINT <name> UNIQUE (...)` in the
constraints section (`:608`–`:638`). A unique constraint is backed by an index carrying the constraint's
name, so PostgreSQL refuses the second statement with `SQLSTATE 42P07 relation "<name>" already exists`.

`ExecuteInitSQLFile` runs every statement in **ONE transaction** and rolls back on the first failure, so
the failure was total rather than partial: **the whole asset rolled back**, and a fresh boot was left
with `createAll`'s 41 tables and none of the tables the asset adds. The failure surfaced at
`uq_cache_context` — the first collision in statement order — which is what hid the other twelve until
the first one was fixed:

`labels_name_key`, `uq_branch_project`, `uq_project_user`, `uq_task_assignee`, `uq_task_dependency`,
`user_api_tokens_token_hash_key`, `user_sessions_refresh_token_key`,
`user_sessions_session_token_key`, `user_token_balances_user_id_key`, `users_email_key`,
`users_password_reset_token_key`, `users_username_key`.

## The fix, and why it is schema-neutral

The 13 redundant `CREATE UNIQUE INDEX` statements are **deleted**; each matching `ADD CONSTRAINT`
creates an index of the same name on the same columns. The registry agrees with the constraint side:
`models.go` declares `CONSTRAINT uq_cache_context UNIQUE (context_id, context_level)` inside the table
(and the generated baseline carries it at line 111), and it has no separate index of that name — as
does the asset, once fixed.

Measured on a scratch database after the fix: of the 13 names whose explicit index statement was
removed, **13 of 13** are still present as index relations (`relkind='i'`), **13** are backed by a
`UNIQUE` constraint, and **none** is missing. The asset now builds **22 base tables** on an empty
database instead of none.

## The two gates (both red first, against the unfixed asset)

- **`init_sql_object_names_test.go`** — `TestTheInitSQLCreatesNoObjectNameTwice`, server-free: collects
  the names the asset creates in one namespace (`CREATE TABLE`, `CREATE [UNIQUE] INDEX`,
  `ADD CONSTRAINT`, whose backing index carries the constraint's name), comment lines dropped so a
  section header reading `-- CREATE TABLES` is not a statement. RED before the fix, naming all 13
  collisions; GREEN after, `97 distinct object names created, 0 collision(s)`.
- **`init_sql_fresh_database_integration_test.go`** — `TestTheEmbeddedInitSQLBuildsAFreshDatabase`,
  DB-gated (skips loudly without `AGENTHUB_TEST_PG_URL` like its neighbours): drives the embedded asset
  through `ExecuteInitSQLFile` on an empty database and then asks the catalogue. RED before the fix with
  the real line — `init SQL statement failed, rolled back: ERROR: relation "uq_cache_context" already
  exists (SQLSTATE 42P07)` — and GREEN after: the file runs to completion, `VerifyTableStructure`
  passes, `uq_cache_context` is one `UNIQUE` constraint, `token_transactions` (which only the asset
  creates) is present, and it logs `22 base tables`.

Why the existing asset tests could not see it: the fake driver records statements and enforces no names,
so an asset that collides with itself passes there. That is the gap these two cases close.

## What this changes for the fold's own evidence

The fold's boot arm measured 41 tables **because the asset never contributed any**. With the asset
completing, the two measured paths union to **44 of the baseline's 47**: 41 from `createAll` (measured)
plus the asset's three production-set tables (`token_transactions`, `user_api_tokens`, `user_sessions`),
which are in the asset and not in the registry's aggregate. The remaining three —
`agent_import_history`, `applied_migrations`, `user_agent_configurations_md` — still have no local
creator: `applied_migrations` is created on demand by the runner, and the other two exist only in the
registry's production set. Stated as a union of the two measured sets, not as a third measurement.

## Not in this change

Nothing else in the asset was touched (13 deleted lines, no other statement edited) and no production
database was contacted. The fold's scope is unchanged: the cutover (deleting `createAll`, the init SQL
and the ensurers) and the ensurers' split stay out; the owner's `0001` baseline mark stays theirs.

## Battery

From `agenthub_go` with `GOCACHE`/`TMPDIR` in-tree: `gofmt -l` over the tracked `.go` files printed
nothing; `go build ./...` rc 0; `go vet ./...` clean; `go test -count=1 ./...` → **141 packages ok, 0
FAIL**; and with `AGENTHUB_TEST_PG_URL=postgresql://agenthub_user@127.0.0.1:55451/postgres` the
DB-gated case above passes on a scratch database that the case creates and drops.
