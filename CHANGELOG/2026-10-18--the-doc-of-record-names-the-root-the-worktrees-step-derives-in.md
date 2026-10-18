## The doc of record names the root the worktrees step derives in

### Recorded

- `ai_docs/core-architecture/seat-worktrees.md` - the worktrees step reads the room's own repository from
  the definition's seat `cwds` (`SeatProjectRoot`, client `4fd6c67`), not the working directory's toplevel;
  a room whose readable seat directories name two repositories is printed and the working directory's
  answer stands. `doctor`'s worktrees row reads the same root (`68c7ae9`).

### Why it is written

The doc described `Start` and `Check` path by path and never said which repository they were judged in,
and the omission was measured: the same `up --room-only --allow-peak` refused 6 of 6 derived paths when run
from a seat's client worktree, naming the client repository, while the same command from the project root
printed six kept lines and exit 0.
