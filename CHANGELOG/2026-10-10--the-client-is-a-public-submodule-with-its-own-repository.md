## `agenthub_client/` is a git submodule of the public `4genthub-client` repository

### Changed
- `agenthub_client/` is no longer tracked in this repository: it is a submodule at the SAME path (`.gitmodules`, `git@github.com:phamhung075/4genthub-client.git`), so every path that names it (`agenthub_client/tests/`, `paths.CLIENT_DIR`, the editable install) keeps working.
- The client's 15 commits were split out with `git subtree split` and published as the new repository's `main`, with the author identity rewritten to the GitHub noreply address and one absolute path scrubbed from a commit message. The new repository adds a `README.md` and a `.gitignore`.
- Why: the client is what runs on a developer's machine for ANY project, so it is published and versioned alone; the server stays here.

### Testing
- `PYTHONPATH=agenthub_client/src python3 -m pytest agenthub_client/tests` -> 325 passed before the split and after the submodule was in place.
