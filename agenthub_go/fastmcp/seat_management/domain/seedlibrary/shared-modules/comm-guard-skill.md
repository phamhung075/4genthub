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
- Exit code 5 means the policy allowed the message but it could not be delivered (unknown or ambiguous recipient, or `rig send` failed). It is not a policy decision; report it instead of retrying another way.
- Never use `rig send`, `rig queue`, `rig broadcast`, or `tmux send-keys` / `tmux paste-buffer` to reach another seat.
