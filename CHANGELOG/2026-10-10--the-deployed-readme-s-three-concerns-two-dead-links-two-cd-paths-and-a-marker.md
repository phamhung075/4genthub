## The deployed README's three concerns: two dead links, two `cd` paths, and a marker cell that quoted rotted readings

### Changed
- `README.md`, five lines and nothing else. The commit's own `git diff -U0` prints hunks at **`:216`, `:361`, `:539`, `:542`, `:654`** and ten changed lines (5 insertions + 5 deletions), and `git show --name-only` prints the single path:

| line | was | is | why |
|---|---|---|---|
| `:361`, `:539` | `[CHANGELOG.md](CHANGELOG.md)` | `[CHANGELOG/](CHANGELOG/)` | the target did not exist: `git cat-file -e origin/main:CHANGELOG.md` -> `fatal: path 'CHANGELOG.md' does not exist in 'origin/main'`, while `CHANGELOG/` is a tree (278 entries at HEAD). Dead on the DEPLOYED tip, not merely uncommitted |
| `:216`, `:654` | `cd agentic-project` | `cd 4genthub` | a directory name that exists in no ref of this repository, in both clone-and-run recipes |
| `:542` | a deploy-marker cell measured `0.0.28` / `0.0.27` / `0.0.22` on 2026-10-09 and asserted that "the deployed and the prepared state now DIFFER" | the cell described below | every figure was stale and the divergence false; the cell now carries NO reading and invites none |

- **The marker cell now names a check rather than a number.** It says the deployed version IS the tree's `config.ReleaseVersion` (`agenthub_go/fastmcp/config/version.go:21`), served by `healthVersion = config.ReleaseVersion` (`agenthub_go/fastmcp/server/httpapp/http.go:160`), and tells the reader to compare that literal with `curl -sS https://api.4genthub.com/health`. **The number was removed rather than refreshed because this cell has now rotted twice** (`0.0.22` -> `0.0.27`/`0.0.28` -> `0.0.31`): a figure in a README cell has no instrument behind it. Readings live in one place, `DEPLOY-READY.md`, where they are re-measured at the seal.

### Verified
- **The divergence the old cell asserted is false, measured at all three ends.** `const ReleaseVersion = "0.0.31"` read in the worktree, at HEAD and at `origin/main` — three identical reads — and `curl -sS --max-time 15 https://api.4genthub.com/health` (exit 0) answering `{"status":"healthy",...,"version":"0.0.31",...}`, the response's own timestamp decoding to **2026-10-10T10:36:34Z**, uptime 4739.9s. The deployed and the prepared state AGREE today; the cell said they differ.
- **The replacement's two citations were re-derived in the turn that wrote them, not remembered:** `21:const ReleaseVersion = "0.0.31"` and `160:const healthVersion = config.ReleaseVersion` (the value reaches the response body at `http.go:173`).
- **The fixed links resolve at the commit and the dead name is gone:** at `e38b59a3`, `git cat-file -t HEAD:CHANGELOG` -> `tree`; `HEAD:CHANGELOG.md` -> does not exist; `grep -c 'cd agentic-project'` -> **0** against `&& cd 4genthub` -> **2**.
- **Nothing unrelated rode in.** The diff was shown in full before staging and carried only the five lines above; the commit used an explicit pathspec (`git add -- README.md`, `git commit -F - -- README.md`) so `.claude`, `.env.sample`, `agenthub_go/cmd/agenthubclient/main.go` and `agenthub_client`, all dirty in the same shared tree, were untouched — the same discipline the pre-commit hook's stash/restore makes necessary rather than optional (its `Stashing unstaged files …` / `Restored changes …` pair ran twice during this commit, and the other seats' files were re-measured intact afterwards).
- **A guard wrote itself out of the record, and this entry keeps it that way.** A pre-commit assertion script meant to gate this commit aborted on its own off-by-one — 667 lines asserted where `split('\n')` on a newline-terminated file yields 668 elements — BEFORE evaluating its remaining checks, and because it was not chained to the commit, the commit ran anyway: **it gated nothing.** It was an inline `python3 - <<'PY'` heredoc in the shell invocation, never a file, so there is nothing under `scripts/` or `core.hooksPath` to find. `e38b59a3` rests on the four facts above, measured AFTER the fact.

### Found by
- Board row `0c08b443` (the README at the deployed tip), which the lead made a dependency of `d2b6391e` so the reviewer checks it: the links resolve, and the diff is only the three concerns. The three concerns were drafted in the owner's working tree and re-measured here; the owner's word on who commits did not arrive, so the lead committed it on its standing instruction, and that provenance is recorded rather than implied.

### Not taken, and why
- **The owner's own durable rule for the same cell was left out**, on the lead's ruling: his sentence "the distance between them is a count that rots, so read it rather than quote it: `git rev-list --count origin/main..HEAD`" is the same point the cell now makes, and it returns on one word from the owner and one line in a later docs pass.
