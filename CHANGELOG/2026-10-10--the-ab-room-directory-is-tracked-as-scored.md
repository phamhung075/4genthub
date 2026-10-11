## The `4genthub-ab` room directory is tracked, as scored

Item 3 of `DELEGATED-rollout-decision-2026-10-10.md` ("re-pin after the experiment; commit the
directory now"), assigned by the lead at 20:27Z (queue row `qitem-20261010202711-168836dd66569951`).

### Added
- `scripts/team/4genthub-ab/team.json`, `ab-terse.md`, `ab-verify.md` — the room's definition, staged
  **exactly as the live experiment left it**. They were untracked, and only a tracked file can prove
  which pins and overlays the scored runs used.

### Not changed, deliberately
- **No `pinned_version` moved.** The room's four seats stay where the experiment put them until the
  last scored run is done: re-pinning now would hand the control arm (`arm-control`, which does not
  carry `ab-terse`) the token-economy rule that `ab-terse.md:3` states, and a control that contains
  the treatment is not a control. The re-pin is a later, single move through the R1 route once it
  deploys.
- **No file under the directory was edited to make it committable** — the commit stages what is
  there. While the ab rig is live, no seat edits anything under `scripts/team/4genthub-ab/`; this
  commit does not touch a running rig.

### Verified
- `git ls-files scripts/team/4genthub-ab/` names all three files.
- `git show HEAD --name-only` lists only those three plus this changelog.
- `git status --short scripts/team/4genthub-ab/` is empty afterwards — nothing under the directory is
  modified relative to the commit.
- Content hashes at the moment of the commit, so a later reader can tell the scored bytes from any
  later edit: `ab-terse.md` `6ac964e8…`, `ab-verify.md` `4acf2fbe…`, `team.json` `8fce2445…`
  (`sha256sum`, full values in the queue row's report).
