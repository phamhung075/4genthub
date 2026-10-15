# The client pin carries the agy seat guard, the watch fix and the seatcheck send removal

### Changed
- `agenthub_client` moves from `6201870` to `f9bd9dc` (pushed to the client's main). The seven commits:
  - `37172dc` the queue refusal names the room-first rule when a qitem id comes first;
  - `aceadb5` `watch`, `feed` and `ps` follow a seat that switched to agy (they read only omp's logs, so an agy seat looked silent);
  - `73c9cdc` the seat guard ignores heredoc bodies (a body line that began with `tmux` blocked an unrelated `queue close`);
  - `e836471`, `baecdcb`, `c2fb7f1` go-dev's removal of `seatcheck send`: `4genteam send` is the one send path, and it decides and audits (the server half is `9709c993`, already on main);
  - `f9bd9dc` an agy seat runs under the same guard and tool-call log as an omp seat (a `seat-guard` entry in agy's `~/.gemini/config/hooks.json`, installed when an agy seat starts, other entries untouched).

### Testing
- Client: `go vet ./...` and `go test ./...` are clean; `cargo test --offline` in `rust/agenthub-runtime` passes (105).
- Live: after a daemon restart and a reseat of all five seats, the agy reviewer's `git push --dry-run` was refused with rule `push` and logged, and its ordinary calls are logged as `ok` in `tool-calls.jsonl`.
