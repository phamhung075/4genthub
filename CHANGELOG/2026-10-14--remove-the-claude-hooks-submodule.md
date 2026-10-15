## 2026-10-14 — Remove the `.claude` hooks submodule

### Changed
- Removed the `.claude` submodule (`4genthub-hooks`) and its `.gitmodules` entry. Sessions run through the
  4genteam runtime (`4genteam up`, seats, rooms), not through a Claude Code project configuration.
- The `4genthub-hooks` remote keeps its history. Its local commit `ca2383f` (the `4genteam whoami` rewrite) was
  never pushed and is gone with the local clone.

### Not changed
- Documents that still name `.claude/` paths (`CLAUDE.local.md`, `README.md`, `ai_docs/*`, `.gitignore`,
  `.gemini/gemini.local.md`, `.automation/template/*`) are not yet updated.
