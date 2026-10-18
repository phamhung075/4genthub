# The changelog-updater sentence drops a count no single tree agreed on

`skills/share/changelog-updater/SKILL.md` said "740 such files at `ls CHANGELOG | wc -l`". The command
names one surface; the number was read on another. Measured on 2026-10-18 across the trees in play:

| Surface | Command | Count |
| :--- | :--- | ---: |
| hub tree at the pin commit | `git ls-tree -r --name-only HEAD CHANGELOG \| wc -l` | 741 |
| hub worktree, `go-dev-root` | `ls CHANGELOG \| wc -l` | 741 |
| canonical clone worktree | `ls CHANGELOG \| wc -l` | 762 |
| a hub tree read earlier by the lead | — | 737 |

One file is one author's write, so any of these figures drifts the next time a task merges. The sentence
now reads "hundreds of dated files, and there is no `CHANGELOG.md`": the claim that carries the rule — the
directory IS the changelog, and no single changelog file exists — survives without a figure that cannot be
re-derived from the sentence itself.

## Where it landed

- Client branch `4genthub-min/changelog-count-surface`, commit `3d71ea9`, one file, `+1/−2`.
- Hub pin commit follows on `agenthub_client` with `Task: 8c271b85-158e-4058-9238-f971d09aed7a`.

## Runs at this change

- `cd agenthub_client && go test -count=1 ./internal/clientskills/...` = `ok` (0.024s), exit 0.
- `grep -rn '740\|762 such' skills/` = no match after the edit.
