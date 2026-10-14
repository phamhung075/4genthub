## Client pin carries decide --detail-file

### Changed
- `agenthub_client` pin: `38b0bc9` to `9a86841`. `4genteam decide` reads its context from `--detail-file`, and the `jev-decisions` and `room-decision-request` skills tell seats to use it, so a quote in the text can no longer break the shell command.

### Tested
Client `go vet ./...` and `go test ./...` pass, including a detail with quotes, a `$` and a newline.
