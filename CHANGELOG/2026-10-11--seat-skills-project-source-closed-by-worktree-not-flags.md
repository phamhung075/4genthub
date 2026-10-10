## Seat skills: the project skill source is closed by the worktree and the symlink removal, not by the launch flags

### Changed
- `ai_docs/core-architecture/seat-skills.md` §5: a measured correction, made on a question from a sender I could not authenticate who claimed to be the owner session.
  - `--setting-sources project,local` still loads `<cwd>/.claude/skills`. In the main checkout, that is the 13 skills under `.agents/skills`.
  - The flags close only the user sources. The project source is closed by the symlink removal (section 4) and the worktree cwd (`F1`).
  - Dropping `project` is rejected, because that would also drop the hooks.

### Verified
- The architect probed with its own argv in the main checkout and killed each probe at the init event.
  - Today's argv loads 13 project skills, 3 user skills and 7 user plugins, and nothing from the agent directory.
  - `--setting-sources project,local --plugin-dir` loads 13 project skills and the 18 agent-directory skills.
  - `--setting-sources local --plugin-dir` loads the 18 agent-directory skills only.
- No code changed in this commit, so no tests apply.
