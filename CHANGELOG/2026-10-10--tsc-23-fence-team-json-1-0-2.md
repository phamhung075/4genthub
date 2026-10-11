## TSC-23 fence (5/5): `team.json` moves the `project-4genthub` ref to 1.0.2

Fence holder: writer. Spec: §7 of `DISPOSITION-tsc-23-count-cluster-2026-10-10.md` ("`team.json:9` is inside the writer's fence, so the bump is the follow-up's, not the train's — but it rides with the four text commits").

### Changed
- `scripts/team/4genthub/team.json:9` — the `project-4genthub` entry's `"version": "1.0.1"` becomes `"1.0.2"`.

**Why 1.0.2 and not 1.0.1:** module versions are immutable, and 1.0.1 is the armed, owner-approved-as-is publish whose body carries the uncorrected text. The corrected text therefore cannot reuse 1.0.1, so the ref moves. It is **one line**: the `company_overlay` list carries slugs only and `overlayBody` derives each op's version from the team's module table (`agenthub_client/internal/clientteam/plan.go`), so this single line moves the publish target and the overlay op together. No other `1.0.1` under `scripts/` is this ref (the rest are vendored `caveman/` files), and the one test that once pinned it was removed with the retired Python client (`91cf4295`).

### Verified
- `python3 -c "import json"` on the file: parses; the version list reads `['1.0.2', '1.0.0', '1.0.0', '1.0.0', '1.0.0', '1.1.0']` — nothing but the ref moved.
- §4's per-file loop over the four text files: `stale=0` and `command>=1` on every one.

### Still owed after this landing, and not by this commit
The chain needs **two applies**: the armed 1.0.1 run, then — after these five commits — the second publish, re-resolve and `4genteam sync rig --update`. A landing that stops at the commits is inert. Two carriers are deliberately **not** edited here: the `seedlibrary` guides (`guide-fe-dev.md`, `guide-reviewer.md` — go-dev's fence, still `stale=1`) and the four rig mirrors, whose sentence is byte-identical to the served render and which are the pipeline's output rather than a source.
