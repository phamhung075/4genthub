## The G2 status paragraph contradicted its own AT HEAD block about which directory the probes look for

### Fixed
- **`ai_docs/core-architecture/agenthub-system-architecture.md:467`** — the "Status — re-verified 2026-10-09 (writer seat)" paragraph still asserted **"G2's code sites are still live and still key the answer on the tree: `…/subtask_repository_factory.go:58,65` probes for an `agenthub_main` directory at runtime"**, four lines above the AT HEAD bullet at `:472` that records `d1114170` re-keying exactly those sites and says "the sentence above is no longer true" — so one page carried a false claim about the tree beside its own refutation, on a gate document the owner reads. The clause is corrected in place and dated: the probe is stated as what it **was** when the paragraph was written, `d1114170` is named beside it, and the original wording is kept **inside the quotation that marks it as the earlier reading** rather than rewritten away, which is the shape this document's own AT HEAD rule prescribes. No Go file is in the commit; the code was already correct.

### Verified
- **Re-measured at the tip, not quoted from the reviewer's reading** (`G1-G6-EVIDENCE-2026-10-10.md` §G2, taken at `15693b6a`): `git show HEAD:agenthub_go/fastmcp/task_management/infrastructure/repositories/subtask_repository_factory.go | grep -n 'agenthub_go\|agenthub_main'` → **five lines, `:58`, `:65`, `:70`, `:79`, `:84`, every one naming `agenthub_go`, none naming `agenthub_main`**, rc 0; read at `5871152b` (the then-tip) and re-checked at `f9886cbe` (the tip before it landed, the file unchanged between them).
- **Both halves of the contradiction are measurable, and the second is what makes this a correction rather than a deletion:** over the document, `grep -c 'probes for an `agenthub_main` directory at runtime'` → **0** (the asserting form is gone) while `grep -n 'still live and still key the answer on the tree'` → **1**, and that single hit sits inside `this clause read "…"` — the wording survives only as the dated reading it was.
- Docs only: `git show --numstat` names the document and `CHANGELOG.md`.

### Found by
- The reviewer's G1–G6 pass (row `1d3ea1bd`), whose measurement is the evidence; re-derived here against the tip rather than accepted from the earlier base.
