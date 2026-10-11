## The task UPDATE animation: the frontend chain is sound and the status-change path broadcasts nothing

- **Owner report, 2026-10-07:** CREATE fires once (confirmed on screen), but UPDATE of a task does not
  animate and neither does a status change. **DIAGNOSED TO ONE CAUSE WITH TWO FACES, and the frontend half
  has no defect in it.**
- **SOUND, PROVEN BY REPRODUCTION RATHER THAN BY READING:** `src/tests/services/taskUpdateAnimation.test.ts`
  unmocks the factory, registers a real `<tr>`, and asserts the element's CLASS - the animation LANDS. The
  service subscribes (`init` -> `client.on('update')`, `WebSocketAnimationService.ts:32`); the row registers
  (`TaskRowRefactored.tsx:78`/`:97` wire the refs the register effect reads); and the ordinary update route
  calls the LIVE hooks (`task_wiring.go:130` wires `NewUpdateTaskUseCase(...).WithHooks(taskHooks)`, and
  `update_task.go:160` emits `NotifyTaskEvent(ctx, "updated", ...)`), which the service maps. **An ordinary
  task update therefore DOES animate.**
- **BROKEN, AND IT IS A BACKEND WIRING DEFECT:** the status-change path is DEAD. Status changes route through
  `TaskEventHandlers`, and `event_handler_initializer.go:69` constructs them as
  `NewTaskEventHandlers(nil, nil, nil)` - **all three dependencies nil** - so every
  `h.NotificationService.NotifyTaskStarted / NotifyTaskCompleted / NotifyTaskBlocked / NotifyTaskReady /
  NotifyTaskNeedsReview` call goes nowhere. **No type anywhere in the repo implements
  `TaskEventNotificationService`; the only implementation that exists is the TEST's stub.** A status change
  therefore broadcasts NOTHING, which is why it neither animates nor updates the cache - the data seen
  changing came from React Query's own refetch, not from a frame.
- **SUPERSEDED (added 2026-10-08), AND THE DIAGNOSIS ABOVE IS LEFT INTACT ON PURPOSE — it was right about the tree it
  was written against.** The family in the bullet above was DELETED in `e1970dc5` — see **"The dormant task-event family
  is deleted"** below — so `NewTaskEventHandlers(nil, nil, nil)` describes a tree that no longer exists:
  `grep -rn --include=*.go NewTaskEventHandlers agenthub_go` returns nothing, and both files are gone from every package
  directory. **AND MEASURED SINCE, which is why the alarm above does not survive that deletion:** a status change still
  reaches the live path this entry's FIRST bullet proved sound — `update_task.go:66-73` handles `request.Status` through
  `UpdateStatus` and `:160` emits `NotifyTaskEvent(ctx, "updated", ...)` — so the deleted family was a SECOND, parallel
  path rather than the only one, and the client-side half of this owner report was fixed on the mutation
  (`updateMutation.onMutate` resolved the branch id from a cache a list page never fills; `e42fdbdc`).
- **The two observations are therefore one bug**, and it belongs to the backend: either that path must
  broadcast (the handlers are already registered to the bus at `:73`), or a status change must route through
  the update use case that has live hooks. The backend's own allowed action vocabulary is
  `created/updated/deleted/completed/assigned/unassigned`, so **`started`/`blocked` are not in it** and
  inventing client-side mappings for them would be guessing rather than fixing.
- **A method note, since it cost time twice tonight:** the service's suite mocking `animate` is what made a
  passing test prove less than it appeared to, and a read that ELIDES a function body made me claim `init`
  "subscribes to nothing" when it does - the third partial read of the night, retracted on the task record.
