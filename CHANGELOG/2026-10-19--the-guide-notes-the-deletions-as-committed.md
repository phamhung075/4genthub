# The guide's dated notes name the deletion as committed

Date: 2026-10-19
Task: f8386987 (`The guide's dated notes say staged; the deletions are committed in 1c7b6631`)

## What was wrong

`ai_docs/operations/complete-operations-guide.md` said in five places that the retired deployment scripts
and `.github/workflows/production-deployment.yml` were "gone from the working tree and the index (staged
deletion, held)", and that `git show HEAD:scripts/deployment/deploy-production.sh` still resolved. Both
halves are false of this tree: the deletions were committed in `1c7b6631` (2026-10-09 22:48:34 +0200, 33
paths), `git status --porcelain -- scripts/deployment/ .github/workflows/` is empty, and `git show HEAD:`
on either path fails with *does not exist in 'HEAD'*. The `ci.yml` paragraph also named line numbers from
before gofmt, typecheck and lint joined its jobs, so every offset in it was stale.

## What changed

- The Quick Reference rows for deploy production, health check and rollback say the scripts were deleted
  in `1c7b6631`.
- The struck note under the table records the commit and its date, the empty status, the failing
  `git show`, the earlier `d1114170` deletion of `scripts/deployment/security/apply-security-fixes.sh`,
  and the two files `scripts/deployment/` carries now (`caprover-env-setup.sh`,
  `force-caprover-rebuild.sh`).
- The `production-deployment.yml` note says the workflow was deleted in `1c7b6631` and that its paragraph
  describes `1c7b6631^`.
- The `ci.yml` paragraph is re-measured at `5c254778`: go job `:9-30` (gofmt `:28`, vet `:29`, test
  `:30`), frontend job `:32-51` (install `:47`, typecheck `:48`, lint `:49`, test `:50`, build `:51`),
  working directories `:13` and `:36`.
- The Deployment Execution block marks the pre-deployment security script struck (deleted in `d1114170`)
  and the rollback section names `1c7b6631`.

## Evidence

- `git log -1 --format='%h %ad %s' --date=iso 1c7b6631` -> `1c7b6631 2026-10-09 22:48:34 +0200
  chore(scripts): the retired fleet scripts leave the tree - 33 paths, 13 017 deletions, on the gate`.
- `git status --porcelain -- .github/workflows/ scripts/deployment/` -> empty.
- `git show HEAD:scripts/deployment/deploy-production.sh` and
  `git show HEAD:.github/workflows/production-deployment.yml` -> both fail, *does not exist in 'HEAD'*.
- `git log --diff-filter=D -1 -- scripts/deployment/security/apply-security-fixes.sh` -> `d1114170`.
- `cat -n .github/workflows/ci.yml` -> the line numbers above.
- Documentation only: no code path changed.
