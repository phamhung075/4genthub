# The pin carries the C7 state-home fix, and its record awaits a carrier

The hub's gitlink moves `086dc38 -> 0d0f114` (hub pin, gitlink only). Client main took
`4genthub-min/fe-dev-client` as a merge (`0d0f114`, parents `086dc38` + `4941b3c`): main had already
moved with C6's skill fix, so a fast-forward was no longer possible.

## Changed (client)

C7's check was run in a sandbox whose passwd-derived home IS a temp dir, with the three candidate
roots (`~/config/4genthub`, `~/.openrig`, `~/.config/4genthub/agenthub-seats`) created and then
renamed away inside it, and the socket/XDG unset: `ps`, `continue`, `room status`, `room stop` and
`watchdog` exit 0; `up` wrote only `rooms/<room>/{spec.json,seats,logs,run}` under the root. The
check found two bounded splits the code half had left, both fixed in the lane:

- `internal/clientenv` and every caller: ONE root resolution threaded. `--state-root` reached
  briefs/logs while tmux was still asked on the DEFAULT root's server (`continue`, `watchdog`); `ps`
  had no flag at all; `watch` ignored its own resolved root; `up`'s supervisor, idle guard and
  interrupt used the default. `clientenv.TmuxArgvAt` refuses an empty root instead of falling back.
- `internal/clientps`, `internal/clientwatch`: an absent tmux server is "no sessions". Only tmux's
  "no server running" spelling was understood; a fresh root answers
  `error connecting to ... (No such file or directory)`, so `ps`, `watch feed` and `watch grid`
  exited 3 there. A failed read with no output now counts as no sessions - the rule `continue` and
  `watchdog` already had.

## Evidence

- Reviewer gate PASS at `4941b3c` (row `qitem-20261017061853-75fad9b4e990`): all tests green, the
  sandbox verified with the roots renamed away.
- The lane's own audit: `seats/`, `briefs/`, `logs/`, `state/`, `bin/`, `rooms/` each have a code
  site; `state/omp/` and `transcripts/` are absent with no code site (native seats live under
  `rooms/`, transcripts are the per-seat JSONL under `rooms/.../sessions`).
- Lead at the merged tip: merge parents `086dc38` + `4941b3c`, 20 files `+338/-211`;
  `go test ./...` green on the lane; the hub commit is a bare gitlink bump (`numstat` 1 file
  `+1 -1`).

## Deferred, named not dropped

- The live data move waits for C5's snapshot, which the owner push unblocks.
- The flag-spelling split (`up`/`room --state-dir` vs `--state-root`) needs its own row before a
  caller-visible rename.
- The client's SECOND log home (`clientservices.logDir` writes `~/.local/state/4genthub/logs`) is
  task `0d42b77a`; moving it with the state root alone would make `status`/`doctor` read every
  safeguard as absent.

## Held

Held record: a pin commit cannot carry its docs from a seat (pre-commit drops the gitlink, so a
pin+docs commit arrives as docs-only and the docs-only guard refuses it; no hook was bypassed). It
rides any commit that touches a non-doc file, or the owner's `types_or: [file, directory]` one-liner
(`qitem-20261017002819-8e1c6aff25f2`).

The push is not authorized and waits for the owner's word (`qitem-20261017030506`).
