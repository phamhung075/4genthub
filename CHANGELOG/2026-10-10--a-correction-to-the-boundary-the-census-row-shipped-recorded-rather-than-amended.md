## A correction to the boundary the census row shipped, recorded rather than amended

### Fixed
- `scripts/S3-REDERIVE.py` (docstring) and the entry `2026-10-10--the-census-runs-where-the-suite-runs-and-its-third-instrument-is-tracked.md` both said **"§2, §4 and §3.5 are covered by NOTHING"**. That is false for §3.5, and the row's own description had already measured the correction before the file was written: `scripts/COUNTS-AUDIT.py` reads the document's headline figures BY ANCHORED PATTERN (11 keys, 10 of them stating a figure in the document), and §3.5's seat-table, registered-total and `ProductionTables` counts are among them. The docstring now says so, and says what the real uncovered surface is.
- **The real uncovered surface, measured at this commit rather than quoted:** the two instruments resolve TABLE ROWS and nothing else — §1's route rows (144) by `scripts/CITATION-AUDIT.py`, §3.1–§3.4's rows (46 rows, 66 anchors) by `scripts/S3-REDERIVE.py` — while **149** `file:line`-shaped tokens sit on NON-table lines: §2.1 29, §2.3 17, Appendix A 16, §1's own prose 15 + 11 + 4, §3.3 14, §4 10, §3.6 7, §5 7, §2.5 5, §2.4 4, §2.2 3, §3.4 2, the remainder spread thinner. Pattern, stated because a count without its pattern is not re-derivable: `re.finditer(r"(?:[\w./-]+\.(go|py|sql|ts|tsx|md|json)|)\:(\d+)")` over `ai_docs/api-integration/surface-inventory.md`. **Some of the 149 are QUOTATIONS**, which the inventory's own rule forbids "repairing" (a citation asserts what the code says now; a quotation asserts what a document said then), so they stay DECLARED-UNCOVERED rather than half-covered by a weaker check under a stronger name.

### Why a second commit and not an amend
- The wrong sentence was committed in `22293e7b`. The room's rule is that a commit which already exists is not rewritten — an amend can orphan a hash another seat has read — so the correction is a following commit, and the earlier entry's body is left as the record of what it said. This is the same treatment `1b183904`'s body got when it was found overstated.

### Testing
- `python3 scripts/S3-REDERIVE.py` -> `rev=HEAD base=a7990665 rows=46 anchors=66`, `FRESH 66`, rc 0 (the docstring changed; the parsing did not).
- `python3 -m pytest --noconftest -p no:cacheprovider scripts/tests -q` -> 99 passed, with all three instruments and their `--self-test`s green under it.
