#!/usr/bin/env bash
# stamp-frontend.sh - write agenthub-frontend/BUILD-SHA on the `frontend` branch and commit it.
#
# WHY. CapRover's captain-definition schemaVersion 2 has no build-args field, and its build context is
# the uploaded project with no .git - so `--build-arg VITE_BUILD_SHA` cannot arrive, and the served
# bundle inlined VITE_BUILD_SHA:"" (measured 2026-10-23). The stamp therefore travels as a FILE in the
# pushed tree: this script writes it, docker-system/docker/Dockerfile.frontend.production reads it at
# build time, and `check_served_frontend.py --expect-build-of <ref>` compares what the bundle carries
# with the ref's commit.
#
# USAGE, from a worktree whose branch is `frontend` and whose tree is clean:
#   scripts/stamp-frontend.sh --ref origin/main --task <hub task id>
#   git push origin frontend
set -euo pipefail

ref=origin/main
task=""
while [ $# -gt 0 ]; do
    case "$1" in
        --ref) ref="$2"; shift 2 ;;
        --task) task="$2"; shift 2 ;;
        *) echo "stamp-frontend.sh: unknown argument '$1' (--ref <ref>, --task <hub task id>)" >&2; exit 3 ;;
    esac
done
[ -n "$task" ] || { echo "stamp-frontend.sh: --task <hub task id> is required - the stamp commit names the work it serves" >&2; exit 3; }

root=$(git rev-parse --show-toplevel)
cd "$root"
branch=$(git rev-parse --abbrev-ref HEAD)
[ "$branch" = "frontend" ] || { echo "stamp-frontend.sh: refusing - the stamp belongs on 'frontend', not '$branch'" >&2; exit 3; }
[ -z "$(git status --porcelain --untracked-files=no)" ] || { echo "stamp-frontend.sh: refusing - the tree has uncommitted changes" >&2; exit 3; }

sha=$(git rev-parse --verify "$ref^{commit}")
# The stamped commit must be IN the tree being built: a stamp that names a commit the branch does not
# carry would describe a build nobody made.
git merge-base --is-ancestor "$sha" HEAD || {
    echo "stamp-frontend.sh: refusing - $ref ($sha) is not in this branch; advance it first: git merge --ff-only $ref" >&2
    exit 3
}

printf '%s\n' "$sha" > agenthub-frontend/BUILD-SHA
git add -N -- agenthub-frontend/BUILD-SHA
python3 scripts/git-hooks/git_commit_capture.py -- \
    -m "chore(stamp): the frontend branch serves $ref at ${sha:0:12}" \
    -m "Written by scripts/stamp-frontend.sh. CapRover passes no build arg and the context has no .git, so the sha reaches the build as a file: docker-system/docker/Dockerfile.frontend.production reads agenthub-frontend/BUILD-SHA, and check_served_frontend.py --expect-build-of $ref compares it with the entry chunk's inlined VITE_BUILD_SHA." \
    -m "Task: $task" \
    -- agenthub-frontend/BUILD-SHA

echo "stamped ${sha}"
echo "next: git push origin frontend   (then prove it: python3 scripts/check_served_frontend.py --expect-build-of $ref)"
