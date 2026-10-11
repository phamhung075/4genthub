## A new room launches with its DeepSeek key, a working directory that survives a rebuild, and the seat policy, from one `4genteam sync rig`

### Fixed
- `agenthub_client/src/agenthub_client/seat_sync.py`: creating a room and its seats by hand needed four manual repairs, and `cmd_rig` now does each of them.
  - **Key:** a room with a `deepseek/` seat gets `<out>/<room>/.env`, a link to the one key file `~/.config/deepseek/env` (`DEEPSEEK_ENV`). The secret keeps one home; a missing key file is a refusal that names the path, not a seat that fails at launch with `No API key found for deepseek`.
  - **Working directory:** every member's `cwd` is the room directory. The server's `.` resolved to `rig/`, which `swap_dir` replaces on every build, so a seat launched from it kept a deleted directory.
  - **Policy:** every member launches with `builtin:yolo` (`SEAT_PERMISSION_POLICY`), as the `4genthub-min` seats do.
  - **First launch:** the render install creates a seat's omp agent directory when it is absent, instead of refusing a rig that has never been up and needing a second run.
- `rig.yaml` is no longer the server's text byte for byte: it is the server's spec with `cwd` and `permission_policy` set per member.

### Testing
- `agenthub_client/tests/test_seat_sync.py`: the verbatim and refusal cases are replaced by cases for the launch spec, the agent-directory creation, the key link and the missing-key refusal; `pytest tests` gives 321 passed and 1 failed (`test_team_setup.py::test_context_files_respect_word_limits[area-docs]`, a word-count limit on a file this change does not touch).
