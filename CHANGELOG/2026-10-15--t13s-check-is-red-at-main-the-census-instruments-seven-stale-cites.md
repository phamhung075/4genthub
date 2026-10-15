# T13's check is red at main, and the instrument's seven stale cites are why

T13's own acceptance clause is "`pytest scripts/tests -q` and `go test ./...` both pass cleanly". The
board carried the clause and not the reading. Measured today: the suite is red, and the reason is not
a repoint — it is the citation instrument finding seven stale `app.go` citations on the landed doc set.

The lead's row `qitem-20261015165507-86c503dfe4ba` reported the same two failures; this entry is the
measurement re-run at the source, because a board reading is worth only what its own run is worth.

## Measured

- `python3 -m pytest scripts/tests -q -p no:cacheprovider` → **2 failed, 89 passed in 18.8 s**, run in
  `wt/architect` at `3fc0225a` — whose only commits touch `NEXT-GEN2.md` and `CHANGELOG/`, so this is
  main `80e51824`'s reading for `scripts/`.
- **Failure 1**, `test_the_census_instrument_is_clean_at_head_and_says_how_much_it_read`: it runs
  `CITATION-AUDIT.py` against a clean export of HEAD and asserts exit 0. The instrument answers
  `rows 148  stale 7  unresolved 0`, all seven in `fastmcp/server/httpapp/app.go`, every one stale by
  the same **+9**: `:142 → :151`, `:170 → :179`, `:183 → :192`, `:191 → :200`, `:199 → :208`,
  `:220 → :229`, `:228 → :237`.
- **Failure 2**, `test_the_census_instrument_can_fail`: it asserts the instrument's `--self-test`
  passes, and that self-test's own docstring states its contract — *"Its own `--self-test` perturbs one
  item in a COPY and requires that exact item named."* The run answers *"perturbed the citation on
  line 76 by +7 → 7 stale reported against a baseline of 7, the perturbed row named (FAIL)"*.
- **The two are one finding**: row 76 is one of the seven already stale (`:142 → :151`), so perturbing
  it by +7 leaves it stale and the count cannot move. While the baseline is dirty, the self-test cannot
  demonstrate failure — the instrument's own falsifiability check is defeated by the drift it exists to
  report.

## Why it matters

The seven `app.go` re-points are the unlanded `4genthub-min/census-repoint` (`7360008e`), held at the
reviewer's gate for a different paragraph in the same document. So this clause cannot go green on a
repoint alone, and `go test ./...` passing says nothing about it — the reading belongs beside the
clause, not in a row that the next reader has to find.

## Not in this change

No code, no test, no instrument, no repoint: `NEXT-GEN2.md` plus this entry. The instrument's
behaviour and the document's citations are left exactly as measured.
