## The twelve `### 1.x` header citations resolved: three repaired, five exact, four left with the reason

### Changed
- `ai_docs/api-integration/surface-inventory.md` — the header-line citations, which the §1 preamble
  lists as outside both instruments, were resolved one at a time. **Repaired:** §1.13
  `routes_mount.go:211 → :262` and §1.14 `:310 → :361` (each to the `const base = …` line of its own
  section — the convention §1.9–§1.11 already follow), and §1.15 `:389 → :440`, the
  `func mountTaskSummaryRoutes(…)` whose registrations are the rows the section lists (`:442`–`:475`);
  `:389` was a `}))` closing a *token* handler, so it named the wrong family.
- **Left as they are, with the reason in the document:** §1.2 `branch_routes.go:59`, §1.3
  `task_routes.go:48`, §1.4 `subtask_routes.go:12`, §1.5 `session_stream_routes.go:12` — each points
  into a handler body in the file the header names, and no section states what that line should
  designate, so changing it would be a guess rather than a repair.

### Verified
- Every target read before it was written: `routes_mount.go:262` is `const base = "/api/v2/contexts"`
  and `:361` is `const base = "/api/v2/tokens"`; `:440` is `func mountTaskSummaryRoutes(mux
  *http.ServeMux, deps routeDeps)` and the section's own five rows cite `:442`–`:475`, inside it.
- Five were already exact and were not touched: §1.9/§1.10/§1.11 (`const base`) and §1.18/§1.19
  (`RegisterRoutes`).
- After the edit: `S3-REDERIVE.py` `FRESH 66` rc=0, `COUNTS-AUDIT.py` rc=0, `CITATION-AUDIT.py`
  `rows 145 stale 0 unresolved 0` rc=0.

Seat: 4genthub-min-writer@4genthub-min
