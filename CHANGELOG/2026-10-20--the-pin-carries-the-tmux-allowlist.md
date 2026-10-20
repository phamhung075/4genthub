# Pin: the client carries the tmux allowlist (client 900db14)

The hub gitlink moves `c21e702 -> 900db14`, which carries the SEC-02 unit on the rebased lane:

- `3c2d92e` - the fix. The tmux server is bootstrapped from `env_clear()` plus `ENV_SERVER_ALLOWLIST`
  (`rust/agenthub-runtime/src/main.rs:78`: 12 host-plumbing keys, `LC_` by prefix) instead of the
  daemon's environment minus a deny list; a server that is already up is cleaned by the same allowlist
  before every launch (`pty::clean_server_env`, `rust/agenthub-runtime/src/pty/mod.rs:193`); and a
  seat's `-e` pairs are taken back out of that seat's own session environment once its pane exists
  (`pty::scrub_session_env`, `rust/agenthub-runtime/src/pty/mod.rs:229`). The pane keeps the
  environment the kernel gave it at `exec`, so `mcp.json`'s `${AGENTHUB_TOKEN}` and the model client's
  provider key are still read from there.
- `900db14` - the client `TEST-CHANGELOG.md` entry for the five new cases in `launch_env_tests`.

Why the pin moves: measured on this box 2026-10-19, `tmux show-environment -g` printed
`AGENTHUB_TOKEN`, `DEEPSEEK_API_KEY`, `TYPESAFE_API_KEY`, `PDF2W_API_KEY`, `ANTIGRAVITY_CSRF_TOKEN`
and 30-odd host keys to any pane of any room on the root, and `show-environment -t <another seat's
session>` printed that seat's own `-e` pairs - two readable copies of what only the pane needs. A
deny list cannot hold that line; the ruling (`RULING-sec02-tmux-global-env-2026-10-19.md`) chose the
allowlist for exactly that reason: a credential added to `.env` tomorrow is out without a code change.

The server's argv is the bootstrap client's, not a seat's: `pty::ensure_server`
(`rust/agenthub-runtime/src/pty/mod.rs:294`) starts it from an allowlisted client, because a server
created by the first seat's `new-session` kept that client's `-e` pairs on the longest-lived process
of the room, where `/proc/<server pid>/cmdline` is world-readable.

Register: SEC-02 moves PARTIAL -> GATE at `ai_docs/core-architecture/nfr-register.md:64`, citing
`3c2d92e` and the ruling. "Open gates this register expects" is unchanged - SEC-02 was not an open
gate.

Order, per `RULING-pin-names-a-pushed-client.md`: client `origin/main` carries `900db14` before this
pin commit, so a fresh clone and a submodule sync resolve the gitlink. The earlier tip `04a0875` was
rebased onto `c21e702` and is not an ancestor of the pin.

Not closed by this unit, recorded rather than claimed: `respawn-pane` and `new-window` inside a seat's
session lose its keys after the scrub (no client path does either today), and an under-sized allowlist
surfaces as a launch whose MCP mount comes up empty rather than as a launch error.

Measured at this pin (`900db14`, 2026-10-20): `cargo test --offline` 192 + 1 + 20 + 1 pass,
`launch_env_tests` 12 pass, `cargo clippy` with `-D warnings` and `cargo fmt --check` clean; the
reviewer PASSed `3c2d92e` after the rebase onto `c21e702`, and had PASSed `04a0875` before it.
