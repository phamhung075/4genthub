## The httpapp route count is 128, and the document now carries the three rows it omitted

### What changed
`scripts/COUNTS-AUDIT.py` exited 1 at the tip: the tree registers **128** `httpapp` routes under that
instrument's own pattern while both its `EXPECTED` and `ai_docs/api-integration/surface-inventory.md`
said **125**. The decision is a measurement rather than a matching of numbers, and it says **the tree
is right: the document and the instrument were stale by three.** The three omissions, named from the
tree and each with the commit that landed it:

- `GET /api/v2/ledger` — `ledger_mount.go:39`, from `f285bdf6`
- `POST /api/v2/ledger/intents` — `ledger_mount.go:52`, from `f285bdf6`
- `POST /api/v2/tasks/{id}/evidence` — `task_routes.go:121`, from `5ab853d1`

The fourth recent move, `PUT /api/v2/rooms/{room}/seats/{seat}/pin` (`42de79c2`), was already
recorded by the document's own pass-7 narrative; the anchored figure simply never followed it.

- `ai_docs/api-integration/surface-inventory.md`: the anchored Reproduce line now reads **148**
  (httpapp 128, auth 20), measured at `3e81e1e9`, with the superseded figures kept in the same line as
  the dated history they are; §1.3 gains the evidence row and a new §1.22 carries the ledger's two
  rows — **148 rows for 148 live registrations**, which is the set join the §1 preamble describes and
  which no count can see.
- `scripts/CITATION-AUDIT.py --write` (its own documented escape from a gate marker) rewrote **17**
  stale `file:line` citations in the same document: `rows 148  stale 17 -> 0`.
- `scripts/COUNTS-AUDIT.py`: `EXPECTED["httpapp route registrations"]` 125 -> 128, with the three
  routes named in the comment beside it, per that file's own rule that a count is re-derived rather
  than repinned.

### Verified
- **Reproduction before the change:** `python3 scripts/COUNTS-AUDIT.py` -> `rc=1`,
  `httpapp route registrations   128       128` reading `doc 125 / expected 125 / tree 128` and the
  verdict `TREE has 128, this file expects 125`.
- **After:** the same table reads `doc 128  expected 128  tree 128  matches` on every row, and in a
  clean tree the command exits 0. (In a dirty tree it exits 1 by design — rule 82 — and says so.)
- `python3 scripts/COUNTS-AUDIT.py --self-test` -> **PASS**: it perturbs the row by +1 and requires the
  tree, the document and an unmatchable anchor each to go red, so the check can still fail.
- `python3 scripts/CITATION-AUDIT.py` -> `rows 148  stale 0  unresolved 0`, rc 0.
- The count per revision, measured rather than assumed: **125** at `c08a742e` and `42de79c2`, **126** at
  `6cfd56ab`, **124** at `e5ecff63`, **128** at `03e0d1a1`, `708e3131` and this branch's HEAD — so the
  certified batch is not the cause, and neither is a change of mine.

### What this does NOT do
It does not touch the code: the tree's 128 registrations are what it keeps, and no count was made to
agree by overwriting one side.

`scripts/S3-REDERIVE.py` is still red at this tip — `FRESH 46  STALE->BATCH 19`, all of them §3.1's
`models.go` anchors — and that instrument is read-only by design, so those nineteen numbers are a hand
re-derivation and belong to a row of their own. Named here rather than folded in: this row's subject is
the route count.

Row: `qitem-20261011035411-200db411c0c4e55e`.
