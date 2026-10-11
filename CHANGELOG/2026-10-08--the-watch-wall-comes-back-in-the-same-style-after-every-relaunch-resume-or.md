## The watch wall comes back in the same style after every relaunch, resume or runtime switch

### Changed
- `scripts/openrig_watch_tools.py`: `grid` and `lead_window` first close the rig's earlier `<rig> grid` and `<rig> lead` workspaces (`close_workspaces`), so running `watch` again replaces the wall instead of stacking a second one. The layout is fixed in the script (2 columns, `--back 40 --width 200 --lines 60 --detail`, lead window with its input pane), not in a saved herdr state, so it cannot drift.
- `~/.openrig/bin/rig-continue.sh` (outside the repo): `open_watch` runs `watch --rig <rig>` at the end of every restore; `RIG_CONTINUE_WATCH=0` skips it, `WATCH_TOOL` points at another copy. The `spawn-team` and `rig-runtime-switch` skills and `ai_docs/operations/watching-openrig-seats.md` (new section "Same style on every relaunch, resume or runtime switch") say the same.
- Earlier in the same area, now recorded: a compaction shows as a green `COMPACTED  <before> -> <after>` line and resets the meter to `tokensAfter`; every event line carries the seat's percent and tokens; the header reads `== <seat> | <model> ==  <bar>` (model from the seat's newest log, `claude-opus-5-5` for the architect, `deepseek-flash` for omp seats).

### Tested
- `test_a_relaunched_grid_replaces_the_old_one_and_keeps_the_same_layout`; the herdr fake now answers `workspace create`. 26 script tests pass (`--noconftest`).
