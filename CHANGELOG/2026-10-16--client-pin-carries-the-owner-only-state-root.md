# Client pin carries the owner-only state root

### Fixed

- `agenthub_client` pin moves to `068f941`: the client (`clientenv.RestrictUmask()` in `cmd/4genteam/main.go`)
  and the runtime (`restrict_umask()` in `rust/agenthub-runtime/src/main.rs`) both take `umask 077` before
  anything creates anything, so every path created under the state root is owner-only - including the seat
  transcripts, which are written by the AGENT inside a tmux pane and which no per-site mode in either process
  could reach, because the umask is inherited down the chain (client/runtime -> tmux client -> the server that
  client creates -> each pane's shell -> the agent). Measured on the live `4genthub-min` on 2026-10-16 before the
  change: the daemon and every seat ran with `0022`, 138 of 163 seat transcripts were `0644` over `0755`
  directories, and 13712 of 20937 files under the state root were readable by every local user - the root that
  held 17 files with the live DeepSeek key and 14 with the live Typesafe key.
- Two writers carry their own mode and a umask clamps neither, so each was fixed where it is decided: the
  safeguard heartbeat (`internal/clientservices/services.go`, an explicit `Chmod(0o644)`) is `0600` now, and
  `copy_dir` (`rust/agenthub-runtime/src/supervisor/mod.rs`) no longer lets `fs::copy` carry the rig's bits into
  a seat's installed skills - the copy drops the group's and the world's bits and keeps the owner's, which was
  the last readable part of the state root in the artifact probe. The client's own entry
  (`agenthub_client/CHANGELOG/2026-10-16--the-state-root-goes-owner-only-at-the-process-level.md`) carries the
  mechanism, the measurements and the modes measured after the fix.
- The end-to-end A/B, on a real daemon and a real scratch room, once per binary: the pane's own shell reported
  `umask=0022` before and `umask=0077` after, and the files and directories under the scratch state root that
  were group- or world-readable went from **74** to **2** - the two being the scratch root directory and
  `daemon.log`, both created by the probe's own shell rather than by the runtime.

### Testing

- `TEST-CHANGELOG.md` carries the client suite's change: the new
  `pty::launch_env_tests::a_pane_runs_under_the_umask_the_runtime_took` (red without the umask call, `0022`
  where it wants `0077`), the new `supervisor::tests::an_installed_skill_keeps_the_owners_bits_and_drops_the_rest`,
  the new `internal/clientenv.TestRestrictUmaskLandsOnThisProcessAndOnWhatItStarts`, the heartbeat-mode
  assertion added to `internal/clientservices.TestTheHeartbeatFileLayoutIsSevenTwo`, and the new windows half of
  the mode package. At this change `cargo test` in `rust/agenthub-runtime` is 120 passed / 0 failed and
  `go test` over the three touched packages is ok. No test files changed in this repo.
