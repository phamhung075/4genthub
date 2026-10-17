#!/usr/bin/env bash
# =====================================================================================================
# u3-apply-harness.sh — the ONE way the U3 acceptance harness path is written (C4 instrument, item (a)).
#
# THE RULE THIS ENFORCES: the live harness path is write-only for applies. Iteration happens in a staged copy
# (fe-stageNN.sh, composed and verified by fe-stageNN.py against its base); an install is this script's job,
# and it does five things in this order:
#   1. refuses unless the staged bytes hash to the sha that was announced (--expect-sha is REQUIRED: an
#      install whose bytes nobody named is not an install);
#   2. refuses bytes `bash -n` cannot parse;
#   3. keeps the predecessor aside under its own sha256 (a copy, not a move, so a reader can diff/restore);
#   4. installs with ONE rename in the same directory (same filesystem), so a reader never sees a
#      half-written harness;
#   5. appends before -> after to APPLY-LOG beside the live file, and prints the announcement last.
#
# WHY THE ATOMIC RENAME IS NOT STYLE: the harness records its own sha256 at every run start and REFUSES to
# continue when the file changes under it (harness_unchanged, exit 4) because bash re-reads a running script
# from its byte offset. An in-place `cp` is a window in which a run executes a mixed revision; a rename has
# no such window. Measured 2026-10-15: the live path held three unannounced revisions in 3 minutes
# (8d7be24c -> f54f1f17 -> 28302b7b), which is exactly this window, three times.
#
# WHY --live IS REQUIRED AND NOT DERIVED FROM THIS FILE: the tool is versioned in the repository and RUN from
# beside the harness (u3-run/), so its own directory says nothing about which harness it is installing. The
# path is named by the caller; the log and the aside live beside the live file, not beside this script.
#
# USAGE
#   ./u3-apply-harness.sh --live <.../ACCEPTANCE-cutover-lab-U3.sh> --expect-sha <sha256> \
#       [--note TEXT] [--dry-run]
#   ./u3-apply-harness.sh --live <.../ACCEPTANCE-cutover-lab-U3.sh> --log
#   ./u3-apply-harness.sh --live <.../ACCEPTANCE-cutover-lab-U3.sh> --current
#
# Exit: 0 applied (or a read-only verb), 3 refused (nothing written), 4 verification failed AFTER install
#       (the predecessor is restored from the aside before exiting).
# =====================================================================================================
set -uo pipefail

SEAT="${AGENTHUB_SEAT:-${USER:-unknown}}"

say(){ printf '%s\n' "$*" >&2; }
refuse(){ say "REFUSING: $*"; say "Nothing was written to ${LIVE:-<no live path named>}."; exit 3; }
sha(){ sha256sum "$1" 2>/dev/null | cut -d' ' -f1; }
bytes(){ wc -c < "$1" 2>/dev/null | tr -d ' '; }

# ---------------------------------------------------------------- argument handling
LIVE=""; STAGED=""; EXPECT=""; NOTE=""; DRY=0; VERB=apply
while [ $# -gt 0 ]; do
  case "$1" in
    --live)      shift; [ $# -gt 0 ] || { say "--live needs a path"; exit 3; }; LIVE="$1";;
    --expect-sha) shift; [ $# -gt 0 ] || { say "--expect-sha needs a value"; exit 3; }; EXPECT="$1";;
    --note)      shift; [ $# -gt 0 ] || { say "--note needs a value"; exit 3; }; NOTE="$1";;
    --dry-run)   DRY=1;;
    --log)       VERB=log;;
    --current)   VERB=current;;
    -*)          { say "unknown argument: $1"; exit 3; };;
    *)           [ -z "$STAGED" ] || { say "a second positional file was given: $1"; exit 3; }; STAGED="$1";;
  esac
  shift
done
[ -n "$LIVE" ] || { say "usage: $0 --live <harness path> --expect-sha <sha256> [--note TEXT] [--dry-run] | --log | --current"; exit 3; }
DIR="$(cd "$(dirname "$LIVE")" 2>/dev/null && pwd)" || { say "REFUSING: the directory of $LIVE does not resolve"; exit 3; }
LIVE="$DIR/$(basename "$LIVE")"
LOG="$DIR/APPLY-LOG"

current(){
  [ -f "$LIVE" ] || refuse "no live harness at $LIVE"
  local now b stage f
  now="$(sha "$LIVE")"; b="$(bytes "$LIVE")"
  printf 'live    %s  %s B\n' "$now" "$b"
  stage="<none: no staged file beside it has these bytes>"
  for f in "$DIR"/fe-stage*.sh; do
    [ -f "$f" ] || continue
    [ "$(sha "$f")" = "$now" ] && { stage="$(basename "$f")"; break; }
  done
  printf 'stage   %s\n' "$stage"
  if [ -f "$LOG" ]; then
    printf 'apply-log (last line): %s\n' "$(tail -1 "$LOG")"
  else
    printf 'apply-log (last line): <APPLY-LOG does not exist yet>\n'
  fi
}

case "$VERB" in
  log)
    [ -f "$LOG" ] || { say "no APPLY-LOG at $LOG"; exit 3; }
    cat "$LOG"; exit 0;;
  current)
    current; exit 0;;
esac

# ---------------------------------------------------------------- the preconditions, all refused in words
[ -f "$STAGED" ] || refuse "no staged file at $STAGED"
[ -f "$LIVE" ] || refuse "no live harness at $LIVE (this tool installs ON a predecessor; it does not create one)"
[ -n "$EXPECT" ] || refuse "--expect-sha is required: the bytes being installed must be named (the composer's --print-sha)"
[ "${#EXPECT}" = 64 ] || refuse "--expect-sha must be a full sha256 (64 hex), got ${#EXPECT} chars: $EXPECT"

before="$(sha "$LIVE")"; [ -n "$before" ] || refuse "cannot hash the live harness at $LIVE"
staged_sha="$(sha "$STAGED")"; [ -n "$staged_sha" ] || refuse "cannot hash the staged file at $STAGED"
[ "$EXPECT" = "$staged_sha" ] || refuse "the staged bytes are $staged_sha, not the announced $EXPECT - the file moved under the announcement"
[ "$staged_sha" != "$before" ] || refuse "the staged bytes ARE the live bytes ($before): there is nothing to apply"

bash -n "$STAGED" || refuse "bash -n refused the staged bytes: an install is not where a syntax error is found"
[ -x "$LIVE" ] || refuse "the live harness is not executable at $LIVE"

ASIDE="$LIVE.$before"
if [ -e "$ASIDE" ]; then
  [ "$(sha "$ASIDE")" = "$before" ] || refuse "the predecessor aside $ASIDE exists and is not the current live bytes ($before): resolve it before installing over it"
  ASIDE_WRITE=0
else
  ASIDE_WRITE=1
fi

b_before="$(bytes "$LIVE")"; b_after="$(bytes "$STAGED")"; lines_after="$(wc -l < "$STAGED" | tr -d ' ')"
ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

if [ "$DRY" = 1 ]; then
  say "DRY RUN — nothing is written:"
  say "  live:     $LIVE  $before  $b_before B"
  say "  staged:   $STAGED  $staged_sha  $b_after B  ($lines_after lines)"
  say "  aside:    $ASIDE $([ "$ASIDE_WRITE" = 1 ] && printf '(would be written)' || printf '(exists, sha verified)')"
  say "  would append to $LOG:"
  say "  $ts live $before -> $staged_sha bytes=$b_after composed=$(basename "$STAGED") note=\"${NOTE:-<none>}\" by=$SEAT"
  exit 0
fi

# ---------------------------------------------------------------- the install: one rename, same directory
if [ "$ASIDE_WRITE" = 1 ]; then
  cp -p "$LIVE" "$ASIDE" || refuse "cannot keep the predecessor aside at $ASIDE"
  [ "$(sha "$ASIDE")" = "$before" ] || refuse "the aside copy does not hash to the predecessor ($before): not installing over an unreadable predecessor"
fi

tmp="$DIR/.$(basename "$LIVE").new.$$"
cp "$STAGED" "$tmp" || { rm -f "$tmp"; refuse "cannot write the staged copy at $tmp"; }
chmod 0755 "$tmp" || { rm -f "$tmp"; refuse "cannot make $tmp executable"; }
if [ "$(sha "$tmp")" != "$staged_sha" ]; then rm -f "$tmp"; refuse "the installed copy does not hash to the staged bytes: the filesystem changed them"; fi
mv -f "$tmp" "$LIVE" || { rm -f "$tmp"; refuse "the rename onto $LIVE failed"; }

after="$(sha "$LIVE")"
if [ "$after" != "$staged_sha" ]; then
  say "FAILED AFTER INSTALL: live hashes $after, not $staged_sha — restoring the predecessor from $ASIDE"
  cp -p "$ASIDE" "$LIVE" && [ "$(sha "$LIVE")" = "$before" ] || say "RESTORE ALSO FAILED: restore by hand from $ASIDE"
  exit 4
fi

# ---------------------------------------------------------------- the record, then the announcement
printf '%s live %s -> %s bytes=%s composed=%s note="%s" by=%s\n' \
  "$ts" "$before" "$after" "$b_after" "$(basename "$STAGED")" "${NOTE:-<none>}" "$SEAT" >> "$LOG" \
  || say "WARNING: the install happened but the apply log could not be appended at $LOG"

say "applied  $STAGED -> $LIVE  ($before -> $after, $b_after B, aside $ASIDE)"
say "ANNOUNCE harness $after ($b_after B, $lines_after lines) — predecessor $before; stage $(basename "$STAGED"); apply-log $LOG; by $SEAT"
