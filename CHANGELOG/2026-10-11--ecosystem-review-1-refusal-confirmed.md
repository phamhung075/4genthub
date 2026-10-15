## Ecosystem review 1 - the refusal claim, confirmed in kind

### Changed

- `ai_docs/operations/ecosystem-review-2026-10-11.md`: finding 5's refused-row sentence now carries the confirmation
  the claims gate asked for. The lead re-ran the attempt at 2026-10-11T10:38:56Z -
  `the task queue create --destination 'human@4genthub-min' --summary '…' --body '…' --human-intent decision --json` ->
  `{"error":"invalid_human_notification","message":"humanIntent/humanDetail require a human destination; agent
  continuation belongs in its own qitem."}` - which is the third of the four throws
  (`queue-repository.ts:1560`), read at the site. The probe persisted no row, so the earlier attempt stays
  un-re-derivable from the store and the "which of the four fired" caveat is kept for that attempt only. Nothing else
  in the note changed.

### Impact

- Documentation only. No code, no client change, no live rig action by this seat, no row created, no decision made.

### Verified

- The throw site read at `/home/daihu/__projects__/reference/packages/daemon/src/domain/queue-repository.ts:1552-1566`:
  the quoted error message is the `:1560` string exactly. The reproduction itself is the lead's measurement and is
  reported as theirs. No test, build or formatter was run, because no code changed.
