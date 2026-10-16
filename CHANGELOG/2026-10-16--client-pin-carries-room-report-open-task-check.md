# Client pin carries the `room report` open-task check

### Added

- `agenthub_client` pin moves to `3b77960`: `4genteam room report` lists hub tasks that have commits with a
  `Task: <id>` trailer but are still open, counts commits without the trailer, and prints a
  `tasks closed after commit` target. Pairs with the seat commit-msg hook `task-trailer-guard` (`dda9a267`).

### Testing

- Client: `go vet ./... && go test ./...` clean. Not run against a live hub.
