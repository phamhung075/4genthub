# The pin carries the foreign-base criterion warning

The hub's gitlink moves `5582628 -> ad28da4` (client main, fast-forward). `4genteam complete` now reads the
task's criteria before it calls the gate and names a criterion that measures a base other than the `--base`
it was given: `warning: criterion_N names <sha>, --base is <base>; the gate measures <base>..HEAD`, one line
per criterion, on the same stderr surface as the blind-criterion warning. Exit codes and the verdict are
untouched.

Why it lands: the lead hit the refusal twice tonight after the work was pushed and the reviewer had passed
(tasks `60e2ef5b`, `c898d908`) — the verb knew the mismatch the moment it read `--base`, and the seat's only
act was to rewrite the criterion.

Evidence: reviewer PASS at `ad28da4` (row `qitem-20261018234140-047eefd2c7ce`); `go test
./internal/clientcomplete/ -count=1` green; `go test ./...` rc 0; three tests pin the warning line, the
silent `--base`/head case, and a hex word that resolves to no commit; the built binary printed exactly one
warning line against a stub hub and exited 0. Task `22126102` closed through the gate (0.98 / 0.93).
