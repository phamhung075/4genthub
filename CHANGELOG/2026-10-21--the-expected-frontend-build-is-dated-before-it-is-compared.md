# The expected frontend build is dated before it is compared

`scripts/check_served_frontend.py --expect-dist` compared the live app to whatever
`agenthub-frontend/build` happened to hold. That directory is not rebuilt by any commit, so on 2026-10-21
the served entry was `index-CulHwbQI.js` (Last-Modified 23:54Z, after every frontend commit) while the
expected side was `index-3rbprdLk.js` from a build dated 2026-10-11, and the verdict was `BUILD-MISMATCH` -
"the live frontend is NOT the build it was supposed to be" - about an artifact nobody had produced in ten
days. The check reported on its own stale input, and the report sent a reader to production.

What changed. `dist_staleness()` dates the dist against the last commit that touched the frontend sources
(`git log -1 --format=%ct -- . ':(exclude)build'` from the dist's parent) and compares that to the newest
file in the dist. A dist older than that commit is refused before any comparison: exit 2,
`CANNOT-MEASURE`, with both timestamps and the age in days, and the fix named (rebuild, or pass
`--expect-entry <hash>`). The dated pair also rides in the JSON report as `expected_build`, and the human
report prints `expected build: built … | last frontend commit … | STALE|current`.

Two boundaries, both deliberate. A dist outside a git work tree is returned undated and compared as
before - it cannot be aged, and a caller passed that path on purpose; the real invocation
(`--expect-dist agenthub-frontend/build`) is inside the work tree, so the hole this closes is the one that
was open. And the refusal is `CANNOT-MEASURE` rather than a new verdict, because the census's existing
rule is that it may not pass on input it could not read.

Measured on the defect's own shape, one fixture, one served tree: the old script exits 1 `BUILD-MISMATCH`;
the new one exits 2 naming `built 2026-10-11T… , 10.0 day(s) before the last frontend commit`. Against
the repository itself the run still cannot read a `build/` that is absent in this worktree, and says so.

Docs: `ai_docs/operations/complete-operations-guide.md` now states the refusal next to the command.
