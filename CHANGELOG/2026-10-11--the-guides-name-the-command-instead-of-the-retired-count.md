## The seat guides name the tsc command, not the retired 23-error count

### What changed
Two seedlibrary blocks carried a sentence that counted TypeScript errors by name: `guide-fe-dev.md` said the
untouched frontend tree "reports 0 errors" because "the 23-error baseline was removed 2026-10-03", and
`guide-reviewer.md` carried the same claim in its known-failures list. A count written into a guide goes
stale the moment the tree moves, and this one had: the exception list was retired on 2026-10-03, and the
guides kept citing it as if it were still the thing to compare against.

**The fence is the sentence that names the command instead:**
- `guide-fe-dev.md`: "**the command is the baseline, never a number written down here**: run it on the
  untouched tree, count the `error TS` lines it prints, and compare your run against that".
- `guide-reviewer.md`: "**run `npx tsc --noEmit -p .` on the untouched tree and read the number it prints;
  the command is the baseline, not a number written down here**".

Both keep the history where history belongs (`agenthub-frontend/CHANGELOG.md`), cited by its text rather than
by a line number, because three different line numbers circulate for that entry as the file grows.

### The pairing, re-recorded
Each block is pinned in `guides.lock.json` twice: by its own sha256, and by the sha256 of the repo-side source
it was copied from. The guard refuses a shelf that disagrees with the lock, and it said so in these words:

```
guide-fe-dev: the shelf carries 734bc48b379e but guides.lock.json records 3fab6144f514;
re-copy the block and re-record the pairing
```

Both digests were re-recorded, `sha256` and `source_sha256` together, because the repo-side sources
(`ai_docs/operations/seat-guides/fe-dev.md` and `reviewer.md`) are absent BY DESIGN — the embedded shelf is
the only home for the guide text now, and `TestTheTxtSourcesCarryTheCommandAndTheRecordedSourcesAreGone`
asserts exactly that. Moving one half alone leaves a faithful copy reported as `source-differs`, which is how
the second half of the pair was found.

### Verified
`go test -count=1 ./fastmcp/seat_management/domain/seedlibrary/` → **ok 0.034s**, and the whole family green:
`go test -count=1 ./fastmcp/seat_management/...` → 14 packages ok, 0 FAIL. `go build ./...` rc 0; `go vet
./fastmcp/seat_management/...` clean. The lock guard was RED before the re-record, on exactly the two digests
quoted above, and green after.

### What this does NOT do
It changes the shelf and the lock; it does not touch a running rig. The served rendering of these seats is
re-published by the owner's publish → re-resolve → `4genteam sync rig --update` step, which is theirs to run.
