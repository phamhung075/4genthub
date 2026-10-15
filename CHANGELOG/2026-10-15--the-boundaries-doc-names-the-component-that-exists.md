# The boundaries doc names the component that exists

`ai_docs/core-architecture/rigd-boundaries.md` is the doc of record for the terminal connector. After the
machine-level supervisor was renamed to `agent` (`bc725e6`, 2026-10-15) the doc's section 7 followed the
rename and the rest of the file did not: it instructed a verb that answers `4genteam: unknown command
rigd` (executed, exit 2), named a state file the client no longer writes, and carried 71 `rigd` tokens,
including its title and section 1's ruling. This is the doc half of the architect's decision
`seats/architect/DECISION-doc-of-record-naming-after-the-rigd-rename.md` (D1-D4). No code, no test and no
pin.

## Changed

- **The component reads `agent` wherever the doc names it** - the title, section 1's ruling, and the
  narrative of 2.3a, 3.2, 4.1, 4.4, 5, 6 and 7.1-7.11 - 55 lines, 69 of the file's 71 `rigd` tokens. The
  verb the doc instructs is `4genteam agent` (1, 3.2's "what the user sees first", 4.4's withheld note,
  and 5's step 2), which exists and lists itself in its own help.
- **agent's state file is `agent.json`** in the six clauses that name it (5's phase-2 sentence, 7.1's
  `rigs` list, 7.2's heartbeat paragraph, 7.8's data-list option, and 7.9's two `rigs` clauses). The
  client's own name is `<seat store>/agent.json` (`AgentStatePath`, `internal/clientservices/state.go`,
  and `defaultAgentStatePath`'s comment calls it the path 7.1 and 3.2 name).
- **The consent file takes its own name, `agent-consent.json`** (3.2's local-consent clause), per D3: the
  file the user writes by hand must not be the file agent writes. Mode 0600 and "the server never writes
  this file" are unchanged.
- **The phase-2 companions follow the same rule** (D4): the audit line is
  `<seat store>/agent-audit.jsonl` (3.2's audit clause) and the withheld directory is
  `<seat store>/agent-withheld/` (4.4).
- **A dated naming note sits under the title** (D2), recording the rename, the kept file name and the
  measured cite count - 40 tracked files, 55 occurrences, 24 of them code comments
  (`git grep -l -- rigd-boundaries.md` at main `04fcd5d7`) - so a later reader decides the file rename on
  evidence rather than on taste.
- **One grammar repair the rename caused:** 7.9's latch clause reads "an agent restart", not "a agent".

## Not in this change

- **The file name is unchanged: `rigd-boundaries.md`** (D2). 40 tracked files cite that path and no
  instrument reads prose, so a rename today is a hand sweep whose mistakes nothing catches - board T14's
  class. It becomes worth doing if the doc is ever published consumer-facing.
- **Two clauses keep the old token because they are the record:** 7.2's sentence on the six safeguard
  names, which is where the rename itself is stated, and 7.9's ruled peak clause. Both are dated rulings,
  not instructions.
- **Nothing here is implemented by the new names.** `agent-consent.json`, `agent-audit.jsonl` and
  `agent-withheld/` have no reader until phase 2 (`CapabilityCommands = "commands"`,
  `agenthub_client/internal/clientsync/connector.go:57`, is the capability flag only); D3's naming is the
  design a phase-2 implementer follows, stated now because the doc is what that implementer reads.
- **7.1's "There is no agent verb yet" is renamed, not reworded.** The verb exists
  (`clientlifecycle/agent.go:691`, `4genteam agent status`), so after the rename the clause reads as a
  stale statement of the state on 2026-10-11; rewording it is the architect's to rule, and it is named
  here rather than changed silently.
- **No code, no test and no pin:** the diff is this doc and this entry.
