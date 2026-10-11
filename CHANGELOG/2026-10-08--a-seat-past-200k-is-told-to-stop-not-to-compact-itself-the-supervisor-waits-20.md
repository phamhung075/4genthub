## A seat past 200k is told to stop, not to compact itself; the supervisor waits 20 s, not 60

### Changed
- `scripts/openrig_compact_supervisor.py`: the notice no longer tells the seat to run `rig send <self> /compact --raw`. A `/compact` typed while the seat works is only queued as text (observed on skills-dev at 228k: it said "compacting now", nothing compacted). The notice now says to finish the job, stop, and not compact itself; the supervisor sends `/compact` once the seat is idle. `--quiet` default 60 -> 20 s, `--every` default 30 -> 10 s, so the compaction lands about 20-30 s after the seat goes quiet (skills-dev took 84 s before). The 400k hard limit is unchanged.
- `~/.openrig/briefs/4genthub-min.txt` (outside the repo): the context-limit rule says the same.
