## The F2 port records the two divergences it carried silently

### Changed
- `agenthub_go/fastmcp/seat_management/domain/contextpacks/compose.go` HEADER (comment only): the sentence
  "Every failure is LOUD and names the atom" now reads "— WITH THE TWO RECORDED EXCEPTIONS BELOW", and a block
  records both. **(1)** The source's ONE exception to a loud compose — a POST-COMPACTION compose SKIPS a
  genuinely absent seat recap and reports it in `skipped`, because a compacted seat still has its restore map,
  while a HANDOVER successor's missing recap still fails (`profile-composer.ts:22`-24, the catch at `:122`-130) —
  is **not implemented here**: the port refuses every unreadable atom instead. It is not mechanically portable,
  and the reason is in the file: the source's predicate needs an address SCHEME (`seat:RECAP.md`) and a typed
  `SourceAbsentError`, while this port's refs are untyped by the B2 decision ("the caller's resolver owns what it
  names"), so the fact has to come from the caller. **Ruling (A)** — a seat-recap predicate, a typed absence and
  a `Skipped` field — is ROUTED to the architect and O4's owner, not taken: it is new API surface, and its
  requirement must come from the consumer that needs it (O4's resume brief) rather than from symmetry. **(2)**
  The `order` tiebreak is byte-wise (`walk[i].ID < walk[j].ID`) where the source uses `x.id.localeCompare(y.id)`;
  both are deterministic, and only non-ASCII ids can order differently.
- `agenthub_go/NEXT_GEN.md` F2 status: the same two divergences with the same line cites, plus one sentence
  against the earlier audit — the 2026-10-09 whole-package parity pass closes with "the rest of the algebra is
  parity-exact" while its own list omits the skip rule, which is that sentence's counter-example.

### Verified
- Comment-and-documentation only — no behaviour changes — so the evidence is that the file still compiles and its
  cases still pass: `go test -count=1 ./fastmcp/seat_management/domain/contextpacks/` → `ok`; `gofmt -l` on
  `compose.go` printed nothing; `go vet ./fastmcp/seat_management/domain/contextpacks/` rc=0; `go build ./...`
  rc=0.

### Found by
- The lead's ruling **(B)** of 2026-10-10, taken on the independent parity audit
  (`seats/4genthub-min/FINDING-F2-PORT-FIDELITY-2026-10-10.md`, by context-dev): the omission must be written
  down wherever the port's completeness is claimed, because a header that says every failure is loud while one
  rule is silent is exactly the class this room is removing. The audit's own method: the source read rule by
  rule at a pinned revision against the port at a pinned revision, digests recorded on both sides.
