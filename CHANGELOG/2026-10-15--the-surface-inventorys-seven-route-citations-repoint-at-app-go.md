# The surface inventory's seven route citations repoint at `app.go`

`ai_docs/api-integration/surface-inventory.md` is the document the route census reads, and seven of its
rows cited a `fastmcp/server/httpapp/app.go` line that no longer holds that route. Measured at
`80e51824`, before the change: `python3 scripts/CITATION-AUDIT.py` printed `rows 148  stale 7
unresolved 0` and exited `1`. Every one of the seven is in the projects/health block — `/health` cited
`:142`, `POST /api/v2/projects/` `:170`, `GET /api/v2/projects/` `:183`, `GET /api/v2/projects/{id}`
`:191`, `PUT /api/v2/projects/{id}` `:199`, `DELETE /api/v2/projects/{id}` `:220`, and
`POST /api/v2/projects/{id}/health-check` `:228`. The routes themselves were never missing — the audit
reported `unresolved 0` — so this is drift, not a route that went away.

**One defect, two red legs, and the second one is the reason this was worth chasing.** `pytest
scripts/tests -q` was `1 failed, 90 passed` in a clean worktree at `80e51824` (`2 failed, 89 passed` at
`ddfa5f51`), and the two failures have the same cause. The leg that runs each instrument against a
detached export of the committed revision is red because the committed document is stale. The
`CITATION-AUDIT.py --self-test` leg is red for a subtler reason: the self-test perturbs the FIRST
citation row, which is line 76 — one of the seven — so perturbing it by `+7` leaves it exactly as stale
as it already was. The run said so itself: `perturbed the citation on line 76 by +7 -> 7 stale reported
against a baseline of 7, the perturbed row NOT named (FAIL)`. The delta the self-test asserts is real
and the instrument is sound; the document it reads was not. With the seven rows repointed the same
self-test prints `1 stale reported against a baseline of 0, the perturbed row named (PASS)`.

The fix is the instrument's own rewrite, not a hand edit: `CI= python3 scripts/CITATION-AUDIT.py
--write` repointed the seven rows (`rewrote 7 citations`), and the checker re-run afterwards printed
`rows 148  stale 0  unresolved 0` with exit `0`. The rewrite is guarded — with a gate marker set it
refuses and exits `2`, so the explicit `CI=` form is the deliberate one.

Resolved from the source, not from the tool's report: `app.go:151` is
`mux.HandleFunc("GET /health", handleHealth)`, `app.go:178` declares
`const base = "/api/v2/projects"` inside `registerProjectRoutes`, and `app.go:237` is the
`POST "+base+"/{id}/health-check"` registration. The new numbers are the registrations, which is what
the inventory's route table cites.

## Not in this change

No code, no route table, no test and no instrument changed. The seven rows moved and nothing else did;
the census's counts and the suite's expectations are untouched.
