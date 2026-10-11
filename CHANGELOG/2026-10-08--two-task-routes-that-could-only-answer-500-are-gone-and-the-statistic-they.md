## Two task routes that could only answer 500 are gone, and the statistic they promised is left to O8

### Removed
- `GET /api/v2/tasks/stats/summary` and `GET /api/tasks/{task_id}`, by owner ruling on the architect's decision note (`ai_docs/architecture-design/decision-task-stats-endpoint.md`, option C). Both were deliberate Python parity: `handlerTaskFacade.GetTaskStatistics` and `.GetTaskWithRelations` panicked carrying the Python `AttributeError` text and the handlers turned the panic into a 500. Neither had a caller, and the parity reason expired with the archived Python server, so a caller now gets 404 by absence — the only option in which a route that is listed can also answer.
- The whole chain under both, because a deletion that leaves a caller is a build error rather than a cleanup: the two registrations (`task_routes.go`, `routes_mount.go`), `routes.GetUserTaskStats` and `routes.GetFullTask` with their controller interface methods, the two `httpapp` adapters, `TaskAPIController.GetTaskStatistics` and `.GetFullTask`, `TaskSearchHandler.GetTaskStatistics` and `.GetFullTask`, the two `TaskHandlerFacade` methods, the test fakes, and the four types that then became unused — `types.StatisticsResponse` (with `NewStatisticsResponse` and its `ModelDump`), `routes.UserTaskStatsResult`, `routes.FullTaskResult` and `thStatsFailure`, each confirmed unused by the compiler rather than by eye.
- `ai_docs/api-integration/surface-inventory.md`: the two rows are struck, the neighbouring task-route line references are re-resolved by reading the file's own registrations rather than by arithmetic, and the dated registration count carries the change — **`125 -> 123` in `httpapp`, `145 -> 143` total**, exactly the two removed registrations, under the pattern and scope the paragraph states.

### Not done, on purpose
- O8's statistic is NOT built here. It would have been a second source of task counts before O8 builds the first from the O1 ledger, which is the "counts disagree" failure O8 exists to prevent.
- The two `apiReference.ts` entries in `agenthub-frontend` are a separate row (fe-dev), so this change touches one repo.

### Measured
- The decision note's acceptance instrument, `command grep -rn "GetTaskWithRelations\|GetTaskStatistics\|stats/summary" . --include=*.go` from `agenthub_go`: **21 matches in 10 files at HEAD `1a1ae32c`, 0 after.**
- `GET /api/tasks/{task_id}` is the only half observable as 404. The v2 path sits under the `GET /api/v2/tasks/` prefix route, which matches the whole subtree and answers 403 before auth, so it returns 403 whether or not the dedicated handler exists; that half is evidenced by the grep and the build.
