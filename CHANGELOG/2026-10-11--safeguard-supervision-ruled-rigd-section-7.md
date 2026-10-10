## Safeguard supervision ruled: rigd section 7, and F4's scope names the safeguards

### Added
- `ai_docs/core-architecture/rigd-boundaries.md` section 7: the architect's ruling on the lead's six boundaries (`qitem-20261010225142-6d506ef31156b50b`, requirement row `e59f4162`, ruling row `1526829a`). The ruling answers the incident where the compaction supervisor and the rig watchdog were not running and nothing alerted.
  - **(a) Where supervision lives:** rigd is the single restart authority. It reuses `spawnChild`/`awaitStart` to run the existing verbs as children. `up` starts rigd only. A separate keeper process was rejected because it would be a second supervision mechanism.
  - **(b) Health report:** each child writes a heartbeat file on every pass, which is new. The process decides running or stopped, and the heartbeat decides silent. Log timestamps are never authoritative: the supervisor logs only when it acts.
  - **(c) Alert:** a new socket frame `safeguard` and a new table `rig_safeguards`.
    - The server raises `safeguard_alert` through the existing notification store, which replays to an offline user.
    - The server also raises a rigd dead-man alert on socket timeout.
    - The doc states that no local, cloud-independent owner surface exists yet.
  - **(d) Threshold:** per safeguard, 3 × the longest legitimate sleep: 30 s, 180 s, 360 s and 75 s. No environment knob.
  - **(e) `doctor` and `up`:** `doctor` is new and read-only, and exits 3 naming each down safeguard. `up` exits 3 before the view, the UI and herdr, and the "continuing without" path is deleted.
  - **(f) Composition:** a new capability `safeguards`. The session, cursor and ping/pong rules are unchanged, and commands stay phase 2.

### Changed
- `agenthub_go/NEXT_GEN.md` F4: the remaining-scope text names the safeguards as phase-1 rigd work.

### Verified
- The architect read the client at `63fd184` for each cited line. Measured on this machine: PID 1 is `init`, and `systemctl --user` reports `offline`.
- No code changed, so no tests apply. Ruling row `1526829a` was read back.
