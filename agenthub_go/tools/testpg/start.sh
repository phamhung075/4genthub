#!/usr/bin/env bash
# Starts a throwaway PostgreSQL 16 for the Go integration tests (no root, no Docker).
# Binaries come from the zonky embedded-postgres Maven artifact and are cached in
# ~/.cache/agenthub-testpg. Prints the value for AGENTHUB_TEST_PG_URL - and refuses to print one
# unless a cluster is really running on that port, because a URL for a server that did not start
# sends the caller into a false red against their own commit.
set -euo pipefail
ROOT="${AGENTHUB_TESTPG_DIR:-$HOME/.cache/agenthub-testpg}"
PORT="${AGENTHUB_TESTPG_PORT:-55432}"
VERSION=16.4.0
mkdir -p "$ROOT" "$ROOT/sock"
if [ ! -x "$ROOT/bin/postgres" ]; then
  curl -sfL -o "$ROOT/pg.jar" "https://repo1.maven.org/maven2/io/zonky/test/postgres/embedded-postgres-binaries-linux-amd64/$VERSION/embedded-postgres-binaries-linux-amd64-$VERSION.jar"
  python3 -c "import zipfile,sys;zipfile.ZipFile('$ROOT/pg.jar').extract('postgres-linux-x86_64.txz','$ROOT')"
  tar -xJf "$ROOT/postgres-linux-x86_64.txz" -C "$ROOT"
fi
[ -d "$ROOT/data" ] || "$ROOT/bin/initdb" -D "$ROOT/data" -U agenthub_user --auth=trust -E UTF8 >/dev/null
# The start may legitimately fail because a cluster from an earlier run is ALREADY running under this
# data dir; that is a success for the caller. What is never a success is printing a URL for a server
# that is not up, or for one up on a different port than the URL names - the old `|| true` here did
# exactly that, and cost another seat a false red whose 31 failures were a dead socket and a DSN that
# pointed nowhere, not its commit.
"$ROOT/bin/pg_ctl" -D "$ROOT/data" -o "-p $PORT -k $ROOT/sock -c listen_addresses=127.0.0.1" -l "$ROOT/pg.log" -w start >/dev/null 2>&1 || true
if ! "$ROOT/bin/pg_ctl" -D "$ROOT/data" status >/dev/null 2>&1; then
  echo "ERROR: no cluster is running under $ROOT/data, so there is no URL to print." >&2
  if [ -f "$ROOT/pg.log" ]; then
    echo "--- last 20 lines of $ROOT/pg.log ---" >&2
    tail -n 20 "$ROOT/pg.log" >&2 || true
  else
    echo "(no log at $ROOT/pg.log)" >&2
  fi
  exit 1
fi
# The port the RUNNING server was started with is the 4th line of postmaster.pid. A URL built from
# $PORT while the server listens elsewhere is the same lie in a quieter form.
running_port=$(sed -n '4p' "$ROOT/data/postmaster.pid" 2>/dev/null || true)
if [ "$running_port" != "$PORT" ]; then
  echo "ERROR: a cluster is running under $ROOT/data on port ${running_port:-unknown}, not $PORT." >&2
  echo "The URL would not describe it. Stop that cluster, or set AGENTHUB_TESTPG_PORT=$running_port." >&2
  exit 1
fi
echo "AGENTHUB_TEST_PG_URL=postgresql://agenthub_user@127.0.0.1:$PORT/postgres"
