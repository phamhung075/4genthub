## The friction channel's no-MCP door survives the client relocation, and the guard that found it was red

### Fixed
- `agenthub_go/fastmcp/server/httpapp/seat_feedback_script_test.go`: the guard executed `scripts/seat_feedback.sh`, which the relocation deleted, so BOTH of its tests failed on the worktree — `cannot find the submission script: stat ../../../../scripts/seat_feedback.sh: no such file or directory`, at `:37` and `:82`. The script had moved to `agenthub_client/src/agenthub_client/seat_feedback.sh` byte-identical (empty `diff` against `git show HEAD:scripts/seat_feedback.sh`; landed in `ef359526`), and the guard now runs it there.
- `agenthub_client/src/agenthub_client/cli.py`: `4genteam feedback ...` is a verb. Without it the word fell through to `return lifecycle("up", args)` — a seat on a runtime with no MCP asking for the friction channel would have started a rig (daemon, compaction supervisor, herdr, UI) instead of reporting anything. The verb runs the packaged script and returns its exit code, and never enters the lifecycle path.
- `agenthub_client/pyproject.toml`: `[tool.setuptools.package-data]` names `seat_feedback.sh`. Measured on the built wheel both ways (`uv build`, then the archive's member list): BEFORE, twelve modules and no script; AFTER, `agenthub_client/seat_feedback.sh` present. Without that line only an editable checkout had the door — every other install had the verb and nothing to run.

### Verified on the artifact, not on the source tree
- Wheel built from the package, installed into a throwaway venv with `uv pip install`, and driven there against a local stub of the route: `4genteam feedback --layer openrig --text ...` exits 0, and the stub receives `POST /api/v2/openrig/feedback` with the bearer token and the body `{"room","seat","session","layer","text"}`; a layer outside the vocabulary exits 2 having dialed nothing. The Go guard, both tests: `ok agenthub/fastmcp/server/httpapp 0.108s`.
- What an install needs, stated because it is not obvious: `AGENTHUB_REPO_ROOT` must point at a checkout. Without it a wheel install dies at import — `ModuleNotFoundError: No module named 'utils'` (`team_setup.py:117`) — because `paths.HOOKS_DIR` is derived from the installation directory.

### Not in this commit
- `README.md:147` and `ai_docs/api-integration/surface-inventory.md:322` still name `scripts/seat_feedback.sh` as the no-MCP door. `README.md` was already staged by another seat when this was measured, so the line is reported rather than edited; the inventory sentence is its own one-line fix.
