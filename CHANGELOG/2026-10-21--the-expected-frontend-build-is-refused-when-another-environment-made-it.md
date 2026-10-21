# The expected frontend build is refused when another environment made it

`scripts/check_served_frontend.py --expect-dist` turned a build's entry hash into a verdict: the served
entry chunk must be the built entry chunk. That holds only when both were built the same way, which they
cannot be here. The deploy builds `docker-system/docker/Dockerfile.frontend.production` (node:20-alpine,
arm64) from the `frontend` branch, while a seat or CI build is a different node, a different arch and a
different `VITE_*` set - and `agenthub-frontend/src/config/environment.ts:32` reads
`import.meta.env[key]` dynamically, so vite inlines the whole env object and re-hashes every chunk that
carries it. Measured 2026-10-21 on the served entry and the dist in this worktree: 30 inlined keys
against 6, entry `index-CulHwbQI.js` against `index-B3lTv8BO.js`, and CI (node 22/x64) produced
`index-BaT1A8I-.js` three times that day from the same tree. A fresh local build therefore prints
`BUILD-MISMATCH` against a correct deploy, and the `local-frontend-build` guard means a seat cannot even
produce one to argue with.

What changed. `env_object()`/`env_signature()` read the environment object out of both entry chunks -
brace-matched from `{BASE_URL:"` so a value's own braces cannot cut it short - and `env_comparison()`
decides whether the two hashes are comparable at all, naming keys only in the build, keys only in the
served entry, and keys whose values differ. `dist_expectation()` now also returns the built entry's text.
In `main()` the comparison runs BEFORE identity: when the environments differ the verdict is the new
`FOREIGN-ENV` (exit 2, a refusal like the staleness rule - the census may not pass or fail on input it
could not read), the identity block is not emitted at all, and the JSON carries `environment` instead.
`identity_check` and its callers are untouched when the environments agree.

Four boundaries, deliberate. Neither side inlining an object means the build does not read the env
dynamically, so the hash is environment-independent and the comparison proceeds exactly as before - this
is why every pre-existing identity test still means what it did. Exactly one side inlining it is a
different build shape and also refuses. And a differing VALUE refuses as well, not just a differing key
set: an API URL the deploy does not use re-hashes the chunks that carry it. The fourth: only an object that was READ
may refuse: when the served entry did not arrive, comparability is left alone and the closure reports itself
as incomplete rather than naming a foreign environment.

Measured. `python3 -m pytest scripts/tests/test_check_served_frontend.py -q` 24 passed (19 existing, 5
new); the whole `scripts/tests` tree 140 passed in a full checkout - a worktree without the nested
`agenthub_client` checkout, as the reviewer's gate worktree was, reports 14 unrelated
`test_doc_citations.py` failures there on any base, and the delta from 460b715a to this commit is exactly
the +5 new rows. Against the live origin with an undated copy of this worktree's dist: exit 2, `FOREIGN-ENV`,
`build inlined 6 key(s), served 30`, 24 keys listed as served-only, and no `BUILD-MISMATCH`; the JSON
report has `environment.comparable false` and no `identity` key. Against
`--expect-dist agenthub-frontend/build` from this worktree the earlier staleness rule still answers first
(built 2026-10-15, 5.1 days before the last frontend commit) - the two refusals are independent gates and
the older one wins because it is checked before the fetch. Default mode still reads `OK`.

Docs: `ai_docs/operations/complete-operations-guide.md` said "the same hash in a local build of HEAD
proves the live app IS that build", which is the false premise this closes; it now says identity needs a
build the deploy image made, states the `FOREIGN-ENV` refusal, and names the build-free alternative
(source-tree diff plus served markers).
