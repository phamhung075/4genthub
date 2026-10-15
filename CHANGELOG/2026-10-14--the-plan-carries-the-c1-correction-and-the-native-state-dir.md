# The plan carries the C1 correction and the native state-dir value

The owner's instruction before step 4 was "check C1 against `ps` … and correct the plan if C1 is already
met". C1 was corrected in a changelog entry when `NEXT-GEN2.md` was held by another session; that session
has committed (file clean, no other seat's lines in flight), so this commit lands the correction in the
plan itself. Three edits, no other content:

1. **The group's opening paragraph** claimed the five seats "are still hosted by the OpenRig daemon (node)
   and one `pi-runner.js` per seat" and that `agenthub-runtime` daemons "host no seat". Kept as history,
   with a dated correction beneath it: that stopped being true on 2026-10-14, and the standing decision is
   unchanged (OpenRig's processes stay up until C5, so "up" no longer means "hosting").
2. **The C1 row** `[ ]` → `[x]`, with the measurement: no `openrig` and no `pi-runner.js` process;
   `agenthub-runtime --state-dir ~/.config/4genthub status 4genthub-min` → `lead|go-dev|fe-dev|reviewer`
   `omp Running`, `architect claude-code Running`; every seat's pane is the runtime's own wrapper in the
   runtime's tmux root (`TMUX_TMPDIR=~/.config/4genthub/tmux`, `dead=0` ×5) and each agent is its child.
   The superseded merge/install sentence is kept as a quotation and replaced with the facts: merged as
   `a118585`, room on tip `4567c37`, installed `4genteam` `747d761b…` and `agenthub-runtime` `c1272c6c…`.
   The overlays residual defect is named beneath the row, with its changelog, as outside the check's words.
3. **The C4 precondition (1)** named `~/.openrig/state/omp/4genthub-min-reviewer@4genthub-min/.config/4genthub`
   as the value for `CUTOVER_STATE_DIR`. With OpenRig removed that path does not exist; the value is the
   native state root `$HOME/.config/4genthub`. The *reason* the row gives — two readings that do not name
   their daemon are not comparable — is kept, and now requires the run's provenance to carry the socket and
   both binaries' sha256, which is what the 2026-10-14 run does.

## Evidence
`git show --numstat` on this commit (one file, `NEXT-GEN2.md`); `ps -eo args`, `agenthub-runtime status`,
`tmux list-panes` with `TMUX_TMPDIR=~/.config/4genthub/tmux`, `sha256sum` of both installed binaries.
