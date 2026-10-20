# The pin carries the runner-less pane gate, and its record awaits a carrier

The hub's gitlink moves `2a316a0 -> 61fce91` (hub pin `68557da1`, gitlink only): client main took the
merge `61fce91` (parents `308d2c1` + `b9325ef`), a merge because the lane and main both moved.

`308d2c1` `fix(runtime): a runner-less seat is live by its pane, and its launch writes the record it can
back`: the deployed daemon gated liveness on the file's word (`seat_is_idle`), so the agy reviewer's stale
`agent_socket_closed` silenced the nudge pass while its pane, created 3h later, was live. The gate now splits
by runtime - publishing seats keep the Running gate and the busy words; runner-less seats take the alert as
the trigger and the pane as liveness (`session` plus `#{pane_dead}=0`; a failed probe is not a death). A
runner-less launch writes `running`, activity `unknown`, the pane's pid and a fresh stamp, so a pre-reseat
death word cannot outlive the pane. The commit records three measured reds (the deployed predicate, the
dead-pane gate disabled, the launch write disabled) and that restoring only the `state != Running` line
turns none of them.

The merge kept both sides' test blocks (main's blocked-row wake test and the lane's three runner-less
tests). Nothing pushed; the push is the owner's.
