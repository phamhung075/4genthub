---
name: comm-guard-skill
description: How a seat messages another seat. Use before sending any message to a peer.
---

# Messaging other seats

The only way to message another seat is:

```bash
4genteam send <rig> <seat> "<message>" [--intent <task|escalation|report|question|notice>]
```

`4genteam send` is the audited path: it builds your room's communication policy at send time, records the decision in your audit log, delivers the message, and records the outcome. `--intent` defaults to `notice`.

Read the refusal rather than the number alone: two different failures share an exit code.

- "refused by <room>'s communication policy ... nothing was sent" (exit 2) means the room's declared links do not license this send. Do not try another way to send it; escalate through a seat your links allow, or tell your requester.
- "nothing was sent" (exit 3) means the link source or your audit log could not be read or written, so no decision was made. Report it; do not retry another way.
- "the runtime at <socket> refused it; nothing was sent" (exit 1) means the message did not reach the seat. Report it instead of retrying another way.
- "the message was delivered, but its outcome line could not be written" (exit 3) means the message ARRIVED and the audit is incomplete. Report it; do not resend.
- Never use `4genteam input`, `tmux send-keys` or `tmux paste-buffer` to reach another seat.
