---
name: comm-guard-skill
description: How a seat messages another seat. Use before sending any message to a peer.
---

# Messaging other seats

The only way to message another seat is:

```bash
seatcheck send --to <seat> --intent <task|escalation|report|question|notice> -- <text>
```

`seatcheck` checks your pinned communication policy, records the send in your audit log, and then delivers the message.

- Exit code 3 means company policy denied the message. Do not try another way to send it; escalate through a seat your policy allows, or tell your requester.
- Exit code 2 means the policy or your identity could not be read. Nothing was sent.
- Never use `rig send`, `rig queue`, `rig broadcast`, or `tmux send-keys` / `tmux paste-buffer` to reach another seat.
