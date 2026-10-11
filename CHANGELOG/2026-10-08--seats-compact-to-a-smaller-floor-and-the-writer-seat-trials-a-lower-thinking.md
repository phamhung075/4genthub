## Seats compact to a smaller floor, and the writer seat trials a lower thinking level

### Changed
- `scripts/openrig_seat_policy.py`: every seat's generated `config.yml` now carries `compaction.keepRecentTokens: 8000` (omp default 20000), which should bring the post-compaction context floor from ~42k to ~30k. The `writer` seat also gets `defaultThinkingLevel: medium` (default high) as a trial, because reasoning is ~41% of a live context. `render_config` takes the rig so the trial table `SEAT_THINKING` is per rig; `openrig_seat_sync.py` passes it.
- Takes effect when each seat next starts. Lazy loading was measured and left alone: fixed overhead is ~11.8k tokens and skills already load descriptions only.
