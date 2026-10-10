## Unreleased — `progress_history` and `progress_count` leave the task and subtask payloads

### Changed
- `agenthub_go/fastmcp/types/entities.go`, `converters.go`: `TaskDTO` and `SubtaskDTO` no longer carry `ProgressHistory` or `ProgressCount`, so `ModelDump` omits both keys.
- `agenthub_go/fastmcp/task_management/application/dtos/task/task_response.go`, `services/websocket_payload_builder.go`, `minimal_response_serializer.go`, `websocket_notification_service.go`, `facades/subtask_application_facade.go`, `domain/entities/task.go`, `subtask.go`: the same two keys are no longer built, and the task `ToDict` no longer emits them. `details` is still built from the progress history text.
- `agenthub_go/fastmcp/middleware/response_validator_middleware.go`, `websocket_message_logger.go`: `progress_count` is no longer a required field of the task schema or of a task websocket event (10 required fields instead of 11).

### Fixed
- `agenthub_go/fastmcp/task_management/application/services/websocket_payload_builder_test.go` and the middleware tests still set or asserted the removed fields: `go vet ./fastmcp/...` failed on `ProgressCount`, and the middleware tests failed on the old field counts. The fixtures and counts now match the code.

### Testing
- `cd agenthub_go && go vet ./fastmcp/...` and `go test ./fastmcp/...` pass.
