## progressHistoryUtils.ts survives the O8 mount, and its deletion rides the carry

### Changed
`ai_docs/core-architecture/agenthub-system-architecture.md:411` said `ProgressHistoryTimeline.tsx` and
`progressHistoryUtils.ts` are deleted together in the commit that mounts O8. The reviewer's frontend gate
found that this does not describe the code, and the lead routed the doc fix (row
`qitem-20261011042715-c447f8b0757f5284`). The line now records what is true at fe-dev's mount commit
`f05714c4` (not yet on main):

- `ProgressHistoryTimeline.tsx` is deleted there, so the two timelines never coexist.
- `progressHistoryUtils.ts` survives, correctly under ruling `0cf37f6f` Q1: the mount re-pointed its callers
  instead of removing them. It has three importing files and four live functions: `SubtaskRow.tsx`,
  `ui/ProgressDisplay.tsx` and the new `lib/taskTimeline.ts`.
- Its deletion rides the carry, as a go-dev row.

The ruling is not re-opened, and the subtask-dialog sentence (Q2: no progress section until the subtask's
own `details` are served) is unchanged. Docs only; the callers were measured by `git grep` at `f05714c4`.
