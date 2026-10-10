## The census boundary's number and its split are both repaired, and the count is re-derivable again

### Fixed
- `scripts/S3-REDERIVE.py` (docstring). The bullet shipped in `b101d407` said "the two instruments resolve TABLE ROWS and nothing else" and then listed **149** tokens as if they all sat on NON-table lines. The total was right and the breakdown was not: the list mixed the two surfaces, summing to 144 while the prose said 149. Both are now stated split, as TOKENS, with the pattern beside them:
  - **What the two instruments resolve are table rows, and only their own**: §1's route rows (144 anchors, `scripts/CITATION-AUDIT.py`) and §3.1–§3.4's rows (46 rows, 66 anchors, this instrument). **Not every table row is resolved** — 11 further table ROWS carry **17** anchors neither reads, because `CITATION-AUDIT.py`'s row shape needs a METHOD in the first cell and §2.3's published-tools table puts a tool NAME there (10 rows, lines 402–411, 15 anchors, some rows carrying two or three `:NN` refs) plus §4's Gone list (1 row, line 568, 2 anchors).
  - **On non-table lines: 132 anchors over 51 lines** — §2.1 29, Appendix A 16, §1's own prose 15 + 11 + 4, §3.3 14, §4 8, §3.6 7, §5 7, §2.5 5, §2.4 4, §2.2 3, §2.3 2, §3.4 2, and 5 spread thinner (§1.16, §1.17, §1.21, §3., §3.5 — one each).
  - **Total outside both: 149 = 132 + 17**, re-derived with the pattern `re.finditer(r"(?:[\w./-]+\.(go|py|sql|ts|tsx|md|json)|)\:(\d+)")` over `ai_docs/api-integration/surface-inventory.md`, counted as tokens.

### The conflation question, answered either way
- **No, I did not reuse `CITATION-AUDIT.py`'s row count of 144.** The coincidence has an arithmetic explanation, and it is worth recording because it is the same mistake one level down: 132 (non-table tokens) + the reviewer's 12 (table tokens counted by ROW for §2.3 and by TOKEN for §4) = **144**, which was then reported as the non-table figure and had the 12 added a second time to reach 156. Under one consistent unit (tokens over the whole file) the number is 132 + 17 = **149**, and the per-row inventory above lets a reader count it.
- **The reviewer's 156 does not reproduce here**, and I am not shipping a number the shipped pattern cannot yield — that is the exact defect this row exists to close. The instrument, the pattern, the split and the per-line inventory are all in the docstring; a reader can settle it in one command, and if a different parse is right I will adopt that number instead.

### Testing
- `python3 scripts/S3-REDERIVE.py` -> `rev=HEAD base=a7990665 rows=46 anchors=66`, `FRESH 66`, rc 0 (docstring only; the parse is untouched).
- `python3 -m pytest --noconftest -p no:cacheprovider scripts/tests -q` -> 101 passed.
