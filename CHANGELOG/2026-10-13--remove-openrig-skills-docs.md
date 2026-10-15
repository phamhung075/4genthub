# Clean OpenRig References from Skills & Client Documentation

Remove legacy OpenRig daemon and dependency mentions from client skills and operator documentation, establishing `4genteam` native supervisor as the single orchestrator. OpenRig codebase and historic review materials remain isolated in their respective folders for review only.

## Summary of Changes

- **Client Skills Overhaul (`agenthub_client/skills/`)**:
  - `install/SKILL.md`: Removed OpenRig daemon startup checks (`~/.openrig/daemon.json`, `rig daemon start`) and obsolete paths; preserved essential directories (`~/.config/4genthub`, `~/.config/deepseek`) and doctor validation.
  - `spawn-team/SKILL.md`: Updated team launch documentation to reflect the native 4genteam supervisor stack (`seats + rigd + auto-compact + watchdog + bridge + watch wall`) instead of OpenRig daemon.
  - `watch-team/SKILL.md`: Clarified room watch instructions using `4genteam watch --rig <rig>`.
  - `rig-runtime-switch/SKILL.md` & `seat-runtime-switch/SKILL.md`: Cleaned descriptions and instructions to target team rigs via 4genteam.
  - `room-decision-request/SKILL.md`: Updated architecture to reflect Jev AI auto-selection and 4genteam client supervisor drain, replacing OpenRig daemon references.
  - `test-driven-development/SKILL.md`: Cleaned frontmatter metadata from `openrig` to `agenthub`.
- **Project Root Documentation & Guidelines (`README.md`, `AGENTS.md`)**:
  - `README.md`: Replaced `Rig and OpenRig workflow` with `Rig and Team Orchestration Workflow` under `4genteam`; clarified that client LLMs run locally on client machines and server hosts no client LLMs; noted OpenRig code is retained for review only.
  - `AGENTS.md`: Updated header and rule 6 to explicitly mandate `4genteam` as the single orchestrator and document OpenRig retirement.
  - `ai_docs/operations/`: Added OpenRig decommissioning notices across operational manuals (`watching-openrig-seats.md`, `openrig-seat-limits.md`).
- **Submodule Pinning**:
  - Pinned `agenthub_client` commit `536ad18`. All unit tests pass cleanly.
