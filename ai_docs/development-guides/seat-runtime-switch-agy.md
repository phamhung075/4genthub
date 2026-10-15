# Switching a seat's runtime (omp, claude-code, agy) with its context

Owner request, 2026-10-15: run the `4genthub-min` team on `agy` with the same context as the running team. The predecessor 4genteam could do this for claude and codex; the native client cannot yet.

## What exists (measured 2026-10-15)

- `agenthub_client/rust/agenthub-runtime/src/runner/mod.rs` `child_argv` has native paths for `omp` (RPC) and `claude-code` (stream-json bridge). `agy` and `codex` are refused by name (test `a_runtime_without_a_native_path_is_refused_by_name`).
- `internal/clientsync/switchverb.go`: `sync switch` records a runtime change in the cloud and prints manual steps; it applies a model change only.
- `agy` 1.3.5 is installed (`~/.local/bin/agy`). Its print mode takes `--input-format stream-json --output-format stream-json` (one NDJSON message per line on stdin, one turn each), `--model`, `--dangerously-skip-permissions`, `--mode accept-edits|auto|plan`, `--conversation <id>`, `--add-dir`. That is the same shape as the claude-code bridge, so the agy runner is a sibling of `runner/claude.rs`, not a new protocol family.

## Work

1. **agy runner.** `AgentRuntime::Agy` gets a `child_argv` arm (print mode, stream-json both ways, policy `yolo` -> `--dangerously-skip-permissions`, otherwise `--mode auto` or the mode `approval_mode` maps to; model from the seat spec) and a bridge that parses agy's stream-json events into the same seat events the claude bridge emits. Tests beside `runner/claude.rs`; replace the refusal test with one for `codex`.
2. **Context carry-over.** A resume id cannot cross runtimes, so the context travels as a handoff brief: on a runtime switch the client reads the old seat's last session log (`~/.config/4genthub/rooms/<room>/seats/<seat>/sessions/*.jsonl`), builds a bounded brief (the seat's role prompt, its open MCP tasks with their progress notes, the last assistant turns, the files it touched), writes it to the seat directory, and sends it as the first message of the new session. Same-runtime restarts keep using the runtime's own resume.
3. **`sync switch --runtime R`.** Applies in place: stop the seat, build the brief, write the new runtime to the room spec, start the seat under `R`, deliver the brief. `--apply none` keeps today's record-only behavior. The cloud record stays the authority.
4. **Team file.** `team.json` `runtime` accepts `agy` for any seat; `4genteam up` validates the runtime is installed before launch.

## Constraints

- No compatibility path: the manual-steps text in `switchverb.go` is deleted once the verb applies the change.
- The brief has a size cap from an environment variable (no hard-coded number), and never includes `.env` values or tokens.
- Verify with one seat first (the reviewer), compare its first answers with the old seat's open tasks, then switch the rest.
- Models: `agy models` lists what the runtime accepts; the team file names the exact id.
