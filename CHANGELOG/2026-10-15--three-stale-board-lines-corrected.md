# Three stale board lines corrected, each against a fresh measurement

The reviewer read the board after the sequencing block landed and named three lines that no longer say
what the system says. All three are corrected in place with the instrument that moved them, and none of
them touches code, tests or a pin.

## Changed

- **§3 head, "T13's surface": the 13 was not a test count.** `ls scripts/tests/*.py | wc -l` → 13, but
  that 13 includes `gitfixture.py`; `ls scripts/tests/test_*.py | wc -l` → **12**. The line now gives the
  12 as the test count and names the 13 as the directory count that must not be quoted as tests.
- **§3, the two units after `a58e684`: "and NEITHER IS LANDED" is superseded, and the required edit is
  done.** `git merge-base --is-ancestor` puts **both** `0a968fc` and `ad03a16` inside
  `feat/support-agy-watch` — the C3 merge carried them. The pin's one required edit is **`400e568`**
  ("test(client): the retired-verb pin allows a negation, not a licence", parent `0a968fc`):
  `Allowed[4].Match` became **`"and no"`**, the negating words of the sentence that names the retired
  form, with the negation pinned in `retiredverbs_test.go` (three files, +93/−7). `400e568` is on
  `4genthub-min/seat-runtime-socket` and is **not yet an ancestor of `feat/support-agy-watch`**, so it
  stays delivered-and-awaiting-gate rather than landed.
- **§3, C4's instrument revision: the live harness is `5b2e15b3`, and the history of the line is now
  written down.** `8d7be24c` (136414 B) was live from 22:10:25Z until 22:13:45Z (bytes kept as
  `u3-run/reviewer-stage3.sh`); `28302b7b…` (151731 B) was live from 22:13:45Z until **2026-10-15
  04:54:5xZ**, written straight to the live path with no rail row naming it (bytes kept as
  `u3-run/reviewer-stage5.sh` and `/tmp/u3guard/live-before-28302b7b….sh`); the live bytes are now
  **`5b2e15b38b3c13407cee3eaa07195b03d0144e8e2dd165ad714323e1da3b0a1c`, 157965 B**, installed at
  04:54:5xZ and present byte-identically at the live path and at `u3-run/fe-stage6.sh`, announced as one
  triple with `fe-stage6.patch` and with `/tmp/u3guard/apply.log` carrying
  `target_before=28302b7b staged=5b2e15b3 target_after=5b2e15b3`. The corrected line records the rule the
  unannounced 22:13:45Z write paid for — the live path is write-only for applies, iterate in a scratch
  copy, log the before/after shas, and announce the sha and its triple — and states the sizes so a leg
  quoted against either older revision is visibly not a leg of the live instrument.

## Instruments

- `ls scripts/tests/test_*.py | wc -l` → 12 and `ls scripts/tests/*.py | wc -l` → 13, in this repo.
- `git merge-base --is-ancestor {0a968fc,ad03a16,400e568} feat/support-agy-watch` in `agenthub_client`:
  in, in, **not in**; `git show 400e568:internal/retiredverbs/retiredverbs.go | grep -n 'Match:'` → the
  entry reads `"and no"`; `git show --stat 400e568` → three files, +93/−7; `git branch --contains
  400e568` → `4genthub-min/seat-runtime-socket` only.
- `sha256sum u3-run/ACCEPTANCE-cutover-lab-U3.sh u3-run/fe-stage6.sh` → both **`5b2e15b3…`, 157965 B**
  (`ls -la` mtimes 2026-10-15T06:54:52Z and 06:54:50Z local); `sha256sum u3-run/reviewer-stage5.sh` →
  `28302b7b…`, 151731 B (mtime 06:15:42Z local, the previous live revision); `sha256sum
  u3-run/reviewer-stage3.sh` → `8d7be24c…`, 136414 B (23:57:47Z). The apply log and the pre-apply bytes
  are named in the row that announced the move, `qitem-20261015045511-def22a9acb5a`
  (`/tmp/u3guard/apply.log`, `/tmp/u3guard/live-before-28302b7b….sh`).

## Not in this change

No code, no test, no pin: the diff is `NEXT-GEN2.md` plus this entry, so the landing stays a
fast-forward with nothing to build.
