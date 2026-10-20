# PORT-02 names the three shell lines, not three `format!` commands

`ai_docs/core-architecture/nfr-register.md:117` cited `pty/mod.rs:579` for "three `format!`-built tmux
commands remain". Opened at both pins, that line is a serde assertion (`outcomes_serialize_kebab_case`)
at `c21e702` and a `paste-buffer` argv element at `900db14` - stale before the SEC-02 pin and still
stale after it. The mechanism it named was wrong twice over: no tmux command is built with `format!`
(tmux is reached through `tmux_command().args([...])`), and `format!` appears on those paths only in
error text.

Re-derived at `900db14`: the count of three survives, the species does not.

- `pane_command` (`rust/agenthub-runtime/src/pty/mod.rs:74`) builds the one string tmux hands to the
  pane's SHELL - `env -u <denied keys> -u TMUX -u TMUX_PANE <runner command>`, assembled with
  `push_str`, not `format!`. The runner command is re-parsed by that shell rather than passed as argv;
  that is the residual, and it is why the status stays PARTIAL.
- `AGY_MCP_COMMAND` (`rust/agenthub-runtime/src/supervisor/mod.rs:498`) is agy's cloud-bridge entry,
  `{"command": "sh", "args": ["-c", ...]}` at `:506` and `:523`.
- `AGY_DEEPSEEK_COMMAND` (`supervisor/mod.rs:516`) is the delegation entry in the same form. Both lines
  read the seat's variables at run time instead of carrying values, so the shared `mcp_config.json`
  holds neither a credential nor a hardcoded path.

No production `sh -c` exists beyond those: the two `Command::new("sh")` sites
(`supervisor/mod.rs:3391`, `:4975`) are test helpers, and the Go client spawns through `exec.Command`
with argv (`git -c` is a git config flag, not a shell).

Checks: the row is seven cells under the escape-aware split; `git apply --check` answers rc 0 for this
hunk alone and together with the SEC-02 hunk on `wt/go-dev-root`'s working tree; the test the row cites
was run by me at `900db14` -
`cargo test --offline the_pane_command_unsets_the_tmux_pane_variables_and_the_denied_keys` -> 1 passed.
