# The queue verbs default the room, and a changelog entry is one per merged task

Two owner decisions from the 19:10Z rail row, both measured.

## What changed

- **`room queue` ROOM defaults to `$AGENTHUB_ROOM`.** Measured: 147 failed `queue show` calls in 24h, every
  one an id typed where the room belonged. `agenthub_client/internal/clientroom/queue.go` now fills ROOM from
  `$AGENTHUB_ROOM` when a sub-verb is exactly one positional short, so the form a seat actually types works:

  ```
  4genteam room queue show qitem-20261018191043-71c5b76963e8
  4genteam room queue list
  4genteam room queue close qitem-… --reason handed_off_to --target reviewer
  ```

  The COUNT decides which form was typed, not the shape of the words: one short of the verb's own positional
  list is ROOM-omitted, and an explicit room still wins (`queue list another-room` reads `another-room`).
  With `$AGENTHUB_ROOM` unset the verb refuses before any round trip, naming the variable
  (`ROOM was left out and $AGENTHUB_ROOM is unset, …`, exit 3) — it never asks the daemon about a room named
  after an id. `queueArgumentRefusal` therefore names the missing tail (`a QITEM_ID is required`), and the
  old "the ROOM comes first" branch is deleted: the form it was explaining now works. Usage lines read
  `[ROOM]` and the help paragraph says what fills the gap.
- **The changelog is one entry per merged task, not per commit.** Measured: 56 of 71 commits carried a
  changelog file, so a task's fix, its test and its correction restated one change under three titles.
  Rule updated in three places that teach it: `ai_docs/agent-system/repo-agent-rules.md` (Changelog duties,
  and the one-file-per-entry bullet), `AGENTS.md` §3.3 and `CHANGELOG/README.md`. A task's commits share the
  one entry, written with its first commit and finished before the merge; after the merge a change is a new
  task and gets its own file.

## Runs at this change

- Live, through the built client (`go build -o /tmp/4genteam-queue-default ./cmd/4genteam`, `$AGENTHUB_ROOM=4genthub-min`):
  `room queue show qitem-20261018191043-71c5b76963e8` printed the row (exit 0, pair `4genthub-min@…`);
  `env -u AGENTHUB_ROOM … queue show <qitem>` refused with the variable named (exit 3); `room queue list`
  printed the rail.
- `cd agenthub_client && go test -count=1 ./...` = exit 0; `go vet ./internal/clientroom/` clean.
- New cases: `TestRoomQueueShowDefaultsTheRoomFromTheSeatEnv` (the frame carries `"room":"room-a"`),
  `TestRoomQueueListDefaultsTheRoomAndAnExplicitRoomStillWins` (both forms, two frames in order),
  `TestRoomQueueWithNoRoomAndNoEnvRefusesNamingTheVariable` (exit 3, nothing rendered, no frame written) and
  `TestQueueArgumentRefusalNamesTheMissingTail`. The case that pinned the "ROOM comes first" message is
  deleted with the message it pinned.

Client branch `4genthub-min/test-argv-refusal`.
