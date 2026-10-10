## An installed client no longer dies at import, and names `AGENTHUB_REPO_ROOT` instead

### Fixed
- `agenthub_client/src/agenthub_client/team_setup.py`: the module imported the repository's Claude hooks AT MODULE LEVEL (`from utils.env_loader import get_project_root`). `paths.HOOKS_DIR` is derived from the installation directory, so an install that is not a checkout died with `ModuleNotFoundError: No module named 'utils'` before anything ran - and because `cli.py` imports this module, the whole `4genteam` CLI died with it, `--help` included.
- **Measured first**: a wheel built from the package, installed into a throwaway venv, with `AGENTHUB_REPO_ROOT` unset -> `site-packages/agenthub_client/team_setup.py line 117, in <module> ... ModuleNotFoundError: No module named 'utils'`; `4genteam --help` died the same way. Control: with `AGENTHUB_REPO_ROOT=$PWD` the same import was `import ok`.
- The hook import moved into `get_project_root()`, where its result is used, and a missing hook tree now raises a named failure - `4genteam: this client needs the repository's Claude hooks, which only a checkout has (No module named 'utils'). Set AGENTHUB_REPO_ROOT to the repository root; looked in <HOOKS_DIR>` - instead of a bare `ModuleNotFoundError`. The name is unchanged because it is this module's seam.

### Tested
- The same wheel, rebuilt and reinstalled with the fix and NO `AGENTHUB_REPO_ROOT`: `import agenthub_client.team_setup` -> **import ok**; `4genteam --help` -> the top-level document, exit 0; `4genteam team --help` -> its usage, exit 0; `team_setup.get_project_root()` -> the SystemExit naming `AGENTHUB_REPO_ROOT`; with the variable set -> the real root.
- `test_team_setup.py`'s `test_import_project_uses_the_hooks_project_root_derivation` asserted IDENTITY with the hooks' function, which held only because the import was at module level. It now asserts the property that survives the move - the module returns the hooks' answer, and the identity is now FALSE, which is what proves the import is no longer at module level. The other 43 tests in that file pass unchanged; they replace `team_setup.get_project_root`, which keeps its name.
- Commands and results: `cd agenthub_client && python3 -m pytest tests/test_team_setup.py -q` -> **44 passed**.

### Known, stated rather than hidden
- A wheel still derives `REPO_ROOT` as the Python lib directory, so `LOG_DIR`/`TEAM_DIR`/`SKILL_INVENTORY` are wrong there (`LOG_DIR: <venv>/lib/logs`, measured). Reading verbs are unaffected; a verb that WRITES (`compact` mkdirs `LOG_DIR`) would write into site-packages. Same defect class one step further out; reported, not fixed unasked.
