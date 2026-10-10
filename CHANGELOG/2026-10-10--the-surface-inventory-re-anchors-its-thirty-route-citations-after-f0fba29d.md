## The surface inventory re-anchors its thirty route citations after the notify-ingress fix moved `routes_mount.go`

### Changed

- `ai_docs/api-integration/surface-inventory.md` — all thirty `file:line` citations in the route
  tables re-resolved against HEAD. **30 insertions / 30 deletions**, every pair differing in nothing
  but the line number: `f0fba29d` is the only commit between `d6c345e5` and HEAD that touches
  `agenthub_go/fastmcp/server/httpapp/routes_mount.go` (`+15/-17`, net −2 lines), so every citation
  below the change shifted by 2 to 6 — `tokens/{token_id}/rotate` `404 -> 402`, `broadcast/notify`
  `211 -> 206`, and the other twenty-eight in the same table.
- **No code change.** The code is the source of truth and the document is the pointer that follows
  it; no Go file, and nothing under `scripts/`, was touched.
- Re-anchored with the audit's own writer rather than by hand:
  `CI= python3 scripts/CITATION-AUDIT.py --write`. The tool refuses while a gate marker is set
  (`CI`, `PRE_COMMIT_*`) and every agent shell in this fleet carries `CI=true`, so the deliberate
  form is the tool's own documented one.

### Why this was red, and what proves it was

`python3 scripts/CITATION-AUDIT.py` → **rc 1 before** (`rows 144 stale 30 unresolved 0`), **rc 0 after**
(`rows 144 stale 0 unresolved 0`); `--write` → rc 0, "rewrote 30 citations". The stale document was
clean and committed in the worktree (md5 `23a7b1f02818f40330adf4529b880289` before, identical to
`HEAD:`), so no seat's uncommitted edit was involved.

The instrument was proven able to see drift **before** its green was trusted:
`python3 scripts/CITATION-AUDIT.py --self-test` → rc 0, "perturbed the citation on line 62 by +7 ->
31 stale reported against a baseline of 30, the perturbed row named (PASS)". A green audit from a
reader that cannot see drift would prove nothing.

### Testing

- `python3 -m pytest --noconftest -p no:cacheprovider scripts/tests -q` → **82 passed, 0 failed**
  (3 warnings, 10.44s). At `f0fba29d` the same suite was **1 failed / 81 passed** — the reviewer's
  reading, filed in row `cb39c88e`; the precondition is measured above, since
  `scripts/tests/test_census_audits.py` requires this audit to exit 0 and it exited 1.
- The document itself is the only changed path in the commit; the two pin-conditional doc edits this
  seat holds (`README.md:149`, `agenthub_go/NEXT_GEN.md:241`) were left uncommitted, as ordered.

### Method note

A `git log --name-only -- <path>` cannot tell you what a commit touched: the pathspec filters the
*displayed* file list, so the equivalent earlier commit `d6c345e5` appears to have changed only the
inventory when it also carried its own `CHANGELOG/` entry. `git show --stat <hash>` with **no**
pathspec is the instrument that answers that question — this note exists because that trap was hit
while preparing this change.
