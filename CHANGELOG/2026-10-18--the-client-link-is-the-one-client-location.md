## The client link is the one place a seat's client code lives

### Ruled

- `ai_docs/core-architecture/seat-worktrees.md` — a seat's client code lives only at
  `<roomDir>/wt/<seat>/agenthub_client`. The legacy `<roomDir>/wt/<seat>-client` is the migration's
  subject by PATH, not by the branch it holds: it is removed clean only (no `--force`), its branch
  survives, and the link then attaches to it. A kept seat path with a missing link gets one placed, on
  that legacy branch, else on the derived branch, else created at the gitlink. A legacy worktree holding
  uncommitted or untracked work is named and left, the run continues, and `Check` names the seat until
  the link exists. The two alternatives - a per-seat client location, and a `Check` that treats a
  missing link as a detail - are rejected in the same section.

### Measured

- go-dev's link holds `4genthub-min/go-dev` (52 ahead of client main) and works; the lead's and the
  integration worktree's links hold their own branches. The architect's and fe-dev's links were never
  placed: their client work sits in `architect-client` (`4genthub-min/architect-client`, 3 ahead) and
  `fe-dev-client` (`4genthub-min/fe-dev-edit-yield`, one untracked `captures/` directory), so `Check`
  called both seats Wrong. The migration's first form required the legacy worktree to hold exactly
  `<rig>/<seat>`; no lane branch ever matched it.
- The client skill `skills/share/seat-worktree/SKILL.md` still says `.claude` is detached inside a seat
  worktree; that sentence goes with the same implementation (client lane).

### Testing

Ruled, not implemented. The client implementation (go-dev) carries the cases the doc's table names: the
clean legacy migrated onto its lane branch, the dirty legacy named and kept with the run continuing, and
`Check` still reporting the seat until the link exists.
