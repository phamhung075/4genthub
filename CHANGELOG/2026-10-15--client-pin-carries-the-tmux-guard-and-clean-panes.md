# The client pin carries the tmux guard rule and panes without the tmux variables

### Changed
- `agenthub_client` pin `908c2fe` -> `6201870`: the seat guard blocks a bare tmux command that changes anything (`tmux-mutate`), and a seat's pane starts without `TMUX` and `TMUX_PANE`, so a bare `tmux` in a seat can no longer reach the room's own server (fe-dev's `tmux kill-server` ended all five seats on 2026-10-15).

### Testing
- `cargo test --offline` in the runtime: 104 passed. The room was restarted and every seat reseated on this build; the five omp processes carry no tmux variables and have the guard hook.
