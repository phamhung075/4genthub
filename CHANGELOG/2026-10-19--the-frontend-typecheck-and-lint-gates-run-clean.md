The frontend typecheck and lint gates run clean

`agenthub-frontend` had no `typecheck` and no `lint` script: CI ran `pnpm test` and a build, and the
`eslintConfig` in `package.json` named the CRA presets (`react-app`, `react-app/jest`) whose packages
are not installed, so nothing checked types or lint. Board task `c1c3540b` (T4a, MAINT-04).

`package.json` now carries `"typecheck": "tsc --noEmit -p ."` and `"lint": "eslint src
--max-warnings=0"`, and the dead `eslintConfig` block is gone. The replaced tooling is a flat config,
`eslint.config.mjs`: `@eslint/js` + `typescript-eslint` recommended + `eslint-plugin-react-hooks`
recommended, over `src`, with no baseline, no allowlist and no rule loosened. `globals` covers the
browser and the jest-installed test runner.

Violations were fixed forward, not suppressed: `any` replaced by the API's own types (the branch and
project payloads now share one `BranchLike = Branch | BranchSummary` in `src/types/api.types.ts`,
re-exported from `src/api.ts`), untyped API envelopes narrowed at the boundary where each response
arrives, dead imports and unused parameters removed, `catch (error: any)` replaced by `unknown` plus a
real narrowing, and the two `useEffect` dependency arrays corrected. `useWebSocketV2` reads the
client's private `isConnecting`/`userId`/`token` through the client's own public accessors
(`isConnectingNow`, `credentials`) instead of property casts. The dialog state types that were `any`
are `unknown` at the shared type and narrowed once per dialog through `isSubtask` (id/title/status/
priority - a nested subtask carries `parent_task_id`, not `task_id`). A test that asserted an
impossible state (`onSelect: undefined` on a required prop) was deleted; it left an unhandled
`TypeError` in the run.

Counts, measured at the same HEAD (`cad91428`), with this config:

- `npx tsc --noEmit -p .` - before: 0 errors (the gate did not exist; the typing errors surfaced only
  once the `any`s were removed, and all were fixed); after: 0.
- `npx eslint src --max-warnings=0` - before: 996 problems (980 errors, 16 warnings); after: 0.
- `npx vitest run` - before and after: 131 files, all passing (1925 tests after the deleted
  impossible-state test, 0 unhandled errors).

`ci.yml` is unchanged (go-dev owns it); the two commands are ready for CI to call.
