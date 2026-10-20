# The `activity` verb reads the state root it is given

## Fixed

`ai_docs/core-architecture/nfr-register.md` row **PORT-03** ("`--state-root` is honoured on every
verb") was PARTIAL for one verb: `4genteam activity` called `clientenv.DefaultStateRoot()`
(`internal/clientactivity/activity.go:138`) and its parser had no `--state-root` case, so a caller
pointing at another tree got this machine's own events, silently. Client commit **`a788477`** (client
`main`, base `14d1f3e`) makes the verb take the flag through `clientenv.StateRootFromFlags` and resolve
it through `clientenv.ResolveStateRoot` - the same two calls `doctor`, `ps`, `room` and the rest use.
The flag, else the machine's own root; an empty value means the default; the retired `--state-dir`
spelling is refused by the shared extractor before any record is read. Usage gains
`[--state-root DIR]`, and the package's closing line reads "Reads the state root only".

## Verified

- `go test ./internal/clientactivity/ -run StateRootFlag` -> ok. The new test
  `TestTheStateRootFlagIsReadInsteadOfTheMachineDefault` builds its fixture under a directory whose own
  basename is the room name - a room the machine default cannot carry - so it fails both on the old code
  and on any code that reads the default. Re-checked by the lead: with the parent `activity.go` restored
  under the new test it fails `want the flag honoured`; with `a788477` it passes.
- `go vet ./...` clean; `go test ./...` green (35 packages, exit 0) in the client at `a788477`.
- Reviewer PASS (`qitem-20261019195202-95af1a6a9cd4`).
- Installed binary after `scripts/build.sh`: `4genteam activity --help` lists `[--state-root DIR]`;
  `4genteam activity demo --state-root <fixture>` returns the fixture's own row (exit 0) while the same
  verb without the flag returns this machine's records - the two trees are distinguishable in output.

## Not in this change

The register row itself: the architect reseeds PORT-03 as GATE with this test as its verification. Any
other verb that ignores the flag is out of scope here; the seat's scan reports the ones that use
`StateRootFromFlags` (`doctor`, `ps`/`room` via `lifecycle`, `agent`, `idleguard`, `budget-run`,
`policy`, `continue`, `watchdog`).
