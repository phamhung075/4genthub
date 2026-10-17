# G3 drop classification

G3 of the Python-removal gate (the single architecture file, §G3) says every Go comment that
records behaviour the Python tree had and the port does not must carry a one-word class:
`logging`, `unused-arg`, `unreachable` or `ported-elsewhere`. The reviewer's table from HEAD
`15693b6a` lived in a seat session and was never committed, so the gate could not be read from the
tree. This file is that table, re-derived from the tree and re-runnable.

## The sweep

Run from the REPOSITORY ROOT (`scripts/G3-DROP-CLASSIFY.py` refuses any other cwd):

```
$ python3 scripts/G3-DROP-CLASSIFY.py
G3-DROP-CLASSIFY: root=/home/daihu/.config/4genthub/rooms/4genthub-min/wt/architect
  swept 760 tracked non-test .go file(s) under agenthub_go/ from the repository root
  candidates=96 markers=48 non-markers=48
  classes: logging=16, ported-elsewhere=11, unreachable=11, unused-arg=10
  not markers: agrees=20, domain=24, named=4
```

`--list` prints every candidate with its comment line; `--self-test` deletes one row and invents
another, and requires both to be named, so a green run cannot come from an instrument that never
looks. Exit 1 names every unclassed candidate and every stale row.

The root and the file count are printed because the same lexical sweep run inside `agenthub_go/`
reads as clean for the wrong reason: its pathspec is a subtree and its relative paths stop matching
this table's rows. That false clean is what the file count guards.

## What a candidate is

A comment line (the text after the first `//`) in a tracked, non-test `.go` file under
`agenthub_go/` that carries BOTH an absence term (`dropped`, `not ported`, `no-op`,
`no equivalent`, `unreachable`, `omitted`, `skipped`, `does not exist`, ...) and a Python
reference (the word `python`/`Python`, a `.py` path, or a snake_case identifier). Both, on the same
line: an absence term alone matches the domain's own vocabulary ("a dropped answer is acked"),
and a snake_case token alone matches SQL columns (`uuid_generate_v4`, `next_action`) and the path
`agenthub_go` itself. The second table lists every candidate that is NOT a marker, so nothing the
sweep saw disappears silently.

## What this does not cover

* The Python tree (`agenthub_main` was deleted 2026-10-09; the last copy is the tag
  `python-backend-final`). A Python behaviour no Go comment mentions leaves no marker to class;
  this measures the Go-comment census and nothing else.
* `_test.go` files: test prose says "dropped" about fixtures, not about the server.
* Markers whose comment wraps so the absence term and the Python reference land on different
  lines: the sweep is line-keyed, and such a half-line appears in the second table when only one
  half qualified.

## Markers (48)

The class is the verdict; the basis is the check that settles it.

| Marker | Disposition | Basis |
|---|---|---|
| `agenthub_go/fastmcp/auth/keycloak_dependencies.go:408` | ported-elsewhere | FastAPI `Depends` wrappers have no Go form; auth runs as middleware (`auth/middleware/dual_auth_middleware.go`) |
| `agenthub_go/fastmcp/auth/middleware/dual_auth_middleware.go:247` | unused-arg | `usage_count` has no reader in the application layer (`api_token.go:30`, `token_validator.go:159` only marshal it), and the layering rule forbids the DB write |
| `agenthub_go/fastmcp/auth/middleware/jwt_auth_middleware.go:20` | ported-elsewhere | `require_auth` is a route decorator; the same routes carry the middleware instead |
| `agenthub_go/fastmcp/auth/services/mcp_token_service.go:7` | ported-elsewhere | the async methods are the same service's ctx-first methods |
| `agenthub_go/fastmcp/config/tool_registry.go:130` | logging | the group summary is only logged; no state changes |
| `agenthub_go/fastmcp/middleware/response_validator_middleware.go:442` | logging | the try/except only logs; the response path is unchanged |
| `agenthub_go/fastmcp/middleware/websocket_message_logger.go:218` | logging | an `__init__` log call; no state |
| `agenthub_go/fastmcp/server/routes/analytics_routes.go:10` | unreachable | no analytics route is mounted, and the ported helpers' only caller is `drafting_routes_test.go:19` |
| `agenthub_go/fastmcp/server/routes/token_router.go:2` | ported-elsewhere | `Depends` plumbing becomes explicit arguments; the handlers are ported |
| `agenthub_go/fastmcp/task_management/application/services/audit_service.go:14` | logging | the log call is the drop |
| `agenthub_go/fastmcp/task_management/application/services/branch_statistics_integration_service.go:11` | logging | the log call is the drop |
| `agenthub_go/fastmcp/task_management/application/services/context_cache_optimizer.go:515` | ported-elsewhere | the attribute-access shim becomes map access in the same service |
| `agenthub_go/fastmcp/task_management/application/services/context_cache_service.go:12` | unreachable | `ContextCacheRepository` has no implementation and the service is built with nil (`unified_context_service.go:116`) |
| `agenthub_go/fastmcp/task_management/application/services/context_delegation_service.go:101` | unused-arg | `session`/`user_id` is not taken; the repository is returned unchanged |
| `agenthub_go/fastmcp/task_management/application/services/context_inheritance_service.go:18` | logging | nil stands for None; the log call is the drop |
| `agenthub_go/fastmcp/task_management/application/services/unified_context_service.go:556` | ported-elsewhere | delegation is skipped in sync mode, which is the port's only mode |
| `agenthub_go/fastmcp/task_management/application/use_cases/ai_task_creation_use_case.go:56` | ported-elsewhere | the dependency is injected through the constructor |
| `agenthub_go/fastmcp/task_management/application/use_cases/batch_context_operations.go:261` | unreachable | `CopyContexts` has no non-test caller, so `include_task_contexts` is never read |
| `agenthub_go/fastmcp/task_management/application/use_cases/complete_task.go:81` | ported-elsewhere | production wiring passes `completeContextFactory` (`task_wiring.go:154`); nil is the test form |
| `agenthub_go/fastmcp/task_management/application/use_cases/create_task.go:154` | logging | invalid dependencies are skipped in both; only the Python log differs |
| `agenthub_go/fastmcp/task_management/application/use_cases/delete_branch.go:20` | unused-arg | `db_session_factory` and `logging_service` are unused arguments |
| `agenthub_go/fastmcp/task_management/application/use_cases/delete_task.go:19` | unused-arg | `db_session_factory` and `logging_service` are unused arguments |
| `agenthub_go/fastmcp/task_management/domain/exceptions/authentication_exceptions.go:19` | unused-arg | a Python default argument; `""` cannot be told from omitted |
| `agenthub_go/fastmcp/task_management/domain/services/event_dispatcher.go:15` | unused-arg | an unused dict field |
| `agenthub_go/fastmcp/task_management/domain/services/pagination_service.go:9` | unused-arg | an unused class flag |
| `agenthub_go/fastmcp/task_management/infrastructure/cache/context_cache.go:148` | unreachable | no Redis client in `agenthub_go/go.mod`; the in-memory backend is the only one |
| `agenthub_go/fastmcp/task_management/infrastructure/cache/context_cache.go:17` | unreachable | no Redis client in `agenthub_go/go.mod`; the in-memory backend is the only one |
| `agenthub_go/fastmcp/task_management/infrastructure/database/database_source_manager.go:184` | logging | Python warns and returns; only the log is dropped |
| `agenthub_go/fastmcp/task_management/infrastructure/database/init_database.go:9` | unreachable | the async migration runner needs an async driver, which Go does not have; `AUTO_MIGRATE` runs `create_all` |
| `agenthub_go/fastmcp/task_management/infrastructure/database/schema_validator.go:230` | logging | the Python logging around FAIL/warnings is the drop |
| `agenthub_go/fastmcp/task_management/infrastructure/repositories/mock_repository_factory.go:6` | logging | logging calls are the drop |
| `agenthub_go/fastmcp/task_management/infrastructure/repositories/mock_task_context_repository.go:4` | unused-arg | `session_factory=None` is unused |
| `agenthub_go/fastmcp/task_management/infrastructure/repositories/project_repository.go:5` | logging | `CacheInvalidationMixin` effects are logging; `log_access` is a log |
| `agenthub_go/fastmcp/task_management/infrastructure/repositories/task_repository.go:2097` | unreachable | `ORMTaskRepository.InvalidateCache` has no call site (`grep '\.InvalidateCache\('` finds none) and the cache it fronted is gone |
| `agenthub_go/fastmcp/task_management/infrastructure/repositories/token_repository.go:7` | ported-elsewhere | the APIToken-only methods are the port's whole token surface |
| `agenthub_go/fastmcp/task_management/infrastructure/repositories/user_scoped_orm_repository.go:4` | logging | the audit log is the drop |
| `agenthub_go/fastmcp/task_management/infrastructure/services/performance_cache_manager.go:1056` | unreachable | `cancel()` needs an event loop; there is no task to cancel |
| `agenthub_go/fastmcp/task_management/infrastructure/services/performance_monitor.go:222` | unreachable | `asyncio.create_task` needs an event loop; Go has no monitoring task |
| `agenthub_go/fastmcp/task_management/infrastructure/services/performance_monitor.go:230` | unreachable | `cancel()` needs an event loop; there is no task to cancel |
| `agenthub_go/fastmcp/task_management/infrastructure/unified_logging.go:161` | logging | `WithGroup` no-ops because Python logging has no group |
| `agenthub_go/fastmcp/task_management/infrastructure/workers/metrics_reporter.go:102` | unreachable | no template engine exists in the Go reporter; it builds its output directly |
| `agenthub_go/fastmcp/task_management/interface/facade_provider.go:8` | ported-elsewhere | the `FacadeService` field is the accessor |
| `agenthub_go/fastmcp/task_management/interface/mcp_controllers/subtask_mcp_controller/handlers/crud_handler.go:25` | ported-elsewhere | `tokenTracker` replaces the unported helper |
| `agenthub_go/fastmcp/task_management/interface/mcp_controllers/task_mcp_controller/validators/business_validator.go:145` | logging | the in_progress warning only |
| `agenthub_go/fastmcp/task_management/interface/utils/mcp_parameter_validator.go:6` | unused-arg | decorator and print helpers have no Go form |
| `agenthub_go/fastmcp/types/converters.go:260` | logging | logging calls are the drop |
| `agenthub_go/fastmcp/utilities/id_validator.go:313` | logging | logging of warnings is the drop |
| `agenthub_go/fastmcp/utilities/pyyaml/nodes.go:4` | unused-arg | the marks are always None in the dumper pipeline |

## Candidates that are not markers (48)

`named` - one of the dropped behaviours that already carry their own note in the tree (the task
names them out of this row's bulk scope). `agrees` - Python itself was a no-op, a bug or an
already-unreachable branch, so nothing healthy was dropped. `domain` - the absence word is the
domain's own (SQL, the entity's vocabulary, an incident note), not a parity note.

| Candidate | Disposition | Basis |
|---|---|---|
| `agenthub_go/fastmcp/ledger/domain/entities/handover.go:111` | domain | the absence word is the domain rule (an omitted key is legal when done) |
| `agenthub_go/fastmcp/room_decisions/domain/repositories/room_decision.go:138` | domain | `dropped answer` is the domain noun |
| `agenthub_go/fastmcp/room_decisions/infrastructure/repositories/orm/room_decision_repository.go:334` | domain | `dropped answer` is the domain noun |
| `agenthub_go/fastmcp/room_decisions/infrastructure/repositories/orm/room_decision_repository.go:378` | domain | `no-op` describes the domain's idempotent push |
| `agenthub_go/fastmcp/seat_management/infrastructure/database/seat_tables.go:334` | domain | the absence word is SQL: `uuid_generate_v4() does not exist` |
| `agenthub_go/fastmcp/seat_management/infrastructure/database/seat_tables.go:384` | domain | the absence word is SQL: `uuid_generate_v4() does not exist` |
| `agenthub_go/fastmcp/seat_management/infrastructure/database/seat_tables.go:440` | domain | the absence word is SQL: `uuid_generate_v4() does not exist` |
| `agenthub_go/fastmcp/seat_management/infrastructure/repositories/orm/seat_feedback_repository.go:37` | domain | the absence word is SQL: `uuid_generate_v4() does not exist` |
| `agenthub_go/fastmcp/seat_management/infrastructure/repositories/orm/seat_message_repository.go:36` | domain | the absence word is SQL: `uuid_generate_v4() does not exist` |
| `agenthub_go/fastmcp/server/httpapp/misc_mount.go:143` | domain | `drop every session idle for more` is the ported pruning behaviour, not a parity note |
| `agenthub_go/fastmcp/server/httpapp/task_event_controller.go:73` | domain | `no-op` describes re-taking one's own advisory lock |
| `agenthub_go/fastmcp/task_management/application/event_handlers/progress_event_handlers.go:112` | agrees | `_add_blocker_insight` was a no-op in Python |
| `agenthub_go/fastmcp/task_management/application/event_handlers/progress_event_handlers.go:127` | agrees | Python's call raised AttributeError and was only logged |
| `agenthub_go/fastmcp/task_management/application/facades/token_application_facade.go:12` | agrees | `decode_token` did not exist on the Python service |
| `agenthub_go/fastmcp/task_management/application/services/domain_service_factory.go:243` | named | HintManager, already noted in the tree (task bf16c808 names it out of scope) |
| `agenthub_go/fastmcp/task_management/application/services/domain_service_factory.go:41` | named | HintManager, already noted in the tree (task bf16c808 names it out of scope) |
| `agenthub_go/fastmcp/task_management/application/services/feature_flag_service.go:279` | domain | `the flag does not exist` is the domain's false return |
| `agenthub_go/fastmcp/task_management/application/services/progress_tracking_service.go:138` | agrees | the skipped item matches Python's own try/except |
| `agenthub_go/fastmcp/task_management/application/services/websocket_notification_service.go:68` | agrees | Python swallowed the exception; the no-op matches |
| `agenthub_go/fastmcp/task_management/application/services/workflow_analysis_service.go:655` | agrees | the omitted lines were unreachable in Python too |
| `agenthub_go/fastmcp/task_management/application/use_cases/add_subtask.go:123` | agrees | `TaskCreatedEvent.create` did not exist in Python |
| `agenthub_go/fastmcp/task_management/application/use_cases/complete_subtask.go:137` | agrees | `TaskStatusChangedEvent.create` did not exist in Python |
| `agenthub_go/fastmcp/task_management/application/use_cases/complete_task_optimized.go:165` | agrees | Python called the absent `task.add_metadata`, so it stored nothing |
| `agenthub_go/fastmcp/task_management/application/use_cases/context_search.go:384` | agrees | the except branch was a no-op in Python |
| `agenthub_go/fastmcp/task_management/application/use_cases/create_git_branch.go:43` | agrees | the nested creation was a no-op in Python |
| `agenthub_go/fastmcp/task_management/application/use_cases/create_task.go:180` | agrees | `TaskCreatedEvent.create` did not exist in Python |
| `agenthub_go/fastmcp/task_management/application/use_cases/delete_branch.go:56` | named | named dropped behaviour already in the tree (WebSocketService) |
| `agenthub_go/fastmcp/task_management/application/use_cases/delete_project.go:64` | named | named dropped behaviour already in the tree (WebSocketService) |
| `agenthub_go/fastmcp/task_management/domain/entities/task.go:1155` | agrees | the method was a no-op in Python |
| `agenthub_go/fastmcp/task_management/domain/entities/task.go:715` | agrees | the method was a no-op in Python |
| `agenthub_go/fastmcp/task_management/domain/entities/task.go:718` | agrees | the method was a no-op in Python |
| `agenthub_go/fastmcp/task_management/domain/services/git_branch_name_validator.go:87` | agrees | the final Python check was unreachable in Python too |
| `agenthub_go/fastmcp/task_management/infrastructure/cache/context_cache.go:168` | domain | `None values skipped` is the port's key-building behaviour |
| `agenthub_go/fastmcp/task_management/infrastructure/database/database_adapter.go:129` | agrees | `MigrateToPostgresql` was a no-op in Python too |
| `agenthub_go/fastmcp/task_management/infrastructure/database/db_initializer.go:235` | agrees | `CreateDefaultData` was a no-op in Python too |
| `agenthub_go/fastmcp/task_management/infrastructure/database/ensure_ai_columns.go:28` | domain | `no-op` describes the AUTO_MIGRATE opt-in behaviour |
| `agenthub_go/fastmcp/task_management/infrastructure/database/schema_validator.go:200` | domain | `drop parameters` is the normalisation step |
| `agenthub_go/fastmcp/task_management/infrastructure/database/task_audit_tables.go:4` | domain | `the table does not exist` is SQL metadata, not a parity note |
| `agenthub_go/fastmcp/task_management/infrastructure/database/task_event_ensurer.go:9` | domain | `column "user_seq" does not exist` is a live incident note |
| `agenthub_go/fastmcp/task_management/infrastructure/database/task_event_tables.go:4` | domain | `the table does not exist` is SQL metadata, not a parity note |
| `agenthub_go/fastmcp/task_management/infrastructure/monitoring/metrics_collector.go:231` | domain | `the oldest item is dropped` is the deque's behaviour |
| `agenthub_go/fastmcp/task_management/infrastructure/repositories/cascade_data_provider.go:82` | domain | `a column that does not exist` is SQL, not a parity note |
| `agenthub_go/fastmcp/task_management/infrastructure/repositories/task_repository.go:818` | agrees | the Python raw SQL was dead; the ORM query is the port |
| `agenthub_go/fastmcp/task_management/infrastructure/utilities/directory_utils.go:48` | domain | the word is this file's own note about a branch it deleted; the snake token is the path `agenthub_go` |
| `agenthub_go/fastmcp/task_management/interface/mcp_controllers/auth_helper/services/token_extraction_service.go:46` | domain | `None values are dropped` is the port's parameter-building behaviour |
| `agenthub_go/fastmcp/task_management/interface/mcp_controllers/auth_helper/services/token_extraction_service.go:72` | domain | `drop None values` is the port's parameter-building behaviour |
| `agenthub_go/fastmcp/tools/tool_transform.go:117` | domain | `hidden/dropped` is the transform's own vocabulary |
| `agenthub_go/fastmcp/utilities/json_schema.go:123` | agrees | Python recursed unguarded and raised; the Go guard is the improvement |
