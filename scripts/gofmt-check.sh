#!/bin/sh
# gofmt over every tracked .go file, minus the paths named in .gofmt-excludes.
#
# Two tracked files carry a .go suffix and are not Go: captain-definition.backend.go (a CapRover
# JSON definition) and docker-system/docker/Dockerfile.backend.go (a Dockerfile). gofmt reports
# both on stderr and exits 2, so a sweep from the repository root that reads the exit code fails
# for a reason that is not formatting. Neither may be renamed - both are load-bearing by name, and
# .gofmt-excludes records why beside each path. That file is the ONE place the sweep learns them.
#
# Exit: 0 clean | 1 unformatted files listed | 2 the instrument itself is misconfigured.
set -eu
cd "$(git rev-parse --show-toplevel)"

patterns=$(mktemp)
trap 'rm -f "$patterns"' EXIT
sed -e 's/#.*//' -e 's/[[:space:]]*$//' -e '/^[[:space:]]*$/d' .gofmt-excludes > "$patterns"

list=$(git ls-files '*.go')
[ -n "$list" ] || { echo "gofmt-check: no tracked .go files - wrong directory?" >&2; exit 2; }

# A named path that is no longer a tracked .go file would rot the exclusion silently.
while IFS= read -r path; do
	printf '%s\n' "$list" | grep -qxF -- "$path" || {
		echo "gofmt-check: .gofmt-excludes names a path that is not a tracked .go file: $path" >&2
		exit 2
	}
done < "$patterns"

skipped=$(printf '%s\n' "$list" | grep -xF -f "$patterns" || true)
checked=$(printf '%s\n' "$list" | grep -vxF -f "$patterns" || true)

n_skipped=$(printf '%s\n' "$skipped" | grep -c . || true)
if [ "$n_skipped" -gt 0 ]; then
	echo "gofmt-check: skipped $n_skipped named non-Go path(s), from .gofmt-excludes:" >&2
	printf '  %s\n' "$skipped" >&2
fi

n_checked=$(printf '%s\n' "$checked" | grep -c . || true)
[ "$n_checked" -gt 0 ] || { echo "gofmt-check: nothing left to check" >&2; exit 0; }

findings=$(printf '%s\n' "$checked" | xargs gofmt -l) || {
	echo "gofmt-check: gofmt itself failed over the checked set (a parse error in a checked file?)" >&2
	exit 1
}
if [ -n "$findings" ]; then
	echo "gofmt-check: $n_checked checked, unformatted:" >&2
	printf '%s\n' "$findings" >&2
	exit 1
fi
echo "gofmt-check: clean over $n_checked tracked .go file(s)" >&2
exit 0
