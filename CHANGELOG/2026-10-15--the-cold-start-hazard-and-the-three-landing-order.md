# The cold-start hazard and the three-landing order, on the board before the ffs

One clause the board was missing and the lead asked for by name: what the split costs while it is in
flight. No other content.

## Changed

- **The link bullet gains item (x): the hazard and the order.**
  - **The hazard:** the DEFINITION on main still declares `links: []` while the LIVE room declares 23,
    so **a cold start writes `spec.json` from the definition and drops the 23.** None is pending, the
    room is up, and if one becomes necessary first the 23 are re-merged from go-dev's `e3074353` rather
    than lost — the live `spec.json` and its `before-links` backup hold them meanwhile.
  - **The order, and why it is three landings rather than one:** (a) the board delta first (base = main,
    reviewed content the room is already reading), (b) the definition delta second, **re-based onto main
    so `e3074353` is not in its ancestry**, (c) the links last, after the owner ratifies the table.
    Landing the definition on its old base would have put an unmade owner decision on main inside a
    commit whose subject is a runtime line; the split costs one re-base and buys a measured,
    owner-independent fix that does not wait on a person.

## Instruments

- The re-based definition delta, measured after the re-base: `4genthub-min/definition-on-main`, base
  `02c63789`, tip `16f0032f`, own patch-id **`ae899a1ada0ed7f3332abf01ce9c39800fc04c21` — identical to
  the value the reviewer was given for the `e3074353`-based version**, because the patch-id is
  content-based, so the gate holds on the content it read.
- `git show 16f0032f:scripts/team/4genthub-min/team.json` → `links` **0** and architect
  `omp`/`deepseek/deepseek-flash`: the table does **not** ride in it.
- `git merge-base --is-ancestor e3074353 16f0032f` → **rc 1**, the property the re-base was for.
- `python3 -m pytest --noconftest -p no:cacheprovider scripts/tests -q` on that branch → **91 passed**;
  with the architect line drifted back to `claude-code`/`opus`, **2 failed / 89 passed** in exactly the
  two cases that guard it; green again on restore.
- The socket probe from the previous entry is unchanged: `RoomLinks(4genthub-min)` → `ok:true`, 23 rows.

## Not in this change

No code, no test, no pin. `NEXT-GEN2.md` plus this entry, one commit above the board delta's fourth.
