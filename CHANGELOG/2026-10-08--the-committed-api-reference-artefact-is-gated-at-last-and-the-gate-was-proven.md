## The committed API-reference artefact is gated at last, and the gate was proven red before it was trusted

- **The gap, measured:** `agenthub-frontend/src/docs/apiReference.ts` is consumed by the page, and **no code
  path opened it** — the only mentions of the filename were the writer's default (`cmd/apirefgen/main.go:33`), a
  comment in `reference.go`, and `reference_test.go:103`, which renders into `t.TempDir()`. The drift witness in
  `docs_page_drift_test.go` is a real check, but **both of its sides come from the code** — its own walk of the
  mount files against `apiref.Entries`, the producer — so it proves the producer agrees with an independent
  extractor and **cannot see whether the file on disk matches either**. A stale artefact would have been served
  with every test green. The renderer's own comment predicted this check (*"if this file and the code disagree,
  the artefact is wrong rather than the test"*) and the page note asserted `reference_test.go` performed it: the
  intent existed and the instrument did not.
- **The gate:** `internal/apiref/committed_artefact_test.go` reads the real file, parses the renderer's own
  envelope, and compares **both directions** against `apiref.Entries` — a registered route absent from the
  artefact, and an artefact route registered nowhere — with the same two directions for tools.
- **STRUCTURAL, NEVER TEXTUAL, which is the trap the page note records:** the comparison is entry-by-entry on the
  method and the path exactly as written, so `{$}` is never rewritten into a parameter (it is Go's end-anchor for
  a trailing slash) and an absorbed literal segment is never mistaken for a missing route. A substring gate would
  have been red on correct code and would have been disabled rather than fixed.
- **PROVEN RED, THEN GREEN:** removing one registered route from the artefact turned the gate red naming exactly
  that route — *"DIRECTION 1 FAILS: 1 route(s) are registered in the code and absent from the committed
  artefact … POST /api/auth/dev-login"* — and restoring it returned the artefact to its exact bytes
  (`sha256 7be90f01…` before and after, `git status` clean for the file), with the gate green.
- **AND THE GATE'S OWN PROOF NEEDS NO SCRATCH COPY:** `TestTheArtefactGateCanFailBothWays` perturbs the PARSED
  reference, so both directions are shown failing without editing the tree — the rule the witness header states:
  a check is only a check once each direction has been seen failing.
- Files: `internal/apiref/committed_artefact_test.go`, `CHANGELOG.md`, `TEST-CHANGELOG.md`. **The artefact itself
  is UNCHANGED**: the gate was written against the tree as it stands and passes on it.
