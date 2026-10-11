## Seats may pass 200k tokens, never 400k, and a supervisor compacts them

### Added
- `scripts/openrig_compact_supervisor.py`: a host-level loop (log `~/.openrig/logs/compact-supervisor.log`). When a seat passes 200k it tells the seat once that the limit is reached and that it should finish its job and then run `rig send <own session> /compact --raw`. If the seat stays quiet for 180s the supervisor sends `/compact`; at 400k it sends it at once. `--raw` is required: without it `rig send` wraps the text in a From/To envelope and the seat reads `/compact` as a message (the first 8 sends were not witnessed for that reason; with `--raw`, fe-dev, go-dev and feedback-dev each gained a `compaction` record). A compaction is logged WITNESSED only when a new `compaction` record appears or the context drops below 60%.

### Changed
- `scripts/openrig_watch_tools.py`: one `COMPACT_LIMIT = 200_000` for every seat (it was 850k for omp seats, an assumed 200k for Claude Code) plus `HARD_LIMIT = 400_000`. The pinned bar turns red with ` LIMIT REACHED ` past 200k. The omp harness still compacts at about 850k on its own, as a backstop. The Claude Code limit remains an assumption.
