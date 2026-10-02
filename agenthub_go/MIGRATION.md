# MIGRATION.md — Python `fastmcp` → Go

Source: `agenthub_main/src/fastmcp` (Python, untouched). Target: `agenthub_go/` (module `agenthub`), same directory layout, one `.go` file per `.py` module.
`__init__.py` files map to the Go package clause (no file). Files whose stem ends in a Go-reserved suffix get `_py` appended.

## Slice order
0 shared/config → 1 domain → 2 infrastructure/db → 3 application → 4 server routes/MCP → 5 auth → 6 websocket

## Module map

| Slice | Python module | Go file | Lines | Status |
|---|---|---|---|---|
| 0-shared/config | `__main__.py` | `fastmcp/__main__.go` | 38 | n/a (Python -m entry point; Go binary built from cmd/ or main.go) |
| 0-shared/config | `cli/claude.py` | `fastmcp/cli/claude.go` | 142 | n/a (FastMCP dev CLI Claude desktop config; server-only Go runtime) |
| 0-shared/config | `cli/cli.py` | `fastmcp/cli/cli.go` | 444 | n/a (FastMCP Typer CLI; server-only Go runtime) |
| 0-shared/config | `cli/run.py` | `fastmcp/cli/run.go` | 212 | n/a (FastMCP Uvicorn CLI runner; server-only Go runtime) |
| 0-shared/config | `client/auth/bearer.py` | `fastmcp/client/auth/bearer.go` | 17 | n/a (FastMCP client SDK; server-only Go runtime) |
| 0-shared/config | `client/auth/oauth.py` | `fastmcp/client/auth/oauth.go` | 390 | n/a (FastMCP client SDK; server-only Go runtime) |
| 0-shared/config | `client/client.py` | `fastmcp/client/client.go` | 697 | n/a (FastMCP client SDK; server-only Go runtime) |
| 0-shared/config | `client/logging.py` | `fastmcp/client/logging.go` | 29 | n/a (FastMCP client SDK; server-only Go runtime) |
| 0-shared/config | `client/progress.py` | `fastmcp/client/progress.go` | 40 | n/a (FastMCP client SDK; server-only Go runtime) |
| 0-shared/config | `client/roots.py` | `fastmcp/client/roots.go` | 77 | n/a (FastMCP client SDK; server-only Go runtime) |
| 0-shared/config | `client/sampling.py` | `fastmcp/client/sampling.go` | 48 | n/a (FastMCP client SDK; server-only Go runtime) |
| 0-shared/config | `client/transports.py` | `fastmcp/client/transports.go` | 924 | n/a (FastMCP client SDK; server-only Go runtime) |
| 0-shared/config | `config/auth_config.py` | `fastmcp/config/auth_config.go` | 56 | done |
| 0-shared/config | `config/auth_tools.py` | `fastmcp/config/auth_tools.go` | 187 | done (tested) |
| 0-shared/config | `config/cors_factory.py` | `fastmcp/config/cors_factory.go` | 110 | done |
| 0-shared/config | `config/tool_config_loader.py` | `fastmcp/config/tool_config_loader.go` | 297 | done (tested) |
| 0-shared/config | `config/tool_registry.py` | `fastmcp/config/tool_registry.go` | 249 | done (tested) |
| 0-shared/config | `config/version.py` | `fastmcp/config/version.go` | 24 | done |
| 0-shared/config | `dual_mode_config.py` | `fastmcp/dual_mode_config.go` | 187 | done |
| 0-shared/config | `exceptions.py` | `fastmcp/exceptions.go` | 39 | done |
| 0-shared/config | `session_stream/hub.py` | `fastmcp/session_stream/hub.go` | 39 | done (tested) |
| 0-shared/config | `session_stream/repository.py` | `fastmcp/session_stream/repository.go` | 241 | done (tested) |
| 0-shared/config | `settings.py` | `fastmcp/settings.go` | 433 | done (tested) |
| 0-shared/config | `setup.py` | `fastmcp/setup.go` | 20 | n/a (Python setuptools; Go uses go.mod) |
| 0-shared/config | `task_management/utils/response_formatter.py` | `fastmcp/task_management/utils/response_formatter.go` | 134 | done |
| 0-shared/config | `types/bulk.py` | `fastmcp/types/bulk.go` | 47 | done |
| 0-shared/config | `types/converters.py` | `fastmcp/types/converters.go` | 297 | done |
| 0-shared/config | `types/entities.py` | `fastmcp/types/entities.go` | 178 | done |
| 0-shared/config | `types/responses.py` | `fastmcp/types/responses.go` | 188 | done |
| 0-shared/config | `types/summaries.py` | `fastmcp/types/summaries.go` | 84 | done |
| 0-shared/config | `utilities/cache.py` | `fastmcp/utilities/cache.go` | 26 | done |
| 0-shared/config | `utilities/components.py` | `fastmcp/utilities/components.go` | 76 | done |
| 0-shared/config | `utilities/debug_service.py` | `fastmcp/utilities/debug_service.go` | 387 | done |
| 0-shared/config | `utilities/environment.py` | `fastmcp/utilities/environment.go` | 171 | done (tested) |
| 0-shared/config | `utilities/exceptions.py` | `fastmcp/utilities/exceptions.go` | 51 | n/a (Python TaskGroup exceptiongroup debugging handler) |
| 0-shared/config | `utilities/http.py` | `fastmcp/utilities/http.go` | 8 | done |
| 0-shared/config | `utilities/id_validator.py` | `fastmcp/utilities/id_validator.go` | 602 | done |
| 0-shared/config | `utilities/id_validator_examples.py` | `fastmcp/utilities/id_validator_examples.go` | 346 | done (tested) |
| 0-shared/config | `utilities/json_schema.py` | `fastmcp/utilities/json_schema.go` | 164 | done |
| 0-shared/config | `utilities/logging.py` | `fastmcp/utilities/logging.go` | 205 | n/a (Python logging setup; Go uses unified_logging.go) |
| 0-shared/config | `utilities/mcp_config.py` | `fastmcp/utilities/mcp_config.go` | 89 | done |
| 0-shared/config | `utilities/openapi.py` | `fastmcp/utilities/openapi.go` | 974 | done (tested) |
| 0-shared/config | `utilities/tests.py` | `fastmcp/utilities/tests.go` | 131 | n/a (Python multiprocessing uvicorn test helper; Go uses httptest) |
| 0-shared/config | `utilities/types.py` | `fastmcp/utilities/types.go` | 296 | done |
| 1-domain | `agent_management/domain/entities/agent_template.py` | `fastmcp/agent_management/domain/entities/agent_template.go` | 260 | done |
| 1-domain | `agent_management/domain/entities/user_agent_instance.py` | `fastmcp/agent_management/domain/entities/user_agent_instance.go` | 384 | done |
| 1-domain | `agent_management/domain/enums/ordering.py` | `fastmcp/agent_management/domain/enums/ordering.go` | 18 | done |
| 1-domain | `agent_management/domain/repositories/agent_template_repository.py` | `fastmcp/agent_management/domain/repositories/agent_template_repository.go` | 92 | done |
| 1-domain | `agent_management/domain/repositories/user_agent_instance_repository.py` | `fastmcp/agent_management/domain/repositories/user_agent_instance_repository.go` | 154 | done |
| 1-domain | `agent_management/domain/services/agent_customization_service.py` | `fastmcp/agent_management/domain/services/agent_customization_service.go` | 327 | done |
| 1-domain | `agent_management/domain/services/agent_instantiation_service.py` | `fastmcp/agent_management/domain/services/agent_instantiation_service.go` | 167 | done |
| 1-domain | `agent_management/domain/services/agent_sharing_service.py` | `fastmcp/agent_management/domain/services/agent_sharing_service.go` | 334 | done |
| 1-domain | `agent_management/domain/value_objects/agent_configuration.py` | `fastmcp/agent_management/domain/value_objects/agent_configuration.go` | 142 | done |
| 1-domain | `agent_management/domain/value_objects/agent_template_id.py` | `fastmcp/agent_management/domain/value_objects/agent_template_id.go` | 27 | done |
| 1-domain | `agent_management/domain/value_objects/user_agent_instance_id.py` | `fastmcp/agent_management/domain/value_objects/user_agent_instance_id.go` | 33 | done |
| 1-domain | `agent_management/domain/value_objects/user_id.py` | `fastmcp/agent_management/domain/value_objects/user_id.go` | 31 | done |
| 1-domain | `ai_task_planning/domain/entities/planning_request.py` | `fastmcp/ai_task_planning/domain/entities/planning_request.go` | 227 | done |
| 1-domain | `ai_task_planning/domain/entities/task_plan.py` | `fastmcp/ai_task_planning/domain/entities/task_plan.go` | 488 | done |
| 1-domain | `ai_task_planning/domain/services/requirement_analyzer.py` | `fastmcp/ai_task_planning/domain/services/requirement_analyzer.go` | 632 | done |
| 1-domain | `auth/domain/entities/user.py` | `fastmcp/auth/domain/entities/user.go` | 257 | done |
| 1-domain | `auth/domain/permissions.py` | `fastmcp/auth/domain/permissions.go` | 377 | done |
| 1-domain | `auth/domain/repositories/token_balance_repository.py` | `fastmcp/auth/domain/repositories/token_balance_repository.go` | 167 | done |
| 1-domain | `auth/domain/services/jwt_service.py` | `fastmcp/auth/domain/services/jwt_service.go` | 421 | done |
| 1-domain | `auth/domain/services/password_service.py` | `fastmcp/auth/domain/services/password_service.go` | 256 | done |
| 1-domain | `auth/domain/value_objects/email.py` | `fastmcp/auth/domain/value_objects/email.go` | 65 | done |
| 1-domain | `auth/domain/value_objects/user_id.py` | `fastmcp/auth/domain/value_objects/user_id.go` | 46 | done |
| 1-domain | `connection_management/domain/entities/connection.py` | `fastmcp/connection_management/domain/entities/connection.go` | 115 | done |
| 1-domain | `connection_management/domain/entities/server.py` | `fastmcp/connection_management/domain/entities/server.go` | 168 | done |
| 1-domain | `connection_management/domain/events/connection_events.py` | `fastmcp/connection_management/domain/events/connection_events.go` | 146 | done |
| 1-domain | `connection_management/domain/exceptions/connection_exceptions.py` | `fastmcp/connection_management/domain/exceptions/connection_exceptions.go` | 66 | done |
| 1-domain | `connection_management/domain/repositories/connection_repository.py` | `fastmcp/connection_management/domain/repositories/connection_repository.go` | 47 | done |
| 1-domain | `connection_management/domain/repositories/server_repository.py` | `fastmcp/connection_management/domain/repositories/server_repository.go` | 36 | done |
| 1-domain | `connection_management/domain/services/connection_diagnostics_service.py` | `fastmcp/connection_management/domain/services/connection_diagnostics_service.go` | 38 | done |
| 1-domain | `connection_management/domain/services/server_health_service.py` | `fastmcp/connection_management/domain/services/server_health_service.go` | 36 | done |
| 1-domain | `connection_management/domain/services/status_broadcasting_service.py` | `fastmcp/connection_management/domain/services/status_broadcasting_service.go` | 42 | done |
| 1-domain | `connection_management/domain/value_objects/connection_health.py` | `fastmcp/connection_management/domain/value_objects/connection_health.go` | 51 | done |
| 1-domain | `connection_management/domain/value_objects/server_capabilities.py` | `fastmcp/connection_management/domain/value_objects/server_capabilities.go` | 50 | done |
| 1-domain | `connection_management/domain/value_objects/server_status.py` | `fastmcp/connection_management/domain/value_objects/server_status.go` | 45 | done |
| 1-domain | `connection_management/domain/value_objects/status_update.py` | `fastmcp/connection_management/domain/value_objects/status_update.go` | 83 | done |
| 1-domain | `task_management/domain/constants.py` | `fastmcp/task_management/domain/constants.go` | 88 | done |
| 1-domain | `task_management/domain/entities/agent.py` | `fastmcp/task_management/domain/entities/agent.go` | 479 | done |
| 1-domain | `task_management/domain/entities/agent_session.py` | `fastmcp/task_management/domain/entities/agent_session.go` | 448 | done |
| 1-domain | `task_management/domain/entities/base/base_timestamp_entity.py` | `fastmcp/task_management/domain/entities/base/base_timestamp_entity.go` | 289 | done (tested) |
| 1-domain | `task_management/domain/entities/context.py` | `fastmcp/task_management/domain/entities/context.go` | 1440 | done |
| 1-domain | `task_management/domain/entities/git_branch.py` | `fastmcp/task_management/domain/entities/git_branch.go` | 306 | done |
| 1-domain | `task_management/domain/entities/global_context_schema.py` | `fastmcp/task_management/domain/entities/global_context_schema.go` | 294 | done |
| 1-domain | `task_management/domain/entities/label.py` | `fastmcp/task_management/domain/entities/label.go` | 56 | done (tested) |
| 1-domain | `task_management/domain/entities/project.py` | `fastmcp/task_management/domain/entities/project.go` | 745 | done (create_git_branch_async deferred to repositories slice) |
| 1-domain | `task_management/domain/entities/rule_content.py` | `fastmcp/task_management/domain/entities/rule_content.go` | 121 | done (compiles) |
| 1-domain | `task_management/domain/entities/rule_entity.py` | `fastmcp/task_management/domain/entities/rule_entity.go` | 199 | done (compiles) |
| 1-domain | `task_management/domain/entities/subtask.py` | `fastmcp/task_management/domain/entities/subtask.go` | 621 | done |
| 1-domain | `task_management/domain/entities/task.py` | `fastmcp/task_management/domain/entities/task.go` | 1690 | done |
| 1-domain | `task_management/domain/entities/template.py` | `fastmcp/task_management/domain/entities/template.go` | 271 | done |
| 1-domain | `task_management/domain/entities/work_session.py` | `fastmcp/task_management/domain/entities/work_session.go` | 281 | done |
| 1-domain | `task_management/domain/enums/agent_roles.py` | `fastmcp/task_management/domain/enums/agent_roles.go` | 268 | dup of value_objects/agent_roles.py: see notes |
| 1-domain | `task_management/domain/enums/common_labels.py` | `fastmcp/task_management/domain/enums/common_labels.go` | 374 | dup of value_objects/common_labels.py: see notes |
| 1-domain | `task_management/domain/enums/compliance_enums.py` | `fastmcp/task_management/domain/enums/compliance_enums.go` | 60 | dup of value_objects/compliance_enums.py: see notes |
| 1-domain | `task_management/domain/enums/estimated_effort.py` | `fastmcp/task_management/domain/enums/estimated_effort.go` | 164 | dup of value_objects/estimated_effort.py: see notes |
| 1-domain | `task_management/domain/enums/progress_enums.py` | `fastmcp/task_management/domain/enums/progress_enums.go` | 75 | dup of value_objects/progress_enums.py: see notes |
| 1-domain | `task_management/domain/enums/rule_enums.py` | `fastmcp/task_management/domain/enums/rule_enums.go` | 157 | dup of value_objects/rule_enums.py: see notes |
| 1-domain | `task_management/domain/enums/template_enums.py` | `fastmcp/task_management/domain/enums/template_enums.go` | 96 | dup of value_objects/template_enums.py: see notes |
| 1-domain | `task_management/domain/events/agent_events.py` | `fastmcp/task_management/domain/events/agent_events.go` | 265 | done (tested) |
| 1-domain | `task_management/domain/events/base.py` | `fastmcp/task_management/domain/events/base.go` | 124 | done (tested) |
| 1-domain | `task_management/domain/events/branch_lifecycle_events.py` | `fastmcp/task_management/domain/events/branch_lifecycle_events.go` | 127 | done (tested) |
| 1-domain | `task_management/domain/events/context_events.py` | `fastmcp/task_management/domain/events/context_events.go` | 175 | done (tested) |
| 1-domain | `task_management/domain/events/hint_events.py` | `fastmcp/task_management/domain/events/hint_events.go` | 278 | done (tested) |
| 1-domain | `task_management/domain/events/progress_events.py` | `fastmcp/task_management/domain/events/progress_events.go` | 246 | done (tested) |
| 1-domain | `task_management/domain/events/project_lifecycle_events.py` | `fastmcp/task_management/domain/events/project_lifecycle_events.go` | 96 | done (tested) |
| 1-domain | `task_management/domain/events/task_events.py` | `fastmcp/task_management/domain/events/task_events.go` | 79 | done (tested) |
| 1-domain | `task_management/domain/events/task_lifecycle_events.py` | `fastmcp/task_management/domain/events/task_lifecycle_events.go` | 111 | done (tested) |
| 1-domain | `task_management/domain/exceptions/authentication_exceptions.py` | `fastmcp/task_management/domain/exceptions/authentication_exceptions.go` | 51 | done (tested) |
| 1-domain | `task_management/domain/exceptions/base.py` | `fastmcp/task_management/domain/exceptions/base.go` | 7 | done (tested) |
| 1-domain | `task_management/domain/exceptions/base_exceptions.py` | `fastmcp/task_management/domain/exceptions/base_exceptions.go` | 305 | done (tested) |
| 1-domain | `task_management/domain/exceptions/task_exceptions.py` | `fastmcp/task_management/domain/exceptions/task_exceptions.go` | 158 | done (tested) |
| 1-domain | `task_management/domain/exceptions/template_exceptions.py` | `fastmcp/task_management/domain/exceptions/template_exceptions.go` | 144 | done (tested) |
| 1-domain | `task_management/domain/exceptions/vision_exceptions.py` | `fastmcp/task_management/domain/exceptions/vision_exceptions.go` | 65 | done (tested) |
| 1-domain | `task_management/domain/interfaces/cache_service.py` | `fastmcp/task_management/domain/interfaces/cache_service.go` | 89 | done |
| 1-domain | `task_management/domain/interfaces/database_session.py` | `fastmcp/task_management/domain/interfaces/database_session.go` | 103 | done |
| 1-domain | `task_management/domain/interfaces/event_bus.py` | `fastmcp/task_management/domain/interfaces/event_bus.go` | 92 | done |
| 1-domain | `task_management/domain/interfaces/event_store.py` | `fastmcp/task_management/domain/interfaces/event_store.go` | 64 | done |
| 1-domain | `task_management/domain/interfaces/logging_service.py` | `fastmcp/task_management/domain/interfaces/logging_service.go` | 78 | done |
| 1-domain | `task_management/domain/interfaces/monitoring_service.py` | `fastmcp/task_management/domain/interfaces/monitoring_service.go` | 123 | done |
| 1-domain | `task_management/domain/interfaces/notification_service.py` | `fastmcp/task_management/domain/interfaces/notification_service.go` | 81 | done |
| 1-domain | `task_management/domain/interfaces/repository_factory.py` | `fastmcp/task_management/domain/interfaces/repository_factory.go` | 128 | done |
| 1-domain | `task_management/domain/interfaces/utility_service.py` | `fastmcp/task_management/domain/interfaces/utility_service.go` | 130 | done |
| 1-domain | `task_management/domain/interfaces/validation_service.py` | `fastmcp/task_management/domain/interfaces/validation_service.go` | 112 | done |
| 1-domain | `task_management/domain/repositories/agent_repository.py` | `fastmcp/task_management/domain/repositories/agent_repository.go` | 57 | done |
| 1-domain | `task_management/domain/repositories/base_repository.py` | `fastmcp/task_management/domain/repositories/base_repository.go` | 96 | done |
| 1-domain | `task_management/domain/repositories/context_repository.py` | `fastmcp/task_management/domain/repositories/context_repository.go` | 87 | done |
| 1-domain | `task_management/domain/repositories/git_branch_repository.py` | `fastmcp/task_management/domain/repositories/git_branch_repository.go` | 99 | done |
| 1-domain | `task_management/domain/repositories/label_repository.py` | `fastmcp/task_management/domain/repositories/label_repository.go` | 89 | done |
| 1-domain | `task_management/domain/repositories/project_repository.py` | `fastmcp/task_management/domain/repositories/project_repository.go` | 72 | done |
| 1-domain | `task_management/domain/repositories/rule_repository.py` | `fastmcp/task_management/domain/repositories/rule_repository.go` | 112 | done |
| 1-domain | `task_management/domain/repositories/subtask_repository.py` | `fastmcp/task_management/domain/repositories/subtask_repository.go` | 96 | done |
| 1-domain | `task_management/domain/repositories/task_repository.py` | `fastmcp/task_management/domain/repositories/task_repository.go` | 90 | done |
| 1-domain | `task_management/domain/repositories/template_repository.py` | `fastmcp/task_management/domain/repositories/template_repository.go` | 56 | done |
| 1-domain | `task_management/domain/repositories/token_repository_interface.py` | `fastmcp/task_management/domain/repositories/token_repository_interface.go` | 157 | done |
| 1-domain | `task_management/domain/services/branch_statistics_service.py` | `fastmcp/task_management/domain/services/branch_statistics_service.go` | 257 | done |
| 1-domain | `task_management/domain/services/cascade_calculator.py` | `fastmcp/task_management/domain/services/cascade_calculator.go` | 447 | done |
| 1-domain | `task_management/domain/services/cascade_deletion_service.py` | `fastmcp/task_management/domain/services/cascade_deletion_service.go` | 365 | done |
| 1-domain | `task_management/domain/services/content_analyzer.py` | `fastmcp/task_management/domain/services/content_analyzer.go` | 476 | done |
| 1-domain | `task_management/domain/services/context_derivation_service.py` | `fastmcp/task_management/domain/services/context_derivation_service.go` | 282 | done |
| 1-domain | `task_management/domain/services/dependency_validation_service.py` | `fastmcp/task_management/domain/services/dependency_validation_service.go` | 449 | done |
| 1-domain | `task_management/domain/services/event_dispatcher.py` | `fastmcp/task_management/domain/services/event_dispatcher.go` | 131 | done |
| 1-domain | `task_management/domain/services/git_branch_name_validator.py` | `fastmcp/task_management/domain/services/git_branch_name_validator.go` | 167 | done |
| 1-domain | `task_management/domain/services/hint_rules.py` | `fastmcp/task_management/domain/services/hint_rules.go` | 447 | done |
| 1-domain | `task_management/domain/services/intelligence/context_prioritizer.py` | `fastmcp/task_management/domain/services/intelligence/context_prioritizer.go` | 627 | done |
| 1-domain | `task_management/domain/services/intelligence/intelligent_context_selector.py` | `fastmcp/task_management/domain/services/intelligence/intelligent_context_selector.go` | 680 | done |
| 1-domain | `task_management/domain/services/intelligence/pattern_recognition_engine.py` | `fastmcp/task_management/domain/services/intelligence/pattern_recognition_engine.go` | 822 | done |
| 1-domain | `task_management/domain/services/intelligence/predictive_loader.py` | `fastmcp/task_management/domain/services/intelligence/predictive_loader.go` | 583 | done |
| 1-domain | `task_management/domain/services/intelligence/progressive_expander.py` | `fastmcp/task_management/domain/services/intelligence/progressive_expander.go` | 502 | done |
| 1-domain | `task_management/domain/services/intelligence/semantic_matcher.py` | `fastmcp/task_management/domain/services/intelligence/semantic_matcher.go` | 482 | done |
| 1-domain | `task_management/domain/services/orchestrator.py` | `fastmcp/task_management/domain/services/orchestrator.go` | 411 | done |
| 1-domain | `task_management/domain/services/pagination_service.py` | `fastmcp/task_management/domain/services/pagination_service.go` | 151 | done |
| 1-domain | `task_management/domain/services/project_name_validator.py` | `fastmcp/task_management/domain/services/project_name_validator.go` | 137 | done |
| 1-domain | `task_management/domain/services/protocols/cascade_data_provider.py` | `fastmcp/task_management/domain/services/protocols/cascade_data_provider.go` | 198 | done |
| 1-domain | `task_management/domain/services/rule_composition_service.py` | `fastmcp/task_management/domain/services/rule_composition_service.go` | 499 | done |
| 1-domain | `task_management/domain/services/task_completion_service.py` | `fastmcp/task_management/domain/services/task_completion_service.go` | 334 | done |
| 1-domain | `task_management/domain/services/task_priority_service.py` | `fastmcp/task_management/domain/services/task_priority_service.go` | 451 | done |
| 1-domain | `task_management/domain/services/task_progress_service.py` | `fastmcp/task_management/domain/services/task_progress_service.go` | 374 | done |
| 1-domain | `task_management/domain/services/task_state_transition_service.py` | `fastmcp/task_management/domain/services/task_state_transition_service.go` | 503 | done |
| 1-domain | `task_management/domain/services/task_validation_service.py` | `fastmcp/task_management/domain/services/task_validation_service.go` | 616 | done |
| 1-domain | `task_management/domain/services/template_domain_service.py` | `fastmcp/task_management/domain/services/template_domain_service.go` | 311 | done |
| 1-domain | `task_management/domain/validators/label_validator.py` | `fastmcp/task_management/domain/validators/label_validator.go` | 393 | done |
| 1-domain | `task_management/domain/value_objects/agent_id.py` | `fastmcp/task_management/domain/value_objects/agent_id.go` | 19 | done (tested) |
| 1-domain | `task_management/domain/value_objects/agent_roles.py` | `fastmcp/task_management/domain/value_objects/agent_roles.go` | 268 | done (compiles; light tests) |
| 1-domain | `task_management/domain/value_objects/agents.py` | `fastmcp/task_management/domain/value_objects/agents.go` | 214 | done (compiles; light tests) |
| 1-domain | `task_management/domain/value_objects/base_entity_id.py` | `fastmcp/task_management/domain/value_objects/base_entity_id.go` | 153 | done (tested) |
| 1-domain | `task_management/domain/value_objects/common_labels.py` | `fastmcp/task_management/domain/value_objects/common_labels.go` | 374 | done (tested) |
| 1-domain | `task_management/domain/value_objects/compliance_enums.py` | `fastmcp/task_management/domain/value_objects/compliance_enums.go` | 60 | done (tested) |
| 1-domain | `task_management/domain/value_objects/compliance_objects.py` | `fastmcp/task_management/domain/value_objects/compliance_objects.go` | 93 | done (compiles; light tests) |
| 1-domain | `task_management/domain/value_objects/context_enums.py` | `fastmcp/task_management/domain/value_objects/context_enums.go` | 43 | done (tested) |
| 1-domain | `task_management/domain/value_objects/coordination.py` | `fastmcp/task_management/domain/value_objects/coordination.go` | 363 | done (tested) |
| 1-domain | `task_management/domain/value_objects/error_severity.py` | `fastmcp/task_management/domain/value_objects/error_severity.go` | 12 | done (tested) |
| 1-domain | `task_management/domain/value_objects/estimated_effort.py` | `fastmcp/task_management/domain/value_objects/estimated_effort.go` | 164 | done (tested) |
| 1-domain | `task_management/domain/value_objects/git_branch_id.py` | `fastmcp/task_management/domain/value_objects/git_branch_id.go` | 19 | done (tested) |
| 1-domain | `task_management/domain/value_objects/hints.py` | `fastmcp/task_management/domain/value_objects/hints.go` | 224 | done (tested) |
| 1-domain | `task_management/domain/value_objects/pagination.py` | `fastmcp/task_management/domain/value_objects/pagination.go` | 81 | done (tested) |
| 1-domain | `task_management/domain/value_objects/priority.py` | `fastmcp/task_management/domain/value_objects/priority.go` | 93 | done (tested) |
| 1-domain | `task_management/domain/value_objects/progress.py` | `fastmcp/task_management/domain/value_objects/progress.go` | 278 | done (tested) |
| 1-domain | `task_management/domain/value_objects/progress_enums.py` | `fastmcp/task_management/domain/value_objects/progress_enums.go` | 75 | done (tested) |
| 1-domain | `task_management/domain/value_objects/progress_percentage.py` | `fastmcp/task_management/domain/value_objects/progress_percentage.go` | 140 | done (tested) |
| 1-domain | `task_management/domain/value_objects/project_id.py` | `fastmcp/task_management/domain/value_objects/project_id.go` | 19 | done (tested) |
| 1-domain | `task_management/domain/value_objects/rule_enums.py` | `fastmcp/task_management/domain/value_objects/rule_enums.go` | 157 | done (tested) |
| 1-domain | `task_management/domain/value_objects/rule_value_objects.py` | `fastmcp/task_management/domain/value_objects/rule_value_objects.go` | 279 | done (tested; generic over entity types) |
| 1-domain | `task_management/domain/value_objects/subtask_id.py` | `fastmcp/task_management/domain/value_objects/subtask_id.go` | 105 | done (tested) |
| 1-domain | `task_management/domain/value_objects/task_id.py` | `fastmcp/task_management/domain/value_objects/task_id.go` | 154 | done (tested) |
| 1-domain | `task_management/domain/value_objects/task_status.py` | `fastmcp/task_management/domain/value_objects/task_status.go` | 225 | done (tested) |
| 1-domain | `task_management/domain/value_objects/template_enums.py` | `fastmcp/task_management/domain/value_objects/template_enums.go` | 96 | done (tested) |
| 1-domain | `task_management/domain/value_objects/template_id.py` | `fastmcp/task_management/domain/value_objects/template_id.go` | 19 | done (tested) |
| 1-domain | `task_management/domain/value_objects/vision_objects.py` | `fastmcp/task_management/domain/value_objects/vision_objects.go` | 291 | done (tested) |
| 1-domain | `task_management/domain/websocket_protocol.py` | `fastmcp/task_management/domain/websocket_protocol.go` | 586 | done |
| 2-infrastructure | `agent_management/infrastructure/database/models.py` | `fastmcp/agent_management/infrastructure/database/models.go` | 386 | done (tested; see models_agent_management.go) |
| 2-infrastructure | `agent_management/infrastructure/repositories/orm/agent_template_repository.py` | `fastmcp/agent_management/infrastructure/repositories/orm/agent_template_repository.go` | 377 | done (tested; flat under repositories/) |
| 2-infrastructure | `agent_management/infrastructure/repositories/orm/user_agent_instance_repository.py` | `fastmcp/agent_management/infrastructure/repositories/orm/user_agent_instance_repository.go` | 696 | done (tested; flat under repositories/) |
| 2-infrastructure | `auth/infrastructure/database/models.py` | `fastmcp/auth/infrastructure/database/models.go` | 287 | done (tested; see models_auth.go) |
| 2-infrastructure | `auth/infrastructure/email_service.py` | `fastmcp/auth/infrastructure/email_service.go` | 722 | done (tested) |
| 2-infrastructure | `auth/infrastructure/enhanced_auth_service.py` | `fastmcp/auth/infrastructure/enhanced_auth_service.go` | 496 | done (tested) |
| 2-infrastructure | `auth/infrastructure/repositories/email_token_repository.py` | `fastmcp/auth/infrastructure/repositories/email_token_repository.go` | 328 | done (tested) |
| 2-infrastructure | `auth/infrastructure/repositories/token_balance_repository.py` | `fastmcp/auth/infrastructure/repositories/token_balance_repository.go` | 318 | done (tested) |
| 2-infrastructure | `auth/infrastructure/repositories/user_repository.py` | `fastmcp/auth/infrastructure/repositories/user_repository.go` | 429 | done (tested) |
| 2-infrastructure | `auth/infrastructure/supabase_auth.py` | `fastmcp/auth/infrastructure/supabase_auth.go` | 670 | done (tested) |
| 2-infrastructure | `connection_management/infrastructure/repositories/in_memory_connection_repository.py` | `fastmcp/connection_management/infrastructure/repositories/in_memory_connection_repository.go` | 56 | done (tested) |
| 2-infrastructure | `connection_management/infrastructure/repositories/in_memory_server_repository.py` | `fastmcp/connection_management/infrastructure/repositories/in_memory_server_repository.go` | 48 | done (tested) |
| 2-infrastructure | `connection_management/infrastructure/services/mcp_connection_diagnostics_service.py` | `fastmcp/connection_management/infrastructure/services/mcp_connection_diagnostics_service.go` | 134 | done (tested) |
| 2-infrastructure | `connection_management/infrastructure/services/mcp_server_health_service.py` | `fastmcp/connection_management/infrastructure/services/mcp_server_health_service.go` | 112 | done (tested) |
| 2-infrastructure | `connection_management/infrastructure/services/mcp_status_broadcasting_service.py` | `fastmcp/connection_management/infrastructure/services/mcp_status_broadcasting_service.go` | 126 | done (tested) |
| 2-infrastructure | `database_init.py` | `fastmcp/database_init.go` | 206 | done (tested) |
| 2-infrastructure | `database_migrations.py` | `fastmcp/database_migrations.go` | 258 | done (tested) |
| 2-infrastructure | `shared/infrastructure/messaging/event_bus.py` | `fastmcp/shared/infrastructure/messaging/event_bus.go` | 488 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/adapters/cache_service_adapter.py` | `fastmcp/task_management/infrastructure/adapters/cache_service_adapter.go` | 121 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/adapters/event_store_adapter.py` | `fastmcp/task_management/infrastructure/adapters/event_store_adapter.go` | 83 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/adapters/placeholder_adapters.py` | `fastmcp/task_management/infrastructure/adapters/placeholder_adapters.go` | 424 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/adapters/repository_factory_adapter.py` | `fastmcp/task_management/infrastructure/adapters/repository_factory_adapter.go` | 257 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/adapters/service_adapter_factory.py` | `fastmcp/task_management/infrastructure/adapters/service_adapter_factory.go` | 165 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/adapters/sqlalchemy_session_adapter.py` | `fastmcp/task_management/infrastructure/adapters/sqlalchemy_session_adapter.go` | 103 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/ai_services/ml_dependency_predictor.py` | `fastmcp/task_management/infrastructure/ai_services/ml_dependency_predictor.go` | 515 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/cache/cache_invalidation_mixin.py` | `fastmcp/task_management/infrastructure/cache/cache_invalidation_mixin.go` | 334 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/cache/cache_manager.py` | `fastmcp/task_management/infrastructure/cache/cache_manager.go` | 389 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/cache/context_cache.py` | `fastmcp/task_management/infrastructure/cache/context_cache.go` | 366 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/configuration/tool_config.py` | `fastmcp/task_management/infrastructure/configuration/tool_config.go` | 102 | done |
| 2-infrastructure | `task_management/infrastructure/database/auto_migration.py` | `fastmcp/task_management/infrastructure/database/auto_migration.go` | 320 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/database/connection_pool.py` | `fastmcp/task_management/infrastructure/database/connection_pool.go` | 446 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/database/connection_retry.py` | `fastmcp/task_management/infrastructure/database/connection_retry.go` | 267 | done |
| 2-infrastructure | `task_management/infrastructure/database/database_adapter.py` | `fastmcp/task_management/infrastructure/database/database_adapter.go` | 184 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/database/database_config.py` | `fastmcp/task_management/infrastructure/database/database_config.go` | 630 | done |
| 2-infrastructure | `task_management/infrastructure/database/database_initializer.py` | `fastmcp/task_management/infrastructure/database/database_initializer.go` | 137 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/database/database_source_manager.py` | `fastmcp/task_management/infrastructure/database/database_source_manager.go` | 324 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/database/database_utils.py` | `fastmcp/task_management/infrastructure/database/database_utils.go` | 681 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/database/db_initializer.py` | `fastmcp/task_management/infrastructure/database/db_initializer.go` | 381 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/database/dependency_installer.py` | `fastmcp/task_management/infrastructure/database/dependency_installer.go` | 130 | n/a (pip install script; no Go meaning) |
| 2-infrastructure | `task_management/infrastructure/database/ensure_ai_columns.py` | `fastmcp/task_management/infrastructure/database/ensure_ai_columns.go` | 139 | done |
| 2-infrastructure | `task_management/infrastructure/database/init_database.py` | `fastmcp/task_management/infrastructure/database/init_database.go` | 274 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/database/models.py` | `fastmcp/task_management/infrastructure/database/models.go` | 1136 | done |
| 2-infrastructure | `task_management/infrastructure/database/schema_validator.py` | `fastmcp/task_management/infrastructure/database/schema_validator.go` | 569 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/database/session_manager.py` | `fastmcp/task_management/infrastructure/database/session_manager.go` | 277 | done |
| 2-infrastructure | `task_management/infrastructure/database/supabase_config.py` | `fastmcp/task_management/infrastructure/database/supabase_config.go` | 290 | done |
| 2-infrastructure | `task_management/infrastructure/database/timestamp_events.py` | `fastmcp/task_management/infrastructure/database/timestamp_events.go` | 227 | done |
| 2-infrastructure | `task_management/infrastructure/database/uuid_column_type.py` | `fastmcp/task_management/infrastructure/database/uuid_column_type.go` | 171 | done |
| 2-infrastructure | `task_management/infrastructure/di_container.py` | `fastmcp/task_management/infrastructure/di_container.go` | 303 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/event_bus.py` | `fastmcp/task_management/infrastructure/event_bus.go` | 363 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/event_store.py` | `fastmcp/task_management/infrastructure/event_store.go` | 480 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/events/event_handler_initializer.py` | `fastmcp/task_management/infrastructure/events/event_handler_initializer.go` | 259 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/events/event_queue.py` | `fastmcp/task_management/infrastructure/events/event_queue.go` | 366 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/events/event_worker.py` | `fastmcp/task_management/infrastructure/events/event_worker.go` | 501 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/factories/project_service_factory.py` | `fastmcp/task_management/infrastructure/factories/project_service_factory.go` | 133 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/factories/rule_service_factory.py` | `fastmcp/task_management/infrastructure/factories/rule_service_factory.go` | 33 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/factories/unified_context_facade_factory.py` | `fastmcp/task_management/infrastructure/factories/unified_context_facade_factory.go` | 14 | done (see application/factories/unified_context_facade_factory.go) |
| 2-infrastructure | `task_management/infrastructure/logging/logger_config.py` | `fastmcp/task_management/infrastructure/logging/logger_config.go` | 335 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/monitoring/metrics_collector.py` | `fastmcp/task_management/infrastructure/monitoring/metrics_collector.go` | 557 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/monitoring/metrics_integration.py` | `fastmcp/task_management/infrastructure/monitoring/metrics_integration.go` | 514 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/monitoring/optimization_metrics.py` | `fastmcp/task_management/infrastructure/monitoring/optimization_metrics.go` | 731 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/monitoring/process_monitor.py` | `fastmcp/task_management/infrastructure/monitoring/process_monitor.go` | 236 | n/a (dead code in Python: ImportError; Go port removed) |
| 2-infrastructure | `task_management/infrastructure/notification_service.py` | `fastmcp/task_management/infrastructure/notification_service.go` | 474 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/parsers/rule_content_parser.py` | `fastmcp/task_management/infrastructure/parsers/rule_content_parser.go` | 333 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/performance/performance_config.py` | `fastmcp/task_management/infrastructure/performance/performance_config.go` | 85 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/performance/task_performance_optimizer.py` | `fastmcp/task_management/infrastructure/performance/task_performance_optimizer.go` | 331 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/repositories/agent_repository_factory.py` | `fastmcp/task_management/infrastructure/repositories/agent_repository_factory.go` | 303 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/repositories/base_orm_repository.py` | `fastmcp/task_management/infrastructure/repositories/base_orm_repository.go` | 403 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/repositories/base_timestamp_repository.py` | `fastmcp/task_management/infrastructure/repositories/base_timestamp_repository.go` | 379 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/repositories/base_user_scoped_repository.py` | `fastmcp/task_management/infrastructure/repositories/base_user_scoped_repository.go` | 244 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/repositories/branch_context_repository.py` | `fastmcp/task_management/infrastructure/repositories/branch_context_repository.go` | 419 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/repositories/cached/cached_agent_repository.py` | `fastmcp/task_management/infrastructure/repositories/cached/cached_agent_repository.go` | 257 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/repositories/cached/cached_git_branch_repository.py` | `fastmcp/task_management/infrastructure/repositories/cached/cached_git_branch_repository.go` | 290 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/repositories/cached/cached_project_repository.py` | `fastmcp/task_management/infrastructure/repositories/cached/cached_project_repository.go` | 204 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/repositories/cached/cached_subtask_repository.py` | `fastmcp/task_management/infrastructure/repositories/cached/cached_subtask_repository.go` | 318 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/repositories/cached/cached_task_repository.py` | `fastmcp/task_management/infrastructure/repositories/cached/cached_task_repository.go` | 258 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/repositories/clean_timestamp_repository_mixin.py` | `fastmcp/task_management/infrastructure/repositories/clean_timestamp_repository_mixin.go` | 51 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/repositories/event_publishing_mixin.py` | `fastmcp/task_management/infrastructure/repositories/event_publishing_mixin.go` | 197 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/repositories/git_branch_repository_factory.py` | `fastmcp/task_management/infrastructure/repositories/git_branch_repository_factory.go` | 167 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/repositories/global_context_repository.py` | `fastmcp/task_management/infrastructure/repositories/global_context_repository.go` | 774 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/repositories/mock_repository_factory.py` | `fastmcp/task_management/infrastructure/repositories/mock_repository_factory.go` | 547 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/repositories/mock_task_context_repository.py` | `fastmcp/task_management/infrastructure/repositories/mock_task_context_repository.go` | 79 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/repositories/orm/agent_repository.py` | `fastmcp/task_management/infrastructure/repositories/orm/agent_repository.go` | 979 | done (tested; flat under repositories/) |
| 2-infrastructure | `task_management/infrastructure/repositories/orm/cascade_data_provider.py` | `fastmcp/task_management/infrastructure/repositories/orm/cascade_data_provider.go` | 253 | done (tested; flat under repositories/) |
| 2-infrastructure | `task_management/infrastructure/repositories/orm/git_branch_repository.py` | `fastmcp/task_management/infrastructure/repositories/orm/git_branch_repository.go` | 1979 | done (tested; flat under repositories/) |
| 2-infrastructure | `task_management/infrastructure/repositories/orm/label_repository.py` | `fastmcp/task_management/infrastructure/repositories/orm/label_repository.go` | 548 | done (tested; flat under repositories/) |
| 2-infrastructure | `task_management/infrastructure/repositories/orm/project_repository.py` | `fastmcp/task_management/infrastructure/repositories/orm/project_repository.go` | 1087 | done (tested; flat under repositories/) |
| 2-infrastructure | `task_management/infrastructure/repositories/orm/subtask_repository.py` | `fastmcp/task_management/infrastructure/repositories/orm/subtask_repository.go` | 1088 | done (tested; flat under repositories/) |
| 2-infrastructure | `task_management/infrastructure/repositories/orm/supabase_optimized_repository.py` | `fastmcp/task_management/infrastructure/repositories/orm/supabase_optimized_repository.go` | 273 | done (tested; flat under repositories/) |
| 2-infrastructure | `task_management/infrastructure/repositories/orm/task_repository.py` | `fastmcp/task_management/infrastructure/repositories/orm/task_repository.go` | 2448 | done (tested; flat under repositories/) |
| 2-infrastructure | `task_management/infrastructure/repositories/orm/template_repository.py` | `fastmcp/task_management/infrastructure/repositories/orm/template_repository.go` | 496 | done (tested; flat under repositories/) |
| 2-infrastructure | `task_management/infrastructure/repositories/project_context_repository.py` | `fastmcp/task_management/infrastructure/repositories/project_context_repository.go` | 226 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/repositories/project_repository_factory.py` | `fastmcp/task_management/infrastructure/repositories/project_repository_factory.go` | 381 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/repositories/repository_factory.py` | `fastmcp/task_management/infrastructure/repositories/repository_factory.go` | 492 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/repositories/subtask_repository_factory.py` | `fastmcp/task_management/infrastructure/repositories/subtask_repository_factory.go` | 225 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/repositories/task_context_repository.py` | `fastmcp/task_management/infrastructure/repositories/task_context_repository.go` | 259 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/repositories/task_repository_factory.py` | `fastmcp/task_management/infrastructure/repositories/task_repository_factory.go` | 240 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/repositories/template_repository_factory.py` | `fastmcp/task_management/infrastructure/repositories/template_repository_factory.go` | 135 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/repositories/token_repository.py` | `fastmcp/task_management/infrastructure/repositories/token_repository.go` | 352 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/repositories/user_scoped_orm_repository.py` | `fastmcp/task_management/infrastructure/repositories/user_scoped_orm_repository.go` | 268 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/repositories/utils.py` | `fastmcp/task_management/infrastructure/repositories/utils.go` | 411 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/security/access_controller.py` | `fastmcp/task_management/infrastructure/security/access_controller.go` | 110 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/services/agent_converter.py` | `fastmcp/task_management/infrastructure/services/agent_converter.go` | 189 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/services/agent_doc_generator.py` | `fastmcp/task_management/infrastructure/services/agent_doc_generator.go` | 263 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/services/context_schema.py` | `fastmcp/task_management/infrastructure/services/context_schema.go` | 572 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/services/performance_cache_manager.py` | `fastmcp/task_management/infrastructure/services/performance_cache_manager.go` | 876 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/services/performance_monitor.py` | `fastmcp/task_management/infrastructure/services/performance_monitor.go` | 409 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/services/rule_parser_service.py` | `fastmcp/task_management/infrastructure/services/rule_parser_service.go` | 406 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/services/template_engine_service.py` | `fastmcp/task_management/infrastructure/services/template_engine_service.go` | 291 | n/a (dead code in Python: pybars/redis missing) |
| 2-infrastructure | `task_management/infrastructure/services/template_registry_service.py` | `fastmcp/task_management/infrastructure/services/template_registry_service.go` | 585 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/unified_logging.py` | `fastmcp/task_management/infrastructure/unified_logging.go` | 93 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/utilities/directory_utils.py` | `fastmcp/task_management/infrastructure/utilities/directory_utils.go` | 76 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/utilities/path_resolver.py` | `fastmcp/task_management/infrastructure/utilities/path_resolver.go` | 229 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/validation/document_validator.py` | `fastmcp/task_management/infrastructure/validation/document_validator.go` | 242 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/validation/global_context_validator.py` | `fastmcp/task_management/infrastructure/validation/global_context_validator.go` | 567 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/websocket/agent_communication_hub.py` | `fastmcp/task_management/infrastructure/websocket/agent_communication_hub.go` | 669 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/websocket/context_notifications.py` | `fastmcp/task_management/infrastructure/websocket/context_notifications.go` | 488 | done (tested) |
| 2-infrastructure | `task_management/infrastructure/workers/metrics_reporter.py` | `fastmcp/task_management/infrastructure/workers/metrics_reporter.go` | 919 | done (tested) |
| 3-application | `agent_management/application/facades/agent_management_facade.py` | `fastmcp/agent_management/application/facades/agent_management_facade.go` | 778 | done |
| 3-application | `agent_management/application/services/yaml_agent_template_loader.py` | `fastmcp/agent_management/application/services/yaml_agent_template_loader.go` | 235 | done |
| 3-application | `ai_task_planning/application/services/ai_planning_service.py` | `fastmcp/ai_task_planning/application/services/ai_planning_service.go` | 706 | done |
| 3-application | `ai_task_planning/interface/controllers/ai_planning_mcp_controller.py` | `fastmcp/ai_task_planning/interface/controllers/ai_planning_mcp_controller.go` | 509 | done |
| 3-application | `auth/application/auth_factory.py` | `fastmcp/auth/application/auth_factory.go` | 615 | done |
| 3-application | `auth/application/services/auth_service.py` | `fastmcp/auth/application/services/auth_service.go` | 465 | done |
| 3-application | `auth/application/services/token_consumption_service.py` | `fastmcp/auth/application/services/token_consumption_service.go` | 440 | done |
| 3-application | `connection_management/application/dtos/connection_dtos.py` | `fastmcp/connection_management/application/dtos/connection_dtos.go` | 110 | done |
| 3-application | `connection_management/application/facades/connection_application_facade.py` | `fastmcp/connection_management/application/facades/connection_application_facade.go` | 183 | done |
| 3-application | `connection_management/application/use_cases/check_connection_health.py` | `fastmcp/connection_management/application/use_cases/check_connection_health.go` | 77 | done |
| 3-application | `connection_management/application/use_cases/check_server_health.py` | `fastmcp/connection_management/application/use_cases/check_server_health.go` | 105 | done |
| 3-application | `connection_management/application/use_cases/get_server_capabilities.py` | `fastmcp/connection_management/application/use_cases/get_server_capabilities.go` | 66 | done |
| 3-application | `connection_management/application/use_cases/get_server_status.py` | `fastmcp/connection_management/application/use_cases/get_server_status.go` | 89 | done |
| 3-application | `connection_management/application/use_cases/register_status_updates.py` | `fastmcp/connection_management/application/use_cases/register_status_updates.go` | 61 | done |
| 3-application | `task_management/application/dtos/agent/agent_response.py` | `fastmcp/task_management/application/dtos/agent/agent_response.go` | 24 | done |
| 3-application | `task_management/application/dtos/agent/assign_agent_request.py` | `fastmcp/task_management/application/dtos/agent/assign_agent_request.go` | 26 | done |
| 3-application | `task_management/application/dtos/agent/register_agent_request.py` | `fastmcp/task_management/application/dtos/agent/register_agent_request.go` | 76 | done |
| 3-application | `task_management/application/dtos/agent/register_agent_response.py` | `fastmcp/task_management/application/dtos/agent/register_agent_response.go` | 29 | done |
| 3-application | `task_management/application/dtos/agent/update_agent_request.py` | `fastmcp/task_management/application/dtos/agent/update_agent_request.go` | 27 | done |
| 3-application | `task_management/application/dtos/common/agent_role.py` | `fastmcp/task_management/application/dtos/common/agent_role.go` | 19 | done |
| 3-application | `task_management/application/dtos/common/task_context.py` | `fastmcp/task_management/application/dtos/common/task_context.go` | 30 | done |
| 3-application | `task_management/application/dtos/common/task_progress_info.py` | `fastmcp/task_management/application/dtos/common/task_progress_info.go` | 18 | done |
| 3-application | `task_management/application/dtos/common/validation_result.py` | `fastmcp/task_management/application/dtos/common/validation_result.go` | 19 | done |
| 3-application | `task_management/application/dtos/context/context_request.py` | `fastmcp/task_management/application/dtos/context/context_request.go` | 118 | done |
| 3-application | `task_management/application/dtos/context/context_response.py` | `fastmcp/task_management/application/dtos/context/context_response.go` | 156 | done |
| 3-application | `task_management/application/dtos/dependency/add_dependency_request.py` | `fastmcp/task_management/application/dtos/dependency/add_dependency_request.go` | 12 | done |
| 3-application | `task_management/application/dtos/dependency/dependency_response.py` | `fastmcp/task_management/application/dtos/dependency/dependency_response.go` | 15 | done |
| 3-application | `task_management/application/dtos/project/create_project_request.py` | `fastmcp/task_management/application/dtos/project/create_project_request.go` | 16 | done |
| 3-application | `task_management/application/dtos/project/update_project_request.py` | `fastmcp/task_management/application/dtos/project/update_project_request.go` | 17 | done |
| 3-application | `task_management/application/dtos/subtask/add_subtask_request.py` | `fastmcp/task_management/application/dtos/subtask/add_subtask_request.go` | 33 | done |
| 3-application | `task_management/application/dtos/subtask/create_subtask_request.py` | `fastmcp/task_management/application/dtos/subtask/create_subtask_request.go` | 28 | done |
| 3-application | `task_management/application/dtos/subtask/subtask_info.py` | `fastmcp/task_management/application/dtos/subtask/subtask_info.go` | 30 | done |
| 3-application | `task_management/application/dtos/subtask/subtask_response.py` | `fastmcp/task_management/application/dtos/subtask/subtask_response.go` | 33 | done |
| 3-application | `task_management/application/dtos/subtask/update_subtask_request.py` | `fastmcp/task_management/application/dtos/subtask/update_subtask_request.go` | 40 | done |
| 3-application | `task_management/application/dtos/task/create_task_request.py` | `fastmcp/task_management/application/dtos/task/create_task_request.go` | 121 | done |
| 3-application | `task_management/application/dtos/task/create_task_response.py` | `fastmcp/task_management/application/dtos/task/create_task_response.go` | 30 | done |
| 3-application | `task_management/application/dtos/task/dependency_info.py` | `fastmcp/task_management/application/dtos/task/dependency_info.go` | 186 | done |
| 3-application | `task_management/application/dtos/task/list_tasks_request.py` | `fastmcp/task_management/application/dtos/task/list_tasks_request.go` | 19 | done |
| 3-application | `task_management/application/dtos/task/next_task_request.py` | `fastmcp/task_management/application/dtos/task/next_task_request.go` | 13 | done |
| 3-application | `task_management/application/dtos/task/search_tasks_request.py` | `fastmcp/task_management/application/dtos/task/search_tasks_request.go` | 16 | done |
| 3-application | `task_management/application/dtos/task/task_info.py` | `fastmcp/task_management/application/dtos/task/task_info.go` | 38 | done |
| 3-application | `task_management/application/dtos/task/task_list_item_response.py` | `fastmcp/task_management/application/dtos/task/task_list_item_response.go` | 78 | done |
| 3-application | `task_management/application/dtos/task/task_list_response.py` | `fastmcp/task_management/application/dtos/task/task_list_response.go` | 154 | done |
| 3-application | `task_management/application/dtos/task/task_progress.py` | `fastmcp/task_management/application/dtos/task/task_progress.go` | 21 | done |
| 3-application | `task_management/application/dtos/task/task_response.py` | `fastmcp/task_management/application/dtos/task/task_response.go` | 279 | done |
| 3-application | `task_management/application/dtos/task/update_task_request.py` | `fastmcp/task_management/application/dtos/task/update_task_request.go` | 31 | done |
| 3-application | `task_management/application/dtos/task/update_task_response.py` | `fastmcp/task_management/application/dtos/task/update_task_response.go` | 30 | done |
| 3-application | `task_management/application/dtos/task_dtos.py` | `fastmcp/task_management/application/dtos/task_dtos.go` | 129 | done |
| 3-application | `task_management/application/dtos/template_dtos.py` | `fastmcp/task_management/application/dtos/template_dtos.go` | 226 | done |
| 3-application | `task_management/application/event_handlers/agent_event_handlers.py` | `fastmcp/task_management/application/event_handlers/agent_event_handlers.go` | 545 | done |
| 3-application | `task_management/application/event_handlers/hint_event_handlers.py` | `fastmcp/task_management/application/event_handlers/hint_event_handlers.go` | 384 | done |
| 3-application | `task_management/application/event_handlers/progress_event_handlers.py` | `fastmcp/task_management/application/event_handlers/progress_event_handlers.go` | 350 | done |
| 3-application | `task_management/application/event_handlers/project_event_handlers.py` | `fastmcp/task_management/application/event_handlers/project_event_handlers.go` | 570 | done |
| 3-application | `task_management/application/event_handlers/task_event_handlers.py` | `fastmcp/task_management/application/event_handlers/task_event_handlers.go` | 386 | done |
| 3-application | `task_management/application/exceptions.py` | `fastmcp/task_management/application/exceptions.go` | 133 | done |
| 3-application | `task_management/application/facades/agent_application_facade.py` | `fastmcp/task_management/application/facades/agent_application_facade.go` | 505 | done |
| 3-application | `task_management/application/facades/auth_application_facade.py` | `fastmcp/task_management/application/facades/auth_application_facade.go` | 164 | done |
| 3-application | `task_management/application/facades/dependency_application_facade.py` | `fastmcp/task_management/application/facades/dependency_application_facade.go` | 82 | done |
| 3-application | `task_management/application/facades/git_branch_application_facade.py` | `fastmcp/task_management/application/facades/git_branch_application_facade.go` | 1187 | done |
| 3-application | `task_management/application/facades/project_application_facade.py` | `fastmcp/task_management/application/facades/project_application_facade.go` | 366 | done |
| 3-application | `task_management/application/facades/rule_application_facade.py` | `fastmcp/task_management/application/facades/rule_application_facade.go` | 188 | done |
| 3-application | `task_management/application/facades/subtask_application_facade.py` | `fastmcp/task_management/application/facades/subtask_application_facade.go` | 1385 || done |
| 3-application | `task_management/application/facades/task_application_facade.py` | `fastmcp/task_management/application/facades/task_application_facade.go` | 2691 | done |
| 3-application | `task_management/application/facades/token_application_facade.py` | `fastmcp/task_management/application/facades/token_application_facade.go` | 480 | done |
| 3-application | `task_management/application/facades/unified_context_facade.py` | `fastmcp/task_management/application/facades/unified_context_facade.go` | 633 | done |
| 3-application | `task_management/application/factories/agent_facade_factory.py` | `fastmcp/task_management/application/factories/agent_facade_factory.go` | 246 | done |
| 3-application | `task_management/application/factories/context_response_factory.py` | `fastmcp/task_management/application/factories/context_response_factory.go` | 307 | done |
| 3-application | `task_management/application/factories/git_branch_facade_factory.py` | `fastmcp/task_management/application/factories/git_branch_facade_factory.go` | 191 | done |
| 3-application | `task_management/application/factories/project_facade_factory.py` | `fastmcp/task_management/application/factories/project_facade_factory.go` | 142 | done |
| 3-application | `task_management/application/factories/subtask_facade_factory.py` | `fastmcp/task_management/application/factories/subtask_facade_factory.go` | 93 | done |
| 3-application | `task_management/application/factories/task_facade_factory.py` | `fastmcp/task_management/application/factories/task_facade_factory.go` | 230 | done |
| 3-application | `task_management/application/factories/token_facade_factory.py` | `fastmcp/task_management/application/factories/token_facade_factory.go` | 95 | done |
| 3-application | `task_management/application/factories/unified_context_facade_factory.py` | `fastmcp/task_management/application/factories/unified_context_facade_factory.go` | 313 | done |
| 3-application | `task_management/application/orchestration/orchestrator_router.py` | `fastmcp/task_management/application/orchestration/orchestrator_router.go` | 96 | done |
| 3-application | `task_management/application/orchestration/project_orchestrator.py` | `fastmcp/task_management/application/orchestration/project_orchestrator.go` | 465 | done |
| 3-application | `task_management/application/services/agent_coordination_service.py` | `fastmcp/task_management/application/services/agent_coordination_service.go` | 568 | done |
| 3-application | `task_management/application/services/agent_inheritance_service.py` | `fastmcp/task_management/application/services/agent_inheritance_service.go` | 184 || done |
| 3-application | `task_management/application/services/ai_integration_service.py` | `fastmcp/task_management/application/services/ai_integration_service.go` | 512 | done |
| 3-application | `task_management/application/services/audit_service.py` | `fastmcp/task_management/application/services/audit_service.go` | 206 || done |
| 3-application | `task_management/application/services/automated_context_sync_service.py` | `fastmcp/task_management/application/services/automated_context_sync_service.go` | 376 || done |
| 3-application | `task_management/application/services/base_timestamp_service.py` | `fastmcp/task_management/application/services/base_timestamp_service.go` | 498 || done |
| 3-application | `task_management/application/services/branch_statistics_integration_service.py` | `fastmcp/task_management/application/services/branch_statistics_integration_service.go` | 174 || done |
| 3-application | `task_management/application/services/context_cache_optimizer.py` | `fastmcp/task_management/application/services/context_cache_optimizer.go` | 765 | done |
| 3-application | `task_management/application/services/context_cache_service.py` | `fastmcp/task_management/application/services/context_cache_service.go` | 785 | done |
| 3-application | `task_management/application/services/context_delegation_service.py` | `fastmcp/task_management/application/services/context_delegation_service.go` | 1146 | done |
| 3-application | `task_management/application/services/context_detection_service.py` | `fastmcp/task_management/application/services/context_detection_service.go` | 104 || done |
| 3-application | `task_management/application/services/context_field_selector.py` | `fastmcp/task_management/application/services/context_field_selector.go` | 1046 | done |
| 3-application | `task_management/application/services/context_hierarchy_validator.py` | `fastmcp/task_management/application/services/context_hierarchy_validator.go` | 386 || done |
| 3-application | `task_management/application/services/context_inheritance_service.py` | `fastmcp/task_management/application/services/context_inheritance_service.go` | 662 | done |
| 3-application | `task_management/application/services/context_template_manager.py` | `fastmcp/task_management/application/services/context_template_manager.go` | 622 | done |
| 3-application | `task_management/application/services/context_validation_service.py` | `fastmcp/task_management/application/services/context_validation_service.go` | 344 || done |
| 3-application | `task_management/application/services/dependencie_application_service.py` | `fastmcp/task_management/application/services/dependencie_application_service.go` | 96 || done |
| 3-application | `task_management/application/services/dependency_management_engine.py` | `fastmcp/task_management/application/services/dependency_management_engine.go` | 546 | done |
| 3-application | `task_management/application/services/dependency_resolver_service.py` | `fastmcp/task_management/application/services/dependency_resolver_service.go` | 437 || done |
| 3-application | `task_management/application/services/domain_service_factory.py` | `fastmcp/task_management/application/services/domain_service_factory.go` | 309 || done |
| 3-application | `task_management/application/services/facade_service.py` | `fastmcp/task_management/application/services/facade_service.go` | 220 || done |
| 3-application | `task_management/application/services/feature_flag_service.py` | `fastmcp/task_management/application/services/feature_flag_service.go` | 445 || done |
| 3-application | `task_management/application/services/git_branch_service.py` | `fastmcp/task_management/application/services/git_branch_service.go` | 619 | done |
| 3-application | `task_management/application/services/git_branch_service_wrapper.py` | `fastmcp/task_management/application/services/git_branch_service_wrapper.go` | 119 || done |
| 3-application | `task_management/application/services/metrics_dashboard.py` | `fastmcp/task_management/application/services/metrics_dashboard.go` | 998 | done |
| 3-application | `task_management/application/services/minimal_response_serializer.py` | `fastmcp/task_management/application/services/minimal_response_serializer.go` | 262 || done |
| 3-application | `task_management/application/services/mock_unified_context_service.py` | `fastmcp/task_management/application/services/mock_unified_context_service.go` | 228 || done |
| 3-application | `task_management/application/services/orchestrator.py` | `fastmcp/task_management/application/services/orchestrator.go` | 18 || done |
| 3-application | `task_management/application/services/parameter_enforcement_service.py` | `fastmcp/task_management/application/services/parameter_enforcement_service.go` | 414 || done |
| 3-application | `task_management/application/services/parameter_transformation_service.py` | `fastmcp/task_management/application/services/parameter_transformation_service.go` | 217 || done |
| 3-application | `task_management/application/services/performance_benchmarker.py` | `fastmcp/task_management/application/services/performance_benchmarker.go` | 1231 | done |
| 3-application | `task_management/application/services/progress_tracking_service.py` | `fastmcp/task_management/application/services/progress_tracking_service.go` | 592 | done |
| 3-application | `task_management/application/services/progressive_enforcement_service.py` | `fastmcp/task_management/application/services/progressive_enforcement_service.go` | 347 || done |
| 3-application | `task_management/application/services/project_application_service.py` | `fastmcp/task_management/application/services/project_application_service.go` | 341 || done |
| 3-application | `task_management/application/services/project_management_service.py` | `fastmcp/task_management/application/services/project_management_service.go` | 542 || done |
| 3-application | `task_management/application/services/real_time_status_tracker.py` | `fastmcp/task_management/application/services/real_time_status_tracker.go` | 652 | done |
| 3-application | `task_management/application/services/repository_provider_service.py` | `fastmcp/task_management/application/services/repository_provider_service.go` | 296 || done |
| 3-application | `task_management/application/services/response_optimizer.py` | `fastmcp/task_management/application/services/response_optimizer.go` | 576 | done |
| 3-application | `task_management/application/services/rule_application_service.py` | `fastmcp/task_management/application/services/rule_application_service.go` | 236 || done |
| 3-application | `task_management/application/services/statistics_initializer.py` | `fastmcp/task_management/application/services/statistics_initializer.go` | 96 || done |
| 3-application | `task_management/application/services/subtask_application_service.py` | `fastmcp/task_management/application/services/subtask_application_service.go` | 188 || done |
| 3-application | `task_management/application/services/task_application_service.py` | `fastmcp/task_management/application/services/task_application_service.go` | 293 || done |
| 3-application | `task_management/application/services/task_authorization_service.py` | `fastmcp/task_management/application/services/task_authorization_service.go` | 232 || done |
| 3-application | `task_management/application/services/task_context_sync_service.py` | `fastmcp/task_management/application/services/task_context_sync_service.go` | 433 | done |
| 3-application | `task_management/application/services/task_progress_service.py` | `fastmcp/task_management/application/services/task_progress_service.go` | 156 || done |
| 3-application | `task_management/application/services/token_usage_tracking_service.py` | `fastmcp/task_management/application/services/token_usage_tracking_service.go` | 135 || done |
| 3-application | `task_management/application/services/unified_context_service.py` | `fastmcp/task_management/application/services/unified_context_service.go` | 2884 | done |
| 3-application | `task_management/application/services/websocket_notification_service.py` | `fastmcp/task_management/application/services/websocket_notification_service.go` | 1447 | done |
| 3-application | `task_management/application/services/websocket_payload_builder.py` | `fastmcp/task_management/application/services/websocket_payload_builder.go` | 223 || done |
| 3-application | `task_management/application/services/work_distribution_service.py` | `fastmcp/task_management/application/services/work_distribution_service.go` | 580 | done |
| 3-application | `task_management/application/services/workflow_analysis_service.py` | `fastmcp/task_management/application/services/workflow_analysis_service.go` | 680 | done |
| 3-application | `task_management/application/use_cases/add_context_insight.py` | `fastmcp/task_management/application/use_cases/add_context_insight.go` | 45 | done |
| 3-application | `task_management/application/use_cases/add_context_progress.py` | `fastmcp/task_management/application/use_cases/add_context_progress.go` | 47 | done |
| 3-application | `task_management/application/use_cases/add_dependency.py` | `fastmcp/task_management/application/use_cases/add_dependency.go` | 126 | done |
| 3-application | `task_management/application/use_cases/add_subtask.py` | `fastmcp/task_management/application/use_cases/add_subtask.go` | 295 | done |
| 3-application | `task_management/application/use_cases/agent_mappings.py` | `fastmcp/task_management/application/use_cases/agent_mappings.go` | 153 | done |
| 3-application | `task_management/application/use_cases/ai_task_creation_use_case.py` | `fastmcp/task_management/application/use_cases/ai_task_creation_use_case.go` | 259 | done |
| 3-application | `task_management/application/use_cases/assign_agent.py` | `fastmcp/task_management/application/use_cases/assign_agent.go` | 66 | done |
| 3-application | `task_management/application/use_cases/batch_context_operations.py` | `fastmcp/task_management/application/use_cases/batch_context_operations.go` | 439 | done |
| 3-application | `task_management/application/use_cases/call_agent.py` | `fastmcp/task_management/application/use_cases/call_agent.go` | 45 | done |
| 3-application | `task_management/application/use_cases/cleanup_obsolete_use_case.py` | `fastmcp/task_management/application/use_cases/cleanup_obsolete_use_case.go` | 86 | done |
| 3-application | `task_management/application/use_cases/clear_dependencies.py` | `fastmcp/task_management/application/use_cases/clear_dependencies.go` | 32 | done |
| 3-application | `task_management/application/use_cases/complete_subtask.py` | `fastmcp/task_management/application/use_cases/complete_subtask.go` | 296 | done |
| 3-application | `task_management/application/use_cases/complete_task.py` | `fastmcp/task_management/application/use_cases/complete_task.go` | 919 | done |
| 3-application | `task_management/application/use_cases/complete_task_optimized.py` | `fastmcp/task_management/application/use_cases/complete_task_optimized.go` | 189 | done |
| 3-application | `task_management/application/use_cases/context_search.py` | `fastmcp/task_management/application/use_cases/context_search.go` | 513 | done |
| 3-application | `task_management/application/use_cases/context_templates.py` | `fastmcp/task_management/application/use_cases/context_templates.go` | 725 | done |
| 3-application | `task_management/application/use_cases/context_versioning.py` | `fastmcp/task_management/application/use_cases/context_versioning.go` | 529 | done |
| 3-application | `task_management/application/use_cases/create_context.py` | `fastmcp/task_management/application/use_cases/create_context.go` | 72 | done |
| 3-application | `task_management/application/use_cases/create_git_branch.py` | `fastmcp/task_management/application/use_cases/create_git_branch.go` | 129 | done |
| 3-application | `task_management/application/use_cases/create_project.py` | `fastmcp/task_management/application/use_cases/create_project.go` | 240 | done |
| 3-application | `task_management/application/use_cases/create_rule.py` | `fastmcp/task_management/application/use_cases/create_rule.go` | 78 | done |
| 3-application | `task_management/application/use_cases/create_task.py` | `fastmcp/task_management/application/use_cases/create_task.go` | 314 | done |
| 3-application | `task_management/application/use_cases/delete_branch.py` | `fastmcp/task_management/application/use_cases/delete_branch.go` | 167 | done |
| 3-application | `task_management/application/use_cases/delete_project.py` | `fastmcp/task_management/application/use_cases/delete_project.go` | 380 | done |
| 3-application | `task_management/application/use_cases/delete_rule.py` | `fastmcp/task_management/application/use_cases/delete_rule.go` | 57 | done |
| 3-application | `task_management/application/use_cases/delete_task.py` | `fastmcp/task_management/application/use_cases/delete_task.go` | 127 | done |
| 3-application | `task_management/application/use_cases/get_agent.py` | `fastmcp/task_management/application/use_cases/get_agent.go` | 59 | done |
| 3-application | `task_management/application/use_cases/get_blocking_tasks.py` | `fastmcp/task_management/application/use_cases/get_blocking_tasks.go` | 41 | done |
| 3-application | `task_management/application/use_cases/get_context.py` | `fastmcp/task_management/application/use_cases/get_context.go` | 32 | done |
| 3-application | `task_management/application/use_cases/get_dependencies.py` | `fastmcp/task_management/application/use_cases/get_dependencies.go` | 44 | done |
| 3-application | `task_management/application/use_cases/get_project.py` | `fastmcp/task_management/application/use_cases/get_project.go` | 147 | done |
| 3-application | `task_management/application/use_cases/get_rule.py` | `fastmcp/task_management/application/use_cases/get_rule.go` | 48 | done |
| 3-application | `task_management/application/use_cases/get_subtask.py` | `fastmcp/task_management/application/use_cases/get_subtask.go` | 50 | done |
| 3-application | `task_management/application/use_cases/get_subtasks.py` | `fastmcp/task_management/application/use_cases/get_subtasks.go` | 72 | done |
| 3-application | `task_management/application/use_cases/get_task.py` | `fastmcp/task_management/application/use_cases/get_task.go` | 201 | done |
| 3-application | `task_management/application/use_cases/intelligence/intelligent_context_selection.py` | `fastmcp/task_management/application/use_cases/intelligence/intelligent_context_selection.go` | 408 | done |
| 3-application | `task_management/application/use_cases/list_agents.py` | `fastmcp/task_management/application/use_cases/list_agents.go` | 59 | done |
| 3-application | `task_management/application/use_cases/list_contexts.py` | `fastmcp/task_management/application/use_cases/list_contexts.go` | 29 | done |
| 3-application | `task_management/application/use_cases/list_projects.py` | `fastmcp/task_management/application/use_cases/list_projects.go` | 130 | done |
| 3-application | `task_management/application/use_cases/list_rules.py` | `fastmcp/task_management/application/use_cases/list_rules.go` | 78 | done |
| 3-application | `task_management/application/use_cases/list_tasks.py` | `fastmcp/task_management/application/use_cases/list_tasks.go` | 86 | done |
| 3-application | `task_management/application/use_cases/manage_dependencies.py` | `fastmcp/task_management/application/use_cases/manage_dependencies.go` | 194 | done |
| 3-application | `task_management/application/use_cases/next_task.py` | `fastmcp/task_management/application/use_cases/next_task.go` | 747 | done |
| 3-application | `task_management/application/use_cases/project_health_check.py` | `fastmcp/task_management/application/use_cases/project_health_check.go` | 151 | done |
| 3-application | `task_management/application/use_cases/rebalance_agents_use_case.py` | `fastmcp/task_management/application/use_cases/rebalance_agents_use_case.go` | 79 | done |
| 3-application | `task_management/application/use_cases/register_agent.py` | `fastmcp/task_management/application/use_cases/register_agent.go` | 63 | done |
| 3-application | `task_management/application/use_cases/remove_dependency.py` | `fastmcp/task_management/application/use_cases/remove_dependency.go` | 41 | done |
| 3-application | `task_management/application/use_cases/remove_subtask.py` | `fastmcp/task_management/application/use_cases/remove_subtask.go` | 139 | done |
| 3-application | `task_management/application/use_cases/rule_orchestration_use_case.py` | `fastmcp/task_management/application/use_cases/rule_orchestration_use_case.go` | 387 | done |
| 3-application | `task_management/application/use_cases/search_tasks.py` | `fastmcp/task_management/application/use_cases/search_tasks.go` | 19 | done |
| 3-application | `task_management/application/use_cases/template_use_cases.py` | `fastmcp/task_management/application/use_cases/template_use_cases.go` | 393 | done |
| 3-application | `task_management/application/use_cases/unassign_agent.py` | `fastmcp/task_management/application/use_cases/unassign_agent.go` | 84 | done |
| 3-application | `task_management/application/use_cases/unregister_agent.py` | `fastmcp/task_management/application/use_cases/unregister_agent.go` | 66 | done |
| 3-application | `task_management/application/use_cases/update_context.py` | `fastmcp/task_management/application/use_cases/update_context.go` | 52 | done |
| 3-application | `task_management/application/use_cases/update_project.py` | `fastmcp/task_management/application/use_cases/update_project.go` | 108 | done |
| 3-application | `task_management/application/use_cases/update_rule.py` | `fastmcp/task_management/application/use_cases/update_rule.go` | 81 | done |
| 3-application | `task_management/application/use_cases/update_subtask.py` | `fastmcp/task_management/application/use_cases/update_subtask.go` | 227 | done |
| 3-application | `task_management/application/use_cases/update_task.py` | `fastmcp/task_management/application/use_cases/update_task.go` | 259 | done |
| 3-application | `task_management/application/use_cases/validate_dependencies.py` | `fastmcp/task_management/application/use_cases/validate_dependencies.go` | 334 | done |
| 3-application | `task_management/application/use_cases/validate_integrity_use_case.py` | `fastmcp/task_management/application/use_cases/validate_integrity_use_case.go` | 87 | done |
| 3-application | `task_management/application/use_cases/validate_rule.py` | `fastmcp/task_management/application/use_cases/validate_rule.go` | 113 | done |
| 4-server-routes | `agent_management/interface/mcp_controllers/call_agent.py` | `fastmcp/agent_management/interface/mcp_controllers/call_agent.go` | 103 | done |
| 4-server-routes | `agent_management/interface/mcp_controllers/call_agent_controller.py` | `fastmcp/agent_management/interface/mcp_controllers/call_agent_controller.go` | 62 | done |
| 4-server-routes | `agent_management/interface/rest/agent_management_routes.py` | `fastmcp/agent_management/interface/rest/agent_management_routes.go` | 1344 | done |
| 4-server-routes | `agent_management/interface/rest/models.py` | `fastmcp/agent_management/interface/rest/models.go` | 297 | done |
| 4-server-routes | `connection_management/interface/controllers/connection_mcp_controller.py` | `fastmcp/connection_management/interface/controllers/connection_mcp_controller.go` | 161 | done |
| 4-server-routes | `connection_management/interface/controllers/desc/connection/manage_connection_description.py` | `fastmcp/connection_management/interface/controllers/desc/connection/manage_connection_description.go` | 113 | done |
| 4-server-routes | `connection_management/interface/controllers/desc/description_loader.py` | `fastmcp/connection_management/interface/controllers/desc/description_loader.go` | 91 | done |
| 4-server-routes | `connection_management/interface/controllers/manage_connection_description.py` | `fastmcp/connection_management/interface/controllers/manage_connection_description.go` | 298 | done |
| 4-server-routes | `connection_management/interface/ddd_compliant_connection_tools.py` | `fastmcp/connection_management/interface/ddd_compliant_connection_tools.go` | 95 | done |
| 4-server-routes | `middleware/response_validator_middleware.py` | `fastmcp/middleware/response_validator_middleware.go` | 419 | done |
| 4-server-routes | `prompts/prompt.py` | `fastmcp/prompts/prompt.go` | 264 | done |
| 4-server-routes | `prompts/prompt_manager.py` | `fastmcp/prompts/prompt_manager.go` | 201 | done |
| 4-server-routes | `resources/resource.py` | `fastmcp/resources/resource.go` | 173 | done |
| 4-server-routes | `resources/resource_manager.py` | `fastmcp/resources/resource_manager.go` | 492 | done |
| 4-server-routes | `resources/template.py` | `fastmcp/resources/template.go` | 272 | done |
| 4-server-routes | `resources/types.py` | `fastmcp/resources/types.go` | 151 | done |
| 4-server-routes | `server/__main__.py` | `fastmcp/server/__main__.go` | 10 | done |
| 4-server-routes | `server/auth/auth.py` | `fastmcp/server/auth/auth.go` | 73 | done |
| 4-server-routes | `server/auth/mcp_auth_config.py` | `fastmcp/server/auth/mcp_auth_config.go` | 107 | done |
| 4-server-routes | `server/auth/providers/bearer.py` | `fastmcp/server/auth/providers/bearer.go` | 401 | done |
| 4-server-routes | `server/auth/providers/in_memory.py` | `fastmcp/server/auth/providers/in_memory.go` | 327 | done |
| 4-server-routes | `server/auth/providers/jwt_bearer.py` | `fastmcp/server/auth/providers/jwt_bearer.go` | 223 | done |
| 4-server-routes | `server/cache/cache_invalidation_hooks.py` | `fastmcp/server/cache/cache_invalidation_hooks.go` | 297 | done |
| 4-server-routes | `server/cache/redis_cache_decorator.py` | `fastmcp/server/cache/redis_cache_decorator.go` | 380 | done |
| 4-server-routes | `server/connection_health_tool.py` | `fastmcp/server/connection_health_tool.go` | 258 | done |
| 4-server-routes | `server/connection_manager.py` | `fastmcp/server/connection_manager.go` | 255 | done |
| 4-server-routes | `server/connection_status_broadcaster.py` | `fastmcp/server/connection_status_broadcaster.go` | 273 | done |
| 4-server-routes | `server/context.py` | `fastmcp/server/context.go` | 340 | done |
| 4-server-routes | `server/dependencies.py` | `fastmcp/server/dependencies.go` | 89 | done |
| 4-server-routes | `server/error_middleware.py` | `fastmcp/server/error_middleware.go` | 256 | done |
| 4-server-routes | `server/http_server.py` | `fastmcp/server/http_server.go` | 1059 | done |
| 4-server-routes | `server/mcp_entry_point.py` | `fastmcp/server/mcp_entry_point.go` | 980 | done |
| 4-server-routes | `server/mcp_status_tool.py` | `fastmcp/server/mcp_status_tool.go` | 397 | done |
| 4-server-routes | `server/middleware.py` | `fastmcp/server/middleware.go` | 236 | done |
| 4-server-routes | `server/openapi.py` | `fastmcp/server/openapi.go` | 1019 | done |
| 4-server-routes | `server/proxy.py` | `fastmcp/server/proxy.go` | 401 | done |
| 4-server-routes | `server/routes/agent_routes.py` | `fastmcp/server/routes/agent_routes.go` | 433 | done |
| 4-server-routes | `server/routes/alert_system_routes.py` | `fastmcp/server/routes/alert_system_routes.go` | 535 | done |
| 4-server-routes | `server/routes/analytics_routes.py` | `fastmcp/server/routes/analytics_routes.go` | 667 | done |
| 4-server-routes | `server/routes/branch_routes.py` | `fastmcp/server/routes/branch_routes.go` | 453 | done |
| 4-server-routes | `server/routes/broadcast_routes.py` | `fastmcp/server/routes/broadcast_routes.go` | 60 | done |
| 4-server-routes | `server/routes/connection_routes.py` | `fastmcp/server/routes/connection_routes.go` | 155 | done |
| 4-server-routes | `server/routes/context_routes.py` | `fastmcp/server/routes/context_routes.go` | 587 | done |
| 4-server-routes | `server/routes/performance_metrics_routes.py` | `fastmcp/server/routes/performance_metrics_routes.go` | 390 | done |
| 4-server-routes | `server/routes/project_routes.py` | `fastmcp/server/routes/project_routes.go` | 297 | done |
| 4-server-routes | `server/routes/session_stream_routes.py` | `fastmcp/server/routes/session_stream_routes.go` | 211 | done |
| 4-server-routes | `server/routes/subtask_routes.py` | `fastmcp/server/routes/subtask_routes.go` | 257 | done |
| 4-server-routes | `server/routes/task_routes.py` | `fastmcp/server/routes/task_routes.go` | 517 | done |
| 4-server-routes | `server/routes/task_user_routes.py` | `fastmcp/server/routes/task_user_routes.go` | 540 | done |
| 4-server-routes | `server/routes/token_router.py` | `fastmcp/server/routes/token_router.go` | 368 | done |
| 4-server-routes | `server/secure_connection_tool.py` | `fastmcp/server/secure_connection_tool.go` | 230 | done |
| 4-server-routes | `server/secure_health_check.py` | `fastmcp/server/secure_health_check.go` | 311 | done |
| 4-server-routes | `server/server.py` | `fastmcp/server/server.go` | 2263 | done |
| 4-server-routes | `server/session_health_tool.py` | `fastmcp/server/session_health_tool.go` | 253 | done |
| 4-server-routes | `server/session_store.py` | `fastmcp/server/session_store.go` | 931 | done |
| 4-server-routes | `task_management/interface/adapters/simple_multi_agent_adapter.py` | `fastmcp/task_management/interface/adapters/simple_multi_agent_adapter.go` | 86 | done |
| 4-server-routes | `task_management/interface/api_controllers/agent_api_controller.py` | `fastmcp/task_management/interface/api_controllers/agent_api_controller.go` | 333 | done |
| 4-server-routes | `task_management/interface/api_controllers/auth_api_controller.py` | `fastmcp/task_management/interface/api_controllers/auth_api_controller.go` | 129 | done |
| 4-server-routes | `task_management/interface/api_controllers/branch_api_controller.py` | `fastmcp/task_management/interface/api_controllers/branch_api_controller.go` | 1035 | done |
| 4-server-routes | `task_management/interface/api_controllers/context_api_controller.py` | `fastmcp/task_management/interface/api_controllers/context_api_controller.go` | 323 | done |
| 4-server-routes | `task_management/interface/api_controllers/project_api_controller.py` | `fastmcp/task_management/interface/api_controllers/project_api_controller.go` | 426 | done |
| 4-server-routes | `task_management/interface/api_controllers/subtask_api_controller.py` | `fastmcp/task_management/interface/api_controllers/subtask_api_controller.go` | 690 || done |
| 4-server-routes | `task_management/interface/api_controllers/task_api_controller.py` | `fastmcp/task_management/interface/api_controllers/task_api_controller.go` | 5 | done |
| 4-server-routes | `task_management/interface/api_controllers/task_api_controller/handlers/crud_handler.py` | `fastmcp/task_management/interface/api_controllers/task_api_controller/handlers/crud_handler.go` | 351 | done |
| 4-server-routes | `task_management/interface/api_controllers/task_api_controller/handlers/dependency_handler.py` | `fastmcp/task_management/interface/api_controllers/task_api_controller/handlers/dependency_handler.go` | 21 | done |
| 4-server-routes | `task_management/interface/api_controllers/task_api_controller/handlers/search_handler.py` | `fastmcp/task_management/interface/api_controllers/task_api_controller/handlers/search_handler.go` | 286 | done |
| 4-server-routes | `task_management/interface/api_controllers/task_api_controller/handlers/workflow_handler.py` | `fastmcp/task_management/interface/api_controllers/task_api_controller/handlers/workflow_handler.go` | 94 | done |
| 4-server-routes | `task_management/interface/api_controllers/task_api_controller/task_api_controller.py` | `fastmcp/task_management/interface/api_controllers/task_api_controller/task_api_controller.go` | 123 | done |
| 4-server-routes | `task_management/interface/api_controllers/token_api_controller.py` | `fastmcp/task_management/interface/api_controllers/token_api_controller.go` | 323 | done |
| 4-server-routes | `task_management/interface/consolidated_mcp_server.py` | `fastmcp/task_management/interface/consolidated_mcp_server.go` | 57 | done |
| 4-server-routes | `task_management/interface/ddd_compliant_mcp_tools.py` | `fastmcp/task_management/interface/ddd_compliant_mcp_tools.go` | 444 | done |
| 4-server-routes | `task_management/interface/facade_provider.py` | `fastmcp/task_management/interface/facade_provider.go` | 250 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/agent_mcp_controller/agent_mcp_controller.py` | `fastmcp/task_management/interface/mcp_controllers/agent_mcp_controller/agent_mcp_controller.go` | 442 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/agent_mcp_controller/factories/operation_factory.py` | `fastmcp/task_management/interface/mcp_controllers/agent_mcp_controller/factories/operation_factory.go` | 178 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/agent_mcp_controller/factories/response_factory.py` | `fastmcp/task_management/interface/mcp_controllers/agent_mcp_controller/factories/response_factory.go` | 75 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/agent_mcp_controller/handlers/agent_invocation_handler.py` | `fastmcp/task_management/interface/mcp_controllers/agent_mcp_controller/handlers/agent_invocation_handler.go` | 55 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/agent_mcp_controller/handlers/assignment_handler.py` | `fastmcp/task_management/interface/mcp_controllers/agent_mcp_controller/handlers/assignment_handler.go` | 95 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/agent_mcp_controller/handlers/crud_handler.py` | `fastmcp/task_management/interface/mcp_controllers/agent_mcp_controller/handlers/crud_handler.go` | 188 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/agent_mcp_controller/handlers/rebalance_handler.py` | `fastmcp/task_management/interface/mcp_controllers/agent_mcp_controller/handlers/rebalance_handler.go` | 55 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/agent_mcp_controller/manage_agent_description.py` | `fastmcp/task_management/interface/mcp_controllers/agent_mcp_controller/manage_agent_description.go` | 94 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/agent_mcp_controller/services/agent_discovery_service.py` | `fastmcp/task_management/interface/mcp_controllers/agent_mcp_controller/services/agent_discovery_service.go` | 38 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/agent_mcp_controller/unified_agent_description.py` | `fastmcp/task_management/interface/mcp_controllers/agent_mcp_controller/unified_agent_description.go` | 149 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/auth_helper/auth_helper.py` | `fastmcp/task_management/interface/mcp_controllers/auth_helper/auth_helper.go` | 65 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/auth_helper/extractors/context_object_extractor.py` | `fastmcp/task_management/interface/mcp_controllers/auth_helper/extractors/context_object_extractor.go` | 57 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/auth_helper/extractors/mcp_context_extractor.py` | `fastmcp/task_management/interface/mcp_controllers/auth_helper/extractors/mcp_context_extractor.go` | 66 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/auth_helper/extractors/request_state_extractor.py` | `fastmcp/task_management/interface/mcp_controllers/auth_helper/extractors/request_state_extractor.go` | 69 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/auth_helper/services/authentication_service.py` | `fastmcp/task_management/interface/mcp_controllers/auth_helper/services/authentication_service.go` | 130 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/auth_helper/services/context_import_service.py` | `fastmcp/task_management/interface/mcp_controllers/auth_helper/services/context_import_service.go` | 79 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/auth_helper/services/debug_service.py` | `fastmcp/task_management/interface/mcp_controllers/auth_helper/services/debug_service.go` | 57 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/auth_helper/services/token_extraction_service.py` | `fastmcp/task_management/interface/mcp_controllers/auth_helper/services/token_extraction_service.go` | 234 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/context_id_detector/context_id_detector.py` | `fastmcp/task_management/interface/mcp_controllers/context_id_detector/context_id_detector.go` | 51 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/dependency_mcp_controller/dependency_mcp_controller.py` | `fastmcp/task_management/interface/mcp_controllers/dependency_mcp_controller/dependency_mcp_controller.go` | 165 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/dependency_mcp_controller/factories/dependency_controller_factory.py` | `fastmcp/task_management/interface/mcp_controllers/dependency_mcp_controller/factories/dependency_controller_factory.go` | 59 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/dependency_mcp_controller/handlers/dependency_operation_handler.py` | `fastmcp/task_management/interface/mcp_controllers/dependency_mcp_controller/handlers/dependency_operation_handler.go` | 121 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/dependency_mcp_controller/manage_dependency_description.py` | `fastmcp/task_management/interface/mcp_controllers/dependency_mcp_controller/manage_dependency_description.go` | 94 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/dependency_mcp_controller/services/description_service.py` | `fastmcp/task_management/interface/mcp_controllers/dependency_mcp_controller/services/description_service.go` | 24 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/enhanced_dependency_controller.py` | `fastmcp/task_management/interface/mcp_controllers/enhanced_dependency_controller.go` | 696 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/git_branch_mcp_controller/factories/operation_factory.py` | `fastmcp/task_management/interface/mcp_controllers/git_branch_mcp_controller/factories/operation_factory.go` | 207 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/git_branch_mcp_controller/git_branch_mcp_controller.py` | `fastmcp/task_management/interface/mcp_controllers/git_branch_mcp_controller/git_branch_mcp_controller.go` | 277 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/git_branch_mcp_controller/handlers/advanced_handler.py` | `fastmcp/task_management/interface/mcp_controllers/git_branch_mcp_controller/handlers/advanced_handler.go` | 114 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/git_branch_mcp_controller/handlers/agent_handler.py` | `fastmcp/task_management/interface/mcp_controllers/git_branch_mcp_controller/handlers/agent_handler.go` | 183 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/git_branch_mcp_controller/handlers/crud_handler.py` | `fastmcp/task_management/interface/mcp_controllers/git_branch_mcp_controller/handlers/crud_handler.go` | 195 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/git_branch_mcp_controller/manage_git_branch_description.py` | `fastmcp/task_management/interface/mcp_controllers/git_branch_mcp_controller/manage_git_branch_description.go` | 89 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/project_mcp_controller/factories/operation_factory.py` | `fastmcp/task_management/interface/mcp_controllers/project_mcp_controller/factories/operation_factory.go` | 159 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/project_mcp_controller/factories/response_factory.py` | `fastmcp/task_management/interface/mcp_controllers/project_mcp_controller/factories/response_factory.go` | 80 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/project_mcp_controller/handlers/crud_handler.py` | `fastmcp/task_management/interface/mcp_controllers/project_mcp_controller/handlers/crud_handler.go` | 203 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/project_mcp_controller/handlers/maintenance_handler.py` | `fastmcp/task_management/interface/mcp_controllers/project_mcp_controller/handlers/maintenance_handler.go` | 150 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/project_mcp_controller/manage_project_description.py` | `fastmcp/task_management/interface/mcp_controllers/project_mcp_controller/manage_project_description.go` | 77 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/project_mcp_controller/project_mcp_controller.py` | `fastmcp/task_management/interface/mcp_controllers/project_mcp_controller/project_mcp_controller.go` | 796 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/subtask_mcp_controller/factories/operation_factory.py` | `fastmcp/task_management/interface/mcp_controllers/subtask_mcp_controller/factories/operation_factory.go` | 265 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/subtask_mcp_controller/handlers/crud_handler.py` | `fastmcp/task_management/interface/mcp_controllers/subtask_mcp_controller/handlers/crud_handler.go` | 624 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/subtask_mcp_controller/handlers/progress_handler.py` | `fastmcp/task_management/interface/mcp_controllers/subtask_mcp_controller/handlers/progress_handler.go` | 245 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/subtask_mcp_controller/manage_subtask_description.py` | `fastmcp/task_management/interface/mcp_controllers/subtask_mcp_controller/manage_subtask_description.go` | 346 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/subtask_mcp_controller/subtask_mcp_controller.py` | `fastmcp/task_management/interface/mcp_controllers/subtask_mcp_controller/subtask_mcp_controller.go` | 564 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/task_mcp_controller/factories/operation_factory.py` | `fastmcp/task_management/interface/mcp_controllers/task_mcp_controller/factories/operation_factory.go` | 417 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/task_mcp_controller/factories/response_factory.py` | `fastmcp/task_management/interface/mcp_controllers/task_mcp_controller/factories/response_factory.go` | 234 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/task_mcp_controller/factories/validation_factory.py` | `fastmcp/task_management/interface/mcp_controllers/task_mcp_controller/factories/validation_factory.go` | 239 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/task_mcp_controller/handlers/ai_handler.py` | `fastmcp/task_management/interface/mcp_controllers/task_mcp_controller/handlers/ai_handler.go` | 379 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/task_mcp_controller/handlers/crud_handler.py` | `fastmcp/task_management/interface/mcp_controllers/task_mcp_controller/handlers/crud_handler.go` | 480 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/task_mcp_controller/handlers/search_handler.py` | `fastmcp/task_management/interface/mcp_controllers/task_mcp_controller/handlers/search_handler.go` | 445 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/task_mcp_controller/handlers/workflow_handler.py` | `fastmcp/task_management/interface/mcp_controllers/task_mcp_controller/handlers/workflow_handler.go` | 183 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/task_mcp_controller/manage_task_description.py` | `fastmcp/task_management/interface/mcp_controllers/task_mcp_controller/manage_task_description.go` | 328 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/task_mcp_controller/task_mcp_controller.py` | `fastmcp/task_management/interface/mcp_controllers/task_mcp_controller/task_mcp_controller.go` | 858 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/task_mcp_controller/validators/business_validator.py` | `fastmcp/task_management/interface/mcp_controllers/task_mcp_controller/validators/business_validator.go` | 216 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/task_mcp_controller/validators/context_validator.py` | `fastmcp/task_management/interface/mcp_controllers/task_mcp_controller/validators/context_validator.go` | 109 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/task_mcp_controller/validators/parameter_validator.py` | `fastmcp/task_management/interface/mcp_controllers/task_mcp_controller/validators/parameter_validator.go` | 340 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/token_consumption_helper.py` | `fastmcp/task_management/interface/mcp_controllers/token_consumption_helper.go` | 237 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/unified_context_controller/factories/operation_factory.py` | `fastmcp/task_management/interface/mcp_controllers/unified_context_controller/factories/operation_factory.go` | 43 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/unified_context_controller/handlers/context_operation_handler.py` | `fastmcp/task_management/interface/mcp_controllers/unified_context_controller/handlers/context_operation_handler.go` | 168 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/unified_context_controller/manage_unified_context_description.py` | `fastmcp/task_management/interface/mcp_controllers/unified_context_controller/manage_unified_context_description.go` | 187 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/unified_context_controller/unified_context_controller.py` | `fastmcp/task_management/interface/mcp_controllers/unified_context_controller/unified_context_controller.go` | 422 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/workflow_guidance/agent/agent_workflow_factory.py` | `fastmcp/task_management/interface/mcp_controllers/workflow_guidance/agent/agent_workflow_factory.go` | 15 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/workflow_guidance/agent/agent_workflow_guidance.py` | `fastmcp/task_management/interface/mcp_controllers/workflow_guidance/agent/agent_workflow_guidance.go` | 482 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/workflow_guidance/base.py` | `fastmcp/task_management/interface/mcp_controllers/workflow_guidance/base.go` | 126 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/workflow_guidance/context/context_workflow_factory.py` | `fastmcp/task_management/interface/mcp_controllers/workflow_guidance/context/context_workflow_factory.go` | 12 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/workflow_guidance/context/context_workflow_guidance.py` | `fastmcp/task_management/interface/mcp_controllers/workflow_guidance/context/context_workflow_guidance.go` | 281 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/workflow_guidance/git_branch/git_branch_workflow_factory.py` | `fastmcp/task_management/interface/mcp_controllers/workflow_guidance/git_branch/git_branch_workflow_factory.go` | 15 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/workflow_guidance/git_branch/git_branch_workflow_guidance.py` | `fastmcp/task_management/interface/mcp_controllers/workflow_guidance/git_branch/git_branch_workflow_guidance.go` | 527 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/workflow_guidance/rule/rule_workflow_factory.py` | `fastmcp/task_management/interface/mcp_controllers/workflow_guidance/rule/rule_workflow_factory.go` | 15 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/workflow_guidance/rule/rule_workflow_guidance.py` | `fastmcp/task_management/interface/mcp_controllers/workflow_guidance/rule/rule_workflow_guidance.go` | 499 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/workflow_guidance/subtask.py` | `fastmcp/task_management/interface/mcp_controllers/workflow_guidance/subtask.go` | 118 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/workflow_guidance/subtask/subtask_workflow_factory.py` | `fastmcp/task_management/interface/mcp_controllers/workflow_guidance/subtask/subtask_workflow_factory.go` | 35 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/workflow_guidance/subtask/subtask_workflow_guidance.py` | `fastmcp/task_management/interface/mcp_controllers/workflow_guidance/subtask/subtask_workflow_guidance.go` | 501 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/workflow_guidance/task/task_workflow_factory.py` | `fastmcp/task_management/interface/mcp_controllers/workflow_guidance/task/task_workflow_factory.go` | 35 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/workflow_guidance/task/task_workflow_guidance.py` | `fastmcp/task_management/interface/mcp_controllers/workflow_guidance/task/task_workflow_guidance.go` | 1000 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/workflow_hint_enhancer/services/enhancement_service.py` | `fastmcp/task_management/interface/mcp_controllers/workflow_hint_enhancer/services/enhancement_service.go` | 439 | done |
| 4-server-routes | `task_management/interface/mcp_controllers/workflow_hint_enhancer/workflow_hint_enhancer.py` | `fastmcp/task_management/interface/mcp_controllers/workflow_hint_enhancer/workflow_hint_enhancer.go` | 193 | done |
| 4-server-routes | `task_management/interface/utils/description_loader.py` | `fastmcp/task_management/interface/utils/description_loader.go` | 81 | done |
| 4-server-routes | `task_management/interface/utils/error_handler.py` | `fastmcp/task_management/interface/utils/error_handler.go` | 588 | done |
| 4-server-routes | `task_management/interface/utils/flexible_schema_generator.py` | `fastmcp/task_management/interface/utils/flexible_schema_generator.go` | 295 | done |
| 4-server-routes | `task_management/interface/utils/json_parameter_mixin.py` | `fastmcp/task_management/interface/utils/json_parameter_mixin.go` | 125 | done |
| 4-server-routes | `task_management/interface/utils/json_parameter_parser.py` | `fastmcp/task_management/interface/utils/json_parameter_parser.go` | 181 | done |
| 4-server-routes | `task_management/interface/utils/mcp_parameter_validator.py` | `fastmcp/task_management/interface/utils/mcp_parameter_validator.go` | 207 | done |
| 4-server-routes | `task_management/interface/utils/parameter_validation_fix.py` | `fastmcp/task_management/interface/utils/parameter_validation_fix.go` | 469 | done |
| 4-server-routes | `task_management/interface/utils/response_formatter.py` | `fastmcp/task_management/interface/utils/response_formatter.go` | 557 | done |
| 4-server-routes | `tools/tool.py` | `fastmcp/tools/tool.go` | 388 | done |
| 4-server-routes | `tools/tool_manager.py` | `fastmcp/tools/tool_manager.go` | 215 | done |
| 4-server-routes | `tools/tool_path.py` | `fastmcp/tools/tool_path.go` | 145 | done |
| 4-server-routes | `tools/tool_transform.py` | `fastmcp/tools/tool_transform.go` | 669 | done |
| 5-auth | `auth/api/supabase_endpoints.py` | `fastmcp/auth/api/supabase_endpoints.go` | 356 | done |
| 5-auth | `auth/config/token_costs.py` | `fastmcp/auth/config/token_costs.go` | 133 | done |
| 5-auth | `auth/dependencies.py` | `fastmcp/auth/dependencies.go` | 130 | done |
| 5-auth | `auth/hook_auth.py` | `fastmcp/auth/hook_auth.go` | 235 | done |
| 5-auth | `auth/interface/auth_endpoints.py` | `fastmcp/auth/interface/auth_endpoints.go` | 1593 | done |
| 5-auth | `auth/interface/fastapi_auth.py` | `fastmcp/auth/interface/fastapi_auth.go` | 115 | done |
| 5-auth | `auth/interface/supabase_fastapi_auth.py` | `fastmcp/auth/interface/supabase_fastapi_auth.go` | 279 | done |
| 5-auth | `auth/interface/unified_auth.py` | `fastmcp/auth/interface/unified_auth.go` | 188 | done |
| 5-auth | `auth/keycloak_auth.py` | `fastmcp/auth/keycloak_auth.go` | 384 | done |
| 5-auth | `auth/keycloak_dependencies.py` | `fastmcp/auth/keycloak_dependencies.go` | 295 | done |
| 5-auth | `auth/keycloak_integration.py` | `fastmcp/auth/keycloak_integration.go` | 464 | done |
| 5-auth | `auth/mcp_dependencies.py` | `fastmcp/auth/mcp_dependencies.go` | 129 | done |
| 5-auth | `auth/mcp_integration/jwt_auth_backend.py` | `fastmcp/auth/mcp_integration/jwt_auth_backend.go` | 547 | done |
| 5-auth | `auth/mcp_integration/mcp_auth_middleware.py` | `fastmcp/auth/mcp_integration/mcp_auth_middleware.go` | 116 | done |
| 5-auth | `auth/mcp_integration/repository_filter.py` | `fastmcp/auth/mcp_integration/repository_filter.go` | 435 | done |
| 5-auth | `auth/mcp_integration/server_config.py` | `fastmcp/auth/mcp_integration/server_config.go` | 194 | done |
| 5-auth | `auth/mcp_keycloak_auth.py` | `fastmcp/auth/mcp_keycloak_auth.go` | 424 | done |
| 5-auth | `auth/mcp_keycloak_validator.py` | `fastmcp/auth/mcp_keycloak_validator.go` | 377 | done |
| 5-auth | `auth/middleware/dual_auth_middleware.py` | `fastmcp/auth/middleware/dual_auth_middleware.go` | 904 | done |
| 5-auth | `auth/middleware/jwt_auth_middleware.py` | `fastmcp/auth/middleware/jwt_auth_middleware.go` | 313 | done |
| 5-auth | `auth/middleware/request_context_middleware.py` | `fastmcp/auth/middleware/request_context_middleware.go` | 385 | done |
| 5-auth | `auth/models/api_token.py` | `fastmcp/auth/models/api_token.go` | 72 | done |
| 5-auth | `auth/service_account.py` | `fastmcp/auth/service_account.go` | 484 | done |
| 5-auth | `auth/services/mcp_token_service.py` | `fastmcp/auth/services/mcp_token_service.go` | 270 | done |
| 5-auth | `auth/ssl_config.py` | `fastmcp/auth/ssl_config.go` | 63 | done |
| 5-auth | `auth/supabase_client.py` | `fastmcp/auth/supabase_client.go` | 259 | done |
| 5-auth | `auth/token_validator.py` | `fastmcp/auth/token_validator.go` | 381 | done |
| 5-auth | `auth/unified_token_validator.py` | `fastmcp/auth/unified_token_validator.go` | 320 | done |
| 6-websocket | `middleware/websocket_message_logger.py` | `fastmcp/middleware/websocket_message_logger.go` | 339 | done |
| 6-websocket | `server/metrics/websocket_metrics.py` | `fastmcp/server/metrics/websocket_metrics.go` | 214 | done |
| 6-websocket | `server/routes/websocket_routes.py` | `fastmcp/server/routes/websocket_routes.go` | 2194 | done |
| 6-websocket | `websocket/batch_processor.py` | `fastmcp/websocket/batch_processor.go` | 376 | done |
| 6-websocket | `websocket/connection_manager.py` | `fastmcp/websocket/connection_manager.go` | 426 | done |
| 6-websocket | `websocket/fastapi_integration.py` | `fastmcp/websocket/fastapi_integration.go` | 223 | done |
| 6-websocket | `websocket/models.py` | `fastmcp/websocket/models.go` | 269 | done |
| 6-websocket | `websocket/protocol.py` | `fastmcp/websocket/protocol.go` | 402 | done |
| 6-websocket | `websocket/server.py` | `fastmcp/websocket/server.go` | 413 | done |
| 6-websocket | `websocket/types.py` | `fastmcp/websocket/types.go` | 23 | done |

## Conventions

- Python `ValueError`/`TypeError` raised by value-object `__post_init__` → Go constructors `NewX(...) (X, error)` returning `*value_objects.ValueError` / `*value_objects.TypeError` with the **same message text**.
- Python `Enum` → `type X string` + typed consts + `XValues` slice (declaration order).
- Python `Optional[X]` return → `(X, bool)`.
- Python dataclass `frozen=True` → struct with unexported mutation; constructors validate.
- Files whose Python stem ends in a Go-reserved suffix (`_test`, `_linux`, …) get `_py` appended.
- Go error messages that join a Python `set` (nondeterministic order) use declaration order.

## Notes / decisions needing owner review

- Go ParseISO rejects datetime.fromisoformat forms Python 3.11+ accepts: space separator, basic format 20260102T030405, truncated times (T03:04, T03), ISO week dates, +0530/-0800 offsets, T24:00:00 (accepted, low risk; Python's specific out-of-range messages also differ from the generic `Invalid isoformat string`).
- JSON-decoded dicts carry float64 numbers; TemplateFromDict accepts integral float64 for `version`. Repository/infrastructure decoding must do the same or use typed structs.
- `Task.to_dict` lazily imports application `agent_mappings`; Go registers it via `entities.AgentNameResolver` (set by use_cases init).
- ProgressTimeline keeps `MilestoneOrder` (Python dict insertion order decides milestone event order).
- Python defect preserved: `context.TaskContext.from_dict` known_fields is missing a comma (`"task_id" "user_id"` → `task_iduser_id`), so `task_id`/`user_id` and progress_* keys are re-imported as a root_level_custom_fields section.
- Python behavior preserved: `TaskContext.to_dict` walks dataclass `__dict__`, so `metadata._domain_events` (timestamp events, random ids) leaks into the output; Go reproduces it via `RawDict()` on the base timestamp events.
- Dict iteration order from JSON input is lost in Go maps: `TaskContextUnified.merge_context_updates`/`validate_context_data` and `checkKwargs` iterate sorted keys (error text order may differ from Python for multi-key inputs).
- `Project.create_git_branch_async`, Python `GlobalContext`/`TaskContextUnified` numeric fields: progress is kept as int.
- Python set output order (agent profile lists) is unspecified; Go sorts (capabilities in enum declaration order).
- All Go clocks truncate to microseconds so isoformat round-trips like Python datetime.
- `Agent.calculate_task_suitability_score` raises ZeroDivisionError for max_concurrent_tasks=0; Go returns `ErrZeroDivision`.

- `task_management/domain/enums/*.py` duplicates 7 files in `domain/value_objects/` (byte-identical bodies; `diff` shows only `__init__.py` differs). Nothing imports the duplicates directly except `enums/__init__.py` (re-exports `AgentRole`, `EstimatedEffort`, `EffortLevel`, `CommonLabel`, `LabelValidator`). Go keeps one implementation in `value_objects`; `domain/enums/` will hold type aliases for the `__init__` exports only. Confirm before merging duplicates in Python.
- `agent_roles.py` reads YAML at runtime; needs `gopkg.in/yaml.v3` (dependency decision pending network access check).

- Name collisions (Python modules → one Go package): non-canonical duplicates get a module-name prefix: `agents.AgentRole` → `AgentsAgentRole`, `compliance_objects.ComplianceStatus/ValidationResult` → `ComplianceObjectsComplianceStatus/ComplianceObjectsValidationResult`. Plain names belong to the types exported by `value_objects/__init__.py`.
- Accepted deviations (dev-check finding 2/3, slice 1a): Go is stricter than Python for exotic ID inputs: `+`/`0x`/underscore-padded hex and non-ASCII Unicode digits (Python `int(hex,16)`, `\d`, `isdigit`), `str.strip()` of \x1c-\x1f, and subtask numeric suffixes beyond int64.
- `compliance_objects.py` lacks `SecurityContext`/`ProcessInfo`, which `infrastructure/security/access_controller.py` and `monitoring/process_monitor.py` import (broken imports in Python; revisit in slice 2).

- Float-typed Python fields that may also receive `int` (e.g. `ProgressSnapshot.percentage`) format error text as Go floats (`got 150.0` vs Python `got 150` when an int was passed).
- `rule_value_objects.py` imports `entities.rule_entity` (RuleContent/RuleInheritance); a `value_objects`→`entities` import would be a Go import cycle. Deferred until entities are ported; `CompositionResult`/`CacheEntry` will need the entity types moved or referenced via interface.

- Dict-ordered float sums: Python sums over dict insertion order, so Go takes ordered slices (`SkillRequirement`, `KeyedProgress`) or tracks first-seen order instead of ranging over maps. Apply this to any float accumulation over a map in later slices.
- Python `seq[:n]` with negative `n`: use `pySliceEnd` (value_objects/hints.go) instead of raw Go slicing.
- YAML: `agent_roles` uses `gopkg.in/yaml.v3` rather than PyYAML `safe_load`; YAML 1.1 scalars differ (`yes`→True in Python, string in Go; `0o17`; date types). `DisplayName`/`Description`/`WhenToUse` return "" for non-string values. No `job_desc.yaml` exists in the repo, so the loader currently yields nil in practice.
- Domain exceptions: Python classes → structs embedding the parent + `Unwrap()` so `errors.As(err, &parent)` mirrors `isinstance`. `DatabaseConnectionException`/`RepositoryError` keep the Python quirk that their `error_code`/`severity` overrides are discarded by `DatabaseException` (code `DATABASE_ERROR`, severity HIGH). `domain/exceptions/__init__.py` re-exports application exceptions (domain→application import); Go skips the re-export aliases (would cycle) — callers use the application package directly.

- `PyStr`/`PyRepr` (value_objects/coordination.go) mirror Python `str()`/`repr()` for JSON-like values; use them wherever Python interpolates or stringifies arbitrary values into messages/contexts (`True`, `1.0`, `['a', 1]`, `None`). Dict keys print sorted (Python: insertion order).
- Go `""` stands in for an omitted optional string argument in exception constructors (`DatabaseConnectionException("")` uses the default message, Python keeps `""`; `UserAuthenticationRequiredError("")` defaults to "This operation"). `strings.ToUpper` differs from Python `.upper()` for `ß` (error codes built from resource/service names; ASCII in practice).
- `WithContext` is accepted but ignored by constructors whose Python versions raise `TypeError` for a duplicate `context` kwarg (Concurrency/External/Configuration/ResourceNotFound/AlreadyExists/OperationNotPermitted). Python kwargs that override `severity`/`recoverable`/`error_code` are unrepresentable.

- Events: plain `BaseDomainEvent` subclasses are generated from the Python AST (scratchpad `genevents.py`) with `dict:"snake_name"` tags; `EventToDict` reflects over them (`asdict` + event_id/occurred_at/event_type fixups). Events with hand-written `to_dict`/`event_type` (context, hint, progress, branch) are ported by hand. Nil maps render as `None`; nil slices as `[]`; construct events with `NewX()` to get the Python defaults.
- Hint events declare `user_id: str`, shadowing the base `user_id`; Go keeps the base pointer field and adds `User string` for that Python field (the dict key stays `user_id`).
- `events/__init__.py` aliases (`TaskCreated = TaskCreatedEvent`, ...) are Go type aliases in `task_lifecycle_events.go`; the dead legacy `task_events.py` classes keep module-prefixed names (`TaskEventsTaskCreated`, ...). `DomainEvent` is an alias of `BaseDomainEvent`.
- `branch_lifecycle_events.py` raises `TypeError` on import in Python (non-default `project_id` after a default field); it is imported only by `cascade_deletion_service.py`. The Go port keeps the intended shape; naive `utcnow()` timestamps render without offset (`IsoFormatNaive`). Owner decision needed: fix in Python or keep as-is.
- `orchestrator.py` defects preserved (probed on real Python): `orchestrate_project` raises `ValueError: Agent <uuid> not registered` whenever an unassigned branch meets an available agent (AgentId object never matches the str keys of `registered_agents`); `balance_workload` raises `KeyError "AgentId(value='...')"` for any agent above 80% and ZeroDivisionError with no agents; the `prerequisite_not_active` issue of `coordinate_cross_tree_dependencies` is dead code. Owner decision: fix in Python first?
- `task_state_transition_service.py`: its rules allow `blocked -> todo` but `TaskStatus.can_transition_to` forbids it, so `handle_dependency_completion` never unblocks a task (transition fails with `Transition failed: Cannot transition from blocked to todo`). Go reproduces this; fixtures in `testdata/task_state_transition_cases.json` come from real Python. Logging calls are dropped (no logger in the domain services).
- `task_validation_service.py`: `Task.due_date` is a str, so `validate_business_constraints` raises AttributeError (`'str' object has no attribute 'tzinfo'`) for any non-empty due date and returns that single error (Go reproduces it). `Task` has no `project_id`, so the project checks are dead code and not ported. Fixtures: `testdata/task_validation_cases.json` (real Python).
- `hint_rules.py`: Task has no `progress`/`progress_breakdown`, so ImplementationReadyForTesting and NearCompletion never fire; any non-nil TaskContext raises AttributeError (`ContextNotes` has no `.get`) in MissingContext/Collaboration; a non-nil `Task.progress_timeline` raises TypeError (not subscriptable) in StalledProgress, so the stall hints are unreachable (Go keeps `stalledHint` for the intended shape, unit-tested directly). Fixtures: `testdata/hint_rules_cases.json` (real Python).
- `content_analyzer.py` uses Python `re` with Unicode `\b`/`\w`/`\s` and IGNORECASE folding that RE2 and .NET both get wrong. Go uses `github.com/dlclark/regexp2` (new dependency, v1.11.5) with `pyRegex` translating each pattern: `\w`/`\s`/`\d` become explicit Unicode classes, leading/trailing `\b` become look-behind/look-ahead, and IGNORECASE is expanded by hand (a-z ranges also match `İ ı ſ K`; literal s/k/i get their extras). Positions are code point indexes. Differential corpus (accented, NFD Vietnamese, Kelvin/long-s, Arabic digits, tabs/NBSP) in `testdata/content_analyzer_cases.json` matches real Python exactly.
- Cross-cutting: Python 3.12+ `sum()` over floats is Neumaier-compensated, so plain Go `+=` loops differ in the last bits (117 of 240 random lists). `value_objects.PySum` reproduces it bit for bit (`testdata/pysum_cases.json`). Applied to progress.py (3 sites), vision_objects.py, agents.py quality_score, orchestrator balance_workload, content_analyzer. RULE for all later ports: every Python `sum(` over floats must use `PySum`; also look for `statistics.mean`, `fsum` and `math.prod`.
- `rule_composition_service.py`: `RuleContent.sections/variables/parsed_content` were plain Go maps; they are now `*entities.OrderedMap` (insertion order decides composed output). New `value_objects.PyJSONDumps(v, indent)` mirrors `json.dumps` (ensure_ascii, ordered maps via `OrderedAny`, `indent=None` as -1) and is the JSON encoder to reuse for any Python `json.dumps` parity; `PyRepr` handles `OrderedAny` too. `RuleMetadata` has no `priority`, so sorting only uses rule type (core 1000, workflow 500). 498 composition scenarios (3 rules × 4 conflict modes × 4 strategies × 5 formats, plus the empty-output failure path) match real Python (`testdata/rule_composition_cases.json`).
- `intelligence/semantic_matcher.py`: production Python has neither `sentence_transformers` nor `faiss` (numpy only), so it runs the `MockSentenceTransformer` (random 384-d vectors) and `_build_faiss_index` returns None before doing anything; hence `find_similar_contexts` is always `[]` and `index_size` is 0. Go ports exactly that (an `Embedder` interface defaulting to the mock; no index). The embedding cache stores JSON floats (`<md5>.json`) instead of pickles. Owner decision: if real semantic search is wanted, plug a real `Embedder` and add a vector index.
- Cross-cutting (libm parity): Go's `math.Log`/`math.Exp` differ from glibc (Python) in the last bit for ~3% / ~12% of inputs. `value_objects.PyLog` / `PyExp` (160-bit big.Float, round once) cut that to ~0.1% against 3000 random Python samples each (`testdata/pymath_cases.json`). RULE: every Python `math.log/exp` (and `**` with floats, `math.pow`, trig) must use these helpers (add `PyPow` when first needed). `math.sqrt` is exactly rounded in both, so plain `math.Sqrt` is fine. `intelligence/context_prioritizer.py` matches Python bit for bit on 18 batch runs (fixtures with a pinned clock: `testdata/context_prioritizer_cases.json`).
- `intelligence/progressive_expander.py` (and the other intelligence modules): context dicts are `map[string]any` and ids are normally strings. Python keeps non-string ids (e.g. int 7) as-is as dict keys and candidate ids; Go renders them with `str()` (`"7"`) and never matches them in string-keyed lookups. Deviation accepted (ids are UUID/str in every producer). `UserPreferences` of this module is `ProgressiveExpanderUserPreferences` (name owned by context_prioritizer in the shared Go package).
- `intelligence/predictive_loader.py`: `hash(tuple)` pattern ids and `list(set(patterns_used))` order are per-process randomised in Python, so Go uses an FNV-64a id and first-seen order (tests compare by position / sorted). Non-ASCII-digit hour segments in a time key (`int()` accepts Unicode digits, `strconv.Atoi` does not) are an accepted deviation; the ValueError for a malformed key (context_type containing `_`) is preserved. Time/duration use microsecond-truncated UTC via an injectable `Now`.
- CROSS-CUTTING (dev-check 1c-iii-c-5): (a) regenerate Python fixtures ONLY with `agenthub_main/.venv/bin/python` (py3.14, no numpy/faiss/sentence_transformers); the system python3 has numpy 2.3.5 and would silently switch `np.mean` (pairwise) in pattern_recognition_engine. (b) Python `timedelta.total_seconds()` = `value_objects.PyTotalSeconds(d)`; never use `time.Duration.Seconds()/Hours()` for parity (double rounding, 1 ulp). (c) `PyExp`/`PyLog` are correctly rounded but glibc 2.39 `exp`/`log` are not: 0.08% / 0.02% of inputs differ by 1 ulp from CPython on this host (recency/frequency scores); accepted, no code change unless bit-exact scoring is required. (d) `PyParseUUID` mirrors `uuid.UUID(str)` incl. `int(hex, 16)` leniency (whitespace, sign, 0x, `_`, Unicode digits); `EntityId` now uses it (1586 valid / 4022 generated cases match).
- `connection_management/domain/*`: naive local `datetime.now()` is the package var `Now` (entities, value_objects; microsecond-truncated, overridable in tests). Python dicts that are published (`to_dict`, server `details`, `available_actions`, `data`) are `*entities.OrderedMap` (task_management) to keep insertion order and in-place `**` override semantics (ServerStatus details, StatusUpdate data); free-form `client_info` stays `map[string]any`. `ConnectionEvent.to_dict` keeps the Python quirk that `**self.__dict__` replaces the ISO timestamp with the datetime object and that `StatusUpdateBroadcasted.event_type` replaces the class name in place. `ServerCapabilities.AuthenticationEnabled/MvpMode` are `any` (raw dict values, no bool coercion). Abstract bases (repositories, services) are Go interfaces; exception hierarchy uses embedded `ConnectionError` + `Unwrap`. Shared test helper: `connection_management/domain/internal/testutil`.
- `intelligence/pattern_recognition_engine.py`: numpy is not a dependency (pyproject), so Python runs `MockNumpy.mean` = builtin `sum()/len()`; Go uses `PySum`/len (`mockMean`). `list(set(...))[:20/15]` (file refs, entities) and `file_types`/`entity_types` have per-process-random order in Python; Go keeps first-seen order (set operations are order-insensitive, only >20 refs / >15 entities truncation differs and is itself nondeterministic in Python). Tasks are `PatternTask` (getattr duck type): `DictTask` for training dicts (ISO-string `created_at`, compared as strings; mixed str/datetime raises TypeError and skips the project exactly like Python) and `EntityTask` for entities (no `details`/`completed_at`). Non-string `assignees` elements / `estimated_effort` are rendered with `str()`. Regexes use `services.PyRegex` (exported wrapper of `pyRegex`).
- `intelligence/intelligent_context_selector.py`: Python `hash(query)` cache keys are replaced by the query text itself (same behaviour without hash collisions); metadata dict keys are visited sorted (Go maps are unordered); `selection_time_ms` and cache age use the injectable `Now`; the semantic-match branch is unreachable in production (no FAISS, `FindSimilarContexts` is always empty) but is ported; `user_preferences` is the prioritizer type (Python annotates the expander type but only passes it to the prioritizer). `SelectContext` returns the fallback result on any internal error, like the Python `except Exception`.
- `auth/domain/*`: parity-tested against real Python (`agenthub_main/.venv`; jwt 558 cases with pinned clocks and `secrets.token_hex`, password/email/user_id fixtures with Python-made bcrypt hashes, 153 `User` scenarios, 27 permission payloads + 42 decorator scenarios). JWT is a stdlib HS256 implementation with PyJWT 2.10.1 semantics (sorted header, compact insertion-ordered payload, PEM/ssh keys refused as HMAC secrets, int()-coerced iat/nbf/exp, `aud` required only when an audience is passed, sub/jti must be strings, access<->api_token compatible, missing type accepted, lenient base64url, unverified `get_token_expiry`); `verify_token` is one decode since Python's issuer-first attempt is always followed by an issuer-less fallback. Passwords use `golang.org/x/crypto/bcrypt` (cost 12, `$2a$`->`$2b$` rewrite, >72 bytes is a ValueError in hash and false in verify). The FastAPI decorators `require_permission/require_any_permission/require_scope` are net/http middleware (401 `Not authenticated` / `No token payload found`, 403 messages, `{"detail": ...}` bodies; user = `UserContextKey` holding a `TokenPayloadProvider`). Accepted deviations: set-valued fields (`scopes`, `roles`) are sorted in `ToDict`; non-string items in `scope(s)`/`roles` lists are skipped (Python keeps hashables and raises TypeError on unhashables); the checker copies nested permission dicts (Python aliases the payload and mutates it); `UserFromDict` treats naive ISO strings as UTC so they render with `+00:00` (Python keeps them naive and `is_locked` would raise TypeError on a naive `locked_until`) - the infrastructure layer must decide how stored naive timestamps are rendered; `NaN`/`Infinity` inside token JSON is rejected (Python accepts it, then fails `int()` on exp/iat anyway).
- `ai_task_planning/domain/*`, `validators/label_validator`, `websocket_protocol`: parity-tested against real Python (1,007 ai_task_planning cases: 34 requests, 152 random plans with add/validate/critical-path/groups/MCP-request output, 821 analyzer single+batch+insights; 1,500 label validation cases; 1,820 websocket cases incl. pydantic 2.12 error text). Pydantic `ValidationError` is `domain.ValidationError` and renders the pydantic 2.12 text (incl. its 50-byte `input_value` truncation, `string_type`, `literal_error`, `value_error`); `KeyError` has a Go type. Python set-ordered outputs (`suggested_agents`, `risk_summary`, `agent_recommendations`, `required_agents`) are in first-seen order (tests compare sorted). `sum()` of nothing is the int `0` (`pattern_complexity`, insights `total_estimated_hours`). Accepted deviations: `PlanningRequestFromDict` rejects wrong value types and treats naive ISO datetimes as UTC (Python stores them unvalidated / naive) and copies input lists (Python aliases them); `ValidateTimestamp` has no naive-datetime failure (Go cannot carry one) and accepts any zero-offset zone; label `\s` is `PyIsSpace`; message factories take the payload type (Python does not check it); wrong-type metadata overrides support str/None checking for declared fields only.
- `agent_management/domain/*`: parity-tested against real Python (11 config, 17 template, 16 `from_yaml`, 82 instance operation sequences, 3 service scripts over in-memory fake repositories incl. the exact repository call log; clocks/random ids normalized). Dict-valued fields (`capabilities`, `output_format`, `metadata`, entity `metadata`) are `*entities.OrderedMap[any]` (nil = Python None); repository interfaces take `ctx` and return `error`; service methods that return `None` for "not found / not owner" return `(nil, nil)`; `GenerateShareToken` returns `(token, ok, err)`. `AgentConfiguration` is a value type (With* return copies, maps shared like the frozen dataclass). New shared helpers (task_management): `entities.DecodeJSON` (json.loads into ordered maps; ints beyond int64 are `*big.Int`, `PyJSONDumps` prints them), `entities.LoadYAML` (yaml.safe_load: PyYAML YAML 1.1 implicit resolvers, merge keys, multi-document files are an error like `ComposerError`; verified on all 343 `agent-library` YAML files, incl. the 32 multi-document `metadata.yaml` that PyYAML rejects), `value_objects.NewTypedEntityId`, `value_objects.PyIsAlnum`. Accepted deviations: `AgentConfigurationFromDict` rejects non-list `tools`/`rules` and non-dict `capabilities`/`output_format`/`metadata` (Python accepts any iterable / object unvalidated); YAML timestamps stay strings and non-string mapping keys become their JSON key text (a `1:` and `true:` key collide in Python only); `DecodeJSON` rejects `NaN`/`Infinity`; `AgentTemplate.from_dict` accepts ISO strings for `created_at/updated_at` (Python crashes on strings, real callers pass datetimes); Python's AttributeError/TypeError on odd inputs are one Go error kind; `MergeCapabilities` on nil capabilities starts from empty (Python raises TypeError); `from_yaml` YAML error texts differ (PyYAML vs yaml.v3). Preserved: `customize_configuration` sets configuration/`is_customized` before failing on `None` metadata with notes; entity mutators do not `touch()` or revalidate.

- JSON number text: Python `json.dumps` prints floats with `.0` (`1.0`, `0.0`) while Go `encoding/json` prints `1`/`0`. Equal as JSON numbers, but it differs as raw response text/hashes. Slice 4 (HTTP/MCP responses) must decide on a float-preserving encoder before endpoint-diffing against the Python server. Related: `HintGenerated.confidence` defaults to int `0` in Python.
- `EventToDict` copies nested values as-is; Python `asdict` leaves nested datetime/Enum objects inside dict fields unconverted too. Later serialization layers must handle `time.Time`/string-enum values inside those maps the same way the Python JSON encoder does (the populated-value case is not yet differentially tested).
- Slice 0 shared config (`dual_mode_config`, `config/{version,auth_config,cors_factory}`, `exceptions`, `utilities/pypath`): parity-tested against real Python. Deviations: env names upper-cased with `strings.ToUpper` (not Python `str.upper` for non-ASCII); `cors_factory` does not port `allow_origin_regex`; `McpError` re-export deferred; project root is anchored on the executable path instead of `__file__`.
- Infrastructure batch (`uuid_column_type`, `timestamp_events`, `tool_config`, `performance_config`, `access_controller`, `directory_utils`): `AccessController` constructor always errors, preserving a Python defect (`SecurityLevel.PROTECTED` is missing, so no instance is reachable). DB driver decision for later slices: `database/sql` + pgx stdlib plus a pure-Go sqlite driver.
- Slice 1c-iii-c-9 fixes: `PyRepr` prints `*big.Int`; `ConvertTaskDeleteLegacy` with a dict id and blank title raises `KeyError: slice(None, 8, None)`; `PlanningRequestFromDict` parses `created_at` strictly when the key is present.
- `database/models.go` is generated from the SQLAlchemy metadata by `tools/gen_models/gen_models.py` (run: `cd agenthub_main/src && ../.venv/bin/python ../../agenthub_go/tools/gen_models/gen_models.py`): one row struct per table, `Tables` (columns, client defaults, server defaults, FKs, DDL via the PostgreSQL dialect), `EnumTypes`. Regenerate when models.py changes (it has uncommitted user edits). Enum columns store the member NAME (`INITIAL`), JSON columns are `json.RawMessage`, naive `DateTime` columns are `time.Time` in UTC. Repositories must apply the `Default*` kinds on insert (SQLAlchemy client-side defaults). `CreateTables` ports `create_all(checkfirst)` + critical-table recheck + AI columns.
- Go version: go.mod stays on 1.23 (pgx 5.7.2, go-internal v1.13.1, kr/text v0.2.0 pinned so `go mod tidy` is clean).
- DeepSeek waves 1-2 (built/vetted/race-tested by the owner; audited by dev-check where a Python oracle exists): types/*, utilities/{cache,components,debug_service,http,json_schema,mcp_config,types,environment}, config/{auth_tools,tool_registry,tool_config_loader}, infrastructure/{parsers,services,utilities,cache,events,event_bus,event_store,monitoring,workers,adapters,websocket,validation,ai_services,performance,notification_service,unified_logging}, connection_management infra, shared messaging event_bus. Skips/deviations to decide: `template_engine_service` needs a Handlebars lib (pybars3; e.g. aymerick/raymond) and Redis; `event_store` SQLite backend is in-memory in Go (needs a pure-Go SQLite driver or a PostgreSQL-backed store); `document_validator`/`template_registry_service`/`access_controller` constructors always fail in Python (defects preserved); `process_monitor` Python is broken (ProcessInfo/ProcessStatus members missing), Go uses the intended shape; asyncio loops are not auto-spawned; MetricsMiddleware/decorators not ported; Jinja2 HTML reports are hand-rendered (whitespace differs); `cache_service_adapter`/`event_store_adapter`/`task_performance_optimizer` depend on unported layers.
- utilities/pyyaml: faithful port of PyYAML 6 `yaml.dump` (representer, resolver, serializer, emitter; sort_keys flag, default Dumper, allow_unicode=False, width 80) verified on 6000 + 4x8000 differential cases (fixtures in utilities/pyyaml/testdata). Replaces the two hand-written dumpers.
- Real PostgreSQL for tests: `tools/testpg/start.sh` (embedded PG16 binaries, no root/Docker) prints `AGENTHUB_TEST_PG_URL`; integration tests skip without it.
- `repositories/base_orm_repository.go` (+ user scoped variants) is a generic CRUD layer over the generated `database.Tables`/row structs and `SessionManager` (transaction carried in context.Context, replacing thread-local sessions). Repositories are keyed by Python attribute names (`model_metadata` -> "metadata").

- **WebSocket notifications are currently dropped in ported use cases/facades** (create_task, update_task, update_project, delete_project, delete_branch, agent facade register/update/unregister, event_handlers). Python broadcasts via WebSocketNotificationService (now complete in `application/services/websocket_notification_service.go`, incl. `DBWebSocketContextProvider`). When each of those rows is audited, wire the notifier (Broker = `server/routes.BroadcastDataChange`) where Python calls it. Not done until then: realtime frontend sync.
- Python `_get_branch_cascade_data` runs `ROUND(double precision, int)` on PostgreSQL, which fails, so Python never attaches `metadata.cascade`; Go runs the same SQL and keeps that outcome.

- **event_handlers (decision 2026-10-01, owner):** in Python most handlers raise AttributeError on the first line (events lack the attributes they read) and `process_event` can never route (class-name vs snake_case keys). The Go port bridges the missing attributes and dispatches by Go type, so the handlers work. Kept as an intentional deviation (b); it is only visible once the event bus delivers these events.
- **event_handlers (decision 2026-10-02, owner, after dev-check c38/part 2):** (b) stays for handlers whose only effects are in-memory/log/notification (agent, project, task, hint): they run against the real event fields (invented placeholders are documented in the Go comments). Exception (a) for progress: `ProgressUpdatedHandler.updateContextMilestone` and `SubtaskProgressAggregatedHandler.Handle` are inert in Go, because Python raises AttributeError (`get_by_id`/`update` do not exist) before any DB write; Go must not write task/context rows Python never writes. `AgentEventHandlers` maps are guarded by a mutex (E2).
  - Follow-up (dev-check re-check): hint handlers: Python `_get_hint_details` fallback calls `event_store.get_events_by_aggregate`, which does not exist (AttributeError when no hint repository) — Go works (decision b). Hint/project/task/agent handler maps are mutex-guarded; handlers that call other locked handlers use unlocked cores; the agent handlers release the lock before calling the coordination service. Placeholders are documented in a block comment per Go file.
- **auth_application_facade (2026-10-02):** `DualAuthenticate` tries Supabase first when `SUPABASE_ENABLED=true` through the `SupabaseAuthenticator` interface (field `Supabase`, nil = `get_supabase_client()` None); the concrete client is `auth/infrastructure/supabase_client` (server team, todo). `agent_coordination_service.go` ported (consumer-side interfaces for task/agent repositories and event bus, as Python types them `Any`; no Go implementation of `CoordinationTaskRepository.Get` exists, same as Python where `TaskRepository.get` does not exist).
- **ai_integration_service (2026-10-02):** `createMCPTasksFromPlan` skips every planned task that has an `agent_assignment`: Python builds the request with `planned_task.agent_assignment.agent_id`, but `AgentAssignment` only has `primary_agent`, so each such task raises AttributeError (caught per task) before anything is created. Requirement description/priority non-strings are stringified (Python stores them unvalidated). Logging is dropped as elsewhere.
- Factories: singleton/cache state guarded by `factoriesMu`/per-factory mutex (Python GIL); `ContextDelegationService` is not passed to the unified-context factory (no exported constructor).

- **Use-case side effects (hooks pattern, 2026-10-01):** use cases dropped Python's inline context auto-creation / metadata sync / WS notifications. Fix pattern: a consumer-side `XHooks` interface in `application/use_cases` + implementation in `application/hooks` (imports factories+services, which import use_cases). Done: create_task (`CreateTaskHooks`, `hooks.TaskHooks`; compose with `uc.WithHooks(&hooks.TaskHooks{...})` at server wiring). TODO: update_task, complete_task, delete_task, subtask use cases, project/branch use cases (see `grep -rn "dropped\|unported" application/`). Python `TaskCreatedEvent.create` does not exist, so Python never dispatched task_created from create_task (Go matches).

## Parity checklist

- [x] Slice 1a: value_objects IDs, priority, task_status, pagination, progress_percentage, estimated_effort, context/compliance/progress/template/rule enums — `go build`, `go vet`, `go test` pass; behavior cross-checked against running Python for transitions, ID normalization, subtask ID generation, progress conversion, effort hours/levels.
- [x] Slice 1b (value_objects): agent_roles, agents, common_labels, compliance_objects, coordination, hints, progress, vision_objects — build/vet/test -race pass; common_labels/progress/coordination/vision outputs cross-checked vs Python. `rule_value_objects` deferred (entity dependency).
- [x] Slice 1c-i: domain exceptions (quirks cross-checked vs Python).
- [x] Slice 1c-ii: domain events (all 9 modules; to_dict shapes cross-checked vs Python).
- [x] Slice 1c-iii-a: entities/base/base_timestamp_entity, label, rule_entity, rule_content, value_objects/rule_value_objects (generic over entity types to avoid a cycle).
- [x] Slice 1c-iii-b-1: entities/work_session, agent, template (+ fnmatch helper; clocks truncated to µs like Python datetime).
- [x] Slice 1c-iii-b-2: entities/task, subtask, git_branch, project (+ ordered_map helper; Project.create_git_branch_async waits for the GitBranchRepository interface).
- [x] Slice 1c-iii-b-3 (dev-check PASS, see ledger in Notes): remaining entities (context, agent_session, global_context_schema), interfaces, repositories, constants
- [ ] Slice 1c-iii-c: domain services, validators, rule_value_objects, other bounded contexts' domain rows
- [ ] Slice 2: infrastructure/db (schema parity vs `init_schema_postgresql.sql`, SQLite + Postgres)
- [ ] Slice 3: application (dtos, use_cases, services, facades, factories, event_handlers)
- [ ] Slice 4: server routes / MCP tools / middleware (endpoint diff vs running Python server)
- [ ] Slice 5: auth (Keycloak/JWT)
- [ ] Slice 6: websocket protocol v2.0 + session_stream (uncommitted Python work included)
- [ ] Final: endpoint/behavior comparison against the running Python server; owner+user parity confirmation before any Python removal

### Owner requests (details in "Post-migration requests from the owner" below)

Rules: do not start a group before the one above it is done. Tick a box only when its check is met. Never commit, push, deploy, or touch the production server without the owner's go-ahead. Never print secrets (`.mcp.json` bearer token, `*_SECRET*`, `*PASSWORD*`).

**A. Port the session-streaming backend (belongs to Slices 2, 4, 6; must be done before "Final")** — Request 5
- [ ] A1 (Slice 2): GORM/SQL models for `agent_sessions` and `agent_session_events` with the exact columns, unique keys and index from Request 5. Use a name distinct from the domain `AgentSession` entity (e.g. `StreamedSession`). Check: tables are created on SQLite and on Postgres 14 with no diff against the Python-created schema.
- [ ] A2 (Slice 0): `session_stream/repository.go` — every function takes `userID` and filters on it. Check: session id for `(user, connector, key)` equals the Python `uuid5(6f1c2d3e-4a5b-4c6d-8e7f-0a1b2c3d4e5f, "user:connector:key")` for at least 5 sample inputs; server-assigned `seq` is monotonic; limits 200 events/batch, 64K payload → `{"truncated": true}`, page limit clamp 1000.
- [ ] A3 (Slice 0): `session_stream/hub.go` — per-session fan-out, bounded queue 1000, slow viewer dropped, unsubscribe on viewer exit. Check: test that an idle viewer leaving leaves no subscription.
- [ ] A4 (Slice 4): `WS /ws/connector` — token from `?token=` or `Authorization: Bearer`, scope `sessions:write`, close codes 4001/4003, frames `hello`/`session`/`events` with acks and errors as in Request 5, 1 MiB message cap, sessions set `offline` on disconnect. Check: Go server passes the same scenarios as the 9 Python tests in `agenthub_main/src/tests/session_stream/session_stream_test.py`.
- [ ] A5 (Slice 4): `WS /ws/sessions/{id}` — Keycloak JWT, ownership check with identical close 4004 for missing and not-yours, replay `after_seq` in pages of 500 then live, subscribe before replay, detect client close while idle.
- [ ] A6 (Slice 4): `GET /api/v2/sessions` and `GET /api/v2/sessions/{id}/events` — 404 when not owned, newest `last_seen` first.
- [ ] A7: cross-user isolation test in Go (user B cannot list, read, replay or append to user A's session) and a Python-vs-Go differential test on the same inputs.
- [ ] A8: owner decision recorded here about the in-memory hub with more than one replica (Postgres `LISTEN/NOTIFY`, Redis, or single replica). Decision: _pending owner_.

**B. Verify the Python reference before relying on it** — Request 5
- [ ] B1: confirm `Base.metadata.create_all` creates the two new tables on a Postgres 14 instance (local test DB first; production only with the owner's go-ahead).
- [ ] B2: make the `session_stream` tests runnable in CI with the repo's normal conftest (it needs a Postgres DB `agenthub_test`), or document `--noconftest` in the test file header.

**C. New features (after the Go port is verified)** — Requests 2, 3, 6
- [ ] C1: connector CLI for the user's WSL: list tmux sessions, tail `~/.claude/projects/*/*.jsonl`, redact secrets locally before upload, reconnect with backoff, send the Request 5 frames. Check: a real Claude Code session appears in `GET /api/v2/sessions` for the right user only. **Superseded by F4 (`rigd`): fold into it, do not build separately.**
- [ ] C2: connector token flow: a user creates an API token with scope `sessions:write` from the dashboard (the token endpoint already accepts arbitrary scopes; default is `["read"]`).
- [ ] C3: dashboard page in `agenthub-frontend`: own session list, live view over `/ws/sessions/{id}`, optional xterm.js raw-terminal tab (Keycloak login).
- [ ] C4: two-user end-to-end test: user A and user B each connect a connector and each sees only their own sessions.
- [ ] C5: deploy check: CapRover "Websocket Support" on for `4genthub-backend`, nginx `Upgrade`/`Connection` headers and long `proxy_read_timeout` work for `/ws/*`.

**D. tmux messaging and web input** — Request 1 and Request 6.3
- [ ] D1: ask the owner which case is wanted (agent↔agent, agent→human, or both) and record the answer here before building. Answer: _pending owner_.
- [ ] D2: MCP tool `send_to_agent(name, message)` using the tmux recipe (temp file → `load-buffer` → `paste-buffer -d -r -p` → separate `C-m`), per-pane lock, `has-session` check. Check: a multi-line message arrives as one submission, not one per line. **Superseded by F4 (`rigd`): fold into it, do not build separately.**
- [ ] D3: human notification path chosen in D1 (WSL toast, `tmux display-message`, or dashboard push).
- [ ] D4: web → tmux input, opt-in per session, scope `sessions:input`, read-only by default, commands accepted only for sessions the same connector registered, rate limit, audit log. **Superseded by F4 (`rigd`): fold into it, do not build separately.**
- [ ] D5: teams/sharing (`team_id`, owner/viewer roles). Low priority, single-owner first.

**E. Already done (keep for traceability)**
- [x] E1: deepseek-offload installed in `~/__projects__/4genthub` (Request 4); `doctor` all ok, smoke job returned a correct report.
- [x] E2: Python session-streaming backend written with 9 passing tests (Request 5), uncommitted.
- [x] E3: owner requests written into this file (Request 7).
- [x] E4: Request 8 recorded and planned as group F below (plan only; no code written). Plan file: `~/.claude/plans/compressed-conjuring-aurora.md`.

**F. OpenRig-style system topology in Go, full runtime** — Request 8. Gate: Slices 2, 4, 5 and 6 of this migration are done. Go only (owner decision); do not write a Python version.
- [ ] F1 (spec domain, `fastmcp/rig/spec/`): RigSpec 0.2 structs (`pods[].members[]`, pod-local `edges`, cross-pod `pod.member` edges, `startup.files/actions`, `services`, `continuity_policy`, `restore_policy`), YAML codec (`gopkg.in/yaml.v3`), validator (edge kinds `delegates_to`, `spawned_by`, `can_observe`, `collaborates_with`, `escalates_to`; duplicate ids; unknown refs; cycle detection over `delegates_to`/`spawned_by` only), exporter. Sources: `~/__projects__/openrig/docs/reference/rig-spec.md`, `edge-types.md`, `packages/daemon/src/domain/rigspec-schema.ts`, `rigspec-codec.ts`, `rigspec-exporter.ts`. Check: `openrig/demo/rig.yaml` round-trips unchanged; invalid fixtures from `openrig/packages/test-system/scenarios/*.yaml` are rejected for the same reasons.
- [ ] F2 (persistence): tables `rigs`, `pods` (unique `rig_id`+`namespace`), `nodes` (`logical_id` unique per rig; role, runtime, model, cwd), `edges` (source and target must be in the same rig), `bindings` (node → tmux session/window/pane), `sessions` (node → live state), each with `user_id` filtered in one repository. Sources: `openrig/packages/daemon/src/db/migrations/001_core_schema.ts`, `002_bindings_sessions.ts`, `017_pod_namespace.ts`. Check: identical schema on SQLite and Postgres 14; cross-tenant read/write test (user B gets 404 for user A's rig).
- [ ] F3 (API + MCP): `/api/v2/rigs` CRUD, spec import/export, `ps`; MCP tools `rig_up`, `rig_down`, `rig_ps`, `rig_send`, `rig_whoami`, `rig_capture`. Agent members reference 4genthub agents as `template:<slug>` (from `agent_templates`) or `instance:<id>` (from `user_agent_instances`); the system prompt is injected at launch like the `spawn-team` proxy pattern. A rig may link to a `project_id`. Check: endpoint tests; `whoami` returns identity plus incoming/outgoing edges.
- [ ] F4 (local daemon `cmd/rigd`, replaces C1, D2 and D4): runs on the user's machine and dials OUT over WSS to the server (the Request 5 frames are a subset of its protocol; add command frames `up`, `down`, `send`, `capture`). Contains: tmux adapter ported from `openrig/packages/daemon/src/adapters/tmux.ts` (paste recipe, guarded input, buffer cleanup), a `RuntimeAdapter` interface (`listInstalled`, `project`, `deliverStartup`, `launchHarness`, `checkReady`) with `claude-code`, `codex`, `terminal` adapters (see `domain/runtime-adapter.ts:131`, `adapters/terminal-adapter.ts`), a topological instantiator (see `domain/rigspec-instantiator.ts`), bindings, and the JSONL transcript tailer with local redaction. Check: using a stub runtime (model: `adapters/stub-runtime-adapter.ts`) a 5-member spec launches in edge order in real tmux; a multi-line `send` arrives as one submission; killing the connection reconnects with backoff.
- [ ] F5 (restore and snapshots): port the essentials of `domain/restore-orchestrator.ts` and `snapshot-capture.ts` (resume tokens, launch order on restore). Check: kill the tmux server, restore, and the same nodes are re-bound in edge order.
- [ ] F6 (CLI `cmd/rig`): `up`, `down`, `ps`, `send`, `capture`, `whoami`, `restore`, `snapshot`, `specs` (stdlib `flag` or at most one small dependency). Reference command list: `openrig/packages/cli/src/commands/`.
- [ ] F7 (dashboard): topology graph in `agenthub-frontend` (pods as groups, edges drawn by kind) plus a seats table, live via `/ws/sessions`.
- [ ] F8 (safety): a server command is remote command execution on the user's machine, so `rigd` enforces a LOCAL allowlist (cwd roots, runtimes, permission policy) and refuses anything else; per-user tokens bound to one account; audit log; read-only by default; opt-in for `send`/`up`.
- [ ] F9 (spike, do first): run tmux + Claude Code under WSL2 through `rigd`. OpenRig's own README says WSL2 is untested.
- [ ] F10 (out of scope for now): OpenRig queue, inbox/outbox, workflows, watchdog, TUI, gateway/Slack.


---

# Post-migration requests from the owner (session of 2026-09-30)

Written by the session that built the Python `session_stream` feature. **Do these AFTER the Go migration is finished** (or fold them into Slice 4/5/6 where noted). The owner's requests are quoted as typed, then interpreted. Status is as of 2026-09-30 23:5x; nothing below is committed or deployed. Do not print or copy secret values from servers or `.mcp.json`.

## Request 1 — "make 4genthub work like openrig workspace and tmux send message direct to pc user"
Interpreted: agents in tmux sessions should be addressable and receive messages (agent↔agent), and the human at the PC should be notifiable.
- Status: **design only, not built.** OpenRig reference: `~/__projects__/openrig/packages/daemon/src/adapters/tmux.ts` (`sendText`, lines ~470-520) and `domain/seat-delivery-guard.ts`.
- Delivery recipe (do not use plain `send-keys` for text): write text to a temp file → `tmux load-buffer -b <unique> <file>` → `tmux paste-buffer -t <pane> -b <unique> -d -r -p` → separate `tmux send-keys -t <pane> C-m`. `-p` brackets the paste, `-r` keeps LF (default turns LF into Enter = submit), `-d` drops the buffer. Serialize sends per pane and check `tmux has-session` first.
- To build: an MCP tool `send_to_agent(name, message)`; panes named per agent (`tmux new -d -s agent-<name> 'claude'`). Optional: per-agent message queue table.
- Human notification (owner must choose): WSL→Windows toast (`powershell.exe` BurntToast or `msg.exe`), `tmux display-message`, or a dashboard push over WebSocket. **Open question to ask the owner: agent↔agent, agent→human, or both.**
- Note: tmux must run inside WSL; the backend must run in WSL or call `wsl tmux ...`.

## Request 2 — "is possible reading session direct on 4genthub.com ? how i can link session running to web"
- Status: **backend ingest done in Python; connector and dashboard not built.**
- Architecture (WSL is behind NAT, so the session side dials OUT): `tmux pane / Claude JSONL → local connector (WSL) ══outbound WSS══▶ 4genthub.com ──▶ browser`.
- Sources the connector reads: (a) Claude Code transcripts `~/.claude/projects/<project>/<session-id>.jsonl` (structured, preferred for a chat view); (b) optional raw terminal via `tmux pipe-pane -o -t <pane> 'cat >> file'` (live) or `tmux capture-pane -p -t <pane> -S -200` (snapshot), rendered with xterm.js. OpenRig reference: `packages/daemon/src/domain/transcript-capture.ts` and `transcript-redaction.ts`.
- Risks: transcripts contain secrets → **redact on the user's machine before upload**; batch `pipe-pane` output (~100 ms) and cap sizes.

## Request 3 — "4genthub can use of different user, each user can connect his own session project via 4genthub"
- Status: **tenant isolation implemented in Python; connector and UI pending.**
- Verified by SSH (`ssh 4genthub`, alias in `~/.ssh/config`): CapRover host running `4genthub-backend` (8000), `4genthub-frontend` (3800), `4genthubdb` (Postgres 14.5, database `postgresdb`, user `postgres`), `keycloak` + `keycloak-db` (Postgres 17). Backend env: `AUTH_ENABLED=true`, `AUTH_PROVIDER=keycloak`, `KEYCLOAK_URL=https://keycloak.4genthub.com`, `KEYCLOAK_REALM=mcp`, `KEYCLOAK_CLIENT_ID=mcp-api` (plus secrets — names only: `KEYCLOAK_CLIENT_SECRET`, `JWT_SECRET_KEY`, `DATABASE_PASSWORD`).
- Existing prod tables relevant here: `api_tokens` (id, user_id, name, token_hash, scopes jsonb, created_at, expires_at, last_used_at, usage_count, rate_limit, is_active, token_metadata, usage_stats), `users`, `projects.user_id`, `user_sessions` (login sessions, NOT terminal sessions; empty). Prod had no agent-session tables before this work.
- Isolation rule: PostgreSQL has no row-level security here (that was a Supabase feature), so **every query must filter on `user_id`**, centralized in one repository. The Go port must keep that property and its tests.

## Request 4 — "install deepseek-offload on this project" (make a plan first)
- Status: **DONE** (plan approved, installed, doctor all `ok`, smoke job `job-20260930-230009-7474` returned a correct report).
- Installed from `~/__projects__/deepseek-offload` into `~/__projects__/4genthub` with `install.sh --with-mcp-config --permission allow`. Added untracked `4genthub/.agents/` (symlinks to the package) and a `deepseek` entry in git-ignored `.mcp.json` and `.agents/mcp_config.json`; `sequential-thinking` and `agenthub_http` entries unchanged. Rewrote `~/.dsh/profiles/acp/cordis.patch.yml` (model pin `deepseek-flash`).
- Owner chose `--permission allow` (jobs may write files; git commits refused by `git-guard.cjs`, pushes to `origin` redirected to a sandbox). Delegated jobs get no MCP tools. Uninstall: `~/__projects__/deepseek-offload/install.sh --uninstall --project ~/__projects__/4genthub`.
- Use it for read-heavy Go-migration chunks: `node .agents/skills/deepseek-offload/scripts/dsh-offload.mjs start "<task>" --label x` then `status`/`result <jobId>`. Review any file changes a job makes.
- Plan file: `~/.claude/plans/compressed-conjuring-aurora.md`.

## Request 5 — "yes" (start step 1: session streaming backend) — **DONE in Python, must be ported to Go**
Python reference (all uncommitted in `agenthub_main`):
- `src/fastmcp/task_management/infrastructure/database/models.py`: ORM `AgentSession` (table `agent_sessions`) and `AgentSessionEvent` (`agent_session_events`). Tables are created by `Base.metadata.create_all` at startup; no migration file was written. **Not yet verified against real PostgreSQL.**
- `src/fastmcp/session_stream/repository.py`, `hub.py`, `__init__.py`
- `src/fastmcp/server/routes/session_stream_routes.py`, registered in `server/http_server.py` right after the `/ws/realtime` router.
- Tests: `src/tests/session_stream/session_stream_test.py` (9 pass). They need `--noconftest` because the repo's autouse fixture requires a local Postgres DB `agenthub_test`: `cd agenthub_main/src && PYTHONPATH=. ../venv/bin/python -m pytest tests/session_stream --noconftest -c ../pytest.ini`. I also pip-installed the declared dep `prometheus-client` into `agenthub_main/venv`.

Behavior the Go port MUST reproduce exactly (the map rows above already list these files as todo):
- **Session id** = UUIDv5 with namespace `6f1c2d3e-4a5b-4c6d-8e7f-0a1b2c3d4e5f` over the string `"{user_id}:{connector_id}:{session_key}"`. Python and Go must produce identical ids, or existing rows will not match.
- **Tables**: `agent_sessions(id varchar(36) pk, user_id varchar(64) idx, connector_id varchar(64), session_key varchar(255), name varchar(255), project varchar(255) null, status varchar(20) default 'active', last_seq int default 0, created_at, last_seen; unique(user_id, connector_id, session_key))`; `agent_session_events(id int pk autoinc, session_id fk→agent_sessions.id ON DELETE CASCADE, user_id varchar(64), seq int, type varchar(32), payload json, ts; unique(session_id, seq); index(user_id, session_id, seq))`. Timestamps are naive UTC. Naming warning: the existing domain entity `task_management/domain/entities/agent_session.py` (coordination sessions, no DB table) is a different concept; use a distinct Go name (e.g. `StreamedSession`) for the ORM model.
- **Limits**: ≤200 events per batch, payload >64K chars replaced by `{"truncated": true}`, websocket message >1 MiB rejected with an `error` frame, `type` truncated to 32 chars, `name`/`project` to 255. `seq` is assigned by the server (`last_seq += 1` per event), never taken from the client. Page limit for event listing is clamped to 1000.
- **`WS /ws/connector`**: token from `?token=` or `Authorization: Bearer`; validated with the unified token validator (Keycloak / API token / MCP token); requires scope `sessions:write`. Close codes: `4001` auth required, `4003` missing scope, `4004` not found. Client frames: `hello{connector_id}` (must match `^[A-Za-z0-9._:-]{1,64}$`) → `ready`; `session{session_key,name,project}` → `session_ack{session_key,session_id,last_seq}`; `events{session_key,events[]}` → `events_ack{session_id,last_seq}` (session_key must have been registered on this connection); otherwise `error{error}`. On disconnect, all of that connector's sessions get `status='offline'`.
- **`WS /ws/sessions/{id}`** (browser): token `?token=` (Keycloak JWT); ownership checked; missing and not-yours return the same close `4004` (no id probing). Replays events with `seq > after_seq` (query param, default 0) in pages of 500, then streams live events from the hub. The hub subscription is created BEFORE the replay, and live events with `seq <= last` are skipped. The handler must also watch the socket for client close (an earlier version leaked the subscription; there is a test for it).
- **REST**: `GET /api/v2/sessions` (own sessions, newest `last_seen` first), `GET /api/v2/sessions/{id}/events?after_seq=&limit=` (404 if not owned).
- **Hub**: in-process fan-out, bounded queue (1000) per viewer, slow viewer dropped. This is **single-process only**; with more than one backend replica (CapRover) events will not cross replicas. Decision needed from the owner: Postgres `LISTEN/NOTIFY` or Redis if scaling out.
- Go-side parity test to add: same inputs through Python and Go repositories must yield the same session ids and event rows.

## Request 6 — remaining steps of the same feature (not started; build in Go after migration, or in Python first if the owner wants it sooner)
1. **Connector CLI** (runs in the user's WSL): discover sessions with `tmux list-sessions` and map to JSONL files; tail `~/.claude/projects/*/*.jsonl`; redact secrets locally; open `wss://<host>/ws/connector` with an API token that has scope `sessions:write` (the existing token endpoint `server/routes/token_router.py` already accepts arbitrary scopes; default is `["read"]`); reconnect with backoff; package for `pipx`/`go install`. Send the frames listed above.
2. **Dashboard page** in `agenthub-frontend` (React/Vite, port 3800): list own sessions (`/api/v2/sessions`), live view over `/ws/sessions/{id}`, optional xterm.js tab for raw terminal. Auth is Keycloak.
3. **Web → tmux input**, opt-in per session, behind a separate scope `sessions:input`. This is remote command execution on the user's machine: read-only by default, per-user tokens, each connector bound to one account, only accept commands for sessions that same connector registered, rate-limit, audit log. Use the tmux delivery recipe from Request 1.
4. **Teams/sharing** (later): `team_id` and roles (owner/viewer); start single-owner.
5. **Security follow-ups**: store only token hashes (already the case in `api_tokens`), support revocation, rate-limit per connection.
6. **Deploy notes**: the WebSocket must pass through CapRover's nginx (`Upgrade`/`Connection` headers, long `proxy_read_timeout`); confirm "Websocket Support" is enabled for `4genthub-backend`. Verify `create_all` creates the two new tables on the prod Postgres before relying on them. Do not deploy without the owner's go-ahead.

## Request 7 — "you need write to agenthub_go/MIGRATION.md all demande i ask you, other session will do it when finish migration"
- Status: **DONE** — this section. It was appended to the end of the file (the file is being edited concurrently by the migration session, so nothing above was rewritten). If you fold items into the slice plan, leave this section's request text intact so the owner's asks stay traceable.

## Request 8 — "i want 4genthub have same system topology like openrig" (recorded 2026-10-01)
- Owner decisions (asked and answered): scope = **full runtime** (model + API + dashboard graph + a daemon that launches each member in tmux, bindings, `up`/`down`/`send`/`restore`); language = **Go only in `agenthub_go`, wait for the migration** (no Python version).
- Status: **plan only, nothing built.** Checklist group **F** above holds the work items. Full plan with the OpenRig reference analysis: `~/.claude/plans/compressed-conjuring-aurora.md` (may be overwritten by later plans; this section and group F are the durable record).
- What "OpenRig topology" means (verified in `~/__projects__/openrig`): a `rig` contains `pod`s (namespaced), pods contain `member`s/nodes (a seat = agent + runtime + cwd + model) and `edge`s. Spec format RigSpec 0.2. Only `delegates_to` (source launches before target) and `spawned_by` (parent launches before child) affect launch order (topological sort, a cycle fails); `can_observe`, `collaborates_with`, `escalates_to` are descriptive. A daemon persists rigs/pods/nodes/edges/bindings/sessions in SQLite, launches each node in a tmux pane through a runtime adapter (`claude-code`, `codex`, `terminal`), and exposes `rig up/down/ps/send/capture/whoami/restore/snapshot`.
- What 4genthub has today: agents are configuration rows (`agent_templates` 32, `user_agent_instances` 58, `agents` 3), not running processes; the data model is projects → branches → tasks → subtasks; there is no rig/pod/member/edge, no binding and no daemon.
- Target design: hub-and-spoke. The 4genthub server (multi-user, Keycloak) stores topology with `user_id` on every row. A local `rigd` on each user's machine launches seats and dials OUT to the server, so the server never reaches into a user's machine. `rigd` is the same component as the session-stream connector (Requests 2, 3, 5), so **F4 supersedes C1, D2 and D4: fold them, do not build both.**
- Risks: the TypeScript runtime is large (instantiator ~2.5k lines, restore ~1.9k, tmux ~1k), so F4/F5 are the expensive parts while F1–F3 already deliver value alone; remote launch is remote command execution (see F8); WSL2 is untested upstream (see F9).

## Environment facts useful to the next session
- Working trees: `~/__projects__/4genthub` (branch checked on 2026-09-30: clean of my commits — I made none). Pre-existing unrelated changes not made by me: `.claude`, `CLAUDE.md`, `package-lock.json` (deleted), `testground/`.
- `4genthub/.mcp.json` is git-ignored and contains a plaintext bearer token for `agenthub_http` — treat as a secret, never paste it.
- `agenthub-frontend/` is REQUIRED (owner confirmed 2026-10-01): it is the live dashboard and the home of C3 and F7. It was found deleted from the working tree (384 tracked files, cause unknown, not done by the session that wrote this section) and was restored with `git checkout -- agenthub-frontend`. Do not delete or move it during the Go migration. `node_modules` was lost and needs `pnpm install` there; untracked/ignored files such as a local `.env` could not be recovered.
- The OpenRig repo (`~/__projects__/openrig`) is only a reference for the tmux delivery design; nothing was changed there.

- Repositories/interfaces convention: repository methods take `ctx context.Context` and return `(value, error)`; dict returns are `map[string]any`; optional args are pointers. Interface Python properties become accessor methods; `**kwargs` become `map[string]any`; `@contextmanager` becomes `(value, closeFn, err)`.
- Import-cycle hooks: `domain.UserIDNormalizer` (constants.go) must be registered by infrastructure `uuid_column_type`; `entities.AgentNameResolver` by application `use_cases/agent_mappings`. `entities.GitBranchCreator` is a consumer-side interface because Python duck-types methods missing from the ABC.
- `ProjectNameValidator`/`GitBranchNameValidator`: Python compares `entity.id == exclude_*_id` (value object vs str), which is always False, so the "exclude for updates" branch never triggers; the Go port keeps that behavior (parameter accepted, unused). `GitBranchNameValidator` calls `find_all_by_project`, absent from the GitBranchRepository ABC, so Go declares the consumer-side `services.BranchLister`. `value_objects.PyStrip` mirrors `str.strip()` (includes \x1c-\x1f); older code using `strings.TrimSpace` differs only for those characters.
- `EventDispatcher`: handlers are identified by `EventHandler.Name` (Go funcs are not comparable); handler panics are swallowed like Python's `except Exception`.
- `protocols/cascade_data_provider` owns `EntityType` in Go (Python imports it from `cascade_calculator`, which only imports the protocol for typing; Go cannot cycle packages). `services.EntityType` is a type alias with re-exported consts. `BranchStatisticsService` keeps Python's duck typing via `StatusedTask`/`IdentifiedBranch`: `task.status == "done"` is False for a `TaskStatus` value object, so only plain-string statuses are counted.
- `value_objects/py_compat.go` (helper, no Python counterpart): `PyFloat`, `PyEqual` (Python `==` on JSON-like values, 1 == 1.0). `TemplateDomainService`: `not request.template_id` is never true in Python (object truthiness) so it is not reported; Python's AttributeError on a None enum is returned as a `*TypeError` with the same text; non-string `task_type`/`category` are treated as absent; dict iteration order from maps is sorted-key order.
- PYTHON DEFECT (owner decision): `CascadeDeletionService._dispatch_{task,branch,project}_deleted_event` always raise inside a swallowed `try` (`TaskDeletedEvent.create`/`ProjectDeletedEvent.create` do not exist; `branch_lifecycle_events.py` fails at import with "non-default argument 'project_id' follows default argument 'branch_id'"). No deletion event is ever dispatched, so branch statistics never update on deletion, yet `stats["events_dispatched"]` still lists the names. The Go port reproduces this (no dispatch, names still listed). Fixing it changes behavior and needs an owner decision applied to Python and Go together.
- `CascadeDeletionService` uses consumer-side repository interfaces (`CascadeTaskRepository`, ...) because it calls methods missing from the domain repository ABCs; GitBranch/Project have no `context_id`, so branch/project context deletion is dead code in both languages.
- `TaskProgressService`: `Decimal.quantize(ROUND_HALF_UP)` is reproduced exactly with `big.Rat` (`percentOneDecimal`); weighted sums use explicit `float64()` conversions so amd64/arm64 give identical (non-fused) results. The `except Exception` branch of `calculate_task_progress` has no Go trigger (nothing in the calculation raises), so `createErrorProgressResponse` is only kept for parity. Expected values in `task_progress_service_test.go` come from running Python.

### Checker verdict ledger (dev-check, read-only QA)
- 1c-iii-c-6 (agent_management value objects/entities): PASS.
- 1c-iii-c-7 (auth/domain): findings F1 (b64url decode parity with CPython `a2b_base64`, 6013-case corpus), F2a (`b64:false` header rejected), F3 (bcrypt stored-hash strictness: `$2[abxy]$`, cost 04-31, salt last char in `. O e u`, 60 bytes), F4 (4300-digit int cap in `PyParseInt`) FIXED. Accepted deviations: F2b-d `NaN`/`Infinity` in the JWT header, BOM/UTF-16 JSON bodies, lone surrogates in token JSON.
- 1c-iii-c-8 (agent_management/domain + `LoadYAML`): F1 (recursive alias crash) and F2 (alias bomb) FIXED via node memoization plus an in-progress cycle guard (cyclic aliases are an error, not a self-referential structure); F3 plain `=` is a ConstructorError as a value but a string as a mapping key (checked against PyYAML 6.0.3); F6 mapping keys use Python identity (equal keys collapse, first spelling/position kept, last value wins). Accepted deviations: F4 `%YAML 1.2` directive, F5 strictness gaps vs PyYAML, F7 explicit tags (`!!binary`, `!!int 0o17`, ...).
- 1c-iii-c-4 (task_validation_service, hint_rules, content_analyzer, PySum): PASS with findings, all addressed: (1) `PyLower` now implements Final_Sigma and the full lowercase mapping, checked for every code point against Python (27 code points differ, all Unicode 16.0 additions, pinned in `pylower_test.go`); (2) `agent_session.CalculateHealthScore` now uses `PySum`; (3) regexp2 is ~13x slower than Python on pathological inputs (`'A'*20000+'1'`, `'uses '+'x'*30000`; both quadratic, seconds in Python): content analysis must not be exposed to unbounded input, so the application layer must cap the analysed text length (note for slice 3); (4) `go mod tidy` run (regexp2 is a direct dependency).
- 1c-iii-c-3 (PyRepr fix, PyLower move, FindGitBranch, task_priority_service, orchestrator, task_state_transition_service): PASS. Low finding fixed: `TransitionSubtaskRepository.FindByParentTaskID` now takes `*TaskId` (nil id passed through like Python `None`); test added.
- Slice 1c-iii-b-2 (task, subtask, git_branch, project entities): PASS. Differentials vs real Python: 22-step Task scenario, 4,400 `Project.check_deadline_risk` cases, 6 `GitBranch.remove_task` cases. Finding A (Task events carried `task_id` as a plain string; Python's `asdict` nests the TaskId as `{"value": id}`) FIXED: `TaskCreatedEvent.TaskID`/`TaskUpdatedEvent.TaskID` are `any`, `Task.idRef()` passes the TaskId, `events.asdictValue` serializes it (test `TestTaskEventsSerializeTaskIDLikeAsdict`). No other entity emits events in Python; later application-layer events must use the same pattern for TaskId-typed fields. Finding B (error text echoing caller-supplied numbers: Python `got 150`, Go `got 150.0`) ACCEPTED (typed-input deviation).
  - Not checked by dev-check: `get_assignees_info` YAML metadata, `subtask.go`/`git_branch.go` beyond `remove_task`, project scenarios other than deadline risk, ordered_map beyond those scenarios, `Task.to_dict` with a real agent_mappings resolver.
- Slice 1c-iii-b-3 (repositories, interfaces, constants): PASS on signature parity (51 classes / 273 methods: 0 missing, 0 extra; 167 methods differ only by the leading ctx), 13/13 enums identical, constants messages identical. Follow-ups DONE: `constants.go` uses `PyStrip`; `AssertUserIDNormalizerRegistered()` added; `NewTemplateListFilter()` carries the Python defaults (limit 50, offset 0).
  - TODO (server slice): `server main` must call `domain.AssertUserIDNormalizerRegistered()` at startup and a test must import the real infrastructure `uuid_column_type` package.
  - Not checked by dev-check: behavior of `context.go`, `agent_session.go`, `global_context_schema.go` (+ testdata), `Project.CreateGitBranchAsync`, `BaseRepository[T]` semantics, parameter and return TYPE parity of interface methods (names and parameter counts only).
- Slice 1c-iii-c-1 (domain services batch 1): PASS, no findings. Differentials vs real Python: 80,600 Decimal ROUND_HALF_UP cases (0 diffs), PyStrip over all 1,112,064 scalar values (identical 29-member whitespace set), 528 pagination combos, 48+48 name-format strings, plus Python verification of the two duck-typing claims and the cascade-deletion dispatch defect. Consequence noted by dev-check: in Python an update that keeps its own project/branch name is rejected as a duplicate (exclude id never matches); Go reproduces this.
  - Not independently checked by dev-check: cascade_calculator + protocols/cascade_data_provider, context_derivation_service, task_completion_service, template_domain_service, event_dispatcher, branch_statistics_service beyond the status quirk, task_progress_service beyond the percentage, `PyFloat`/`PyEqual`.
- NEW DEPENDENCY: `golang.org/x/text v0.28.0` (module cache; go directive now `go 1.23.0` + `toolchain go1.23.5`) for `unicodedata.normalize("NFKC")` in `utilities/id_validator.go`. Python 3.14 ships Unicode 16, x/text v0.28 an older table version; only exotic newly-assigned code points can differ. `IDValidator` output verified against 138 real-Python cases (NFKC, control/format/private-use stripping, html.escape entities, redaction, truncation).
- PYTHON DEFECT (owner decision): `DependencyValidationService._check_circular_dependencies` raises ValueError inside its DFS whenever it reaches an already-visited task that is not on the current path (any diamond: A->B->D and A->C->D), the outer `except` swallows it, and the whole check reports NO cycle - even if a real cycle exists elsewhere in the graph. Go reproduces this (`errNotOnPath`). Also, the service has no `find_by_id_across_contexts` probe result beyond `hasattr`; Go uses the optional `AcrossContextsFinder` interface.
- PYTHON DEFECT (owner decision): `TaskPriorityService` treats `Task.due_date` (a `str`) as a datetime. `_calculate_urgency_score` therefore always returns 30.0 (`.tzinfo` raises in a swallowed try); `_get_priority_factors` raises `'str' object has no attribute 'isoformat'` for any task with a due date, which makes `order_tasks_by_priority` return its error fallback (`priority_score` 0.0 + `error`) for ALL tasks in the batch, and `get_next_task_recommendation` then returns None (KeyError 'task_id'). Go reproduces all three. Verified against 7-task Python scenario (scores, ordering, factors, recommendation, dependency adjustment) in `testdata/task_priority_cases.json`.
- Slice 1c-iii-c-2 (id_validator, dependency_validation_service): PASS with one requested change. Differentials vs real Python: 10,610 adversarial sanitizer inputs (0 diffs), 3,000 random dependency graphs (0 diffs; diamond defect quantified: Python misses a reachable cycle in 63 of 1,338 cases = 4.7%), 6,003 parameter-mapping combos (only diffs traced to PyRepr, now fixed). Requested change DONE: `value_objects.PyRepr` now escapes non-printable characters like Python (`\xhh`, `\uhhhh`, `\Uhhhhhhhh`); `pyrepr_test.go` sweeps all 1,112,064 code points against ranges generated from Python 3.14 (`testdata/pyrepr_cases.json`).
  - KNOWN UNICODE-VERSION SKEW (accepted): Go 1.23 tables are Unicode 15.0, Python 3.14 is Unicode 16.0. (a) `PyRepr` escapes 5,812 code points that Python 3.14 prints (the test pins this number); (b) NFKC in `id_validator` differs for 36 code points U+1CCD6..U+1CCF9. Python's own result depends on its interpreter's Unicode DB, so exact parity is undefined for newer code points.
  - Not checked by dev-check: `validate_task_context`/`suggest_fix_for_confusion` beyond the exercised paths, `find_dependency_across_states` with an across-contexts repository, `constants.go` with a registered normalizer, `template_repository` beyond the default constructor.

- Cross-cutting rule (dev-check W1): ports of Python `except Exception` loops over handlers/workers must recover panics and convert them to errors (Go panic would kill the server).

### Open decisions from dev-check (task_repository differential)
- T1: Python `create_task` never persists assignees (UnboundLocalError on `uuid`, swallowed). Go persists them. Kept as an intentional fix pending the user's decision (mirror the bug or keep the fix).
- T2: Python inserts the task row before validating the entity (invalid description/priority leaves a stray row). Go leaves nothing behind. Kept pending the user's decision.
- T3: `get_overdue_tasks` fails on PostgreSQL in both; only the error type differs.
- Use-case domain events: Python never dispatches task_created/updated/deleted/status_changed from the use cases (`X.create` does not exist, or `dispatch_domain_event` is called with one argument). Go matches; the stray add_subtask/complete_subtask dispatches were removed.
- P1: Python `create_project` stores an explicit `project_id` verbatim (any string); Go validates through `value_objects.NewProjectId` (non-canonical ids rejected, whitespace trimmed) because `Project.ID` is a typed value object. The MCP path always passes None. Kept as an intentional deviation pending the user's decision.

## Composition work (Go-only, no Python counterpart file)
Python glues everything with FastAPI/Starlette/FastMCP. The Go ports so far are logic-only (route handler functions, controllers' ManageX methods, facades) so the following must be written before the server runs:
1. `fastmcp/server/httpapp/` — net/http adapter: JSON/FastAPI-style `{"detail": ...}` errors, auth dependency (Keycloak/Supabase/local) -> `authdomain.User`, form/JSON body binding, one `register*` file per Python router (~125 endpoints, paths from the Python decorators), CORS, `/health`.
2. `fastmcp/server/httpapp/wiring.go` — build SessionManager, repositories, factories (set all package-level seams: `TaskFacadeBuilder`, `ProjectFacadeBuilder`, `GitBranchFacadeBuilder`, `AgentApplicationFacadeConstructor`, `UnifiedContextRepositoryBuilder`, `TokenFacadeRepositoryBackend`, `hooks.TaskHooks`/`ProjectHooks` via `WithHooks`, `ParentTaskProgressUpdater`, controller auth hooks).
3. MCP: hand-rolled stateless JSON-RPC over POST `/mcp` (initialize, tools/list, tools/call, ping, notifications; json_response=True semantics). The go-sdk is not used (v1.6.0 needs Go 1.25). Tool registry = `tools/tool.py` equivalent + per-controller `RegisterTools` (manage_task, manage_subtask, manage_context, manage_project, manage_git_branch, manage_agent, call_agent, connection tools, auth tools) driven by `config/tool_registry.go`.
4. `fastmcp/server/mcp_entry_point.go` + `cmd/agenthub/main.go` — startup sequence of `mcp_entry_point.py` (env, migrations, StatisticsInitializer, event handlers, schema validation, auth mode, server, transport/host/port env `FASTMCP_*`).
5. WebSocket (`/ws/realtime`, `/ws/connector`, `/ws/sessions`, `/ws/{user_id}`) over `fastmcp/websocket` + routes.
6. `auth/interface/auth_endpoints.py` (login etc.).

- N1 (dev-check, task_repository batch_update_status): Python's get_db_session yields the held session and never commits, so the UPDATE is not persisted; Go commits. Intentional deviation (persisting is the sane behaviour); user may veto.
- L1 fixed: optional assignee/label inserts in ORMTaskRepository.CreateTask run in savepoints (Python per-step rollback).

### Composition status
- DONE (vertical slice 1, projects): `fastmcp/server/httpapp/{http,app,project_adapter}.go` + `cmd/agenthub/main.go`. Smoke against local PG with AUTH_ENABLED=false: `/health`, POST/GET/PUT/DELETE `/api/v2/projects`, `/{id}/health-check`, 403 without bearer, 404 on missing — all respond with the Python JSON shapes. Python's `dev@localhost` default email fails its own User validation (same in Go; set DEFAULT_USER_EMAIL).
- Open to check: PUT `/api/v2/projects/{id}` returns project id/name "None" (update response built from the use-case result; verify against Python).
- DONE (slice 2, branches): `httpapp/{branch_wiring,branch_routes}.go` (9 endpoints under /api/v2/branches; GitBranchService/facade wired, bulk-summary SQL via bindNamed). Unwired: facade notifier + agent facade (assign-agent returns 500 "Failed to assign agent"), branch context service. PUT/branch update returns an empty DTO (id "None") like projects: needs Python differential.
- DONE (this pass): task_application_facade.go now has every Python method (CreateTask/UpdateTask/GetTask/DeleteTask/CompleteTask/ListTasks/SearchTasks/GetNextTask/ListTasksSummary/ListSubtasksSummary/Add+RemoveDependency/helpers) over injected `TaskFacadeDeps`; row stays `todo` until dev-check audits it. Differential decisions: PUT project/branch now 500 like Python (branch body is JSON `{"detail":...}`, Python plain text); GET /projects/{id}, GET /branches/{id}, task-counts return real data (Python 404/500 from pydantic/unbound-method defects) = intentional deviation; 422 bodies use FastAPI list shape; delete_project git-branch repo + task counter wired; controllers' recover() now returns the failure response (named result).
- DONE (slice 3, tasks CRUD): `httpapp/{task_adapter,task_controller,task_routes}.go` — /api/v2/tasks POST/GET list/GET {id}/PUT/DELETE/POST {id}/complete/GET stats/summary. Smoke vs local PG: create/list/get/update/complete/delete work; stats returns 500 "Failed to get task statistics" because the Python facade has no get_task_statistics (AttributeError, preserved). Wired: SetupTimestampEvents (models.py import side effect), SetRepositoryProviderBackend, UnifiedContextRepositoryBuilder, request auth ctx on `authed`, facade user id normalised like create_task_facade. dev-check audit: task facade and request_context_middleware rows done (F2 slice bounds + M1-M3 fixed; F1/F3 verified equal to Python). Notifier is an empty WebSocketNotificationService (no broker until WebSocket routes exist); ProjectBranchLookup still a stub.
- DONE (slice 4, subtasks HTTP): `httpapp/{subtask_wiring,subtask_routes}.go` — /api/v2/subtasks POST/GET {id}/PUT/DELETE/GET task/{id}/POST {id}/complete via SubtaskAPIController (`WithSubtaskRepositories` injects the per-user repo; complete returns detail "'title'" exactly like Python's subtask_to_dto on {id,completed}). Hand-off note (TEAM_SPLIT): `fastmcp/server/httpapp/` + `cmd/agenthub` are the composition root written before the split; the Agy team owns `server/` from here on and may extend it (register routes in `App.Handler`, wire services in `NewApp`). Claude team stays in task_management.
- tasks-http audit follow-up: C2 fixed generally (py_json typed-nil OrderedAny -> null), C3 fixed (ORMTaskRepository.GetTask swallows query errors like Python's try/except -> DELETE non-uuid 404), C1 = ProjectBranchLookup now raises Python's AttributeError ('ProjectManagementService' has no get_git_branch_by_id) so a branch invisible to the user fails exactly like Python. OPEN for the server team (httpapp is theirs per TEAM_SPLIT): C4 query int 422 body should be the FastAPI list shape; C5 422 `input` should echo the request body.
- subtask-facade audit follow-up: S1 fixed (types.AttrObject = Python SubtaskObj; partial dicts take the entity branch at all subtask controller call sites), S2 fixed (facade builds AddSubtaskRequest via NewAddSubtaskRequest -> "Title cannot be empty"), S3 fixed (ORM TaskProgressStore + SubtaskApplicationFacade.WithProgressStore wires TaskProgressService into add/update/remove subtask; rounding is Python banker's round). OPEN for server team: S4 (query int 422 body shape).
- (old note) task_application_facade.go was only a partial port (CountTasks/GetDependencies subset; row still `todo`, 2691 py lines). Port it fully (create/update/get/delete/complete/list/search/next/summary/dependencies/helpers) before wiring the task, subtask and MCP routes.
- TODO: remaining routers (task summaries /api/*, subtask, context, agent, token, connection, broadcast, analytics, alerts, metrics), MCP `/mcp`, auth endpoints, WebSocket, mcp_entry_point startup, notifier wiring (project hooks Notifier nil), git branch repo/task counter for delete_project.

### Note (dev-owner, 2026-10-02): MCP wiring
`ddd_compliant_mcp_tools` / `consolidated_mcp_server` are implemented (rows stay `todo` until dev-check audit). Go-only glue lives in `interface/ddd_compliant_mcp_tools_wiring.go` (adapters between controller-side interfaces and ported handlers/factories, plus `wireAuthHooks` and `wireWorkflowGuidance`). Request-context hooks take `ctx` (Python reads contextvars). Still unwired: task controller `workflowGuidance` (never assigned in Python's constructor path either), task crud `GetUnifiedContextFacade`/AI-service hooks, `CoerceParameterTypes` hooks. FastMCP registration is via the `MCPServer` interface (server-context owns the implementation).

### Note (dev-owner, 2026-10-02): mcp-wiring schema decisions
- W1-W4: `ToolDefinitions()[i].Parameters` is the full inputSchema (`toolInputSchema`, table `tool_input_schemas.go` derived from the Python signatures), deep-compared against `interface/testdata/tools_golden.json` (generated from real FastMCP) in `TestToolDefinitionsMatchPythonToolRegistry`.
- W5: `RegisterTools` calls `SchemaMCPServer.ToolWithSchema(name, desc, schema, fn)` when the server implements it (falls back to `Tool`). The server context (Agy) owns the implementation and must publish the schema in tools/list.
- W6: intentional deviation: Python's `get_db_config()` calls `sys.exit(1)` when the DB is unreachable; Go continues without the context controller (`DatabaseAvailable=false`).
- context_templates ImportTemplate: JSON syntax-error text families other than "Expecting value", and raw-typed version/author/tags/required, are accepted deviations (typed Go fields).

### Note (dev-owner, 2026-10-02): triage names intentionally not ported
- `project_mcp_controller`: `ContextPropagationMixin` / `_run_async_with_context` / `run_in_new_loop` / `_manage_project_async` are thread/event-loop plumbing (no Go meaning; `ManageProject` is the sync entry). `_handle_create/_get/_list/_update_project` and `_include_project_context` are Python "backward compatibility for tests" helpers (CLAUDE.md: no compatibility code); the logic lives in `handlers/crud_handler.go`.
- `enhanced_dependency_controller`: `analyze_dependencies_ai` / `manage_dependency_model` / `optimize_project_dependencies` are FastMCP closures inside `register_tools` and nothing in Python instantiates the controller; Go ports the `Handle*` bodies and the description getters.
- `utils/error_handler`: `handle_operation_error` decorator (async/sync wrappers) has no Go equivalent (decorators on methods); `UserFriendlyErrorHandler`/`ErrorCode` are ported.
- `utils/flexible_schema_generator`: `FlexibleToolDecorator.enhance_tool_schema` mutates a FastMCP tool instance; Go has no tool instance (schemas are built in `toolInputSchema`).
- `auth_helper/extractors/request_state_extractor`: reads the request ContextVar; Go reads `ctx` via `auth/middleware.GetCurrentUserID`.
