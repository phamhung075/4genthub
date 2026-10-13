## NEXT-GEN2's contradicted claims now carry their measurement and the tree they were read on

### Fixed

- `NEXT-GEN2.md` §1 item 5 (the `rig` shim's drop-in claim) records that it is **measured false** for `rig send`
  — all four argv shapes the client itself uses fail, exit 2 or 3, `4genteam send: RIG, SEAT and MESSAGE are
  required` — and for `rig whoami --json` (exit 3, a prose sentence where `seatcheck` expects JSON), while
  `rig queue` does answer. Holds until the eleven `rig`-exec fallbacks are gone.
- `NEXT-GEN2.md` R1 (headless PTY runner) carries the measurement that the file the item names,
  `rust/agenthub-runtime/src/pty/mod.rs`, is tmux shell-outs: 26 `tmux` references and zero
  `portable_pty`/`nix::` uses, those two appearing crate-wide only in `frame.rs` and `runner/mod.rs`. Tree
  `78e7a58`.
- `NEXT-GEN2.md` R1 (socketpair) is tree-labelled: true at `78e7a58` (`rust/agenthub-runtime/src/runner/mod.rs`,
  3 hits), absent at `f193f34` (0 hits).
- `NEXT-GEN2.md` R2 (token counting "using `tiktoken-rs`") records that the crate requires no tokenizer:
  `rust/agenthub-runtime/Cargo.toml` lists tokio, portable-pty, nix, serde_yaml, regex and clap. Tree
  `f193f34`.
- `NEXT-GEN2.md` R6 (room directory layout) is scoped to what is observable: the only room under
  `~/.config/4genthub/rooms/`, `test-alpha`, holds `spec.json` alone — no `seats/`, `logs/` or `queue.sqlite` —
  and `/run/user/$UID/agenthub.sock` does not exist.
- `NEXT-GEN2.md` P4 names the websocket path the tree actually has
  (`fastmcp/infrastructure/websocket`, `fastmcp/websocket`, `fastmcp/server/routes/websocket_routes.go`)
  instead of `fastmcp/server/websocket/`, which does not exist; the named commit `fcc8a2fc` resolves.

### Notes

- Documentation only; no code path changed.
- Deliberately left alone: R2's rolling-window thresholds (routed to a mission row rather than the doc), O1c's
  `progress_history` check (routed for a dead-code-vs-partial-drop determination), T13 (still open), and every
  performance, behavioural, HTTP, database and frontend-runtime claim, none of which this seat verified.
- Instrument note carried in the same pass: O1c's own check, run verbatim, also counts `agenthub_go/.gocache`
  build bytes (762 lines) unless it is filtered with `--include=*.go`.
