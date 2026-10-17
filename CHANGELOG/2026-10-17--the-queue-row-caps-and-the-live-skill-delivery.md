# The seat guide states the queue caps the CLI enforces, and the live skill delivery

Two documents of record named an instrument that answers otherwise.

**The queue-row rule.** `shared-modules/guide-common.md` rule 4 said a queue row is "one line plus the
commit sha, at most 600 characters". The client caps the two parts separately:
`4genteam room queue create --help` prints `--summary TEXT<=120 [--body TEXT<=600]`, and a summary over
120 is refused - `summary cap: 629 chars exceeds the 120-char cap` - creating nothing. A seat that
drafted to the stated 600 lost the row and, having read the rule rather than the reply, believed it had
filed one. The rule now states both caps as the CLI enforces them, so the text and the check agree.

**The delivery.** `ai_docs/operations/seat-friction-loop.md` named `4genteam sync rig` as "the only
delivery". No such verb exists: the sync group is pull/messages/connector/bundle/switch/install-checker/
offline-install/respawn, and `ai_docs/operations/syncing-seats-with-the-cloud.md` records the removal.
What runs is the runtime's own install: every seat start resolves the tree
(share → room → seat) and writes it under the seat's `skills/`, so a change reaches a seat at its next
start. The paragraph now says that.

## Changed

- `agenthub_go/fastmcp/seat_management/domain/seedlibrary/shared-modules/guide-common.md` - rule 4
  names the 120-character summary and the 600-character body, and keeps "the row names the commit sha".
- `ai_docs/operations/seat-friction-loop.md` - the delivery sentence names the runtime's install at
  seat start instead of the retired `sync rig`.
- `agenthub_go/fastmcp/seat_management/domain/seedlibrary/guides.lock.json` - guide-common's block
  digest and its recorded source digest take the new bytes. The interim source file was retired
  (`cb998795`), so the absent source stays the steady state it already was.
- `agenthub_go/fastmcp/seat_management/domain/seedmap/seedmap.go` - `seedVersion` 1.4.14, with the
  ledger sentence for the change.
- `agenthub_go/fastmcp/seat_management/domain/seedlibrary/seedcontent.lock.json` - 1.4.14's content set
  appended.

## Not in this change

- No code behaviour: the CLI's caps are unchanged; the doc moves to them.
- The two docs ride one commit because the guide block's lock digest is what carries the change into a
  rendered seat, and neither document is worth a separate gate.
