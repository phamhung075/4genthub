## 2026-10-15 - the behind-note reads the seat's own tree

### Fixed
- `scripts/git-hooks/notify-seats`: the post-commit notice's behind-note computed its "is this a git tree" guard, its short sha and its `HEAD..main` count in the COMMITTING worktree's repository. A post-commit hook in a linked worktree receives `GIT_DIR=<main>/.git/worktrees/<wt>`, and `git -C <path>` does NOT override an exported `GIT_DIR`, so all five seats in the room were told the committer's revision and distance: at 17:49Z every seat's pane path was main's own tip `acf916c8` while the note read `/home/daihu/__projects__/4genthub at ea72e6ad ... 3 commit(s) behind main` - one value for the whole room. The same leak defeated the guard, so a path that is not a repository was warned about instead of getting the plain notice. The three reads, and the sha that `printf`'s `$( )` inherited the same way, now run under `env -u GIT_DIR -u GIT_WORK_TREE -u GIT_COMMON_DIR`.
- The hook's own first two lines (`sha`, `subject`) deliberately keep the inherited environment: they describe the commit that fired the hook, which is the one thing the hook is entitled to read from it.

### Known, deliberate
- The note reads the seat's PANE cwd, which is the room's launch directory. In a room whose seats edit in worktrees of their own (`wt/<rig>/<name>`), the note is therefore silent unless a seat is launched INTO its worktree. Naming the seat's worktree needs a seat -> worktree map, and one seat holds more than one worktree (this seat holds three), so the map is not guessed here.

### Testing
- `scripts/tests/test_notify_seats_behind_note.py`: four cases over the real script, with `tmux` (the pane path) and `4genteam` (one running seat, the message captured) stubbed and `GIT_DIR` exported as a post-commit hook receives it. A seat one commit behind ITS OWN `main` is warned with its own revision; the committer's own tree and a path that is not a repository stay silent while the plain notice is still sent; and the leak itself is pinned, so the case cannot pass by reading the wrong repository.
