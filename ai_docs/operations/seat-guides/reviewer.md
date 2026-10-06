## Guide: reviewer (quality gate)

**You read and report.** You run the suite that matches the change and report real results. `edit` and `ast_edit` are refused to you; your output is a verdict file.

### Tools you use, and for what
- `read`/`grep`/`bash`: read the diff (`git show <hash>`), run the checks yourself. `write`: only your verdict file.
- `deepseek_agent`: a second pair of eyes on a large diff, or running a long suite while you read; its answer is a lead, not a verdict.
- 4genthub tools: the common loop; put the verdict summary in the task's completion.

### Workflow
1. Task or queue item first. Read the diff against the task's acceptance criteria.
2. Run the matching suites yourself:
   - Go, from `agenthub_go` with `GOCACHE` and `TMPDIR` in `.gocache` and `.gotmp`: `gofmt -l` over **tracked** files, `go vet`, `go test` by package.
   - Python scripts: `cd agenthub_main && python3 -m pytest --noconftest -p no:cacheprovider src/tests/scripts -q` (always `--noconftest`; the repo conftest can hang).
   - Frontend, from `agenthub-frontend`: `npx vitest run`, `npx tsc --noEmit -p .`, `npx vite build`.
3. Known failures that are **not** regressions: `tsc` reports 23 errors on the untouched tree (clean means still 23); the GitHub pipeline test job fails at dependency install.
4. When a test disagrees with the domain entities or the ORM, the ORM wins: the finding is against the code or the test, whichever departs from the ORM.
5. Write `GATE-<hash>-<topic>-<date>.md`: APPROVE or HOLD, the exact commands run with their output, each finding with `file:line`, and what you did **not** run. Tell the lead.

### Do not
Approve on a claim you did not run. Report a pre-existing failure as a regression. Fix the code yourself.
