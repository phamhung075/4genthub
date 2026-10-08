Decision: remove the Python backend (`agenthub_main/`) in four stages. The deletion comes last, in a commit of its own. Before it can be filed, every gap in the list below must read PORTED or DECLARED OUT OF SCOPE by the owner. The schema's source of truth becomes versioned SQL migrations in `agenthub_go/migrations/`, held to the Go row definitions by a Go test. There is no ORM.

Provenance: the owner decided this on 2026-10-08. It reached this seat from the principal at 18:32Z, with the addendum "all code must be written in Go; whatever the Python server does that Go does not yet do must be ported first". The lead's spec followed at 18:32Z and 18:33Z (sequence, parity record, gap list as the gate). Everything below was measured on 2026-10-08 at `44c81bcb`. Each absence names where it was looked for. A search inside the repository says nothing about `~/.openrig` or any other place outside it. The lead's 18:39Z correction about `COUNTS-AUDIT.py` shows the trap: one scope was reported as the whole world.

One correction to the premise first. The parity record does **not** live in the tree being deleted. `MIGRATION.md` and `PROD_READINESS_REPORT.md` are tracked at `agenthub_go/MIGRATION.md` and `agenthub_go/PROD_READINESS_REPORT.md` (`git ls-files`), so both survive. What breaks is the citations that run from surviving files into `agenthub_main/`. 120 tracked files outside `agenthub_main/` contain the string `agenthub_main` (`git grep -l 'agenthub_main' -- ':!agenthub_main' | wc -l`). That includes 45 lines in 31 Go files, 33 lines in eight Markdown files under `agenthub_go/`, and 29 files in `ai_docs/`. The `agenthub_go/*.md` files also carry 14 `file.py:N` citations. Stage 3 says where each one points afterwards.

## Part 1: the gate

`MIGRATION.md` has eight unchecked boxes (`command grep -n '^- \[ \]' agenthub_go/MIGRATION.md`: lines 809-815 and 861). This list transfers what they still owe. Each box is read as PORTED (the Go file named), UNPORTED (what Python does that Go does not), or NOT A GAP (with the reason). Rows G1-G6 are the work items. The deletion row cannot be filed while any G row is open.

How the gaps were found, so a reader can judge the instruments:
- **Routes.** Every `@<router>.get/post/put/patch/delete/websocket("...")` in `agenthub_main/src/fastmcp` (tests excluded), joined with its file's `APIRouter(prefix=...)`, gives 106 paths. Each path was matched against the paths in `ai_docs/api-integration/surface-inventory.md`, and the 9 without a match were then checked against the Go source and against Python's mount sites (`http_server.py` `include_router` lines). The 97 matches rest on the inventory, not on a re-reading of the Go source. Stage G5 re-checks them on the running server.
- **Files.** For each of the 667 non-test, non-`__init__` Python files under `agenthub_main/src/fastmcp`, I looked for a Go file at the same relative path under `agenthub_go/fastmcp`. 40 have none. 18 of them are FastMCP client/CLI library code (`client/`, `cli/`, `__main__.py`, `setup.py`, `utilities/{logging,exceptions,tests}.py`, `server/__main__.py`), which is not server behaviour. The rest were found under other names in Go, or found unreachable in Python (rows below).
- **Markers.** `command grep -rn -i "dropped\|unported\|not ported" agenthub_go/fastmcp --include=*.go`, test files excluded, gives 159 lines: 54 infrastructure, 41 application, 18 interface, and the rest spread out. Most record dropped logging or unused arguments. A few record dropped behaviour (G3).

| Box | Verdict | Evidence |
|---|---|---|
| 809 Slice 1c-iii-c (domain services, validators, enums) | PORTED; the box is stale | `domain/services`: 19 Python files, 19 Go files, same names. `domain/validators`: 1 and 1. The seven `domain/enums/*.py` live in `domain/value_objects/` in Go (`agent_roles.go`, `common_labels.go`, `compliance_enums.go`, `estimated_effort.go`, `progress_enums.go`, `rule_enums.go`, `template_enums.go`). |
| 810 Slice 2 (schema) | UNPORTED: G1 and G2 | Go's schema still depends on the Python tree. When the database is empty and `AUTO_MIGRATE=true`, `DatabaseInitializer` runs `init_schema_postgresql.sql` (`db_initializer.go:72`), and the path resolves to `agenthub_main/src/fastmcp/task_management/infrastructure/database/` (`db_initializer.go:239`). `models.go:1` says "Code generated from infrastructure/database/models.py", and its generator `agenthub_go/tools/gen_models/gen_models.py` imports the Python `Base`. The task tables' parity rests on a hand transcription (`MIGRATION.md:821`). Six `ProductionTables` are declared and never created (`models_prod.go:96`, inventory §3.4). Closed by Stage 1. |
| 811 Slice 3 (application) | PORTED for what the server reaches, apart from G3 | Every application package has a Go directory. Not gaps: `template_engine_service.py`, because Python's `TemplateUseCases` is referenced only by the template engine, `template_domain_service.py` and `email_service.py`, and by no mounted route or tool. `event_handler_initializer.py`, because the function Python actually calls at startup (`infrastructure/events/__init__.py:14`, called from `mcp_entry_point.py:823`) only returns `True`. `task_event_handlers.py` is reached only through that dead initializer. |
| 812 Slice 4 (routes, MCP tools) | PORTED, apart from G4 | Of the 9 route paths without a match: the three `/api/v1/analytics/*` are not mounted by Python (no `include_router` for them in `http_server.py`), so they are not a gap. `/api/v2/branches/{id}/task-counts` and `/assign-agent` were deleted from Go on purpose (`c08063d5`, `f33db13a`). `/auth/supabase/oauth/{provider}` is served by the prefix route at `supabase_endpoints.go:452`. `POST /projects` (`permissions.py:255`) and `/ws/context/{client_id}` (`context_notifications.py:460`) appear only in docstrings. **`/ws/task-polling` is mounted by Python (`websocket_routes.py:847`, through `http_server.py:383`) and is not served by Go: G4.** MCP tools: `TestToolDefinitionsMatchPythonToolRegistry` against `interface/testdata/tools_golden.json`. The `call_agent` tool was removed on purpose (inventory §4). |
| 813 Slice 5 (auth) | PORTED at route level | Every Python `/api/auth/*` and `/auth/supabase/*` path has a Go registration (inventory §1.18-1.19). Behaviour is proved in G5. |
| 814 Slice 6 (websocket v2, session_stream) | PORTED, apart from G4 | `/ws/realtime`, `/ws/connector` and `/ws/sessions/{id}` are mounted (`ws_mount.go:68-70`). `/ws/{user_id}`, `/ws/health` and `/ws/stats` were declared out of scope by the owner on 2026-10-06 (inventory §1.7). |
| 815 Final (comparison against the running Python server) | REPLACED by G5 | The oracle is what is being removed. Proof moves onto the running Go server. |
| 861 A8 (in-memory hub with more than one replica) | NOT A GAP; it carries over | This is a production-topology decision about Go's hub, not something Python does that Go does not. It moves to `NEXT_GEN.md` as an open owner decision and does not gate the deletion. If the owner wants it as a gate, it becomes G7. |

The gap rows:
- **G1, the init SQL.** Go reads its fresh-database schema from inside `agenthub_main` (`db_initializer.go:239`). Closed by Stage 1: the migrations replace the file, the loader, `gen_models.py` and the "generated" header.
- **G2, path detection keyed on the tree.** Go finds the project root by looking for an `agenthub_main` directory, and it builds SQLite paths inside it: `infrastructure/utilities/directory_utils.go:33,44`, `infrastructure/database/database_source_manager.go:69,80,88,117,129,172-173`, `infrastructure/repositories/subtask_repository_factory.go:58-84,142`, and `fastmcp/dual_mode_config.go:82`. Once the tree is gone, this detection changes answer silently. The Go server is Postgres-only (`MIGRATION.md`, A1), so remove the SQLite branches; do not re-key them on another directory. Nine Go test files also name the tree: `internal/clientsync/status_test.go`, `session_stream/schema_test.go`, `server/httpapp/ws_connector_test.go`, `ws_mount_test.go`, `infrastructure/utilities/directory_utils_test.go`, `infrastructure/database/models_prod_test.go`, `auth/interface/fastapi_auth_test.go`, `config/shared_config_test.go`, and `tools/tool_transform_test.go`. For each one, either it reads a file from the tree (then the fixture moves into its own `testdata/`, frozen) or it only names it (then no change).
- **G3, behaviour Go dropped.** These are the markers that record behaviour rather than logging:
  - `use_cases/delete_branch.go:56` and `delete_project.go:64`: the WebSocket notification is dropped.
  - `facades/agent_application_facade.go:64,149`: the agent created and deleted broadcasts are dropped.
  - `services/domain_service_factory.go:41`: `HintManager` is not ported.
  - `factories/{project,git_branch,task}_facade_factory.go`: they return "... is not ported" when their builder seam is unset.

  For each, show it is unreachable in the running server, or port it. The frontend's realtime sync is the consumer to check for the dropped notifications. The other ~150 markers are checked the same way, and each gets a one-word class: logging, unused-arg, unreachable, or ported-elsewhere. The output is a table in the G3 row, not a claim.
- **G4, `/ws/task-polling`.** Python serves it, and Go does not. No caller was found in `agenthub-frontend/src`, `scripts/` or `agenthub_go` (`command grep -rn "task-polling"`; nothing outside those three was searched). It needs a one-line owner answer: port it, or declare it out of scope like the three on 2026-10-06. Recommended: out of scope, for the same reason as those three.
- **G5, proof on the running Go server**, which replaces "Final". Against a Go server built from the stage-3 tree, on a scratch database created only by the Stage 1 migrations:
  - every path in inventory §1 answers with its documented status for an authorised user, and with 401 or 403 without auth;
  - the MCP `tools/list` matches `tools_golden.json`;
  - Keycloak login and token refresh work end to end;
  - `/ws/realtime`, `/ws/connector` and `/ws/sessions/{id}` each deliver one event;
  - `go test ./...` passes with `AGENTHUB_TEST_PG_URL` set, so the PostgreSQL tests run and do not skip.

  The report records the command for each line and its output. A gate that is never run reads as green while it is red: `COUNTS-AUDIT.py` was one figure behind until `fe216670`, and no seat had been reading its output. The proof is only valid when it is run.
- **G6, the open deviations whose oracle disappears.** `MIGRATION.md:926-944` records T1, T2, P1, N1 and N2: places where Go chose saner behaviour, "pending the user's decision". Without Python there is nothing left to mirror. One owner line closes them all: "Go behaviour stands". Recommended. The same applies to the two always-500 task routes (`decision-task-stats-endpoint.md`, row 6d520676).

## Part 2: the new source of truth

Today the schema has three definitions that can drift apart:
- the Python file `init_schema_postgresql.sql` (744 lines, 24 `CREATE TABLE`);
- Go's `TableDefs` in `models.go`, `models_prod.go`, `models_auth.go`, `seat_tables.go`, `team_tables.go` and `task_event_tables.go`, run by `createAll`, plus four after-the-fact patchers: `column_ensurers.go`, `ensure_ai_columns.go`, `missing_tables.go` and `auto_migration.go`;
- the hand-applied `seat_management/infrastructure/schema/seat_management_postgresql.sql`.

`seat_ddl_parity_test.go` exists because two of these drifted (the ck_modules_kind widening).

Options:
- **A. Versioned SQL migrations are the authority** (the owner's shape). `agenthub_go/migrations/NNNN_<name>.sql` are append-only, embedded with `embed.FS`, applied in order by a small runner in the `database` package, and recorded in a ledger table. Go row structs and `TableDefs` are hand-written and must agree with the migrations. A Go test enforces that agreement. Pros: one file defines each change, and the change itself is reviewable, which `createAll` cannot express because it only creates what is missing. It is plain SQL and Go, with no ORM. It removes the four patchers. Cons: the baseline must be captured correctly once, and every column change needs a migration file as well as a struct edit. The test is what makes that cost safe.
- **B. Go `TableDefs` are the authority** (today's code-first path, without Python). Pros: no new mechanism. Cons: `TableDefs` with `createAll` is an ORM-shaped metadata layer by another name. It still cannot express an `ALTER`, so the patchers stay and keep growing.
- **C. The live database is the authority** (introspect, then generate). Rejected: production becomes the definition, and a change has no reviewed form before it is applied.

Recommendation: A. I agree with the owner's shape, with three refinements.
1. **"Live schema" in the test means a database built by the migrations inside the test**, not production. Tests never connect to production. The test applies every migration to a scratch database (`AGENTHUB_TEST_PG_URL`, the same mechanism as `database_init_integration_test.go`), reads `information_schema.columns`, foreign keys and `CHECK` constraints, and compares them with the Go definitions per table: column names, SQL type, nullability, the set of referenced tables, and the CHECK expressions. That is the comparison `seat_ddl_parity_test.go` already makes, extended from names to types and made general. Comparing names alone would pass for a type drift. Checking production for drift against the migrations is a separate, read-only step (`pg_dump --schema-only`, compared), which the owner runs and approves.
2. **The baseline `0001_baseline.sql` is captured from the schema Go actually runs on.** That means a `pg_dump --schema-only` of a scratch database created by today's Go `AUTO_MIGRATE` path, not a copy of the Python file. It is then reconciled with production's schema in the owner's read-only step, and the six `ProductionTables` go in only if production has them. A production database that already exists is marked as at `0001` and is not re-created. That marking is a production change and needs the owner.
3. **The ledger is the table already declared**, `applied_migrations` (`models_prod.go:118`: `migration_name` UNIQUE, `applied_at`, `success`, `error_message`). Do not invent a second one. Use the standard library and `pgx` only: `go.mod` has no migration library (checked with `command grep -n "goose\|golang-migrate\|atlas\|gorm" agenthub_go/go.mod`, which prints nothing), and the runner is small enough not to need one.

What A removes once the test is green: `createAll` as the creation path, the four patchers, `ExecuteInitSQLFile` and its path function, `tools/gen_models/`, the "Code generated ... DO NOT EDIT" header on `models.go`, `models_prod_test.go`'s comparison with the Python SQL, and `seat_management_postgresql.sql` (folded into `0001`). `seat_ddl_parity_test.go` is superseded by the general test. `session_stream/schema_test.go`'s Python-DDL fixture stays as a frozen fixture, or is dropped for the general test; the dev seat chooses and records the choice. `AUTO_MIGRATE` keeps its meaning (opt-in); only what it runs changes.

The new hierarchy, which replaces "ORM model > database > tests" in `CLAUDE.local.md`:
1. Prompt input: the owner's explicit requirement.
2. Migrations: `agenthub_go/migrations/*.sql`. Append-only. An applied file is never edited; a fix is a new file.
3. Go domain entities and row definitions. They must equal the migrations, and `TestSchemaMatchesGoDefinitions` enforces it.
4. The database. A database that differs from the migrations is a defect in the database.
5. Tests: they check behaviour and do not define it.
6. Code.

The examples change to match: a character limit is read from the migration's `VARCHAR(n)` and the entity's validation, not from `max_length`. PostgreSQL only; no SQLite.

## Part 3: the stages

The lead files one row per stage. Stages 1, 2 and 3 can run in parallel with G2-G6. Stage 4 waits for all of them.

**Stage 1: the source of truth and its test (G1).**
- Behaviour-changing for schema creation. Additive for the migrations directory.
- Dev seat: go-dev.
- May touch:
  - `agenthub_go/migrations/` (new);
  - the `database` package (runner, removals listed in Part 2);
  - `seat_management/infrastructure/` (schema file, parity test);
  - `tools/gen_models/` (delete);
  - CHANGELOG.md, TEST-CHANGELOG.md, and `NEXT_GEN.md` (A8 moved there).
- Must not touch: `agenthub_main/`, any production database or configuration, `captain-definition*`.
- Failing first: `TestSchemaMatchesGoDefinitions` with a fixture migration that adds a column the Go definitions lack. It must be red. With the real migrations it is green.
- Negatives:
  - a type drift (for example `VARCHAR(255)` against `TEXT`) is red, which shows the test compares types and not only names;
  - re-running the runner on a migrated database applies nothing (the ledger is read);
  - a database with tables but no ledger row is refused, not re-created.
- Commands: `cd agenthub_go && go build ./... && AGENTHUB_TEST_PG_URL=<scratch> go test ./fastmcp/task_management/infrastructure/database/... ./fastmcp/seat_management/...`. Then `command grep -rn 'agenthub_main' agenthub_go/fastmcp/task_management/infrastructure/database --include=*.go` must print nothing. At HEAD it prints `db_initializer.go:239` and the `database_source_manager.go` lines.

**Stage 2: the script tests move.**
- Additive, plus a move.
- Dev seat: skills-dev (seat tooling).
- Where they go: `scripts/tests/`, beside the scripts they test. Not the repository root, because new root folders are refused by the hook rules. Not `agenthub_go`, because they are Python.
- Move the twelve files, `git mv agenthub_main/src/tests/scripts/*.py scripts/tests/`. Change each module path from `parents[4]` to `parents[2]` (`test_openrig_seat_policy.py:17` is the pattern).
- What runs them: `python3 -m pytest --noconftest -p no:cacheprovider scripts/tests -q`. No conftest exists above `scripts/tests` (I checked the repository root and `scripts/` for `conftest.py`, `pytest.ini`, `pyproject.toml` and `setup.cfg`; none exists). The flag is kept so that one added later cannot bring back the PostgreSQL hang.
- Baseline, run here at HEAD: `cd agenthub_main && python3 -m pytest --noconftest -p no:cacheprovider src/tests/scripts -q` → **315 passed** in 69s. After the move the new command must print the same count.
- Also touches the canonical command in:
  - `scripts/team/4genthub-min/guide-common.md:24` and `guide-reviewer.md:14`;
  - the seed-library copies `seedlibrary/shared-modules/guide-common.md` and `blocks/guide-reviewer.md`, with their `guides.lock.json` entries re-recorded;
  - `ai_docs/operations/seat-guides/_common.md` and `reviewer.md` if they carry it.

  Decision notes keep their old command as history.
- Owner step: the hook's valid-test-path list is `.claude/hooks/config/__claude_hook__valid_test_paths`. It is not `.valid_test_paths` at the root, which does not exist. It lists `agenthub_main/src/tests` and needs `scripts/tests` added. `.claude` is a separate repository (a gitlink, `160000` in `git ls-files -s .claude`) and is kept out of this repository's commits, so the owner or principal makes that edit.
- If the owner rules that the fleet tooling is rewritten in Go (open; see Part 5), these tests go with their scripts, and the move becomes temporary rather than wasted.

**Stage 3: CI, docker, hooks, and the rules.**
- Behaviour-changing for builds and for every commit.
- Dev seats: go-dev for CI and docker; the lead or the principal for `CLAUDE.local.md`, which is the owner's file.
- Touches:
  - **The pre-commit config, first in this stage, and it is the load-bearing item.** The installed `.git/hooks/pre-commit` runs pre-commit with `--config=agenthub_main/.pre-commit-config.yaml`. Measured here in a scratch repository with pre-commit 4.4.0: when the configured file is missing, `git commit` exits 1 and makes no commit. **Deleting the tree before this moves would stop every seat's commit, including the revert.** Move the config to `scripts/git-hooks/pre-commit-config.yaml`. Drop its two `ruff` hooks (`files: ^agenthub_main/`). Keep the generic hooks and `seat-trailer`. Re-installing with `pre-commit install -c scripts/git-hooks/pre-commit-config.yaml` writes `.git/hooks`, which is an owner step. A root `.pre-commit-config.yaml` would need the owner to allow a new root file.
  - `.github/workflows/test_coverage.yml`: its Python jobs (`working-directory: agenthub_main`, lines 83-291) are replaced by a Go job (`go build`, `go vet`, `go test` with a PostgreSQL service) and a script-test job (Stage 2's command). `production-deployment.yml:65-71`: drop the `skip-dirs: 'agenthub_main'` line and its comment. Changing a deployment workflow needs the owner.
  - Docker, removed:
    - `Dockerfile.backend.dev` and `Dockerfile.backend.production`;
    - `docker-compose.backend-frontend.yml`, `docker-compose.dev.yml` and `docker-compose.production.yml`, which build those;
    - `docker-compose.yml` and `docker-compose.optimized.yml`, which already point at Dockerfiles that do not exist (`docker-system/docker/Dockerfile.backend`, `agenthub_main/docker/Dockerfile`; `ls` fails for both).

    Kept: `Dockerfile.backend.go`, `docker-compose.backend-go-frontend.yml`, `db-only`, `pgadmin`, and the frontend files. `docker-menu.sh`, `lib/{development,troubleshooting,workflows}.sh` and `start-production.sh` lose their Python paths, and the Go option becomes the default. `captain-definition.backend` and `.backend.go` already build `Dockerfile.backend.go`, so production's build definition does not change.
  - Scripts that drive the Python backend or its ORM, removed: `batch-test-runner.py`, `run-tests.py`, `validate_suite.py`, `test-menu.sh`, `start_backend_dev.sh`, `verify_init_schema.py`, `deep_verify_schema.py`, `generate_schema_sql.py`, `compare_schema.py`, `check_fk_cascade.py` and `inspect_database.py`. Stage 1's test replaces the schema tools. `backup-production.sh` and `deployment/security/apply-security-fixes.sh` lose their Python paths; they touch production, so the owner reviews them.
  - `.automation/claude-test-sync-wsl.sh`, the `.gemini/commands/*.toml` and `gemini.local.md`, and `agenthub-frontend/src/components/help/sections/ClaudeHooks.tsx` (help text) are each edited or removed. The two frontend test files only name the path in comments.
  - `CLAUDE.local.md`: the hierarchy from Part 2 replaces "SOURCE OF TRUTH HIERARCHY", the ORM paths, the Python quick-dev commands, the schema-management table and "Key Learning". The no-compatibility rules stay.
  - **The parity record.** `agenthub_go/MIGRATION.md` and `PROD_READINESS_REPORT.md` stay as history, as the stats decision ruled. Each gets one pointer line at the top: "Closed by `ai_docs/architecture-design/decision-remove-python-backend.md`. A Python path cited below resolves at tag `python-backend-final`." That one line repairs the 14 `file.py:N` citations and every `agenthub_main/...` mention in those documents without rewriting history. `PROD_READINESS_REPORT.md:179` → `MIGRATION.md:951` keeps working, because both files survive. The 45 Go comment lines ("ports X.py") stay as provenance and read as tag-relative too. Rewriting them is churn with no reader. `ai_docs/` (29 files) gets the same treatment: history stays; a living guide whose instructions name the tree is edited.
- Acceptance: the pre-commit probe is repeated against the moved config, and a seat's commit succeeds after the owner re-installs. Then `git grep -l 'agenthub_main' -- ':!agenthub_main' ':!CHANGELOG.md' ':!TEST-CHANGELOG.md' ':!agenthub-frontend/CHANGELOG.md' ':!ai_docs' ':!agenthub_go'` prints only files the lead has accepted as history. At HEAD it prints the list above. Then `docker compose -f docker-system/docker/docker-compose.backend-go-frontend.yml config -q` exits 0.

**Stage 4: the tag, then the deletion, last and alone.**
- Precondition: G1-G6 closed, with Stage 1-3 commits on main and G5's report filed.
- Tag: `git tag -a python-backend-final -m "last commit with agenthub_main" <stage-3 HEAD>`. The standing rule names tagging, so the owner approves the tag. It stays local and is not pushed without the owner.
- The deletion commit: `git rm -r --quiet agenthub_main` and nothing else in it, with CHANGELOG.md in a separate commit right after it. `git show --stat <deletion>` must list only `agenthub_main/` paths, so a `git revert` brings back exactly the tree. 1595 tracked files.
- Untracked contents remain on disk: `.venv`, `venv`, `agenthub_dev.db`, `logs`, caches, `py_test.log`, `.claude`, and a stray file named `-X main.installedPinsDir=`. They are the owner's to move aside rather than delete, because `agenthub_dev.db` may hold data.
- Recovery: `git revert <deletion>`, or `git checkout python-backend-final -- agenthub_main`. Neither needs the network.
- Acceptance:
  - `go build ./... && go test ./...` in `agenthub_go`, with `AGENTHUB_TEST_PG_URL` set, passes after the deletion;
  - Stage 2's command still prints 315 passed (or the count at that time);
  - a seat commit succeeds;
  - G5's server proof is re-run on the post-deletion build.

## Part 4: what stays out of scope

Not touched by any stage here: `captain-definition*`, any production database, CapRover configuration, `.git/hooks` (owner), `.claude/` (a separate repository), the frontend apart from the help text, and `agenthub_go/internal/clientbridge/testdata/*` (frozen fixtures). The root strays `=4.0.0` and `test_fixes_summary.md` mention the tree and are left for a separate tidy-up, not folded into the deletion.

## Part 5: open question, the Python tooling outside the backend

This is the owner's question and is not decided here. The inventory below lets the answer drop in without rewriting the note. Measured with `git ls-files 'scripts/*.py'` (22 files) and `find .claude/hooks -name '*.py'` (43 files, in the separate `.claude` repository).

| Group | Files | Status after the backend removal |
|---|---|---|
| Fleet tooling, which the seats run | `openrig_bridge`, `openrig_compact_supervisor`, `openrig_scrub`, `openrig_seat_client`, `openrig_seat_policy`, `openrig_seat_sync`, `openrig_team_setup`, `openrig_watch_tools` (8; each has one test in `src/tests/scripts/`), plus `scripts/git-hooks/prepare-commit-msg` (shell) | Survives the removal unchanged. **This is the part the owner's question covers.** The 315 tests move with Stage 2 either way. |
| Python-backend tools | the 11 scripts Stage 3 removes | Go with the backend, whatever the answer. |
| Python code-mod tools | `add_future_annotations`, `fix_code_quality`, `modernize_type_hints` | They rewrite Python source. With no backend, their only target is the fleet tooling. Remove them if the tooling goes to Go; keep them if it stays. |
| API probes | `test_mcp_crud_suite.py` (an MCP CRUD run against a server), `test-keycloak-auth.py` (Keycloak grants) | They exercise the server over HTTP, so either language works. Candidates for G5's proof script. |
| Claude Code hooks | `.claude/hooks/*.py` (43) | A different repository and a different runtime contract (Claude Code invokes them). Size this separately if the answer includes it. |

Sizing for the owner: the fleet tooling is 8 scripts and 315 tests, which is the second half of "all code in Go" if the answer is yes.

Handoff: to the lead, who files the stage rows from Part 3 and the gate rows G1-G6. Owner decisions this note needs:
- G4: `/ws/task-polling` out of scope?
- G6: "Go behaviour stands"?
- A8 stays non-gating?
- the tag;
- the pre-commit re-install;
- the CI deployment edit;
- the production schema read and the ledger marking;
- the Part 5 tooling question.

Dependencies: nothing here depends on anything deleted or never built. `applied_migrations` is declared today, and `pgx` is in `go.mod`. Stage 4 depends on every other row.
