## The test-postgres starter is TCP-only, because a seat HOME makes its Unix socket too long

### What was wrong
`agenthub_go/tools/testpg/start.sh` created a Unix-domain socket under `$ROOT/sock` and passed
`-k $ROOT/sock` to `pg_ctl`. Under a seat HOME that path is deeper than the kernel's 107-byte
`sun_path` limit, so PostgreSQL **refused to start at all** and the caller had to relocate the whole
cluster by hand — which is exactly what happened to the reviewer running a live case, who moved it to
`/tmp/testpg-rev` on port 55999.

Reproduced before touching anything, with `HOME` 83 characters deep (socket path 127 bytes) and a
free port so the port was not the variable:

```
LOG:  listening on IPv4 address "127.0.0.1", port 55991
LOG:  Unix-domain socket path "/tmp/.../home/.cache/agenthub-testpg/sock/.s.PGSQL.55991" is too long (maximum 107 bytes)
WARNING:  could not create Unix-domain socket in directory "/tmp/.../sock"
FATAL:  could not create any Unix-domain sockets
LOG:  database system is shut down
```

The starter's own guard behaved correctly — it printed no URL, refused to invent one, and showed that
log tail. The cluster simply could not come up.

### The divergence, which is the actual defect
The tree already contained a recipe that avoids this:
`fastmcp/session_stream/testdb/testdb.go` documents `unix_socket_directories=''` with an explicit
port, i.e. TCP-only, so no socket path exists to be too long. The starter had not been given the same
treatment, and the two recipes diverging is what let a seat hit a failure the repository already knew
how to prevent.

### What changed
One line of `start.sh`, plus the reason above it:

- `-o "-p $PORT -k $ROOT/sock -c listen_addresses=127.0.0.1"` becomes
  `-o "-p $PORT -c listen_addresses=127.0.0.1 -c unix_socket_directories=''"`.
- `mkdir -p "$ROOT" "$ROOT/sock"` drops the now-meaningless `sock` directory.

The command-line `-c` is deliberate rather than editing `postgresql.conf`: it applies to a data
directory that already exists, so an existing cluster is fixed by the same change. Everything else is
untouched — the guard that refuses to print a URL for a server that is not running, the check that the
running server's port matches the URL, and the default port.

### Verified
- **The same deep HOME and the same data directory that had just failed**: the fixed starter prints
  `AGENTHUB_TEST_PG_URL=postgresql://agenthub_user@127.0.0.1:55992/postgres`, exit 0.
- **Second run** (cluster already up): prints the same URL, exit 0 — the already-running path is intact.
- **The URL describes the server that is up**: line 4 of `postmaster.pid` reads `55992`.
- **A database-gated case passes with exactly that URL**:
  `cd agenthub_go && GOCACHE=.gocache TMPDIR=.gotmp AGENTHUB_TEST_PG_URL='<the printed URL>' go test -count=1 ./fastmcp/session_stream/` -> `ok agenthub/fastmcp/session_stream 5.307s`.
- `bash -n agenthub_go/tools/testpg/start.sh` -> clean.

### What this does NOT do
It does not choose a port for you. In this environment another seat's cluster already holds the
default 55432, and a starter that cannot bind its port still fails — correctly and loudly, with the
port-conflict line in the log tail and the instruction to set `AGENTHUB_TESTPG_PORT`. Auto-selecting a
free port would change what the printed URL means and was not what the defect asked for.

The throwaway cluster this proof started on 55992 was stopped afterwards; nothing else was signalled.
