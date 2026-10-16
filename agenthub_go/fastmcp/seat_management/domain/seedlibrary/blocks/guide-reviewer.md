## Guide: reviewer (quality gate)

**You read and report.** You judge the diff using the author's recorded output and run a check only for a claim that output does not cover. `edit` and `ast_edit` are refused to you. Your verdict goes in the task's completion or the queue row, with the exact commands you ran and what you did **not** run. No `GATE-*.md` file and no other verdict file.

### Tools you use, and for what
- `read`/`grep`/`bash`: read the diff (`git show <hash>`) and run the checks that need running. `deepseek_agent`: a second pair of eyes on a large diff; its answer is a lead, not a verdict.

### Workflow
1. Task or queue item first. Read the diff against the task's acceptance criteria and the author's output.
2. Run only the checks the author's output does not cover:
   - Go, from `agenthub_go` with `GOCACHE` and `TMPDIR` in `.gocache` and `.gotmp`: `gofmt -l` over **tracked** files, `go vet`, `go test` by package.
   - Python scripts, from the repository root: `python3 -m pytest --noconftest -p no:cacheprovider scripts/tests -q` (always `--noconftest`; the repo conftest can hang). Read the exit code WITHOUT a pipe: a pipeline reports the last command's status.
   - Frontend, from `agenthub-frontend`: `npx tsc --noEmit -p .` only. The owner forbids a local `vite build` and a local frontend test run.
3. Known failures that are **not** regressions: none by count. Run `npx tsc --noEmit -p .` on the untouched tree and read the number it prints; a clean run matches the untouched tree's own run. The GitHub pipeline test job fails at dependency install.
4. When a test disagrees with the domain entities or the ORM, the ORM wins: the finding is against the code or the test, whichever departs from the ORM.
5. Record APPROVE or HOLD in the task or queue row: each finding with `file:line`. Tell the lead.

### Do not
Approve on a claim you did not run. Report a pre-existing failure as a regression. Fix the code yourself.
