# The sequence the room is executing, and C6's check, on the board

The owner answered the room-idle decision with **continue** at 04:38Z, and the lead's assignment to the
architect seat (`qitem-20261015044224-666415a01322`) carries the sequencing the room runs next plus one
open unit whose acceptance shape is the architect's. This entry records what the board now says, the
instrument behind every line, and the two facts that had moved since the lead measured them.

## Changed

- **New §3 head block, "The sequence the room is executing, 2026-10-15 04:4xZ"** — the lead's measured
  facts, laid out in the order the room executes them, each line re-measured here at the instrument it
  names. Two corrections are carried in place rather than added as footnotes:
  - the C2 precondition is **two** commits, not one: `c0ffbe8` and `666978b` are both non-ancestors of
    `feat/support-agy-watch` (`git merge-base --is-ancestor`), and the run tree is rebuilt from one sha;
  - the integration branch and its pin are **not the same sha today**: the pin in main is `5bb6d9c`
    (`git ls-files -s agenthub_client`), while the local branch is `b8e7902` with three commits unpushed
    (`origin/feat/support-agy-watch` = `8e9590f`).
- **C6 gains its measurement and its design line.** The three checks in that item's own `Check` are now
  measured against the installed `4genteam` with a stub standing in for TypeSafe, because a real Jev's
  confidence cannot be dialled: 0.90 at the seat tier decides (exit 0, one request), 0.60 escalates one
  tier and carries the recommended option (exit 5), 0.60 at the lead tier names the owner (exit 5), and
  0.95 on `--category credentials` names the owner **without making a request at all** (stub hits
  3 → 3). The design line states the half the verb cannot prove: `owner` is not a tier the verb accepts,
  so "reaches the owner" is the escalatee's hand-off — a queue row tagged `owner-decision` — and a gate
  on C6 must assert that row, not only the exit code.

## Instruments

- `git merge-base --is-ancestor <sha> feat/support-agy-watch` for the seven ancestors and the two
  non-ancestors; `git ls-files -s agenthub_client` for the pin; `git log origin/..HEAD` for the
  unpushed three.
- `cat u3bin/PROVENANCE.txt` (client `0a968fc`, `4genteam` `fcef38d2…`, `agenthub-runtime` `a5a59568…`,
  built `2026-10-14T21:40Z`); `sha256sum` on the two harness copies → `28302b7b…`, **151731 B** each.
- `ps -eo pid,cmd | grep -iE 'openrig|rigd|pi-runner'` → no rows; `ls -d ~/.openrig` → absent;
  `find /home/daihu -maxdepth 4 -name openrig.sqlite` → nothing.
- `git grep -n '\.openrig' HEAD -- internal cmd` (non-test) → 0 in `agenthub_client`, and
  `OPENRIG_STATE_ROOT` → 0 under the same paths.
- `4genteam decide --help` (rc 0) and four runs of the real binary against a local stub at
  `TYPESAFE_BASE_URL=http://127.0.0.1:8791` with `JEV_DECISION_LOG_PATH=/tmp/uarch/decisions.log`; the
  log's four lines and the stub's hit count are quoted in the item.
- `ls scripts/tests/*.py | wc -l` → 13 (T13's surface).

## Not in this change

No code, no test and no other tracked path is touched: the plan-only diff is `NEXT-GEN2.md` plus this
entry, so the merge onto main stays a fast-forward with no build to re-run.
