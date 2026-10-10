## The MCP task read path: filters the caller sent were discarded, and a failed call handed out a handle

- **TWO DEFECTS, BOTH MEASURED BEFORE BEING FIXED, BOTH ON THE READ PATH.**
- **A FAILED CALL RETURNED A HANDLE TO NOTHING.** `MergeMetadata`
  (`application/services/response_optimizer.go`) promoted `operation_id` into `meta.id` regardless of
  outcome, so a refused `create` - and a refused `add_insight` - came back with `persisted:false` AND an
  `id`. A caller that recorded it, which is the natural thing since a successful create is identified by
  its id, then got "Task not found" on every later update. Measured by context-dev, who proved the first
  one was phantom by searching for its title and finding no such row. The id is now exposed only when
  `data_persisted` is true; `persisted`, `operation` and `timestamp` still report.
- **THE LIST IGNORED ITS ASSIGNEE FILTER.** `ListTasksMinimal` takes an `assigneeID` and its SQL filters on
  it, but the facade passed a literal `nil` in that position on every call - and `IsPerformanceMode()` is
  unconditionally true, so the minimal path was the only path taken. A list filtered by `@go-dev` returned
  50 rows including other seats' work, and a filter matching nothing still returned rows. The facade now
  forwards the assignee, and declines the minimal path when the request cannot be expressed there (labels,
  or more than one assignee) rather than over-returning.
- **THE SEARCH DID NOT IGNORE ITS QUERY - IT DISCARDED ITS FILTERS.** A made-up phrase returns nothing,
  measured, so the query always worked. What `SearchHandler.SearchTasks` did was open with
  `_ = status; _ = priority; _ = assignee; _ = tag`, so a filtered search answered with rows the caller had
  excluded. Those filters are now plumbed through the request DTO, the use case and the repository in the
  same clause shape `FindByCriteria` uses. Recorded because the ticket read "the search ignores its query",
  which measurement did not support.
- **THE TESTS PROVE NEGATIVES, NOT JUST POSITIVES:** a refused call exposes no field that reads as a handle
  while a persisted call still exposes one, an unfiltered list invents no assignee, and a forwarded
  assignee reaches the SQL boundary.
- **NOT IN THIS COMMIT, NAMED RATHER THAN LEFT SILENT:** `offset` is still discarded in `SearchTasks`.
  And the status-change broadcast path no longer exists to be dead - the `TaskEventHandlers` /
  `TaskEventNotificationService` family was DELETED in `e1970dc5` as dormant (zero references remain in
  `agenthub_go`), so anything still describing it as "constructed with three nil dependencies" is
  describing the tree before that deletion.
