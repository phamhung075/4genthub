# The calibration bullet prints the log's own total, not the withdrawn one

`NEXT-GEN2.md` §3's calibration bullet printed `TOTAL 7 pass / 5 fail / 5 skip` and named the pair the
pass ran on as the superseded `462e2a1`. Both readings were wrong, and the pair is the worse of the
two: the numbers a reader takes from that bullet are the reading this room plans the C4 run against.

`CALIBRATION-5e-2026-10-15.md` carries fe-dev's own erratum for both (on the reviewer's finding
`qitem-20261015165045-3271936a7398`). The board is one file and rides whatever commit carries it, so
fe-dev left the edit to its active writer. This entry is that edit, with every number re-read at the
source rather than copied from either row.

## Changed

- **the total** — `**TOTAL 7 pass / 5 fail / 5 skip.**` becomes `**TOTAL 140 pass / 3 fail / 9 skip —
  the log's own final line (`evidence.log:1478`).**`; the withdrawn pair stays in place with its
  erratum beside it, per the board's convention of keeping what was believed visible.
- **the timing** — `05:19:52Z → 05:24:52Z` becomes `05:19:48Z (`run-identity` `started=`) → 05:24:54Z
  (log closed)`; the first leg's own clock remains `05:19:52Z`, named as such.
- **the pair** — `on the SUPERSEDED pair `462e2a1`` becomes the pair `u3bin` held at 05:19
  (`892f867` / `e6860a9c…` / `02644985…`), with `462e2a1`'s real build time (05:02Z), the
  local-time-with-a-`Z` stamp defect, and the artifact that still carries the wrong stamp.
- **why the total was mixed up** — the withdrawn table's rows are enumerable: two are the
  fix-verification `--check` legs' own tallies, one is a `C1` leg this harness revision does not have,
  and its `C4` row read "not reached" while C4 ran. The pass's own three FAILs are named by
  `evidence.log` line.

## Instruments

- `sed -n '1478p' wt/4genthub-min/u3-run/evidence-cal1-PROVISIONAL-20261015T051948Z/evidence.log` →
  `==== TOTAL: 140 pass, 3 fail, 9 skip (a SKIP is never a pass) ====`.
- That directory's `run-identity` → `started=2026-10-15T05:19:48Z`, `run_root=/tmp/u3cal1`,
  `harness_sha256=5b2e15b3…`, `provisional=YES`; the log's mtime is `07:24` local = `05:24Z`.
- `grep -rn "TOTAL: 7 pass" wt/4genthub-min/u3-run` → the report alone; the withdrawn total is in no
  run artifact.
- `evidence-stage8verify-PROVISIONAL-20261015T052834Z-A1/evidence.log:78` → `--- A1: 12 pass, 0 fail`;
  `…-B3/evidence.log:233` → `--- B3: 2 pass, 6 fail`.
- `ls -la wt/4genthub-min/u3bin` → `4genteam.previous-e6860a9c` and
  `agenthub-runtime.previous-02644985` both mtime `07:02` local (= 05:02Z), set aside when the
  `462e2a1` pair (mtime `07:24` local) replaced them; `ls -ld wt/4genthub-min/u3src-892f867` → `07:02`
  local.
- `grep -n built wt/4genthub-min/u3-run/evidence-cal1-…/PROVENANCE-binaries.txt:13` → `built:
  2026-10-15T07:02Z` (the wrong stamp); `u3bin/PROVENANCE.txt.462e2a1:14` → `built: 2026-10-15T05:24Z
  (UTC — the stamp on this file used to print local time with a Z, the fix the lead filed)`.

## Not in this change

No code, no test, no instrument, no pin: `NEXT-GEN2.md` plus this entry. The calibration pass remains
what it always was — **not** a verdict on the C4 candidates.
