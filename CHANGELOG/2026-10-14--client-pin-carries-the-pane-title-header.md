## Client pin carries the pane-title header

### Changed
- `agenthub_client` pin: `7925e39` to `38b0bc9`. In the `4genteam` grid, each pane's title carries the seat, model and token bar instead of a header line in the stream.

### Tested
Client `go vet ./...` and `go test ./...` pass; the titles were read back from `herdr pane list` on the live `4genthub-min` grid.
