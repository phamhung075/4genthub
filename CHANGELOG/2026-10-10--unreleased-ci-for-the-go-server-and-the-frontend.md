## Unreleased — CI for the Go server and the frontend

### Added
- `.github/workflows/ci.yml`: replaces the `test_coverage.yml` deleted in `d1114170`. Job `go` runs `go vet ./...` and `go test ./...` in `agenthub_go`; job `frontend` runs `pnpm install --frozen-lockfile`, `pnpm test` (vitest) and `pnpm build` in `agenthub-frontend` (the lockfile is `pnpm-lock.yaml`). Triggers: push to `main` and pull requests. Not run locally: the workflow has never executed on GitHub, so its first run is the validation.
