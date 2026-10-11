# The agenthub_client gitlink follows the pushed client head

**Change.** `agenthub_client` in the main checkout moved from `36f455ee` to `694cd86` (`fix(seat): relaunch delivers the store skills into the omp seat's own agent directory`), the pushed client head the owner named on 2026-10-11 06:18Z.

**Why the pointer lagged.** The submodule's own worktree already sat at `694cd86` while main still recorded `36f455ee`, so the recorded pointer was behind the checked-out state; the submodule tree is clean, so nothing was discarded to record it.

**Verified.** `git ls-tree HEAD agenthub_client` before = `36f455ee`; `git status --porcelain` inside the submodule empty; `694cd86` present locally and reachable; recorded pointer after = `694cd86`. Committed by explicit pathspec, authored as the main checkout's own HEAD author rather than the repository's configured identity, which is still the corrupt `scan test` from incident `7e6ab69c`.
