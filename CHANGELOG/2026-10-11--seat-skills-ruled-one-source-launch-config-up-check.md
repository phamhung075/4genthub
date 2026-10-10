## Seat skills are ruled: one source, delivery by the client, launch configuration, the up check

### Added
- `ai_docs/core-architecture/seat-skills.md`: the architect's ruling on the owner's rule that seats use skills from `agenthub_client/skills` only (`qitem-20261010232050-55adaf600cf70857`, board `9a5c1bb4`, ruling row `718778c1`; client work `622e9faf`, `fad0bb21`).
  - **Levels:** each skill lives at one level only. comm-guard-skill and queue-handoff go to `share/`; context-engineering and specification-system go to `rooms/4genthub-min/`. There are no seat-level skills today.
  - **The move rule:** every `.agents/skills` copy has a client counterpart, and the client copy is newer or identical in all 13 cases. Nothing moves; the `.agents` copies retire.
  - **Delivery:** `4genteam sync rig` only. `agent.yaml` lists exactly the resolved set, and cloud-snapshot skills are dropped.
  - **Launch configuration:**
    - omp gets `skills.customDirectories` set to the delivered tree, with every other skill provider disabled.
    - claude-code gets `--setting-sources project,local --plugin-dir <agent dir>/skills-plugin`.
  - **Retirement:** `.claude/skills` is removed by a commit in the hooks repository, and `.agents/skills` through `safe-file-removal`. `~/.agents/skills` and `~/.claude/skills` are disabled for seats, never deleted.
  - **The up check:** `F1 cwd`, `F2 foreign`, `F3 missing`, `F4 path`, `F5 stale`, each exiting 3. A running seat with drift is `doctor`'s `skills_stale`.

### Verified
- Measured by the architect on 2026-10-11:
  - In an empty directory, `omp skill list --json` lists three skills from `~/.agents/skills` (`source: agents:user`).
  - With claude 2.1.296, the init event shows that `--setting-sources project,local` drops user skills and user-installed plugins, while `--plugin-dir` delivers `<plugin>:<skill>`.
- No code changed in this commit, so no tests apply.
