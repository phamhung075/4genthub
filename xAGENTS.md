# Repository Guidelines

## Project Structure & Module Organization
- Backend code lives in `agenthub_main/src/fastmcp` with supporting modules under `src/config` and `src/database`.
- Tests shadow the package layout in `agenthub_main/src/tests`; drop new suites beside the feature they exercise.
- `agenthub-frontend/src` hosts the React client, `public/` static assets, and shared UI primitives under `src/components`.
- Docs sit in `ai_docs/`; orchestration scripts (Docker menu, workers) stay under `docker-system/` and root `scripts/`.

## Build, Test, and Development Commands
- Backend: `cd agenthub_main && uv sync` installs dependencies, `uv run --frozen pytest src/tests` runs the suite, and `uv run --frozen pyright` type-checks.
- Justfile shortcuts mirror the flow: `cd agenthub_main && just build` (deps) and `just test` (pytest with `-xvs`).
- Frontend: `cd agenthub-frontend && pnpm install` primes the workspace, `pnpm start` serves Vite dev mode, `pnpm build` emits production assets, and `pnpm test` runs Vitest.
- Need the full stack? launch `./docker-system/docker-menu.sh` and select the target profile.

## Coding Style & Naming Conventions
- Python follows PEP 8 with 4-space indents and type hints; run `uv run --frozen ruff check src --fix` before committing and keep module names concise (`task_service.py`).
- FastAPI routes should return typed response models; reserve the `_async` suffix only when a sync variant also exists.
- React components use PascalCase filenames, hooks stay in `src/hooks` with camelCase names, and pair Tailwind classes with co-located styles.

## Testing Guidelines
- Honour the pytest markers (`fast`, `integration`, `mcp`, etc.) and keep coverage above the 80% bar defined in `pyproject.toml`; name files `test_<feature>.py` and share fixtures via sibling `conftest.py`.
- Quick loops: `uv run --frozen pytest -m fast`; pre-PR: `uv run --frozen pytest --cov=src --cov-report=term-missing`.
- Frontend tests sit next to the component with a `.test.tsx` suffix; scope runs via `pnpm test -- --run MatchPattern`.

## Commit & Pull Request Guidelines
- Follow the Conventional Commit style in history (`fix:`, `refactor:`, `chore:`), adding scopes when it aids review (`feat(frontend): add timeline tabs`).
- Keep commits self-contained with passing checks; document breaking API or schema changes in the body.
- PRs should spell out backend vs. frontend impact, link issues, and add screenshots or terminal output for visible changes.
- Run `uv run pytest`, `uv run pyright`, and `pnpm test` before submission and flag any skips or debt in the description.


