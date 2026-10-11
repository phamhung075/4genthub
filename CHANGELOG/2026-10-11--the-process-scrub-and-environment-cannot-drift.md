## The process scrub and `environment()` cannot drift: one rule, both environs

Row `qitem-20261011064225-ca6df6718d6a9c89` (subtask `07c7d5d0` of incident `7e6ab69c`), the residual the
reviewer's gate on `e0e75084` required. That commit closed the leak - every writer goes through
`environment()` - and left this behind in the guard built to prevent it.

### What was wrong

`e0e75084` taught `environment()` one rule: drop `RELOCATING` **and** every key whose name starts
`GIT_CONFIG`. The autouse fixture in `test_git_commit_capture.py` - which exists precisely because the
wrapper's children inherit the PROCESS environment rather than the call - kept a second statement of the
rule, and it was narrower: it looped over `gitfixture.RELOCATING` only. An exported `GIT_CONFIG_GLOBAL`
(or `GIT_CONFIG_SYSTEM`, `GIT_CONFIG_COUNT`, `GIT_CONFIG_KEY_<n>`) therefore still reached an
inherited-env child.

That is not the leak class - the fixture's own children were scoped, and the shared repository stayed
byte-identical through the hostile run - it is a WRONG VERDICT: an ambient `commit.gpgsign` makes a
commit the suite verifies exit 128, and an ambient `core.hooksPath` would have executed the caller's
hook, in the change whose whole subject is environment hermeticity.

### The reproduction, before the fix

    printf '[commit]\n\tgpgsign = true\n' > /tmp/gate-evil-gitconfig
    GIT_CONFIG_GLOBAL=/tmp/gate-evil-gitconfig \
      python3 -m pytest --noconftest -p no:cacheprovider scripts/tests -q

    -> 1 failed, 89 passed
    test_a_real_commit_is_verified_as_landed_and_leaves_nothing_at_risk: git commit exits 128
    (error: gpg failed to sign the data)

The variable was present at fixture time and not removed, because the fixture's list did not know the
family existed.

### The fix

`gitfixture.py` holds the rule once and both environs read it:

- `relocates(name)` - the one statement of the rule: a member of `RELOCATING`, or a name starting with
  `RELOCATING_PREFIX` (`GIT_CONFIG`), the family being open (`GIT_CONFIG_COUNT`, `GIT_CONFIG_KEY_<n>`, ...).
- `relocating_names(environ=None)` - the names that rule admits, of those present.
- `without_relocating(monkeypatch)` - removes them from the PROCESS environment and reports what it
  removed; the autouse fixture is now one call to it. `monkeypatch` is duck-typed (`Any`) so the module
  stays importable without pytest.
- `environment()` filters through `relocates()` - the same rule, no second list anywhere.

### The guards, and what each one holds

- `test_git_fixture_is_hermetic.py::test_the_process_scrub_drops_the_family_that_environment_already_dropped`
  asserts the rule against BOTH helpers: the names are relocating, a non-relocating name (`GIT_PAGER`) is
  not, `environment()` drops the family, and the scrub removes it from the process and reports it.
- `test_git_commit_capture.py::test_the_scrub_removes_the_ambient_git_config_this_module_runs_with` pins
  the CALL SITE, where the defect actually was. A new `ambient_git_config` fixture exports a
  `GIT_CONFIG_GLOBAL`/`GIT_CONFIG_SYSTEM` demanding a signature, and the autouse scrub requests it, so
  every case in that module now runs WITH the hostile variable present and depends on the scrub to remove
  it. The case asserts the process is clean by the time a body runs.
- The structural case is unchanged: an explicit `env=` is still required on every child that can reach
  git. That requirement is why neither new case spawns a child that deliberately inherits - such a child
  cannot be written in that directory at all, which is the other half of the same guard.

### The perturbations, measured one at a time and restored

1. `GIT_DIR` dropped from `RELOCATING` ->
   `test_a_fixture_git_call_under_a_hostile_git_dir_leaves_the_caller_alone` fails
   `AssertionError: a fixture git call wrote the caller's config`, and the new rule case fails
   `AssertionError: GIT_DIR can relocate a repository or the config git reads`; the structural case still
   passes (1 failed, 1 failed, 1 passed).
2. A child appended with no `env=` -> the structural case fails and names it:
   `these children can reach git without an explicit environment, so a caller's GIT_DIR would reach them:
   test_git_fixture_is_hermetic.py:146`.
3. The call site reverted to the `RELOCATING` loop (the defect itself) -> the wiring case fails
   (`assert 'GIT_CONFIG_GLOBAL' not in environ({...})`), `test_a_real_commit_is_verified_as_landed_...`
   fails 128, and the hostile run fails the same two - so the module no longer depends on a hostile
   process for this to be caught.

### The proof after the fix

    (clean)    92 passed, 3 warnings in 9.91s
    (hostile)  GIT_CONFIG_GLOBAL=/tmp/gate-evil-gitconfig -> 92 passed, 3 warnings in 10.29s
    (hostile)  GIT_DIR=<this worktree's .git>              -> 92 passed, 3 warnings in 10.80s

`90 passed` at `e0e75084` becomes `92 passed`: two cases were added (the rule case and the wiring case)
and none of the 90 changed or was weakened. Scope is `scripts/tests` only - no Go, no frontend.
