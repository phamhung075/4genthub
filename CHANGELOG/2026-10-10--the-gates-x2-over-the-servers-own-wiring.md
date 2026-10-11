## The gate's ×2, finally over the wiring the server runs

The gate asked for one thing by name: write two notes through `AddProgress`, then read them with the
repository's `Get` on testpg. The repository fix (`f99d10eb`) was proven at the repository level, and the gap
— that the test drove the repository rather than the service's `AddProgress` — was named in that commit's
evidence rather than left for a reader to find. This closes it.

`TestAddProgressTwiceReachesTheColumnTheRepositoryReads` lives in `httpapp` because that is where the bridge
between the typed context repository and the service's duck-typed `UnifiedContextRepository` lives: `ctxRepo`
in `context_repos.go`, assembled by `unifiedContextRepositories`, which `app.go` installs as
`factories.UnifiedContextRepositoryBuilder`. `services` cannot import `httpapp` — httpapp imports services — so
the same test in the services package would have had to ship its own adapter and then verify the copy instead
of the code the server runs.

**Red, then green, on the real wiring**: with the pre-fix repository restored by commit
(`git checkout f99d10eb^ -- …/task_context_repository.go`) two `AddProgress` calls both report success and the
repository's read returns `ImplementationNotes[progress_updates]=<nil>` — the gate's own measurement. With the
fix in place the two notes are there, in order, with no duplicates, and `Metadata` no longer carries a second
copy of the column.

**One measurement lesson, recorded so it is not repeated**: the first red attempt used `git stash push -- <file>`,
which reverted nothing because the fix was already committed — that run exercised the fixed code and passed.
Reverting for a red proof has to come from a commit, not the stash.

`gofmt` clean; the case `ok` 1.468s; the whole `httpapp` package `ok` 48.742s with `AGENTHUB_TEST_PG_URL` set.
Never pushed.
