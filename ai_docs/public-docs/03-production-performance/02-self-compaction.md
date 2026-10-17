# Token Economy & Self-Compaction

Large context windows degrade reasoning quality and incur exponential token costs. Allowing agents to run until they hit 200k+ tokens causes hallucinations and stalling.

This system maintains lean, high-performance sessions using an **Automated Compaction Supervisor**.

---

## 1. The Token Compaction Limits

On every pass the supervisor reads each seat's newest session log and checks its context size against three limits. The numbers below are the ones this team runs with:

| Tier | Limit | Variable | Action |
|---|---|---|---|
| **Soft** | 150,000 tokens | `COMPACT_LIMIT_TOKENS` | The seat is told once to find its own safe point and compact |
| **Urgent** | 200,000 tokens | `COMPACT_WARN_TOKENS` | The seat is compacted now, without waiting for it to go quiet |
| **Hard** | 250,000 tokens | `COMPACT_HARD_TOKENS` | The running turn is aborted and compaction is forced |

Set the variables in `~/.config/4genthub/.env`. A variable that is unset or blank uses the client's built-in default: 150,000, 250,000 and 300,000.

---

## 2. Running the Compaction Supervisor

Start the supervisor alongside your team:

```bash
4genteam compact <rig-name>
```

### The Compaction Protocol

The supervisor runs outside the seats and performs these automated steps:
1. **Reads context metrics** directly from the agent session logs.
2. **Waits for quiet:** Ensures the seat is not mid-execution or editing a file.
3. **Issues `/compact`:** Triggers the runtime's native summary compaction.
4. **Verifies token drop:** Checks that context tokens dropped (e.g. from 160k down to 25k).
5. **Re-anchors the seat:** Re-injects the current queue item and active mission pointer so the agent resumes work immediately with a clean context.
