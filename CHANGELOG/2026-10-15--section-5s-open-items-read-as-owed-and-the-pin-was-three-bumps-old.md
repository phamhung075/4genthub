# §5's open items read as owed, and the pin was three bumps old

**What this changes.** Three lines on the board that told a reader to do work that is done, or named
an identity that has moved. §5 item 3 (the C1 ruling) read as an open assignment while §3 records the
ruling delivered at 05:25:5xZ — now it reads delivered, with its commit and the row it was delivered
against, and with its *own* pointer corrected (the row it called the live assignment row resolves to a
different row). §5 item 2's premise that the MCP tools are unmounted — which §3's item 8 already
corrected — is corrected here too, because §5 item 2 is the unit that premise carried. §3's pin bullet
said the pin was `ae3811c`; it is `6e55e0d7`.

**Why it is not cosmetic.** All three are actionable-direction staleness of the kind the lead ruled GO
on row `qitem-20261015180611-22adb32094a3`: a successor reading item 3 authors a ruling that exists,
and a successor reading item 2 sizes a unit around a tool gap that is closed. The pin is what the run
tree is rebuilt from, so a wrong pin is a wrong run.

**Measured 2026-10-15 18:1xZ at the source, not relayed:**

| Reading | Result |
|---|---|
| `git merge-base --is-ancestor e974fdbf HEAD` (this lane) | **rc 0** — the C1 ruling's commit is on the lane; `git log -1 --oneline e974fdbf` = *"docs(next-gen): the C1 ruling, parity 2 measured, the hold and integrate corrections"* |
| `room queue show … qitem-20261015051416-842330a0f342` | **done** at 05:25:53Z, note *"the ruling is written"* — the row the ruling was delivered against |
| `room queue show … qitem-20261015044224-666415a01322` | **handed-off** since 05:32:10Z, summary *"LEAD SEQUENCE (owner answered: continue) - architect"* — **not** the C1 assignment row item 3 pointed at |
| `git rev-parse <sha>:agenthub_client` per pin bump | `8dbadda1`→`ae3811c0` · `9e7d6c87`→`e41d8279` · `2c05e0a0`→`8c8233b8` · `df5e9069`→**`6e55e0d7`** |
| `git rev-parse main:agenthub_client` | `6e55e0d78839fbddfdb3fbb27e7db76686bad7e6` |
| `git log -1 --format=%B df5e9069 \| grep -c '^Seat:'` | **0** — no seat trailer; it carries `Co-Authored-By: Claude Sonnet 5.5` and a `Claude-Session:` line, so it is an outside Claude Code session in the shared checkout, not a seat |
| client repo `git log --oneline -2` | `7d1f662`, `6e55e0d` — client main is one commit above the pin |
| `find ~/.config/4genthub/rooms/4genthub-min/seats -maxdepth 3 -name mcp.json \| wc -l` | **5** |
| `find … -name config.yml \| wc -l` · `spec.json` `agent_dir` · shared skills per seat | **0** · **`null`** · **14** |

**What still stands.** §5 item 2 remains open on its real half — the guide/policy materialisation as
seat files — and item 1, item 4 and item 5 are untouched by this change. No claim is made here about
which revision closes which C4 harness fault.

**Not in this change.** No filing about `df5e9069` to its author (nothing filed reaches an outside
session). No rebase and no landing: the lead's row `qitem-20261015180611-22adb32094a3` holds every
landing until the C4 run reports and the landing window names the sha.
