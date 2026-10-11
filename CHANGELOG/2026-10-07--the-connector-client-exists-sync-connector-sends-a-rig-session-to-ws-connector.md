## The connector client exists: `sync connector` sends a rig session to `/ws/connector`

- Owner ruling 2026-10-07 19:47Z, item 2 (C1). The consumer (the Sessions page) and the server
  (`ws_mount.go:69` mounts the route; `session_stream` writes the rows) were both delivered and **no
  client existed in either language** — which is why registering the machine did not move the page. New
  verb `agenthub-client sync connector [--session <name>] [--connector-id <id>] [--lines <n>]`:
  discovers one local session from `rig ps --json` (with `--session` as an explicit override), reads it
  with `rig transcript`, **redacts each line locally before the frame is built**, then does hello →
  session → events and reports the connector id, the cloud's session id and `last_seq`. Files:
  `agenthub_go/internal/clientsync/connector.go`, `connectorverb.go`, `sync.go`.
- **It adds NO dependency.** The repository speaks WebSocket by hand on both sides (`wsUpgrade` at
  `ws_mount.go:704`, the hand-rolled dialer at `ws_mount_test.go:49`), so the client implements one
  masked text-frame connection rather than introducing a third-party library for a protocol this tree
  already has. The token travels in an `Authorization: Bearer` header rather than `?token=`, because a
  URL is what ends up in logs, error strings and process listings.
- Deliberately NOT in this slice: JSONL tailing, `rig capture`, multi-session, reconnect with backoff,
  the frontend, and any server change (`handleConnector` lives in `ws_mount.go`, which is on the
  do-not-edit-without-asking list).
- Verified: `go build ./...` rc=0, `go vet ./internal/clientsync/` rc=0, `gofmt -l` empty,
  `go test -count=1 ./internal/clientsync/` **ok**; the verb is reachable (`agenthubclient sync` lists
  it) and its failure path was exercised live (`rig transcript` error surfaced, exit 1). **The wire
  itself is NOT yet proven** — the connector's ingest path needs the real server, which needs a
  database, and no Postgres client tooling is on `PATH` in this environment; the run that proves it is
  named in the handoff rather than simulated.
- Two defects in my own first draft were caught by these tests and fixed in place: the redactor deleted
  the space after `AGENTHUB_TOKEN: `, and it kept the token itself on the whole-token patterns because
  `${1}` expanded their capture group.
