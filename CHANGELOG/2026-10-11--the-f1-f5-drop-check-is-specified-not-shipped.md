## The `F1`-`F5` launch check is specified, not shipped

### Fixed
- `ai_docs/operations/seat-friction-loop.md` §2.2 and `CHANGELOG/2026-10-11--seat-friction-loop-design-step1.md`:
  the step-1 design called the `F1`-`F5` drop check "the shipped launch check". It is not shipped at this tip —
  `internal/clientlifecycle/` holds `doctor.go` only, the installed `4genteam doctor` reports the safeguards, and the
  implementation is `63bf909` on `4genthub-min/go-dev` (plan item 1, in flight). Both places now state where it
  actually lives: specified in `ai_docs/core-architecture/seat-skills.md` §6 (4genthub repo), implemented on
  `4genthub-min/go-dev` (`63bf909`), not yet landed — the same wording the client skill pack carries at
  `bad2a53`/`b0354e8`.

### Impact
- Documentation only. No code, no skill text, no push.
