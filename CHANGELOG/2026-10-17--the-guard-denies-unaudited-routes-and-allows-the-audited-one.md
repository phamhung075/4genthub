# The guard denies the unaudited routes and allows the audited one

The `comm-guard` fragment denied `Bash(4genteam send:*)` while `comm-guard-skill` names `4genteam send` as
the only way to message a seat. Both statements were true at once: since 2026-10-15 the client's `send` is
the audited path - it builds the sender's policy at send time, writes the decision line, delivers and
writes the outcome line - and the fragment's deny list was carried over unchanged from the era when the
checker's own `send` was the audited verb. So the guard denied the one route it told every seat to use, and
`commpolicy.BypassSuspected` flagged it as a bypass beside it.

### Fixed

- **The deny list binds unaudited routes only**: `Bash(4genteam input:*)`, `Bash(tmux send-keys:*)`,
  `Bash(tmux paste-buffer:*)`. `Bash(4genteam send:*)` leaves the deny list and joins the allow list beside
  `Bash(4genteam whoami:*)` - the shape the guard had when the checker's `send` was the audited verb, with
  the spelling the client actually carries.
- **The rail's `room queue create` stays admitted**: it records a row the daemon owns, and the row is read,
  not injected; the client's bypass set drops it as well.
- **A seed content change gets its own version**: `seedVersion` 1.4.15, with the new version's 26-file
  content set recorded in `seedcontent.lock.json` by the package's own instrument
  (`TestSeedVersionNamesOneContentSet -args -update-seedcontent-lock`).

### Testing

- Red first: the seedlibrary and renderer expectations were flipped before `comm-guard.json` was touched.
  `TestLoadEmbeddedSeedsCarryCommGuard` failed on the old four-deny list, and
  `TestRenderSeatCodexRulesDenyTheDirectSendSurface` failed on the old fragment - the deny it demanded was
  the defect.
- `cd agenthub_go && go build ./... && go test ./...`: green; `gofmt -l agenthub_go` empty.
- MEASURED, the rendered claude-code settings fragment for a seat carrying the embedded seeds (a throwaway
  `RenderSeat` call, deleted after the run):
  `allow = ["Bash(4genteam whoami:*)","Bash(4genteam send:*)"]`,
  `deny = ["Bash(4genteam input:*)","Bash(tmux send-keys:*)","Bash(tmux paste-buffer:*)"]`.
- The codex rules render carries three `decision = "forbidden"` prefix rules (`4genteam input`,
  `tmux send-keys`, `tmux paste-buffer`) and no rule for `4genteam send`.
- The client half is its own commit in `agenthub_client` (`internal/commpolicy`): a built `seatcheck
  audit-scan` over a file holding all five spellings reports exactly `4genteam input`, `tmux send-keys` and
  `rig send`, and stays silent on `4genteam send` and `room queue create`.

### What this does not do

- No new deny entries: the `rig` spellings were never in this fragment (the client's bypass set keeps
  them), and adding more was not this row.
- No change to `comm-guard-skill.md`; its text already names the audited path, and its digest test still
  matches the committed source.
- No live seat picks the fragment up until it is reseated: a rendered seat dir keeps the file it was
  launched with.

### Supersedes

- `CHANGELOG/2026-10-15--the-comm-guard-points-at-the-audited-send-path.md`: it moved the guard SKILL to
  `4genteam send` and kept the deny list byte-identical, so the fragment denied the path the skill named.
  This entry changes that deny list; the skill text is untouched.
- The client-side premise is superseded by `agenthub_client`'s
  `CHANGELOG/2026-10-17--the-bypass-set-is-the-unaudited-send-routes.md`, which retires
  `2026-10-15--the-comm-guard-binds-the-native-spellings.md`.
