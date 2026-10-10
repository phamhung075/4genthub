## The context-pack purpose trim follows the engine, not Go

### Fixed
- `agenthub_go/fastmcp/seat_management/domain/contextpacks/bundle.go`: a pack's **purpose** was cut with
  `strings.TrimSpace` where the assembler this package ports calls `packEntry.purpose.trim()`
  (`bundle-assembler.ts`). **Measured against the engine over the whole BMP** — a node sweep of
  `("x"+c+"x").trim()` and a Go sweep of `strings.TrimSpace`, diffed — the two sets have 25 code points each and
  differ at exactly **two**: **U+FEFF**, which ECMAScript strips and `unicode.IsSpace` keeps, and **U+0085**,
  which `unicode.IsSpace` strips and ECMAScript keeps. Those are the same two characters `jsTrimEnd` already
  spells out for a file's trailing whitespace, so the purpose call site is the one the 2026-10-09 trimEnd fix
  did not convert: a purpose carrying a leading BOM kept it here and lost it in the assembler, and a purpose
  ending in NEL lost bytes the assembler keeps. `jsTrim` is the ECMAScript set at BOTH ends, and
  `jsTrimEnd`/`jsTrim` now share ONE predicate (`isECMAScriptSpace`) so the two ends cannot drift apart.

### Verified
- `…/bundle_test.go`: NEW `TestAssembleBundleTrimsThePurposeLikeJavaScript` — a purpose with a leading BOM and a
  trailing NEL must come out with the BOM gone and the NEL kept. The case carries its own control
  (`strings.TrimSpace(purpose) != jsTrim(purpose)` on that exact input), so a swap back to `TrimSpace` cannot
  satisfy the control and the three assertions at once. `TestAssembleBundleTrimsEndLikeJavaScript` (2026-10-09)
  still passes unchanged — the guard on the extracted predicate.
- **Falsified by reverting, in a throwaway copy** of the package (stdlib-only, so it builds standalone) with the
  call site restored to `strings.TrimSpace`: `go test -count=1 -run
  TestAssembleBundleTrimsThePurposeLikeJavaScript ./contextpacks/` **FAILS** with all three assertions —
  `bundle_test.go:149` (the purpose was not trimmed to the ECMAScript set), `:152` (the BOM survived) and `:155`
  (the trailing NEL was trimmed) — and the same case passes in the tree.
- `gofmt -l` on the two files printed nothing; `go test -count=1 ./fastmcp/seat_management/domain/contextpacks/`
  → `ok 0.002s`; `go vet ./fastmcp/seat_management/domain/contextpacks/` rc=0; `go build ./...` rc=0.
- No consumer can be affected by the byte change: a grep for the package's import path across the tree finds
  only `NEXT_GEN.md`, so nothing in `agenthub_go` imports it yet.

### Found by
- The independent parity audit of this ported package against `packages/daemon/src/domain/context-packs/`
  (context-dev, 2026-10-10; evidence and line cites in
  `seats/4genthub-min/FINDING-F2-PORT-FIDELITY-2026-10-10.md`). The audit independently reproduces the
  2026-10-09 pass's five parity findings and adds the two its closing sentence ("the rest of the algebra is
  parity-exact") does not carry: this trim call site, and the source's **post-compaction absent-recap skip**,
  which the port does NOT implement — ruled **(B)** by the lead (recorded in `NEXT_GEN.md`'s F2 status and in
  `compose.go`'s header), with **(A)** — a seat-recap predicate, a typed absence and a `Skipped` field — routed
  to the architect and O4's owner rather than taken, because it is new API surface and its justification must
  come from the consumer (O4's resume brief), not from symmetry.
