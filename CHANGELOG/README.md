# CHANGELOG

One file per change: `CHANGELOG/<YYYY-MM-DD>--<kebab-case-title>.md` (ascii, title at most about 80 characters; on a name clash add `-2`).
A file starts with `## <title>`, then Keep a Changelog subsections (`### Added`, `### Changed`, `### Fixed`, ...) with file paths, impact and testing.
To record a change, add ONE new file; never edit another change's file and never read the whole directory (about 250 files, 1 MB). List the newest with `ls CHANGELOG | tail`.
Entries from before the split are in the same format; the old `## [0.0.x]` releases are the `2025-09-*` files, and the old `## [Unreleased]` block is split by its `###` sections (its first bullet is the title).
Frontend-only changes stay in `agenthub-frontend/CHANGELOG.md`; test-suite changes in `TEST-CHANGELOG.md`.

Newest 30 at the time of the split (2026-10-10):

| Date | Title | File |
|---|---|---|
| 2026-10-10 | Every seat now answers in the caveman voice, from a pinned submodule | `2026-10-10--caveman-voice-for-every-seat.md` |
| 2026-10-10 | Release `0.0.30` — the deploy marker, because production already reports `0.0.29` | `2026-10-10--release-0-0-30-the-deploy-marker-because-production-already-reports-0-0-29.md` |
| 2026-10-10 | The seat chat window's POST was answered 405, so the route is mounted and refuses in words | `2026-10-10--the-seat-chat-window-s-post-was-answered-405-so-the-route-is-mounted-and.md` |
| 2026-10-10 | The readiness report still listed an environment variable Go stopped reading | `2026-10-10--the-readiness-report-still-listed-an-environment-variable-go-stopped-reading.md` |
| 2026-10-10 | fastmcp/server/cache was the sibling nobody imported, so it goes with the server package | `2026-10-10--fastmcp-server-cache-was-the-sibling-nobody-imported-so-it-goes-with-the-server.md` |
| 2026-10-10 | The Go bridge reported no topology edges, so a room reported by it drew no graph | `2026-10-10--the-go-bridge-reported-no-topology-edges-so-a-room-reported-by-it-drew-no-graph.md` |
| 2026-10-10 | The seat guide carries the owner's docs rule, and the lock records the new text | `2026-10-10--the-seat-guide-carries-the-owner-s-docs-rule-and-the-lock-records-the-new-text.md` |
| 2026-10-10 | NEXT_GEN's D3 box claimed no human-notification path existed, and the dashboard-push consu | `2026-10-10--next-gen-s-d3-box-claimed-no-human-notification-path-existed-and-the-dashboard.md` |
| 2026-10-10 | The Go bridge named the pinned hash with the Python's old field name, so every report was  | `2026-10-10--the-go-bridge-named-the-pinned-hash-with-the-python-s-old-field-name-so-every.md` |
| 2026-10-10 | Anyone could forge a notification for any user through POST /api/v2/broadcast/notify | `2026-10-10--anyone-could-forge-a-notification-for-any-user-through-post-api-v2-broadcast.md` |
| 2026-10-10 | Unreleased — ai_docs cut from 57 files to 21 | `2026-10-10--unreleased-ai-docs-cut-from-57-files-to-21.md` |
| 2026-10-10 | fastmcp/server was a server nothing could reach, and the tree kept compiling it | `2026-10-10--fastmcp-server-was-a-server-nothing-could-reach-and-the-tree-kept-compiling-it.md` |
| 2026-10-10 | The three facade factories blamed a Python port that already exists | `2026-10-10--the-three-facade-factories-blamed-a-python-port-that-already-exists.md` |
| 2026-10-10 | The cloud's copy of a room's module text can lag the repo, and a resolved hash does not sa | `2026-10-10--the-cloud-s-copy-of-a-room-s-module-text-can-lag-the-repo-and-a-resolved-hash.md` |
| 2026-10-10 | The frontend deploy could not tell which build was live; now it fails on a stale one | `2026-10-10--the-frontend-deploy-could-not-tell-which-build-was-live-now-it-fails-on-a-stale.md` |
| 2026-10-10 | The served frontend is checkable in one command, and the two measures that made the old ce | `2026-10-10--the-served-frontend-is-checkable-in-one-command-and-the-two-measures-that-made.md` |
| 2026-10-10 | Two live pages and a pointer table stopped teaching the retired seat-guide directory | `2026-10-10--two-live-pages-and-a-pointer-table-stopped-teaching-the-retired-seat-guide.md` |
| 2026-10-10 | Unreleased — the bridge reports topology edges | `2026-10-10--unreleased-the-bridge-reports-topology-edges.md` |
| 2026-10-10 | Unreleased — CI for the Go server and the frontend | `2026-10-10--unreleased-ci-for-the-go-server-and-the-frontend.md` |
| 2026-10-10 | The eleven seat-guide copies are gone, and the guard that says so is the lock's own record | `2026-10-10--the-eleven-seat-guide-copies-are-gone-and-the-guard-that-says-so-is-the-lock-s.md` |
| 2026-10-10 | Release `0.0.29` — the deploy marker, because production already reports `0.0.28` | `2026-10-10--release-0-0-29-the-deploy-marker-because-production-already-reports-0-0-28.md` |
| 2026-10-10 | The room's own note taught a company overlay that `team.json` leaves empty (row `2458e090` | `2026-10-10--the-room-s-own-note-taught-a-company-overlay-that-team-json-leaves-empty-row.md` |
| 2026-10-10 | The G2 status paragraph contradicted its own AT HEAD block about which directory the probe | `2026-10-10--the-g2-status-paragraph-contradicted-its-own-at-head-block-about-which.md` |
| 2026-10-10 | The last four `openrig_seat_sync.py` mentions in the Python client now name the module and | `2026-10-10--the-last-four-openrig-seat-sync-py-mentions-in-the-python-client-now-name-the.md` |
| 2026-10-10 | The runtime-switch playbook told the next kickoff to deny omp seats the MCP tools they now | `2026-10-10--the-runtime-switch-playbook-told-the-next-kickoff-to-deny-omp-seats-the-mcp.md` |
| 2026-10-09 | The port-claim sweep: 135 claim lines and 65 false ones, and the gate's 59 is the two-word | `2026-10-09--the-port-claim-sweep-135-claim-lines-and-65-false-ones-and-the-gate-s-59-is-the.md` |
| 2026-10-09 | The artefact gate now compares the served payload, and the stale-text hole is closed (row  | `2026-10-09--the-artefact-gate-now-compares-the-served-payload-and-the-stale-text-hole-is.md` |
| 2026-10-09 | Both recorded digests of a mirrored skill are read, not just the source's: 2 of the 54 sid | `2026-10-09--both-recorded-digests-of-a-mirrored-skill-are-read-not-just-the-source-s-2-of.md` |
| 2026-10-09 | The seat context that names the allowed root files stops naming one that was renamed | `2026-10-09--the-seat-context-that-names-the-allowed-root-files-stops-naming-one-that-was.md` |
| 2026-10-09 | The clause family closes at five: the reader's shape and this seat's own, and the 441 disc | `2026-10-09--the-clause-family-closes-at-five-the-reader-s-shape-and-this-seat-s-own-and-the.md` |

**Project**: agenthub AI Agent Orchestration Platform. Clean code (DRY, SOLID, single source of truth), ORM = truth source, no backward compatibility in the dev phase. Documentation lives in `ai_docs/`.
