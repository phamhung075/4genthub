# The gate refuses a path-only criterion before the judge

Client pin `f0c898b` -> `69f496d` (`fix(client): a path-only criterion is refused before the judge, not judged
blind`), with the register's rule corrected in `ai_docs/agent-system/task-workflow-and-reporting.md`.

## What was wrong

`gate.go`'s `pathOnlyWarnings` already knew a criterion could not be judged: a criterion naming a numstat path
and nothing else is admitted by the register, and then the count-only wire (`clientjev.RedactForWire`, owner
ruling O9a) replaces that path with `<path>` before the judge reads it - so the judge was asked whether
`<path> is fixed`, and answered on an opinion. The gate printed this as a warning and left the criterion in the
judge's set. Task `4670f48e` paid three completion cycles in 18 minutes (0.33/0.37/0.20, then 0.83/0.73/0.97,
then 0.84/0.74/0.97) on criteria the gate could have refused in the same millisecond.

## What changed

- `internal/clientcomplete/gate.go`: `facts.pathOnly()` - a carried path is the criterion's only fact when the
  command, the exit code, a sha prefix and a count are all absent - and the gate refuses such a criterion with
  the vocabulary the warning already spelled (the command with its exit code, a sha prefix, the counts with
  this bundle's value), before a judge call is spent. `register.carries` became `register.names(...).any()`.
- A criterion naming a path AND another fact stays admitted: the claim survives the redaction (precedent
  `35431928`: `go -C agenthub_go test <path> -count=1 exits 0` closed at 0.96-0.98).
- Shadow mode still records and completes instead of refusing (owner ruling O9a).
- `complete_test.go`: the refusal, the completion it stops, the shadow path, and the admissions that must not
  move (`TestAPathPlusCountCriterionIsJudged`, `TestAShaAndCountCriterionIsJudged`).
- `ai_docs/agent-system/task-workflow-and-reporting.md`: the register's fact list and the GOOD/BAD examples now
  say that a path the numstat lists RESOLVES while a criterion about that path alone is refused.
- `skills/share/verification-before-completion/SKILL.md`: names the refusal beside the warning it replaces.

## Verification

- Reviewer gate on `69f496d`: `go test ./... -count=1` 35 packages green, `go vet` and `gofmt` clean; the doc
  audited at DOC-CITATIONS 0 violations, COUNTS 11/11, CITATION-AUDIT 149 rows 0 stale.
- Re-run before the push by the lead in `agenthub_client` at `69f496d`: `go build ./...` clean,
  `go test ./... -count=1` exit 0 with 35 `ok` packages, `gofmt -l .` empty.
- Pushed `f0c898b..69f496d` to `origin/main` of `4genthub-client`; this commit is the hub pin that names it.
