## The files absorbed into the single architecture file are deleted

### Changed
- Deleted thirteen files whose content now lives in `ai_docs/core-architecture/agenthub-system-architecture.md` (commit `c3f45214`): `ai_docs/architecture-design/` (`PRD.md`, `Architecture_Technique.md`, `product-architecture-complete.md` and the eight `decision-*.md`) and `ai_docs/core-architecture/agent-knowledge-skill-system-{specs,summary}.md`. Restore any of them with `git show c3f45214:<path>`; `git revert` of this commit restores all.
