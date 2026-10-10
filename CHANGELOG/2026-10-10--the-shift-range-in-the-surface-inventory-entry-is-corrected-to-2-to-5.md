## The shift range in the surface-inventory entry is corrected to 2 to 5

### Corrected

- `CHANGELOG/2026-10-10--the-surface-inventory-re-anchors-its-thirty-route-citations-after-f0fba29d.md`
  said the thirty route citations "shifted by 2 to 6". Measured from `scripts/CITATION-AUDIT.py`'s own
  `--write` output: **29 rows at Δ2 and exactly 1 at Δ5** (`broadcast/notify` `211 -> 206`). The range
  is **2 to 5**.
- The sentence carrying that figure began "Cause measured, not relayed" **while the range itself was
  relayed** from the routing row's description rather than measured, with the measurement sitting
  unread in the tool output already in hand — so the defect is the provenance claim, not the width of
  the range. Found by the reviewer at the gate on `f9b373e9`
  (`4genthub-min/GATE-f9b373e9-surface-inventory-reanchor-2026-10-10.md`, MINOR).
- `f9b373e9`'s commit message carries the same figure and is **not** rewritten: no branch pointer
  moves in this room, so this entry is the forward correction.
- **Nothing else changed:** no route citation, no line anchor and no Go source is touched. The audit is
  rc 0 / `stale 0` before and after, the inventory's md5 is unchanged, and the canonical suite is
  `82 passed, 0 failed`.
