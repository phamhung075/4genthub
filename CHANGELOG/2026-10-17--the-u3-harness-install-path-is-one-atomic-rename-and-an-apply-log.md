## The U3 harness install path is one atomic rename, and every install is logged

The C4 instrument row (`ebcc1440`) named one open item on the acceptance harness: the live path
(`u3-run/ACCEPTANCE-cutover-lab-U3.sh`) was writable in place, and on 2026-10-15 it held three unannounced
revisions in as many minutes (`8d7be24c` -> `f54f1f17` -> `28302b7b`). A run started inside one of those
windows can execute a mixed revision, and the harness's own `harness_unchanged` guard (which compares the
file's sha before every leg and exits 4) cannot see a write that happened before the run started.

### Added
- `scripts/u3-apply-harness.sh` — the one way that path is written now. It refuses unless (1) the staged
  bytes hash to the sha that was announced (a full sha256 is required), (2) `bash -n` parses them, and (3)
  they differ from the live bytes; it keeps the predecessor aside under its own sha256; it installs with ONE
  `mv` in the same directory, so a reader never sees a half-written harness; it appends
  `before -> after`, bytes, composed file and seat to `APPLY-LOG` beside the live file; and its last line is
  the announcement (harness sha, bytes, predecessor, stage file). `--dry-run` proves the plan and writes
  nothing; `--current` reads the live sha and names the stage file whose bytes match it; `--log` prints the
  append-only record. A failed post-install verification restores the predecessor from the aside and exits 4.
- `scripts/tests/test_u3_apply_harness.py` — the refusals, the aside, the log line, the announcement, the
  dry run and `--current`, hermetic in `tmp_path`.

### Not in this commit
- The install itself. The seat guard (`worktree-scope`) refuses this seat's writes outside its worktrees,
  and `u3-run` is outside them, so the apply is the lead's one command against the same tool
  (`--live <u3-run>/ACCEPTANCE-cutover-lab-U3.sh <staged> --expect-sha <sha>`). The staged revision that
  awaits it is `fe-stage15.sh`, sha256 `f3bbd72d…`, composed on the live `b9127abb…` chain (stage14) through
  stage12, both composers reverse-verified and `bash -n` clean; that install remains the lead's decision
  ("one instrument revision per install").
