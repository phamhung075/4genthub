## Changed

- `agenthub_client` pin moves `46b8b6e` -> `191fbc9` (2 commits).

### Fixed

- A text sent to a seat in the middle of its turn is HELD and published while it waits, then delivered
  when the turn ends, and it names its sender: the runner stamps `from`/`verb` onto the frame it hands
  over, and a refused text that cannot reach the agent - or whose sender the runtime cannot address -
  stays held instead of falling out of the queue (`b812c7b`). The 19 measured give-up lines are what
  this replaces.
- The daemon->runner stamping was asserted NOWHERE: deleting the two lines in `supervisor::deliver_text`
  that stamp it left the suite green (157/0). The frame test now asserts `frame["from"]`/`frame["verb"]`
  (RED with those two lines deleted: `left: Null, right: "agenthub--demo--principal"`), and the CLI's own
  origin is a pure function, `send_origin_from`, with both no-session cases pinned (`191fbc9`).
- Each client carrier names the verb that carried its frame - `SendOptions.Verb`,
  `Client.SendText`/`SendTextToSeat` and `DeliverToSession` - so the rig's `say`/`abort`, the `wake`,
  `messages` and the restore `brief` no longer every one of them claim to be `send` (`191fbc9`).

Validated: at `191fbc9`, `cargo test --offline` in `rust/agenthub-runtime` = 149 unit + 1 held_send + 15
seat_guard + 1 umask = 166 passed, 0 failed; `go vet ./...` rc 0; `gofmt -l .` clean; `go test -count=1
./...` = 32 packages ok, 0 FAIL. Gated by the reviewer at this tip, and the code is provably the gated
code: `git range-diff f5f102d..9f67088 46b8b6e..191fbc9` shows commit 1 `=` and commit 2 differing only
in the entry's base name and count (147 -> 149 unit, 164 -> 166), so its falsifications from `03f3544`
and `9f67088` carry. `cargo fmt --check` is dirty across this crate before this change too, so it is not
a signal here. The three `TEST-CHANGELOG.md` sections for this lane and two earlier ones ride in the same
commit, as their own parked notes asked.
