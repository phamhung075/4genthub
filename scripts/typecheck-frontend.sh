#!/bin/sh
# THE FRONTEND'S TYPECHECK, FROM THE REPO ROOT, NAMED THE ONE WAY THAT COMPILES.
#
# `npx tsc` typed at the repo root does NOT run TypeScript. The root carries no compiler, so npx
# resolves a GLOBAL package named `tsc`, which prints "This is not the tsc command you are looking
# for" and exits 0 without reading a single file (measured 2026-10-21: 0.93 s, rc 0, against
# 11.80 s for the real compiler on the same tree). The completion gate reads exit 0 as the test
# passing, so that form turns a typecheck into decoration in the direction that looks green.
#
# So the binary is named by path, never by bare name, and its absence is a FAILURE rather than a
# pass: `sh scripts/typecheck-frontend.sh` either compiles the frontend with the compiler the
# frontend pins or exits 127 and says why. Everything after the script name is passed through, so
# the skill that widens the check keeps one entry point:
#
#   sh scripts/typecheck-frontend.sh --noUnusedLocals --noUnusedParameters
#
# `npm run typecheck` at the root runs the same line (package.json, `scripts.typecheck`).
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
project="$root/agenthub-frontend"
bin="$project/node_modules/.bin/tsc"

if [ ! -x "$bin" ]; then
	echo "typecheck-frontend: refusing to pass without a compiler - $bin is missing or not executable." >&2
	echo "typecheck-frontend: install the frontend's dependencies (cd agenthub-frontend && pnpm install)." >&2
	exit 127
fi

exec "$bin" --noEmit -p "$project" "$@"
