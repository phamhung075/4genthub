## The verb that types into a prompt refuses to guess which prompt, because the session it used to take was the first of fourteen

### Fixed

- `agenthub_go/internal/clientsync/messagesverb.go` — **`sync messages` without `--session` no longer takes the FIRST session `rig ps --json` reports.** That is what the code did, while the verb's own documentation said it REFUSED when the session was ambiguous, so the doc described a guard that did not exist. On this machine `rig ps --json` reports **fourteen** sessions (the reviewer's measurement, whose probe found `firstRigSession()` = `4genthub-deepseek` here), so a message addressed to one seat's window would have been typed into an arbitrary other seat's prompt — the outcome this verb's own comment calls worse than not delivering. The verb now reads the WHOLE candidate set: more than one candidate and no `--session` is a refusal that names EVERY candidate and says how to name one, and exactly one candidate still flows. The refusal happens before the pull, so a run that cannot deliver spends no ACKs and leaves the cloud untouched. `--dry-run` still needs no session, because it types nothing.
- `agenthub_go/internal/clientsync/connectorverb.go` — `firstRigSession` is split into `rigSessionCandidates` (the whole set, deduped, in the order `rig ps --json` reports it) plus a three-line wrapper that returns the FIRST entry and otherwise errors exactly as before. The split exists so the refusal above reads the same parse instead of re-deriving the shape of `rig ps --json` in a second place; **the wrapper's behaviour is deliberately unchanged**, because other verbs call it and redefining what "the first" means for them is a different change with a different blast radius.

### Known, reported rather than fixed

- **`sync connector` has the same harm, and it keeps it in this commit on purpose.** `RunConnectorVerb` is the ONLY other caller of `firstRigSession` (`connectorverb.go:101-107`): with no `--session` it resolves the first of those fourteen sessions, reads THAT session's transcript, registers it in the cloud and appends its events — so the wrong session's content is published and registered under its own name, rather than a wrong prompt being typed into. Same class of harm, different consequence, and it belongs to its own row: narrowing it here would change a pre-existing verb other callers depend on.

### Testing

From `agenthub_go` with `GOCACHE` and `TMPDIR` inside `.gocache`/`.gotmp`:

- The two new cases in `internal/clientsync/messagesverb_test.go` were **seen red first**: with a fake two-session `rig` on PATH, `TestMessagesVerbRefusesToGuessWhichSessionToTypeInto` failed with `exit = 0, want ExitUnavailable` — the verb silently typed into `alpha` and reported success. After the change both pass: the two-session case refuses with the candidates named and the cloud untouched, and the single-session case still delivers (`GET | SEND only-one hello | ACK m1`).
- `go test -count=1 ./internal/clientsync/... ./internal/clientcmd/...` → both ok. `go vet ./internal/... ./cmd/...` → no output. `go build ./...` → exit 0.

The fake `rig` is a shell script on `PATH`, so the verb's REAL resolution path runs rather than a substituted function; the only other place this verb shells out to `rig` is the local send, which the existing fixture replaces.
