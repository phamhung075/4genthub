## The operations guide told an operator to run nine deployment scripts the tree no longer has

### Fixed
- `ai_docs/operations/complete-operations-guide.md`: the Quick Reference table and the *Deployment Execution* / *Rollback Procedures* blocks carried **nine `./scripts/deployment/*.sh` commands** (lines 7–9 and 47–86) whose paths are absent from the working tree and the index. All nine are struck with a dated note; the block's one surviving command, `./scripts/deployment/security/apply-security-fixes.sh`, is kept.
- **No replacement was invented, because the tree has none.** `4genteam --help` (2026-10-09) lists no deploy, rollback or health-check verb, so the client package is not their moved home. What the working tree still carries under `scripts/deployment/` is exactly three files (`caprover-env-setup.sh`, `force-caprover-rebuild.sh`, `security/apply-security-fixes.sh`), and the note names those plus the CapRover artefacts (`captain-definition.backend` / `captain-definition.frontend`, `docker-system/deployment-manager.sh`, `scripts/deploy-frontend.sh`).
- The same document's CI/CD paragraph now states that `.github/workflows/production-deployment.yml` is in the same state — absent from the working tree, staged for deletion — so the paragraph describes HEAD rather than disk.
- **The trap is stated rather than left to be discovered**: the deletion is STAGED, not committed, so `git show HEAD:scripts/deployment/deploy-production.sh` still resolves while the file on disk does not.

### Verified
- `git status --porcelain -- scripts/deployment/` -> four `D` entries (`deploy-production.sh`, `health-checks/comprehensive-health-check.sh`, `health-checks/smoke-tests.sh`, `rollback/rollback-production.sh`); `find scripts/deployment -type f` -> the three surviving files; `git status --porcelain -- .github/workflows/` -> `D .github/workflows/production-deployment.yml`.
- `4genteam --help` -> `sync seat policy team bridge watch feedback compact-run` plus the lifecycle verbs; no deploy, rollback or health-check verb.
- `grep -nE '^\s*(\./)?scripts/deployment/[^ ]*\.sh' ai_docs/operations/complete-operations-guide.md` after the edit -> one command-shaped line, the live security script; the removed paths survive only inside the struck, dated statements.
