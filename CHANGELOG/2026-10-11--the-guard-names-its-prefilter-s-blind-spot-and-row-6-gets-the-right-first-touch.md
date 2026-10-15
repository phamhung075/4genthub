## The guard names its prefilter's blind spot, its census now says which tree it measured, and row 6 carries the right first touch

### The three findings, each from a gate, each re-verified before it was applied

1. **`GATE-f31062ae` nit 1 — the guard's own first instruction was the blind spot it did not list.** The
   "WHAT IT CANNOT SEE" block named three ways a call can escape; it did not name the one the scan creates
   itself. The prefilter is `bytes.Contains(source, []byte("CreateTables("))`, so the identifier and its
   opening parenthesis must be ADJACENT in the raw bytes, and `cfg.CreateTables (ctx)` or a newline between
   the two never reaches the AST pass at all.
2. **`GATE-f31062ae` nit 2 — the census described a tree, not the commit.** The block's "3120 _test.go files
   with 2631 of them under .gomodcache/.gocache/.gotmp/.claude" is a property of the SHARED CHECKOUT the
   count was taken in: a clean worktree of the same commit measures 490 `_test.go` files and none of them
   under those directories, so the pair could not be cross-checked from a checkout.
3. **`GATE-95966bd` minor — §4.8 row 6 named the wrong first touch.** `internal/clientevidence/evidence.go`
   was ADDED by `63fd184` ("feat(client): 4genteam evidence, the client half of O3"); `a98e78b` only MODIFIES
   it, and `63fd184` is an ancestor of `a98e78b`, so it is not a rebase artifact. Under the section's own
   rule - the column is the first touch of the file that carries the item - the row was wrong.

### The change

Comment and documentation only. No rule, no assertion and no behaviour changed; the guard's allowlist, its
predicate and its three call sites are untouched.

- `agenthub_go/fastmcp/task_management/infrastructure/database/create_tables_guard_test.go` gains a fourth
  blind spot. It states the prefilter is an optimization and NOT the rule, both consequences in opposite
  directions - an unlisted call in such a file is not reported, and an allowlist entry for that file's
  function would read as STALE because the scan never recorded the call the entry names - and what still
  defeats it: a split after the dot, or a receiver on its own line, is caught, because only the
  name-to-parenthesis adjacency is what the prefilter sees.
- The census bullet now says which tree its numbers came from and gives the clean-worktree measurement;
  the number that IS reproducible is the one the guard reports on every run, which it prints with the tree
  it walked.
- `ai_docs/operations/client-features-for-the-dev-team.md` §4.8 row 6 names `63fd184` as the file's first
  touch and keeps `a98e78b` as the commit that landed the item. **The section's preamble was not weakened**:
  the five sibling rows satisfy it as written.

### Verified

- `gofmt -l fastmcp/task_management/infrastructure/database/create_tables_guard_test.go` - empty.
- `go test -count=1 -v -run TestFixturesBringUpTheSchemaThroughCreateSchema ./fastmcp/task_management/infrastructure/database/` -
  PASS, and the run states its own scope: `walked 490 _test.go file(s) under
  /home/daihu/__projects__/4genthub/agenthub_go (dot-directories skipped), 4 of them naming CreateTables,
  and found 3 call site(s) in 3 file(s)`. The guard needs no database, which is why the fix could be checked
  at all.
- `go vet ./fastmcp/task_management/infrastructure/database/` - rc 0.
- Row 6's provenance re-measured rather than relayed: `git log --diff-filter=A -- internal/clientevidence/evidence.go`
  = `63fd184`, `git log -S printDoneReport` = `a98e78b`, and `git merge-base --is-ancestor 63fd184 a98e78b`
  = rc 0.

### Found by

`GATE-f31062ae` (nits 1 and 2) and `GATE-95966bd` (the §4.8 minor), routed to go-dev as
`qitem-20261011210150-edde4ff2e1a56bb6` with the lead having verified all three first.
