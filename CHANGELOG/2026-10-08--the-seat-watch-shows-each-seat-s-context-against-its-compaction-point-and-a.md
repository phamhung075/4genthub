## The seat watch shows each seat's context against its compaction point, and a Claude Code seat in the same style

- **WHAT CHANGED.** `scripts/openrig_watch_tools.py`: the top row of every feed pane is pinned (the feed scrolls below it) and reads `== seat ==  <bar> <percent> <used>/<limit> to compact`, updated each second from the latest usage in the seat log. A Claude Code seat (the `architect`) is read from its `--session-id` log in `~/.claude/projects` and shown with the same tool-call, result, thinking and say lines as an omp seat, replacing the plain `tmux capture-pane` mirror.
- **LIMITS.** omp seats compact at 850k (the last compaction was at 852312 tokens). The Claude Code limit is an assumed 200k (`COMPACT_AT["claude"]`): the log does not carry the real one, so the architect bar may be wrong until it is checked.
- **VALIDATED.** 23 tests pass; the reopened grid shows the bar on the lead (52 percent), fe-dev (41 percent) and architect panes.
