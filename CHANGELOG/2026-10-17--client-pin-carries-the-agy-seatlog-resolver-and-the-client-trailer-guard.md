# The pin carries the agy seat-log resolver and the client's task-trailer hook

The hub's gitlink moves `27955e4 -> 0ec33bb`. `60a68c9` (reviewed PASS): the one seat-log resolver reads an agy seat's transcript. `0ec33bb`: the client gains `scripts/git-hooks/commit-msg`, which runs this repo's `task-trailer-guard`, so a seat commit in `agenthub_client` must name its hub task (task e314fd76); the seat guard's blocked `git add -A` advice now says `commit with a pathspec: git commit -- <paths>`.

Measured in the client: `go test ./...` rc 0, `cargo test --offline` 171 passed. This commit is the gitlink alone.
