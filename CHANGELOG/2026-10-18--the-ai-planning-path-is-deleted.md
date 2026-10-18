# The server-side AI planning path is deleted

On the owner's directive 3: the architecture does not use a server-side model runtime, so the dead
path goes rather than staying unwired.

## Removed

- The `agenthub_go/fastmcp` AI-planning package (whole tree: handler, use case, service, request
  types, and their 5 test files plus the `atptest` helper).
- The five `ai_*` actions of `manage_task` - `ai_plan`, `ai_create`, `ai_enhance`, `ai_analyze`,
  `ai_suggest_agents` - from dispatch and from the published schema: the alts in
  `mcp_controllers/task_mcp_controller/manage_task_description.go` are gone, so are the two
  `AIHandler` cases that dispatched `ai_create`/`ai_enhance`, and `GetAiHandler`/`NewAiHandler` and
  the `AIHandler` type in `mcp_controllers/task_mcp_controller/factory.go` went with them.
- The eleven parameters that existed only for those actions, from BOTH schema sources
  (`manage_task_description.go`'s `buildParameters` and `tool_input_schemas.go`'s table):
  `requirements`, `auto_create_tasks`, `enable_ai_breakdown`, `enable_smart_assignment`,
  `enable_auto_subtasks`, `ai_requirements`, `planning_context`, `analyze_complexity`,
  `suggest_optimizations`, `identify_risks`, `available_agents`. `CreateAIEnhancedTaskPlan` and its request types in the AI task-creation use case were its other
  reachable surface.
- The AI-planning and AI-task-creation interfaces from the dependency-injection construction, and
  the `AITaskIntegrationService` seam sentence: a call to a retired action is now refused as an
  invalid/unknown action, which is the truth.

## Tests

- New `TestManageTaskPublishesAndDispatchesNoAIActions` (`fastmcp/server/httpapp/ai_actions_absent_test.go`)
  asserts BOTH halves: `tools/list` publishes a `manage_task` whose description names none of the five,
  and a call to `ai_plan` is refused without the AI-seam sentence (and names the action it refused).
  Red before the deletion, green after.
- The deleted packages' own tests went with them; `tools_golden.json` lost exactly the eleven retired
  parameters and the two changed description strings, and both tool-definition tests are green.

## Verification

- `gofmt -l fastmcp/task_management/interface`: empty; `go build ./...`: ok.
- `go test ./fastmcp/task_management/... ./fastmcp/server/httpapp/...`: pass.
- `ai_docs/core-architecture/agenthub-system-architecture.md` records the deletion (the "open decision"
  sentence and the option-C row), `agenthub_go/NEXT_GEN.md` O9(c) records it as partly delivered (the
  `ai_*` task COLUMNS are a separate lane), and `agenthub_go/TEAM_SPLIT.md` drops the context.
