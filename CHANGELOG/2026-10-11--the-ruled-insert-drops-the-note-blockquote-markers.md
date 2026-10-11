## The §7.9 insert drops the note's blockquote markers

Follow-up to `d7c3f361`, on the architect's insert-fidelity row (`qitem-20261011151332-215be9e6f77c2cb0`), ruled
**APPLY** by the lead at 15:14Z. Docs only, no test, no gate. Line 462 is still the only line that changes.

### Changed

- `ai_docs/core-architecture/rigd-boundaries.md`, **line 462 only**, third cell: the eleven literal `> ` tokens are
  stripped. They were the blockquote syntax of the architect's ruling note, not part of the ruling's text, and a bare
  `>` inside a GFM table cell is not blockquote syntax — it renders as a visible character (the row showed one
  mid-sentence: *with `allowPeak=false` > literal*). Every word, em-dash, ellipsis and the `14:5xZ` header form stay,
  the block still opens the cell, and the cell's own last words still end it. The single-space joining of the block's
  lines stands, as the lead ruled; the middle cell's SUPERSEDED mark is untouched.

### Verified

- Measured on this tree: `git diff -U0` reports **line 462 and no other line**; the row still parses as exactly three
  cells; `RULED 14` once; `SUPERSEDED` once, inside cell 2 and after `at peak.**`, character-equal to the architect's
  `FIX-ROW-rigd-boundaries-462-placement-and-middle-cell-2026-10-11.md:11`; `**Defect against this rule.**` once;
  **cell 3 contains no `>` at all** and, with whitespace collapsed, contains the ruling file's blockquote with its
  markers stripped and collapsed the same way; cell 1 is byte-identical at 91 characters.
