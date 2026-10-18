# The pin carries the `up --team` cwd fix and a room that starts from its own record

The hub's gitlink moves `0ec33bb -> cc2fd1c`. `61b5648`: a team run keeps each seat's cwd (`up --team` no longer wipes them). `cc2fd1c`: `up` starts a room from its recorded spec without `--team`, so `heal` can start the safeguards. Both reviewed PASS. Measured in the client: `go test ./...` rc 0, `cargo test --offline` 171 passed. This commit is the gitlink alone.
