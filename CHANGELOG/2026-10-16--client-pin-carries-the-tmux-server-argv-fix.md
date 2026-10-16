# Client pin carries the tmux server that is started without a seat's environment

### Fixed

- `agenthub_client` pin moves to `a3ec97f` (`3d85133` plus the entry's doc fix): `launch_session` now calls
  `pty::ensure_server()` FIRST, which starts this root's tmux server from a client that carries no seat's
  environment, so the server's argv no longer holds a seat's `-e KEY=VALUE` pairs. The room's longest-lived
  process had been publishing three credential-shaped args there, and `/proc/<server pid>/cmdline` is readable by
  every local user while the same process's `environ` is readable only by this runtime's uid (3 before, 0 after,
  measured end to end on a scratch daemon and a real room). `exit-empty off` is deliberate rather than incidental:
  the root's server now outlives its last session, so no per-room stop may kill it. The client's own entry
  (`agenthub_client/CHANGELOG/2026-10-16--the-tmux-server-is-started-without-a-seats-environment.md`) carries the
  mechanism, the measurements and the consequence.

### Testing

- `TEST-CHANGELOG.md` carries the client suite's change: the new case
  `pty::launch_env_tests::the_server_is_not_the_process_that_carries_the_seats_environment` (red without the fix,
  118 passed / 0 failed with it) and `pty::test_servers::own` returning a `Server` guard at five call sites. No
  test files changed in this repo.
