# `seat reseat` reads the state root it is given

Client `c46812c` on client main (pin bumped in the same commit).

## Changed

- `internal/clientseat/reseat.go`: `4genteam seat reseat` takes `--state-root DIR` through
  `clientenv.StateRootFromFlags` and resolves it through `clientenv.ResolveStateRoot`, the same two
  calls every other flag-taking verb uses, instead of calling `ResolveStateRoot("")` after a FlagSet
  that knew only `--seat` and `--force`. Before this, passing the flag was refused by the parser and
  the machine's default root was read regardless of what the caller asked for.
- `defaultReseatDeps` is reached through the package-level `reseatDepsFor` seam, so the test asserts
  the root the verb hands the waiter and the seat doctor, not only that the parser accepts it.
- The commit's changelog classifies the remaining `ResolveStateRoot("")` / `DefaultStateRoot()` sites
  in `internal/` (compact, the agent supervisor's scans, a skillscheck fallback, `RoomDir`, tmux argv,
  a seatpark seam, and the default branch inside `ResolveStateRoot` itself): none of them is a
  flag-taking verb that drops the flag.

## Tested

- `go test ./internal/clientseat/ -run Reseat -count=1` -> ok; the lead re-ran it at `c46812c`
  (`TestReseatReadsTheStateRootFlagInsteadOfTheMachineDefault` PASS, 0.00s), `gofmt -l` empty and
  `go vet ./internal/clientseat/` clean.
- Reviewer gate PASS (`qitem-20261019195832-713ad71eee3f`): `go vet ./...` clean, `go test ./...`
  green, test RED on the base revision with the parser's `flag provided but not defined` refusal.

## Effect on the register

PORT-03's residual named in `ai_docs/core-architecture/nfr-register.md` at hub `cc7c17b6`
(`internal/clientseat/reseat.go:77`) is fixed and landed. The register row moves from PARTIAL to GATE
on the next reseed, citing this change and the activity change in `a788477`.
