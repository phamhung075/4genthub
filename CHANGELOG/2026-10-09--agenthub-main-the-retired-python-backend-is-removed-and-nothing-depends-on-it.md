## agenthub_main, the retired Python backend, is removed and nothing depends on it

### Removed
- `agenthub_main/` (commit `a50929c6`). Recover it with `git checkout python-backend-final -- agenthub_main`, or `git revert a50929c6`.
- Python-only tooling: `scripts/{run-tests,validate_suite,verify_init_schema,deep_verify_schema,check_fk_cascade,generate_schema_sql,compare_schema,inspect_database,batch-test-runner}.py`, `scripts/test-menu.sh`, `scripts/start_backend_dev.sh`, `scripts/deployment/security/apply-security-fixes.sh`, `agenthub_go/tools/gen_models/gen_models.py`, `ai_docs/test-runner.py`, `.automation/*`, `.github/workflows/test_coverage.yml`, the `.gemini` and `.claude` unit-test commands.
- `docker-system/docker/`: `Dockerfile.backend.dev`, `docker-compose.{yml,optimized,dev,backend-frontend}.yml`.

### Changed
- `agenthub_go`: the schema SQL moved to `fastmcp/task_management/infrastructure/database/init_schema_postgresql.sql`; the project-root marker and the data paths use `agenthub_go`; the parity fixtures follow.
- `docker-system`: `docker-menu.sh`, `lib/*.sh`, `deployment-manager.sh`, `start-production.sh` and `docker-compose.production.yml` build and run the Go server only (port 8000, `/agenthub -healthcheck`).
- Commit hooks read `scripts/git-hooks/pre-commit-config.yaml` (reinstall with `pre-commit install -c ... --hook-type pre-commit --hook-type prepare-commit-msg`).
- `.claude` hooks and `CLAUDE.local.md` / `.gemini/gemini.local.md` use the Go layout.
- `agenthub_go/NEXT_GEN.md:415` (commit `0d712f48`): the publish-skills step named the removed `python3 scripts/openrig_team_setup.py publish-skills` and cited `openrig_team_setup.py:708-722`; it now names `4genteam team publish-skills` and `agenthub_client/src/agenthub_client/team_setup.py:764-778` (`cmd_publish_skills`). The dated history lines `:191` and `:543` keep the old name.
- `agenthub_go/NEXT_GEN.md:533`: the delivered-items record said a machine token is bound to exactly one route and that tests refuse it on every other route. The code has two routes, `POST /api/v2/openrig/seat-status` and `POST /api/v2/openrig/feedback` (a deliberate widening dated 2026-10-06, `machine_token_mount.go:8-15`), and the scope test refuses it on seven named routes (`machine_token_mount_test.go:281-306`); the line now says both, with the widening date.

### Testing
- With the tree absent: `go build ./...` and `go test ./...` pass, `agenthub_client` 314 passed, `bash -n` clean on every remaining script.
- Not run: `docker-menu.sh` and the production compose (no docker in this environment).
- Still open: `docker-system/docker/captain-definition` names `Dockerfile.backend.production`, which copies `agenthub_main/`.
