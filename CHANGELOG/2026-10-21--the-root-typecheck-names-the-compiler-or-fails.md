## The root typecheck names the compiler or fails

`npx tsc` typed at the repository root is not TypeScript. The root carries no compiler, so npx
resolves a global package named `tsc`, prints "This is not the tsc command you are looking for" and
**exits 0** without reading a file. The completion gate reads exit 0 as the test passing, so two gate
runs on task `b7a2c44c` carried `d3_tests` true on a command that proved nothing (hub task
`951d97e3`, raised from that task's Progress 9).

### Changed

- `scripts/typecheck-frontend.sh` (new): runs `agenthub-frontend/node_modules/.bin/tsc --noEmit -p
  agenthub-frontend` and nothing else. It names the binary by path, so the placeholder package can
  never be reached through it, and it **exits 127** with the reason when that binary is missing - a
  missing install is a failure, not a green. Extra arguments pass through, so the skill that widens
  the check keeps one entry point (`sh scripts/typecheck-frontend.sh --noUnusedLocals
  --noUnusedParameters`).
- `package.json`: a root `scripts.typecheck` = `sh scripts/typecheck-frontend.sh`, so
  `npm run typecheck` at the root is the same real run.
- `ai_docs/agent-system/task-workflow-and-reporting.md`: a new paragraph in the acceptance-criteria
  section names the frontend's acceptance command from the root as `sh scripts/typecheck-frontend.sh`
  (or `npm run typecheck`), records why the bare form is refused, and says which form is still sound
  (`npx tsc --noEmit -p .` **inside** `agenthub-frontend`, where the local binary resolves first).
  This is the sentence the item asked for. It does NOT replace an existing prescription in that file,
  and the difference is worth stating rather than smoothing over: the base doc carried no `npx tsc`
  line at all (`git grep -n 'npx tsc' f0b3f3b9 -- ai_docs/agent-system/task-workflow-and-reporting.md`
  is empty), so the paragraph is new. My first sweep for the prescription also missed the tree's own
  copies of it by omitting `*.txt`; the section below records every one that the second sweep found,
  which had a bare command without a cwd and now pins it.
- `scripts/team/4genthub/mission.md:7` and `scripts/team/4genthub/project-4genthub.txt:14`: both listed
  the frontend's typecheck as a bare `npx tsc --noEmit -p .` with no cwd, so a seat at the repository
  root following either line got the placeholder; both now say `from agenthub-frontend`, the form the
  reviewer measured at 14.82 s rc 0. The mission line also names the root form.
- `agenthub-frontend/tsconfig.tests.json:11`: the comment said `Run it: npx tsc -p
  tsconfig.tests.json` with no cwd; it now says "from this directory" and why.

### Swept, and left alone

`git grep -n 'npx tsc' HEAD` over the tracked tree, excluding the changelog history and the client
submodule, returns 13 files. The prescriptions that already pin the cwd are correct and unchanged:
`scripts/team/4genthub/area-quality.txt:6` ("Frontend: from agenthub-frontend ..."), `:9` (same file,
cwd carried by the line above), `scripts/team/4genthub/area-web-frontend.txt:11` ("Commands, from
agenthub-frontend:"), `agenthub_go/.../seedlibrary/blocks/guide-fe-dev.md:13` and `guide-reviewer.md:13`
(both "from `agenthub-frontend`"). The rest are history - `agenthub-frontend/CHANGELOG.md` and
`agenthub_go/NEXT_GEN.md` - and a historical record is not rewritten. The live `unused-code-cleanup`
skill under `agenthub_client/skills/share/` spells the bare form five times and belongs to the client
repository, not this commit.

### Measured, on one tree, the same session

| command | wall | exit | what it did |
|---|---|---|---|
| `npx tsc --noEmit -p agenthub-frontend` (root) | 0.93 s | 0 | printed npm's placeholder notice, compiled nothing |
| `sh scripts/typecheck-frontend.sh` | 11.89 s | 0 | the frontend's compiler, no output |
| `npm run --silent typecheck` (root) | 11.82 s | 0 | the same compiler |
| `sh scripts/typecheck-frontend.sh --noUnusedLocals --noUnusedParameters` | 12.15 s | 0 | the same compiler, widened |
| the script in a tree with no `agenthub-frontend/node_modules` | 0.04 s | **127** | refused: "no compiler ..." |

The negative is the point, and it is the SCRIPT'S invocation that carries it: `sh
scripts/typecheck-frontend.sh` now either compiles the frontend or fails, where a no-op pass is no
longer reachable through it. The bare `npx tsc` typed at the root is unchanged and still exits 0 doing
nothing - see the section below, which is why the item's criterion 2 needed the amendment recorded on
the board item rather than a claim here.

### What this does not close, and who owns it

The bare string `npx tsc` at the root is a per-machine hazard (a global npm package), so no committed
file can change what it does; what the repository can do is make the documented command impossible to
no-op, which is what this does, and CI already runs a real `pnpm typecheck` inside
`agenthub-frontend`. Two closers were considered and refused as out of this branch's safe scope:

- a root `devDependencies` entry on `typescript` (candidate (b) of the item) would let npx resolve the
  real compiler from the root, but the root's `node_modules` is empty and there are two lockfiles at
  the root, so the fix only exists after an install this seat must not run in a shared tree, and it
  would put a second TypeScript pin beside the frontend's `^4.9.5`;
- refusing the placeholder inside the gate's own runner (`agenthub_client`'s `runTestCommand`) is the
  complete fix and belongs to the client repo.

The live `unused-code-cleanup` skill (`agenthub_client/skills/share/`, a different repository) still
spells `npx tsc`; that edit belongs to the client tree, not this commit.
