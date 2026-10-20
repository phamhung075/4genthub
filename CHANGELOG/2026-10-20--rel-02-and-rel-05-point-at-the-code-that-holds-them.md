# REL-02 and REL-05 point at the code that holds them

A register row's `file:line` is the fact a reader opens to see the requirement enforced. Two reliability
rows pointed at lines that decide nothing about them, both opened at client `bb30cb0`:

- **REL-02** cited `supervisor.go:22`, which is the comment above `tailBytes` inside a `const` block
  (`:25`). The property is `Setsid`-detached children: the spawn is `spawnChildImpl`
  (`supervisor.go:552`), it calls `detach(cmd)` (`:567`), and `detach` sets
  `cmd.SysProcAttr = &syscall.SysProcAttr{Setsid: true}` (`detach_unix.go:14`).
- **REL-05** cited `lifecycle.go:1176`, a `time.After` in a poll loop. The verb is
  `clientrestore/continue.go:34`, its rebuild call is `:159` (`restore.restore(rigName, brief)`), and that
  rebuild is `reviveRoom` (`restore.go:271`) - "Each seat resumes its own saved session", which is the
  durable state the row's requirement names.

REL-05 also gains `restore.go:271` beside its two existing anchors: the verb and its call name the path,
`reviveRoom` is the code that rebuilds. Both rows are dated `2026-10-20`.

Check: `grep -n 'Setsid: true' agenthub_client/internal/clientlifecycle/detach_unix.go` and
`grep -n 'func reviveRoom' agenthub_client/internal/clientrestore/restore.go` answer the two anchors.
