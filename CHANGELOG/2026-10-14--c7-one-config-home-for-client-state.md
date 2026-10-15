## 2026-10-14 - C7: the client's state moves to `~/.config/4genthub/` when 4genteam is gone

### Added
- `NEXT-GEN2.md` item C7 (owner ruling 2026-10-14): `~/.config/4genthub/agenthub-seats/` and the config beside it (state, briefs, logs, transcripts, scripts) move under `~/.config/4genthub/`. It lists the target layout, the 7 code sites measured at client `0683c10`, and the order (after C4 and the C5 snapshot, one path change in `clientenv`, one data move, no compatibility layer, no `AGENTHUB_STATE_ROOT` alias).

### Testing
- Documentation only. The site list comes from `grep -rn '\config/4genthub\|AGENTHUB_STATE_ROOT' internal cmd rust scripts` on the worktree.
