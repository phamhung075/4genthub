## The client package's last four files are tracked, so a fresh checkout has all of it

### Added
- `agenthub_client/pyproject.toml`, `agenthub_client/src/agenthub_client/__init__.py`, `cli.py` and `paths.py`: the four package files that `ef359526` could not carry. A pathspec commit cannot add an untracked file, so that commit took only what had already been STAGED — the renamed modules and the ported tests — and left these four, which were new files rather than renames. Until this commit a fresh checkout had no package metadata and was missing three of the module set's own files.
- **STATED PLAINLY: PINNED, NOT REVIEWED.** The content is committed as it stands; the evidence that it works is `python3 -m pytest --noconftest -p no:cacheprovider agenthub_client/tests -q` -> **304 passed** with these files present on disk. A later edit by the author commits on top of this one.
