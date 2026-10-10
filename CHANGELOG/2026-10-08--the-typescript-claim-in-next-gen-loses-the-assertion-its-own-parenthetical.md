## The TypeScript claim in NEXT_GEN loses the assertion its own parenthetical contradicted

- **What it said:** that web-dev measured `npx tsc --noEmit -p .` at 0 errors **"and 0 again through a
  throwaway test-inclusive config because `tsconfig.json` excludes `src/tests`."** Two assertions, and only the
  first holds: the exclusion offered as the reason the zero extends is exactly why it cannot. Re-measured today,
  a test-inclusive config over `src` gives **779 errors across 68 files** (446 with `vitest/globals` and `node`
  in scope), while the shipped `tsc -p .` is **0**.
- **The fix removes the claim rather than editing a digit**, which is the point: the row exists to correct the
  stale "23 pre-existing TypeScript errors" baseline, and `tsc -p .` = 0 carries that by itself. The sentence now
  ends at *"at 0 errors today, twice."* Nothing else on the line changed.
- Files: `agenthub_go/NEXT_GEN.md`, `CHANGELOG.md`.
