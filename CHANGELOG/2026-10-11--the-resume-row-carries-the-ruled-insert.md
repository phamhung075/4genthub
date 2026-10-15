## The §7.9 resume row's third cell carries the ruling's verbatim insert

Docs only, no code, no test. Owed by the architect's ruling and routed as `qitem-20261011150003-25fa6f0e8bbfbb55`
(the architect declines to edit project files).

### Changed

- `ai_docs/core-architecture/rigd-boundaries.md`, **line 462 only** — the third cell of the `supervisor's
  post-compaction "resume" message` row: appended the block from `ARCH-RULING-peak-held-resume-2026-10-11.md`,
  section "The insert owed 'where the rule lives'", **character for character** — every word, em-dash, ellipsis and
  `> ` marker exactly as the architect wrote it, including the `14:5xZ` header form. The cell is a markdown table
  row, so the block's eleven lines are joined with single spaces: a line break cannot live inside a `|` cell without
  breaking the table. Nothing else in the cell was touched, and no other line of the file changed.

### Verified

- The appended text compares **EQUAL** to the ruling's own block (character comparison against the ruling file), and
  `git diff -U0 -- ai_docs/core-architecture/rigd-boundaries.md` reports line 462 and no other line.

### Not changed, and named for the record

- The same row's **second** cell still reads *"NO: zero gate references in `supervisor.go` (architect grep,
  2026-10-11). Today it can wake a DeepSeek seat at peak."* — stale since the gate went in at `supervisor.go:174`,
  and it now sits beside an insert that says the gate is in. It was not in this row's scope (`no other line of the
  file changed`), so it is untouched; the reviewer had already flagged it to the lead.
