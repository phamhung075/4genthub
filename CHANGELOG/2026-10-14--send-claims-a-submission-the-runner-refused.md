# Send claims a submission the runner refused

## What is wrong
`4genteam send` prints `Sent to <session>` and exits 0 for text the agent never receives, whenever the
target seat is mid-turn. The runner is told to refuse it — omp answers `Agent is already processing. Use
steer() or followUp() to queue messages, or wait for completion.` — the runner neither steers nor queues,
and the text is gone. The caller has no way to tell "delivered and taken" from "refused and dropped".

## Reproduction on the live room, by the lead, 2026-10-14 20:01:5xZ
Command: `4genteam send 4genthub-min-reviewer@4genthub-min "<the fourth gate unit, 2004 bytes>"`.
Receipt: `Sent to agenthub--4genthub-min--reviewer`, exit 0.

What the text did instead — four surfaces, none of which contains it:

| surface | read | result |
|---|---|---|
| the seat's transcript | `seats/reviewer/sessions/2026-10-14T19-09-29-186Z_01a13bd1….jsonl` | 3 user messages; `grep -c 'Fourth gate unit'` = 0, `grep -c '3acf84bd'` = 0 |
| the seat's pane | `tmux capture-pane -S -3000 -t agenthub--4genthub-min--reviewer` | 0 occurrences, and the refusal itself: `[omp-runner] ERROR rpc: Agent is already processing. …` then `[omp-runner] rpc error, nothing to resume: the turn is still running` |
| the state file | `run/reviewer.state.json` | `{"activity":"idle","state":"idle","updated_at":"2026-10-14T19:50:32.987Z"}` — it never published that it was mid-turn, so no observer could have predicted the refusal |
| the queue | the room's rail | nothing (the rail is for qitems, not messages) |

So the message died between the daemon accepting the frame and the runner's refused prompt RPC, and the
receipt had already been printed. This is one of U3 run 1's two failures — the cutover-lab send whose text
was absent from the transcript, the pane, the logs and the queue while the receipt named the target — so it
is the acceptance shape, not a one-off.

## The same defect on fe-dev's lab, 19:55Z
Receipt in the harness log (`/tmp/c2fe-evidence-20261014T195538Z/legBC3.log`):
`{"delivered":"agenthub--c2-lab--dev","outcome":"submitted"}` — while that seat's own runner printed
`gave up: the agent refused the turn :: Agent is already processing. …` and abandoned both sends after ~5
retries each. The lab adds a second, worse symptom: when a prompt IS accepted, what reaches the model is
the envelope's **header line only**. The dev seat's transcript has exactly one user message, 58 bytes —

    [{"type": "text", "text": "From: agenthub--c2-lab--lead"}]

— no `To:`, no `Sent:`, no body. Read from
`/tmp/c2fe-lab/state/rooms/c2-lab/seats/dev/sessions/2026-10-14T20-02-09-938Z_01a13c02-….jsonl` line 5. On
the live room the full envelope does arrive (my 19:43Z and 19:59Z sends to the reviewer are in its
transcript with their bodies, 958 and 2711 bytes), so the truncation is specific to the lab path and wants
localising there before it is stated as a general defect. Provenance note: fe-dev's original 19:55Z
artifact was replaced when it rebuilt the lab at 20:02Z; the 58-byte prompt above is the rebuilt run's.

## Why it matters beyond the two failures
A brief sent to a mid-turn seat is silently dropped, receipts notwithstanding. Every lead handoff in this
pod is exposed — including the gate units queued to the reviewer, which is mid-turn for long stretches.
Until this is fixed, delivery must be verified against the *target's transcript*, never the receipt.

## Whose it is
The client's `send` verdict must not claim more than the runtime knows: it already has a second branch
(`Pasted to <session>, submission unconfirmed`) and this is the case that must take it — go-dev.
The runner must queue rather than drop (omp names `steer()` / `followUp()`), and the state file must
publish mid-turn activity so the refusal is at least observable — the reviewer.

## Verification
Every command above is reproduced in this session; the panes, transcripts, state file and harness log are
at the paths named, and the transcript reads were done by parsing the session jsonl for `role":"user"`.
