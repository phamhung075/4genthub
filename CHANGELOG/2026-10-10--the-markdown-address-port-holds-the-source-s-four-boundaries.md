## The markdown-address port holds the source's four boundaries

### Changed
- `agenthub_go/fastmcp/seat_management/domain/contextpacks/address.go`: four rules the port had taken from the
  format rather than from the source's own cases. Each is pinned by a case mirrored out of the source's suite,
  and each fails against the rules this file carried before it:
  1. **A backtick fence whose INFO STRING contains a backtick does not open a block** (`scanHeaders`). Before,
     ```` ```literal ` backticks``` ```` opened a fence: the heading after it was not a section, and the literal
     line left the section it was written in. The source's suite carries the case by name — "keeps inline
     backtick spans from swallowing later sections". The guard is scoped to the BACKTICK marker and to a CLOSED
     fence: a tilde opener's info string may contain backticks and still opens.
  2. **An empty ATX heading is still a span and a scope boundary.** The header rule now takes an OPTIONAL title
     group, and the H2 scope is carried as a TRI-STATE (`*string`: nil = no scope, a pointer to `""` = a BLANK
     scope). Before, `##`, `## ` and `##\t` were not headings at all, so the section before one never ended and
     the children after it were adopted by the previous H2.
  3. **The validator skips what is not a name.** A blank heading is a scope boundary to skip, and a child of a
     BLANK parent is skipped with it — while a child under a NAMED heading whose slug came out EMPTY stays
     flagged, parent and child both. This is not an independent judgement: it is the second half of rule 2, and
     that was MEASURED rather than reasoned — with only this skip disabled in a throwaway copy
     (`/tmp/pkgfalsify3`), `TestAnEmptyHeadingEndsTheSpanAndOwnsItsChildren` and
     `TestEmptyH1KeepsChildrenUnaddressableAndANamedH1ReleasesThem` fail on exactly the findings a clean file
     would otherwise report (`unaddressable-header` for the blank heading and for its child). The empty-slug
     case is the control: it passes with the skip disabled, so the skip is not blind.
  4. **Indentation**: one to three leading spaces are a heading, four are an indented code block, and a fence
     opened at three spaces still hides its contents. The source keeps a second test file for exactly that
     boundary; the port had no case for it.
- `…/contextpacks/compose.go` (one blank line): the `gofmt` gap `412b6b50` left behind. That commit's own
  verification line reported `gofmt -l` on `compose.go` as empty, and the measurement was taken BEFORE the
  header was added — so the file shipped unformatted (gofmt wanted one blank line removed ahead of a `Piece`
  doc comment). Attribution measured, not assumed: `compose.go` at `2b60daae` is `gofmt -l`-clean and the gap
  enters at `412b6b50`.
- `agenthub_go/NEXT_GEN.md` F2: the audit's own stated limit — "NOT compared: `address.go`'s resolution
  algorithm vs `markdown-address.ts`" — is now compared, so the F2 block records the rules instead of the limit.

### Verified
- `gofmt -l` on the package prints nothing; `go test -count=1 ./fastmcp/seat_management/domain/contextpacks/`
  → `ok`; the package's `=== RUN` count is 37 and its test functions went 7 → 12; `go vet` on the package
  rc=0; `go build ./...` rc=0.
- FALSIFIED against the PREVIOUS rules, not assumed: with `address.go` restored from `HEAD` into a throwaway
  copy and the new test file left in place, these FAIL — the backtick-in-info-string opener, the empty
  heading, the empty H1/H4 scope, and the indentation boundary. The fifth (the empty-slug contrast) passes on
  the old rules by construction; that is its job.

### Found by
- The same independent parity audit that produced `412b6b50`, whose own limits section named this comparison as
  NOT done (`seats/4genthub-min/FINDING-F2-PORT-FIDELITY-2026-10-10.md`, addendum 19:17Z). The comparison basis
  is the source's CASES rather than a reading of CommonMark: source `…/daemon/src/domain/markdown-address.ts`
  `3cbe44d27d229277…`, `test/markdown-address.test.ts` `d133afbf3980b9a4…`,
  `test/markdown-address-indentation.test.ts` `13aaf18ab957a3c3…`, all three clean at `openrig` `1a05af1b`;
  port `address.go` `5dd7766f7fd2e6c2…` and `address_test.go` `afeab7e8aaaa879d…` at `4genthub` `f99d10eb`.
