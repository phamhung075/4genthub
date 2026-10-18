# The two remaining skill texts land: the queue verb form with its ROOM default, and no worktree mid-session

Applied from the architect's `remaining-two-at-3d71ea9.patch` (6938 bytes, sha256 `ddea9fcdab87966c…`,
4 hunks, +50/−0) at client main `3d71ea9`, by go-dev, because a seat cannot make a docs-only commit.

## What the text now says

- `skills/share/queue-row-schema/SKILL.md` (+49) — **"The verb form: ROOM first, and it defaults."** Every
  sub-verb takes ROOM as its first positional and the qitem second; ROOM is the one positional that
  defaults to `$AGENTHUB_ROOM`. The six verbs are tabulated with their optional ROOM. The shortfall rule is
  stated as the COUNT, not the spelling: one positional short means ROOM was omitted, so an id typed where
  the room belonged is never read as a room; short by more than one is a missing tail and is refused naming
  the id. With `$AGENTHUB_ROOM` unset the verb refuses **before** the round trip, naming the variable
  (exit 3). Also carried: the measured 49 `the ROOM comes first` refusals and the 147 failed calls the
  default addresses; that `--summary`/`--body`/`--tag` are required in practice; the per-field caps the
  daemon enforces (facts 280, rule 110, decision 100, next 78) against a `--help` that states only the body
  cap; `close --reason` as an enum with the sentence in `--note`; and **"A cited file is one the reader can
  open"** — `local://` resolves inside the writing session's own directory, so a row cites a room-shared or
  absolute path (measured: `Local file not found`, 51s to locate by hand).
- `skills/share/seat-worktree/SKILL.md` (+1) — rule 4: **do not open a NEW worktree mid-session.** The guard
  is handed its allowlist at launch (`AGENTHUB_WORKTREES`, read once), so a hand-made `wt/<seat>-<lane>`
  takes a `worktree-scope` refusal on every write; measured 16 such blocks on 2026-10-18, the largest class.
  A parallel lane needs the room spec to name it and a reseat, or it reuses an allowed worktree.

## Where it landed

- Client branch `4genthub-min/two-skill-texts`, commit `de2600c`, two files, `git show --numstat` = 49/0 and
  1/0, exactly the patch's shape.
- Hub pin commit carries `agenthub_client` = `de2600c` plus this file, `Task: b08071e5`.

## Runs at this change

- `git apply --check` on the patch at `3d71ea9` = clean, and the sha256 of the file equals the lead's.
- `cd agenthub_client && go test -count=1 ./internal/clientskills/...` = `ok` (0.038s), exit 0.
- Not applied: the spent 7-file patch and the superseded count hunk, as the row said.
