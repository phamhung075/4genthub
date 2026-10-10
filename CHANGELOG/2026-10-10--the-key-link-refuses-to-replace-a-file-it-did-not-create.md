## `4genteam sync rig` no longer overwrites an operator's own `<room>/.env`

### Fixed
- `agenthub_client/src/agenthub_client/seat_sync.py` `link_provider_key`: it unlinked ANY existing `<room>/.env` and symlinked the DeepSeek key over it, so a regular file the client did not create lost its content silently. It now replaces only its own symlink (retargeting one aimed at a moved key file) and REFUSES a regular file, naming the path (exit 2) before the build, so a refused run leaves nothing half-applied.

### Testing
- `agenthub_client/tests/test_seat_sync.py`: a refusal case, a case with no DeepSeek seat (no `.env` is created), and the OMP state root redirected into `tmp_path` in the key cases so a test never writes the operator's real directories. `pytest agenthub_client/tests` gives 325 passed.
