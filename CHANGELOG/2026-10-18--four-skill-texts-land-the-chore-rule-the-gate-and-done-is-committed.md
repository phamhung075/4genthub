# Four skill texts land: the chore claim rule, one verdict per gate, done = committed, one changelog file

Owner-approved texts written by the architect (`seats/architect/TEXT-drafts-2026-10-18.md`), landed in the
client repo by go-dev because a seat cannot make a docs-only commit.

## What changed

- `skills/share/seat-crew/SKILL.md` — **"No work for your seat: claim one chore."** Idle is read, not felt
  (no pending row to you, no in-progress item of yours, `quiet_seconds >= 900`); an idle seat claims ONE
  board item labelled `chore` for at most 30 minutes, and the assignee IS the lock. Never create a chore,
  never start code under one, release with a reason, close only with the output pasted into Details. The
  catalogue the lead seeds is tabulated with what "done" produces for each.
- `skills/rooms/4genthub-min/reviewer/reviewer-workflow/SKILL.md` — **"One row in, one verdict out."** The
  gate's interface is one handed-off row in and exactly one verdict row out (`request changes` to the
  author with `file:line`, or `approve` to the lead), carrying the `Unconfirmed` list and the commands run.
  Progress goes to the board; no finding becomes its own row; no polling rows.
- `skills/share/verification-before-completion/SKILL.md` — **"Done is committed, not said."** Three shapes
  and three verdicts: committed (a sha names it), prepared-not-committed (say so, keep the item open),
  owner-gated (not yours to call done). The same rule for a skill: it reaches a seat only when the commit
  lands AND the seat is reseated.
- `skills/share/changelog-updater/SKILL.md` — full replacement. The `CHANGELOG.md` + `## [Unreleased]` model
  it taught does not exist in this repo (740 dated files, no `CHANGELOG.md`): one new
  `CHANGELOG/<date>--<title>.md` per merged task, the entry riding the task's own code commit, proof named
  (shas, numstat counts, the test command and its exit code), and `TEST-CHANGELOG.md` for the suite only.

## Correction made while landing

The draft said "one file per change that ships" and "write the entry in the commit that merges the task".
The owner's 19:10Z decision, landed earlier as `b8366268`, made it **one entry per merged task, not per
commit** — so the text was aligned to that (the task's fix, test and correction share the file, written with
the first commit and finished before the merge). The file count was measured rather than quoted: 740 at
`ls CHANGELOG | wc -l`, not the draft's 762.

## Runs at this change

- `cd agenthub_client && go test -count=1 ./internal/clientskills/...` = `ok`, exit 0.
- `git apply --check` for the four selected paths passed on this branch before applying; the patch's other
  three paths (the `friction-triage` move, `queue-row-schema`, `seat-worktree`) were **not** taken here —
  they stay review 2's and the architect's.
- Seat-crew carries both sections in order: the owner's "Two rules the rail and the changelog enforce"
  (`030c847`) then the architect's chore section; no overlap.
- Reaching seats needs a reseat: a running seat does not re-read its skills tree.
