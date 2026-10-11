## The dormant task-event family is deleted: its purpose was already served by the live path

- **What went:** `infrastructure/events/event_handler_initializer.go` (the whole registration path, including
  `InitializeEventHandlers`, `SetEventHandlerInitializerEventBus` and the three `register*Handlers`),
  `application/event_handlers/task_event_handlers.go` (the handlers, their statistics maps, and
  `TaskEventNotificationService` with its nine `Notify*` declarations) and the handler's test file.
- **THREE INDEPENDENT MEASURES AGREE, which is what makes this the house style rather than a hunch.**
  (1) **Unreachable from any binary:** `InitializeEventHandlers` and `SetEventHandlerInitializerEventBus` had no
  callers anywhere and no reference from `cmd/` or `fastmcp/` outside their own file. (2) **No reachable
  consumer:** the statistics' only reader is `/stats/summary`, whose facade adapter **panics** — *"'the Python
  facade has no get_task_statistics'"* — a faithful port of an absence. (3) **The purpose is already served:**
  the durable half of the Python divergence **is** the missed-notification store plus its reconnect replay
  (`websocket_routes.go:598` writes it, `ws_mount.go:179` reads it, the store is wired at startup), and the real
  `infrastructure/notification_service.go` is uncalled besides its own `NotifyBatch`.
- **THE CARVE-OUT, UNTOUCHED:** the `missed_notifications` store, its repository and the replay are **live**, and
  they are precisely what makes the deleted nine methods redundant.
- **A false positive worth recording, because the deletion depended on it:** the first grep for references
  matched `event_bus.go`, which turned out to reference `events.EventQueue` — the **live** async queue — and not
  the initializer at all. The package stays; only the registration file went. Deleting on that grep's word would
  have removed a live type, and reading the line first is what kept it.
- **The blast radius was then checked by the compiler rather than by the grep:** `go build ./...` exit 0,
  `go vet ./...` exit 0, `go test -count=1 ./...` → **143 packages ok, 0 FAIL**.
- Files deleted: the three above. Nothing else changed.
