## NEXT_GEN carries the 0.0.37 release record, with the push order that is easy to lose

### What changed
`agenthub_go/NEXT_GEN.md` gains one section — `## Release record — 0.0.37, certified 2026-10-11T01:06Z, waiting
on the owner's two pushes` — inserted between `## Rig capacity (2026-10-05)` and `## Checklist`: **23 insertions,
0 deletions, in that one file**, lines 344–365.

Why it exists: the standing mission names `agenthub_go/NEXT_GEN.md` as the single backlog **and decision record**,
while the `0.0.37` record lived only in `CHANGELOG/2026-10-11--release-0-0-37-the-ledger-slice-the-subtask-details-and-the-client-pin.md`
(the marker commit `294f432b` and its docs-only follow-on `708e3131`) and in the lead's `DEPLOY-READY.md`. Row
`qitem-20261011010701`, filed low priority to ride the first commit of the next batch.

The section carries, in the order a reader needs it:

- **the release's identity** — branch `4genthub-min/batch-0.0.37`, tip `708e3131`, 19 commits above `origin/main`,
  a fast-forward, the marker `config.ReleaseVersion = "0.0.37"` at `agenthub_go/fastmcp/config/version.go:25`
  committed as `294f432b` with `708e3131` as a docs-only follow-on;
- **what it ships** — the ledger's cross-task read and intents route (`f285bdf6`, `4f86a1ac`, `bccf893d`), the
  subtask's own progress served as details (`8e4786dd`), two frontend repairs (`4a5db09f`, `3e8c2084`), the client
  pin bump (`19b783c6`: `36f455e` → `d0d7599`) — and the battery taken at `294f432b`;
- **the push order, with both commands and the reason it cannot be reordered** — client first, then parent,
  because the parent's gitlink names `d0d7599` while the client's **remote** main is still at `36f455e`, so a
  parent-only push ships a gitlink whose target cannot be fetched;
- **the artefact sequencing rule this batch learned by failing** — `agenthub/internal/apiref` is a build output
  whose drift test is a real gate (it failed direction 1 on this batch's own two ledger routes, fixed as
  `03e0d1a1`), so the artefact is regenerated and committed before the release entry, and the entry before the
  marker;
- **how the batch was assembled** — seats' branches enter by merge (`539b6768`, `55764990`), both seat tips were
  confirmed ancestors of the release tip (`go-dev 03e0d1a1`, `fe-dev feb09b6b`), which is why a later commit on a
  seat branch cannot move `708e3131`;
- **the three open carries** — the `SubtaskDetailsDialog.tsx` comment minors (row `qitem-20261011005826`), the
  empty-history wire asymmetry, the 422 body's always-null input for P6 parity;
- **NO SEAT PUSHES**, and the note that `rig gateway human list` is empty, so the ask can only be answered.

### Verified
- the inserted section read back at `agenthub_go/NEXT_GEN.md:344-365`, and `git diff --numstat` → `23 0` in that
  single file, which is the whole commit (no other path was dirty);
- the facts **re-measured at this tip rather than copied from the row**: `git show 708e3131:agenthub_go/fastmcp/config/version.go`
  line 25 → `const ReleaseVersion = "0.0.37"` (my branch's line 25 reads `"0.0.36"`), and
  `agenthub_go/fastmcp/server/httpapp/http.go:160` → `const healthVersion = config.ReleaseVersion`;
- `git show --stat 708e3131` → the release entry only, 3 insertions / 4 deletions in one `.md`; `294f432b` →
  `version.go` plus that same entry file, i.e. the marker is the last commit carrying deploy content;
- no Go, test or frontend file is touched, so no package suite is affected: this commit is prose in one Markdown
  file, and `gofmt` / `go vet` / `go test` are accordingly not run;
- the one line the certified batch holds that this branch does not is `NEXT_GEN.md:425` (an O1c checklist item's
  text), unrelated to this insert — noted because the merge brings it.

### What this does NOT do
It does **not** add a commit after the certified tip: this lands on the seat branch `4genthub-min/go-dev`, which
the lead measured as free, and neither frozen ref moves — `4genthub-min/batch-0.0.37` stays at `708e3131` and the
client's `4genthub-min/go-dev` at `d0d7599`.

It is **not** a second source of truth for the release: the record proper stays the changelog release entry and
the measured tip line stays the lead's `DEPLOY-READY.md`, both named in the new section, so a correction has one
home. The one judgement it adds is the sequencing rule, which neither of those stated as a rule.

It does not push, tag or deploy anything.

Row: `qitem-20261011010701`.
