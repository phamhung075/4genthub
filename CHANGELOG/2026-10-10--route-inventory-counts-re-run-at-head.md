## The route-inventory counts re-run at HEAD: 144 = 124 httpapp + 20 auth, and coverage held

### Changed
- `ai_docs/api-integration/surface-inventory.md` — the reproduce block beside the registration count now carries today's re-run: the same command returns the same
  **144** (`httpapp` 124, `auth` 20) at HEAD, and `go run ./cmd/apirefgen` independently wrote `144 routes, 10 tools`.

### Verified
- Coverage, measured rather than asserted: every one of the tree's 124 `httpapp` registrations (the document's own command, `_test.go` excluded) carries a citation
  in §1 **within three lines**, so **no route is unlisted**; the 143 the older snapshot records is the dated reading at `257a4ab1`/`62b734ec`, not a missing row.
- The check is **coverage only** — the row-by-row re-resolution was not re-run, and the edit says so in those words.
