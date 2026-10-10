## The plain assembler's missing entries carry their path, as the source pins them

### Changed
- `agenthub_go/fastmcp/seat_management/domain/contextpacks/bundle.go` — `AssemblePlainFiles` reported a
  skipped member as a bare `string` in `PlainFileAssembly.MissingFiles`, while the source it ports reports
  `{ path }` objects. New `PlainFileRef{Path string}`, and the field is now `[]PlainFileRef`.
- The entry type was found by **mirroring the source's own cases**, not by re-reading the port: openrig
  `1a05af1b`, `packages/daemon/test/context-pack-compose.test.ts:54-61` asserts
  `expect(result.missingFiles).toEqual([{ path: "absent.md" }])`. Against the port as it stood
  (`bundle.go` `f28c216d`), that assertion **did not compile**: `got.MissingFiles[0].Path undefined (type
  string has no field or method Path)` (/tmp/f2falsify-2). It is the only divergence in the two layers the
  2026-10-10 parity audit had left uncompared.
- Also landed: the source's cases as permanent cases. `bundle_test.go` gains the EOF-newline byte matrix
  (four combinations, unframed, `bytes` = the join's byte length), the missing-entry path case, the
  token-estimate-from-assembled-bytes case, the trimmed-purpose-keeps-its-line-breaks case, and the
  empty-pack case (empty, non-nil lists). `refsafety_test.go` gains the source's literal accepts and
  rejects — `packs/..`, `.`, `packs/.hidden`, `packs/na\tme`, `packs/` + 65 chars, `v1_2+build`, `1:0:0`,
  `@1.0`, a 300-char version. `TestAssembleBundleFramesAndSkipsMissing` now also pins a summary-less
  header, `bytes == len(text)`, the missing entry's **role**, and the trim at the join (which is where an
  untrimmed content is observable).
- `agenthub_go/NEXT_GEN.md` — the F2 block's divergence record and audit limits updated: the two layers
  the audit's limits note named as uncompared are now closed, one divergence found.

### Verified
- **Falsified, then fixed, in throwaway copies (the audit's method — the source's cases run against the
  package unedited first):** copy 1, the eight parity tests against the unedited package → **all PASS**
  (`ok f2falsify/contextpacks 0.003s`), so ref-safety and the bundle frame are parity-exact on every case
  the source pins. Copy 2, the source's own missing-entry assertion against the unedited package →
  **build failed**, `.Path undefined (type string has no field or method Path)`. Copy 3, the same nine
  tests against the fixed package → **all PASS** (`ok 0.005s`).
- In the tree: `gofmt -l fastmcp/seat_management/domain/contextpacks/` prints nothing;
  `go vet ./fastmcp/seat_management/domain/contextpacks/` rc=0;
  `go test -count=1 ./fastmcp/seat_management/domain/contextpacks/` → `ok 0.004s`, 46 passing cases.
- Not checked, and not claimed: no importer of the package exists yet (`grep -rn "domain/contextpacks"`),
  so the shape change reaches no consumer; the wiring line remains the lead's to serialize (F2's status
  stays PORTED, NOT WIRED).

Seat: 4genthub-min-context-dev@4genthub-min
