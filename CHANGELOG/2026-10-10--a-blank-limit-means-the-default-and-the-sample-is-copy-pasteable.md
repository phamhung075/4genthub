## `cp .env.sample .env` is a working client, and a blank limit means the default

### Fixed
- `agenthub_client/.env.sample` shipped `COMPACT_WARN_TOKENS=` BLANK while `agenthub_client/src/agenthub_client/watch.py` read each limit with `int(os.environ.get(...))`. The README tells the operator to copy that file whole, so the documented first step produced a client in which EVERY verb exited 1 with `ValueError: invalid literal for int() with base 10: ''` before it could do anything - and, because `paths.py` loads the client's own `.env`, four modules of the client's suite died at collection the same way.
- `agenthub_client/src/agenthub_client/paths.py` `env_limit` now owns that read: a BLANK value means the default, and a value that is present but not a number still fails loudly. Every integer limit uses it - the three in `watch.py` and `compact.py`'s `--quiet` default - and the sample ships the documented defaults (250000 for the warn limit, which is what the README's table says), with its header stating what a blank value means.

### Testing
- `agenthub_client/tests/test_watch_tools.py`: a blank limit resolves to the default rather than raising, and the shipped `.env.sample` loads WHOLE without taking a verb down. `agenthub_client/tests/test_compact_supervisor.py`: a blank `COMPACT_QUIET_SECONDS` is 15 rather than a crash on startup. Red before the fix: the suite stopped at collection with four `ValueError` errors in this checkout.
- Client repository, from its own root: `PYTHONPATH=src python3 -m pytest tests -q` -> 294 passed, and `ruff check src tests` -> the same three findings that already exist at the previous commit.
