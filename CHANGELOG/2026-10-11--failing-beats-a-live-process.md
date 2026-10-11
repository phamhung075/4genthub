## `failing` beats a live process: the client half, and the pointer at e28ca30

The rigd slice's reviewer left one substantive minor (m1) at the gate
(`GATE-39e51529-rigd-phase1-go-half-2026-10-11.md`): `verifyRow` never surfaced `failing` while a
crash-looping child was momentarily alive. This is the parent's record of the client commit that fixes it.

### What the client now does — `agenthub_client` at **e28ca30**

`internal/clientservices/services.go` (`verifyRow`): the recorded-failing check now sits ahead of the liveness
switch. The architect ruled the precedence on 2026-10-11 as **stopped -> failing -> silent -> running**, and
the ruling's substance is that `failing` beats a live process: rigd counted the deaths inside its window, and
a fresh heartbeat does not undo a crash loop. Before this, a crash-looping child read `running` for the whole
interval in which its heartbeat was fresh — which means §7.5's exit condition ("every row is `running`")
could be met while the row was in fact being retried at the cap. The dead-process branch is untouched: a
dead-and-failing row still reads `failing`, a dead row with no recorded failure still reads `stopped`.

The ruling document was already in main while the code did not match it, which is the defect class worth
naming: a doc in main that the code contradicts is a disagreement somebody will believe.

### Tests, and the retired expectation

`internal/clientservices/services_test.go`: the second half of `TestFailingIsDecidableOnlyByRigd` asserted the
retiring reading — a live, beating child is `running` even while rigd records it as having failed. That
expectation was **retired with the ruling that changed the semantics**, not re-pinned to keep a green run, and
now asserts `failing` with the restart count kept. Recorded rather than quietly swapped, because a test that
pins a superseded interpretation is a decision someone made, and its reversal should be visible.

RED FIRST, quoted from the seat's run before the fix: `services_test.go:215: row = {Rig:demo Safeguard:compact
State:running PID:77 StartedAt:2026-10-11T11:00:00Z Restarts:3 LastBeatAt:2026-10-11T11:59:59Z AgeS:1}, want
failing: rigd counted the deaths, and failing beats a live process`.

### Verified, by the seat that committed it

`gofmt -l` on both files printed nothing; `go build ./...` rc 0; the ruled case `ok`; the whole
`internal/clientservices` package `ok`. The client's own `CHANGELOG.md` carries the same entry at source.
