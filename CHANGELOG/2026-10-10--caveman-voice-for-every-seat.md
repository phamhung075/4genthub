## Every seat now answers in the caveman voice, from a pinned submodule

### Added
- `scripts/caveman`: git submodule of https://github.com/JuliusBrussee/caveman pinned to tag `v3.2.0` (Apache-2.0). Only its skill text is used. Its proxy and installer are not installed: the proxy sits between the agent and the model API and would also carry the DeepSeek route and the keys.
- `agenthub_go/fastmcp/seat_management/domain/seedlibrary/shared-modules/guide-common.md`: new section "Reply voice (caveman)". Chat replies follow `scripts/caveman/skills/caveman/SKILL.md`. Security warnings, irreversible actions, ordered procedures, questions, and everything persisted outside chat (code, commits, docs, CHANGELOG, task fields) stay plain full prose.
- `guides.lock.json`: both digests of `guide-common` re-recorded.

### Verified
- `go test ./fastmcp/seat_management/...` ok. The seats pick the rule up when they next install from a render, so a running seat needs a reseat.
