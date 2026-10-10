## The legacy Python package builds again: hatchling refuses a readme outside the project directory

### Fixed
- `agenthub_main/pyproject.toml:53`: `readme = "../README.md"` -> `readme = "README.md"`. Hatchling refuses a readme path outside the project directory **by name**, so every wheel and sdist build of this package failed at metadata validation while CI and both Python images build it.
- **REPRODUCED FIRST, WITH A CONTROL, on a scratch copy that reproduces the layout rather than in this tree.** The defective form, taken from `HEAD`, fails `uv build --sdist agenthub_main` with `ValueError: Readme path must be within the project directory: ../README.md`, raised by `hatchling/metadata/core.py:550` during `validate_fields`; the same build of the same copy with this one line changed succeeds. In the real tree, `uv build --sdist --out-dir /tmp/out-real agenthub_main` -> **Successfully built agenthub-0.0.1.dev2605+db485a7f.tar.gz**, exit 0.
- **The target exists, which is why this one line is the whole repair and not the first of two failures:** `agenthub_main/README.md` is present in the worktree, in `HEAD` and in `827b8ecb`.

### Notes
- Only the readme line changed: `git diff HEAD -- agenthub_main/pyproject.toml` is exactly that line, blob `9febe23d` -> `abea23f6`, and the new blob equals `827b8ecb:agenthub_main/pyproject.toml` — this path is one of the four whose content came from the other line, so the check was run deliberately rather than assumed.
