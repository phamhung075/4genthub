## The seat watch follows live seats: a removed seat leaves the grid and a Claude seat gets a pane mirror

- **WHAT CHANGED.** `scripts/openrig_watch_tools.py`: `rig_seats` now lists the live tmux sessions of the rig instead of the omp state directories, which outlive a removed seat (the grid kept a pane for `go-dev2` after `rig remove`). `seat_command` gives an omp seat the tool-call feed and any other runtime (the Claude Code `architect`) a read-only `tmux capture-pane` mirror, because only omp writes the session logs the feed reads.
- **VALIDATED.** `test_seats_are_the_live_tmux_sessions_and_a_non_omp_seat_gets_a_pane_mirror`; 20 tests pass; the reopened grid shows 10 panes including `architect` and no `go-dev2`.
