# The test line is argv, so a sentence is refused

`4genteam complete --test` never reaches a shell: the line is split into an argument list in-process.
On 2026-10-18 that split was measured costing a completion: the line

```
go -C agenthub_go test -count=1 ./... (green at 1daa0e6d; repoguards 0.2s)
```

ran as `go … "(green" "at" "1daa0e6d;" "repoguards" "0.2s)"`, exited non-zero for a reason that was
never a test failure, and the gate read **D3 "the test run failed"** over a tree whose own suite was
green. The evidence itself was correct — the command really did fail — so nothing in the gate could
have caught it.

## What changed

- `agenthub_client/internal/clientevidence/evidence.go`: `splitCommand` refuses an **unquoted**
  `(`, `)`, `|`, `&`, `;`, `<`, `>` or backtick. Those are characters a shell acts on and the splitter
  does not, so passing them on ran a different command line than the one typed. The refusal names the
  split and the form that still works:

  ```
  --test is split into an argument list and never read by a shell, so the unquoted '(' would be passed
  to the command as its own argument: pass the bare command, or put the whole line inside a shell you
  name yourself, e.g. sh -c '...'
  ```

- Quoted metacharacters still survive: `sh -c 'go test ./... (green at 1daa0e6d)'` splits into three
  arguments and runs, and `go test -run 'TestAlpha|TestBeta' ./...` is unchanged.

## Runs at this change

Probes, through the built client binary (`go -C agenthub_client build -o /tmp/4genteam-probe ./cmd/4genteam`):

- The measured sentence — `--test "go -C agenthub_go test -count=1 ./... (green at 1daa0e6d; repoguards 0.2s)"` —
  exits 2 with the message above and does no work (no git, no request): the refusal is a usage error.
- A genuinely failing command still yields D3:
  `--test "sh -c 'exit 3'"` on base `bfd4363f` prints
  `{"verdict":"reject","reasons":"D3: the test run failed",…}` and the task is not completed.
- `cd agenthub_client && go test -count=1 ./...` = exit 0; `go vet ./internal/clientevidence/` clean;
  `gofmt -l internal/clientevidence/` empty; `cargo test --offline` in `rust/agenthub-runtime` = 1 passed.
- `TestSplitCommand` carries the five refusal lines and the quoted survivor; `TestEvidenceUsageErrorsNeverWork`
  carries the measured sentence and asserts no dial and no git call.
- False-positive check: the five allowed forms (`go test ./...`, quoting, escapes, empty line, quoted
  metacharacters) still split exactly as before — the existing cases are unchanged and pass.

Client branch `4genthub-min/test-argv-refusal`: `d0ffef4`, base `ccc1acc` (client `main`).
