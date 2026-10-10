## A completed task now broadcasts, because the interface it was handed did not declare the capability

- **The defect, and its shape:** `CompleteTaskHooks` (`complete_task.go:34-39`) declared only
  `SyncTaskStatus` and `SyncTaskMetadata`, while the object the wiring passes to `CompleteTaskUseCase`
  implements `NotifyTaskEvent` as well — `create_task.go:172` and `update_task.go:160` call it on that same
  object. **The compiler proved the call could not exist at the completion site**, so a completion reached the
  client only through React Query's own refetch: no frame and no animation, while created and updated tasks
  animated. It is the evening's recurring class in one line: **an interface that does not declare a capability
  its object has.**
- **The fix is one interface method and one call.** `CompleteTaskHooks` now **embeds `TaskEventHooks`** — the
  interface already exists in the same package, so no signature is restated and the capability keeps one
  source — and the completion path calls `NotifyTaskEvent` where the completion succeeds, mirroring
  `update_task.go:160` literal-for-literal and branch-deref-for-branch-deref. No wiring change, no new
  dependency, no new type, no frontend change.
- **PLACEMENT, AND THE TEST CAUGHT IT: THE BROADCAST IS NOT GATED ON THE CONTEXT FACADE**, which is where the
  first attempt put it. A completion this process cannot build a facade for still HAPPENED — the test's own
  case — so the call was moved out, while the two context syncs stay inside because they synchronise the
  context they follow.
- **THE VOCABULARY, DECIDED RATHER THAN DISCOVERED:** a completion emits **`completed`** — the terminal
  transition the client animates distinctly — and every other status move emits **`updated`**, matching
  `update_task.go`'s literal. Both are already in the client's allowlist, so the frontend mapping needs no
  change; a distinct animation per transition would be a vocabulary addition and the owner's decision.
- **NOT BUNDLED, DELIBERATELY:** `InitializeEventHandlers` and `SetEventHandlerInitializerEventBus` still have
  no callers, so the event-bus handlers are written but never subscribed. That is a real and separate defect
  whose semantics need examining — in the Python, `notification_service` and `WebSocketNotificationService`
  were two different things — and it rides on no other change.
- Files: `agenthub_go/fastmcp/task_management/application/use_cases/complete_task.go` and its test.
