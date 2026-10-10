## Caveman is removed; the token-economy skill now covers messages between seats

### Removed
- `scripts/caveman` (git submodule, tag `v3.2.0`) and its `.gitmodules` entry.
- `scripts/caveman-proxy.sh` (build/start/stop/stats runner for the caveman proxy). No seat ever used it.

### Changed
- `agenthub_client/skills/share/token-economy/SKILL.md`: new section "Messages Between Seats" (seven rules, a never-shorten list, one message template) and the description names seat messages. The skill reaches seats through the client's `skills/share` delivery. Its quality gate is that the reader can act without a follow-up.

### Why
- The voice skill was already replaced by the plain "Writing style" section in `guide-common.md`. The measured evidence for the proxy was one trial in which a maximum was reported as 88 instead of 89, and only the Claude Code seat (`4genthub-min` architect, 1 of 19 seats) could use it. Seat cost is mostly input and cache re-reads, so the saving that applies to every seat is shorter, more targeted seat-to-seat text.

### Not changed
- Earlier `CHANGELOG/` entries that mention caveman stay as history.
- `.claude/skills/token-economy` is a separate copy in the `.claude` submodule and does not have the new section.
- `~/.caveman/` (built binaries) lives outside the repository and was not touched.

### Testing
- Documentation and submodule removal only; no Go or frontend code changed. `git status` shows `.gitmodules` modified and `scripts/caveman` and `scripts/caveman-proxy.sh` deleted, all unstaged.
