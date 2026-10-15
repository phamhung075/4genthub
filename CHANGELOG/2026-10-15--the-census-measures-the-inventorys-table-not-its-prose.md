# The census measures the inventory's table, not its prose

**What this adds.** One open item on the board (T14, beside T13): a checker that reads table rows
reports `stale 0` on a document whose prose citations are wrong, so the prose class has no
instrument at all.

**The measurement.** At `acf916c8`, `CI= python3 scripts/CITATION-AUDIT.py` → `rows 148, stale 0,
unresolved 0, exit 0` on `ai_docs/api-integration/surface-inventory.md` — the same green the bullet
above records. In that file, at the same time, four live prose citations were stale until
`b114d0ae` repointed them (`:84` `:170`/`:175`/`:176`/`:180` → `:179`/`:184`/`:185`/`:189; `:86`
`:139`/`:140` → `:148`/`:149`; `:441` `:71` → `:99`; `:563` `:79-83` → `:88-92`), and one dated note
named a revision that does not carry the set it cites (`48d0cfdd`). `--write` repairs only what it
measures: at `7360008e` it rewrote **0** while `:84` was stale.

**The rule the item's check has to apply.** The document states it at `:735`: a citation asserts what
the code says now and can be wrong; a quotation asserts what a document said then and must be kept.
No pattern separates them — a quotation carries the same `file:line` shape — so the separation has to
be made by reading what the sentence attributes, which is why extending the instrument is a change of
its own and not a widened regex.

**Not in this change.** No instrument, no code: `NEXT-GEN2.md` plus this entry.
