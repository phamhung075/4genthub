# The pin carries the one-state-root flag, and its record awaits a carrier

The hub's gitlink moves `f71becd -> 7e01b65`: the state-root lane (`5b6a615`, gated PASS as
`qitem-20261017064340-c3445d0cbde5`, 25 files +560/-60) merged over the daemon destination resolution as
`c60a38f`, plus `7e01b65`, the merge-time fix. The lane's base was cut before the log-home commit that gave
`startAuthority` the state dir, so the merge is textually clean but leaves four `StateRootFromFlags` call
sites in `internal/clientlifecycle` (doctor, agent, status, log) written against the two-value shape, and the
lane's `rootflag_test.go` hook literal with the old signature. `7e01b65` hands the parser's refusal to all
four and takes the state dir in the literal; the client's own entry gained a Landing section naming it.
At the merged tip: `go build ./...` rc 0, `go vet` and `gofmt -l` clean, `go test ./...` 32 packages rc 0.

This commit is the gitlink alone. The docs and records the room is holding - AGENTS.md section 2 at L-4 v3
(the symbol and file, no line numbers), the Outcome 2s criteria-vocabulary patch's doc halves, the
`TEST-CHANGELOG.md` sections, and the `CHANGELOG/` records the earlier pins left waiting - are refused by
the docs-only guard in a commit that changes no hub code, so they wait for the next hub code commit (which
names what it carries) or the owner's `OWNER_DOCS_COMMIT=1`.
