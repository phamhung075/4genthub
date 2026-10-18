# The client pin carries the legacy client by path, and the link a kept seat was missing

Hub `main` now names client `main` `287f7bc`, which lands the ruling at `a75288f4`: the pre-derivation
client worktree `<roomDir>/wt/<seat>-client` is identified by its PATH rather than by the branch it
holds, so a legacy on a lane branch is reached at all; a clean one is removed (the branch survives) and
a kept seat path without `<seat>/agenthub_client` gets the link placed on that branch, while a legacy
that still holds uncommitted or untracked work is named and kept with no link placed, so a seat never
ends up with two client locations. `Check` is unchanged and still calls a path without the link Wrong,
which is now the truthful state it names only while a seat has work to commit. Running `up` against the
live room is what performs the migration, and it is the lead's step, not this pin's: this commit only
makes the pin name the code.
