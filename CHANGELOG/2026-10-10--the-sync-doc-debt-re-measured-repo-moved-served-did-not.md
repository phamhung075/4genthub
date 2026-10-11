## The sync doc's cloud-vs-repo debt re-measured: the repo half moved, the served half did not

The writer's dated debt, owed once the serves moved and ordered by the lead at 20:30Z as the next thing to take. File: `ai_docs/operations/syncing-seats-with-the-cloud.md`, the "cloud's copy of a room's module text can lag the repo" bullet.

### Changed
- That bullet gains a **dated re-measurement (2026-10-10 20:35Z)** and a **method note**, wrapped to the file's own ~100 columns.

### What it now records, measured rather than carried
- **The TypeScript-baseline hunk is fixed in the repo.** The four `scripts/team/4genthub` sites name the command and carry no count (`8edb60a1`, `d0a18574`, `b60cc986`, `e1720a0b`), and `scripts/team/4genthub/team.json:9` names **1.0.2** (`88424aa4`) instead of 1.0.1 — so the next publish cannot reuse the armed version, and no other room's `pinned_version` moved.
- **A seat still reads the old text.** Production answers `0.0.34` from the same process as before the push; the rooms still serve their 1.0.0 body; `main` is at `c510c065`. So the **source** diverges from the served body in **two** hunks now, while **what a seat reads** still carries all **three**. That two-vs-three distinction is the point of the entry: it is the difference between a corrected repo and a corrected seat, which is the defect this whole cluster is about.
- The remaining chain is the two applies; the publish and re-resolve need the principal's token and a seat does not start them.

### Why the method note is in the document
The three census instruments read **the cited file and the document at a rev** (`git show`, never the worktree), so they can only judge a **commit**: an uncommitted correction is invisible and the audit reports the pre-edit state as stale. A seat that runs them to "pre-check" reads a false red. Recorded so the next reader does not repeat it, with the post-commit results that prove the instruments themselves are green: `S3-REDERIVE.py` `FRESH 66` exit 0 (no argument needed; it defaults to `rev=HEAD base=a7990665`), `COUNTS-AUDIT.py` exit 0, `CITATION-AUDIT.py` `rows 145  stale 0  unresolved 0`.
