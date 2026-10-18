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
mkdir -p "$ROOT"
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
# TCP ONLY, and that is the point: a seat HOME is deep enough that a Unix-domain socket under it
# exceeds the 107-byte sun_path limit, and PostgreSQL then refuses to start at all - the caller sees
# "Unix-domain socket path ... is too long (maximum 107 bytes)" and "FATAL: could not create any
# Unix-domain sockets" in pg.log, and has to relocate the cluster by hand. unix_socket_directories=''
# means no socket path exists to be too long. This is the recipe the session_stream package's testdb.go
# has documented all along; the two diverged and this one was wrong.
# THE ONE VARIABLE NOT TO EXPORT HERE IS TEST_DATABASE_URL. This harness prints AGENTHUB_TEST_PG_URL;
# TEST_DATABASE_URL is another case's switch, and exporting it while "setting the database env vars"
# turns that case from a loud skip into a red that has nothing to do with the caller's change:
# fastmcp/task_management/infrastructure/database/models_prod_test.go:29 reads it
# (prodTestDatabaseURLEnv), :143 skips the run with "SKIPPED, NOT PASSED" when it is unset, and when it
# is set the case RUNS against whatever database the DSN names - on this harness's fresh cluster that
# is a red 0.02s in on six legacy tables ("relation agent_import_history does not exist"), because the
# schema that case needs is not the one the migrations create. The skip is correct behaviour, and the
# export silently disables it.
"$ROOT/bin/pg_ctl" -D "$ROOT/data" -o "-p $PORT -c listen_addresses=127.0.0.1 -c unix_socket_directories=''" -l "$ROOT/pg.log" -w start >/dev/null 2>&1 || true
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
