# C5's comm-guard acceptance is a measurement, not a file

The reviewer read C5's acceptance and found it cites `FINDING-comm-guard-spelling-hole-2026-10-14.md` as
the record of the spelling-hole finding. That file does not exist, has never existed, and the unit the
finding belongs to is not built either. The board now says what C5 actually has to wait for.

## Changed

- **§3's guard bullet** no longer names the file as C5's acceptance. It states that the finding is
  rail-only — rows `qitem-20261015044224-32e082e41851` (to go-dev) and `qitem-20261015044224-333769e01b04`
  (to the reviewer) — and that no `FINDING-*` path exists under `/home/daihu` nor was one ever committed
  in either repo, so the closure is **by measurement**, not by citing a filename.
- **C5 gains the precondition it was silently carrying**: the comm-guard unit
  (`qitem-20261014061206-c11b63fab7d63680`, parked `blocked`) must land **before** C5, and its acceptance
  is a measurement of the send path. The unit's fix **exists and is not in the integration branch**:
  `892f867` "fix(client): the comm guard binds the native 4genteam spellings, deny and allow"
  (parent `8785915`, 2026-10-15 04:58:17Z) changes `internal/commpolicy/policy.go` (+26/−3) and
  `policy_test.go` (+50) plus one changelog, and it is on **`4genthub-min/seat-runtime-socket` only** —
  not an ancestor of `feat/support-agy-watch`, not in the pin `5bb6d9c`; on that branch `policy.go:270`
  reads `case "4genteam":`. So the reviewer's reading that the unit was **not built** was exact for the
  integration tip at 04:57Z (there `policy.go` still carries `case "rig":` at `:258` and its whole
  history across refs is three commits) and the fix appeared **76 seconds later** on the run tree's own
  branch: the unit is delivered, ungated and unmerged.

## Instruments

- `find /home/daihu -maxdepth 6 -name 'FINDING-*'` → nothing; `git log --all --name-only` grepped for
  `finding` in `agenthub_client` → no such path, and in this repo only unrelated older docs
  (`ai_docs/testing-qa/subtask-tdd-findings-2025-09-09.md` and four others).
- `git log --all --oneline -- internal/commpolicy/` in `agenthub_client` → `892f867`, `39c229b`, `bdc5405`,
  `13ccbdc` (the directory history), while the same command scoped to `policy.go` alone lists three,
  which is how the fix was missed on the first reading; `git log -1 --format='%h %ad %s%nparent %p'
  892f867` → 04:58:17Z, parent `8785915`; `git show --numstat 892f867` → `policy.go` +26/−3,
  `policy_test.go` +50, one changelog; `git branch -a --contains 892f867` →
  `4genthub-min/seat-runtime-socket` only; `git merge-base --is-ancestor 892f867 feat/support-agy-watch`
  → no, and the same against `5bb6d9c` → no; `git show 4genthub-min/seat-runtime-socket:internal/commpolicy/policy.go | grep -n 4genteam`
  → the `:242` comment and `case "4genteam":` at `:270`.
- The two rail rows quoted were read with `4genteam room queue show`; the finding text itself is only
  there, which is the reason the board may quote them but must not cite a file.

## Not in this change

No code, no test, no pin: the diff is `NEXT-GEN2.md` plus this entry and the corrections entry beside it.
