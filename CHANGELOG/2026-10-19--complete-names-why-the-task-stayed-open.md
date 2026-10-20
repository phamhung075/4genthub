# complete names why the task stayed open

The completion verb printed one line for three different outcomes, so a seat that read
"the task was not completed" could not tell a refused gate from an evidence write that never
landed. Measured 2026-10-18: `4genteam complete` answered `gate accept` and then lost the evidence
POST (HTTP 500), leaving the task in `in_progress` with no message naming the missing half; two
seats filed friction on it in one hour.

Now, on every post-gate failure the verb prints the consequence that applies - the gate verdict,
the evidence write, or the completion call - and reads the task state back once after a failed
completion, so the line names what the hub holds rather than what the client assumed. An evidence
POST answered 409 for a head that already has evidence continues the completion with a warning
instead of stopping: the gate verdict stands and the replay is not a failure.

Exits are unchanged (0 settled, 1 usage, 5 refused, 6 unjudgeable), so a caller keyed on the exit
code keeps working.

- Client commit 2ffd265 on `4genthub-min/complete-failure-surface`, five new cases
  (`internal/clientcomplete`), reviewed PASS.
- Hub pin: `agenthub_client` 8d9237d -> 2ffd265.
