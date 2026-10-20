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
  This is the sentence the item asked for, and it names what it replaced: the prescription of a
  command that can exit 0 doing nothing.

### Measured, on one tree, the same session

| command | wall | exit | what it did |
|---|---|---|---|
| `npx tsc --noEmit -p agenthub-frontend` (root) | 0.93 s | 0 | printed npm's placeholder notice, compiled nothing |
| `sh scripts/typecheck-frontend.sh` | 11.89 s | 0 | the frontend's compiler, no output |
| `npm run --silent typecheck` (root) | 11.82 s | 0 | the same compiler |
| `sh scripts/typecheck-frontend.sh --noUnusedLocals --noUnusedParameters` | 12.15 s | 0 | the same compiler, widened |
| the script in a tree with no `agenthub-frontend/node_modules` | 0.04 s | **127** | refused: "no compiler ..." |

The negative is the point: the form that used to exit 0 silently now either compiles or fails.

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
