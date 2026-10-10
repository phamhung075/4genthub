## The gofmt instance's counts now carry their measurement base, because they had already expired

### Changed
- **`agenthub_go/NEXT_GEN.md:705` (the ninth instance under rule 16):** the sentence said the counts were re-measured "at the tip this instance was written (`76e04233`)" — **a hash that was the tip then and is an ancestor of the tip now** — and it now says exactly that, plus what the re-measurement actually showed: **the counts belong to the base and not to the tree.** `1277` tracked `.go` files at the root against `1275` under `agenthub_go` at `76e04233`; **`1275` against `1273` minutes later at `ba46ffdc`**. **A count quoted without its base is a claim that has already expired** — which is this clause's own subject, and it is why the pod's row `369df228` exists in the same words for another seat.

### Verified
- **Both pairs measured, each with its base named:** `git ls-files '*.go' | wc -l` → **1277 / 1275** at `76e04233` and **1275 / 1273** at `ba46ffdc`, the first pair re-derived from the commit itself (`git ls-tree -r --name-only <base>`), not from memory.
- **One changed line in the rule home, and no historical entry rewritten:** the earlier changelog entries keep the base they were written against, because this entry names it instead.
- **Rule 16 (`:699`) and rule 17 (`:709`) still match exactly once each**, so the instance's neighbours are intact.
