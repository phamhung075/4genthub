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
- **§3, C4's instrument revision: the live harness is `28302b7b`, not `8d7be24c`.** `8d7be24c`
  (136414 B) was the live harness from 22:10:25Z until 22:13:45Z and its bytes remain as
  `u3-run/reviewer-stage3.sh`; the live bytes have been `28302b7b…`
  (`28302b7b96ff64f4f44a782bc9ab9fcecb0e4256da8c3c748a26c6d45b07897d`), **151731 B**, since 22:13:45Z,
  written straight to the live path with no rail row naming it, and present byte-identically at two paths
  (`u3-run/reviewer-stage5.sh`, `u3-run/ACCEPTANCE-cutover-lab-U3.sh`). The corrected line also records
  the rule that follows from it: the live path is write-only for applies.

## Instruments

- `ls scripts/tests/test_*.py | wc -l` → 12 and `ls scripts/tests/*.py | wc -l` → 13, in this repo.
- `git merge-base --is-ancestor {0a968fc,ad03a16,400e568} feat/support-agy-watch` in `agenthub_client`:
  in, in, **not in**; `git show 400e568:internal/retiredverbs/retiredverbs.go | grep -n 'Match:'` → the
  entry reads `"and no"`; `git show --stat 400e568` → three files, +93/−7; `git branch --contains
  400e568` → `4genthub-min/seat-runtime-socket` only.
- `sha256sum` on the two harness copies → both `28302b7b…`, 151731 B; `sha256sum
  u3-run/reviewer-stage3.sh` → `8d7be24c…`, 136414 B (the difference is 15317 B).

## Not in this change

No code, no test, no pin: the diff is `NEXT-GEN2.md` plus this entry, so the landing stays a
fast-forward with nothing to build.
