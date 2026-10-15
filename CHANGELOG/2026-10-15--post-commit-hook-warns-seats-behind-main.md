# The post-commit notice warns a seat whose tree is behind main

### Changed
- `scripts/git-hooks/notify-seats`: main is the only reference. For each running seat the hook reads the seat's tmux pane path (`TMUX_TMPDIR=~/.config/4genthub/tmux`), counts `git rev-list HEAD..main` there, and when it is above zero appends a WARNING naming the path, the seat's HEAD and the number of commits it is behind, telling it to merge or rebase onto main before it continues. A seat whose path is unreadable or not a git tree gets the plain notice.

### Testing
- Stub `4genteam` and `tmux` pointing a seat at `rooms/4genthub-min/wt/architect`: the send carried "3 commit(s) behind main". Not yet run against the live room (it is down).
