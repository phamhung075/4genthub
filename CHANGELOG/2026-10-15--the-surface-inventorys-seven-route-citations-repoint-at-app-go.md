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
scripts/tests -q` is `2 failed, 89 passed` at `80e51824` in a clean worktree, and the same at `ddfa5f51`
(the two commits differ in no `scripts/` or `ai_docs/` byte). An earlier draft of this entry printed
`1 failed, 90 passed` for `80e51824`; that reading belongs to a worktree with this fix PRESENT BUT
UNCOMMITTED, because the clean-at-HEAD leg audits a detached export of the COMMITTED revision while
`--self-test` perturbs the worktree's own copy of the inventory. The reviewer's gate caught the
misattribution. The two failing legs have one cause. The leg that runs each instrument against a
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

## The prose the instrument cannot see, amended in the same commit

`scripts/CITATION-AUDIT.py` reads one file (`INV`) and only its **table rows** — its own docstring names
the shape it parses. Four more citations in that same file, in ordinary paragraphs, were stale by the
same movement and `--write` could not have reached them: `:84`'s four-number clause
(`:170`/`:175`/`:176`/`:180` -> `:179`/`:184`/`:185`/`:189`), `:86` (`App.Handler`, `:139`/`:140` ->
`:148`/`:149`), `:441` (`DatabaseAvailable: true`, `:71` -> `:99`) and `:563` (`:79-83` -> `:88-92`).
`:441` moved `+28` while the other three moved `+9`, so each of the four was opened in the source rather
than incremented — the whole reason `app.go:71` could not be guessed from `app.go:170`'s shift. Left
alone, `:84` would have stated the project-creation contract two ways seven lines apart in the file whose
subject is citation accuracy, which is how the reviewer's gate found them; all four keep their dated
re-resolution notes and gain a `2026-10-15` one.

`ai_docs/setup-guides/complete-setup-guide.md:559-561` carries the same four citations inside a snippet
and is repointed the same way (`:146`/`:151`/`:152-155`/`:156` -> `:179`/`:184`/`:185-186`/`:189`).

**Recorded, not fixed here:** a checker that reads table rows reports `stale 0` on a document whose prose
citations are wrong, and this file is the proof. Extending it to the prose class needs the document's own
rule at `:735` (a citation asserts what the code says now; a quotation asserts what a document said then)
turned into something a checker can apply, which is a different change from this one.

## Not in this change

No code, no route table, no test and no instrument changed — the eleven citations moved, in the two files
that carried them, and nothing else did. The census's counts and the suite's expectations are untouched.
