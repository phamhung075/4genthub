#!/usr/bin/env bash
# Starts a throwaway PostgreSQL 16 for the Go integration tests (no root, no Docker).
# Binaries come from the zonky embedded-postgres Maven artifact and are cached in
# ~/.cache/agenthub-testpg. Prints the value for AGENTHUB_TEST_PG_URL.
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
"$ROOT/bin/pg_ctl" -D "$ROOT/data" -o "-p $PORT -k $ROOT/sock -c listen_addresses=127.0.0.1" -l "$ROOT/pg.log" -w start >/dev/null || true
echo "AGENTHUB_TEST_PG_URL=postgresql://agenthub_user@127.0.0.1:$PORT/postgres"
