## The by-id task node carries acceptance_criteria and scope, so the closure gate can judge

### Fixed

- `agenthub_go/fastmcp/types/entities.go` - `TaskDTO` gains `AcceptanceCriteria` and `Scope`, and
  `ModelDump` writes `acceptance_criteria` and `scope` between `progress_percentage` and `subtasks`.
- `agenthub_go/fastmcp/types/converters.go` - `TaskToDTO` fills both, in the dict branch (the live
  path: `TaskResponse.ModelDump`, `application/dtos/task/task_response.go:214-215`, already set them)
  and in the entity branch, from the entity's own fields.

### Impact

`GET /api/v2/tasks/{id}` serves both fields, so `4genteam complete` reads the task's own criteria:
`internal/clientcomplete/complete.go:183` `fetchCriteria` GETs this node and `gate.go:38` treated an
empty slice as `uncertain` - every task, so no seat could close one through the gate and the command
exited 6 under `VALIDATION_GATE_ENFORCEMENT=true` (owner outcome 2's block).

A task with no criteria still serves `[]` for both, so its verdict stays `uncertain` and nothing else
changes shape.

### Testing

The route's own serializer, `value_objects.PyJSONDumpsCompact` (`server/httpapp/http.go:26-34`), was
run over the real path `TaskResponse.ToDict -> types.TaskToDTO -> ModelDump`, and it prints
`"acceptance_criteria":["the by-id node carries the criteria","and the scope"],"scope":["agenthub_go/fastmcp/types/**"]`,
and `[]`/`[]` for a task without them. `go build ./...` clean; `go test ./fastmcp/...` 0 failures;
`fastmcp/types` pins the mapping in both branches and the `ModelDump` key order.

### Not proven here

The node a seat's gate reads is the DEPLOYED one (`https://api.4genthub.com`), so the
closure-from-a-seat proof needs this build deployed: a local main cannot satisfy that acceptance
criterion, and saying it did would be a false end-to-end claim (hub task `8bd075eb`).
