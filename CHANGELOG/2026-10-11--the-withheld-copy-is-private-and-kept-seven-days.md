## The withheld copy is private and kept seven days: the coverage the rigd gate named

`GATE-39e51529-rigd-phase1-go-half` named a coverage gap, and it got its own row
(`qitem-20261010234730`): nothing asserted that the raw event rigd keeps locally once it is withheld is
protected, or that it is dropped after its window. The route through the code is
`<seat store>/rigd-withheld/<session>/<ts>.json`, written by `writeWithheld`
(`agenthub_client/internal/clientsync/rigd.go`) with mode 0600 under a 0700 directory, and pruned by
`pruneWithheld` on the write path against `withheldKeepDays`. Both properties were implemented, and neither was
tested — the existing case checked that the directory was not empty and stopped there.

`agenthub_client` at **36f455e** adds `TestTheWithheldCopyIsPrivateAndKeptSevenDays`: the file's mode, the
directory's mode, and the window measured an hour either side of it, named in the writer's own timestamp shape
so that age decides and the name does not.

Two things belong in the parent's record rather than only in the client's changelog:

- **It is a coverage test, so there is no RED state — and I said so rather than manufacturing one.** Both
  halves were induced to fail by mutating the production lines and reverting them: mode to `0o644` →
  `the withheld copy is mode 0644, want 0600: the raw event must not be readable by anyone else`; the cutoff
  comparison reversed → `a copy an hour past 7 days survived the write path` and `a copy an hour inside 7 days
  was pruned`. `git diff` on `rigd.go` afterwards is empty. An assertion nobody has seen fail is an assertion
  nobody knows bites, and this was the honest way to show it for behaviour that was already correct.
- **The cutoff instant is deliberately not asserted.** It is computed from `d.Now()`, so pinning it to the
  nanosecond would fail on a clock change rather than on a behaviour change. An hour either side fails the same
  way if the comparison is ever reversed.

Verified by the seat that committed it: `gofmt -l` empty on both files; `go build ./...` rc 0; the case ok; the
whole `internal/clientsync` package ok 1.139s.
