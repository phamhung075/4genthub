## The §7.9 resume row: the insert moves to the top of its cell, and the stale "NO" is marked

Follow-up to `16d4b1f4` on the lead's fix row (`qitem-20261011150940-ff98137358e1c207`) and the architect's
15:02:57Z note on `qitem-20261011150003-25fa6f0e8bbfbb55`. Docs only, no test, no gate. Line 462 still the only
line that changes.

### Changed

- `ai_docs/core-architecture/rigd-boundaries.md`, **line 462 only**:
  - the ruling insert moves from the END of the third cell to its **TOP**, immediately after the `| ` that opens
    the cell: the block opens *"the two clauses below are settled and are not to be re-opened"*, and those clauses
    are the held-resume behaviour and the compaction-not-held exemption that follow it, so at the end of the cell
    "below" referred to nothing. `**Defect against this rule.** … not a wake.` now follows the block.
  - the middle cell gains the architect's mark **inside** it, after `at peak.**` and before the closing `|`, with
    every existing byte of the cell kept: `**SUPERSEDED 2026-10-11 (architect): the gate is IN - …**`, copied
    verbatim from the architect's note (the lead's 15:01:19Z "do not touch that line" is withdrawn). Line 457's
    header is `| Wake | Gated today? | Ruling |`, so that column is where a reader asks whether the wake is gated
    **today**; the pre-`834dbaa` state is kept because it is the reason `834dbaa` exists.

### Verified

- `git diff -U0` on the file: line 462 and nothing else; the row still parses as exactly three cells (four `|`
  separators, no pipe inside the cell text).
- On line 462: `RULED 14` occurs once, `SUPERSEDED` once, `**Defect against this rule.**` once, and the insert sits
  before the defect sentence.
- The inserted block still compares EQUAL to the ruling's §7.9 block with whitespace normalised.
