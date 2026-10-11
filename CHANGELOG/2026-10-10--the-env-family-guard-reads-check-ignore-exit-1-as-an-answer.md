## The env-family guard stops failing on a clean checkout: `check-ignore`'s exit 1 is an answer, not an error

### Fixed

- `scripts/tests/test_gitignore_env_family.py` — `_hidden_with_rule` ran `git check-ignore` through `_git`, whose `check=True` turned an ordinary state into an exception. `check-ignore` exits 1 when NOTHING it was asked about is ignored, and that is exactly what a CLEAN CHECKOUT looks like: the only env-family members present are the tracked samples (`.env.sample`, `.env.claude`, `agenthub-frontend/.env.sample`), the negations expose them, and the untracked-plus-ignored listing is empty. So the guard was **2 failed, 2 passed** on a fresh clone and **4 passed** on the pod that has `.env.dev` — it failed for a state that is not a defect, in `main`, contradicting its own docstring (commit `609b3c26`, reviewer verdict “changes requested”, row `0caa7fe4`).
- The call now passes `check=False` and reads the two exit codes: 0 and 1 are git’s answers (1 = nothing ignored, so the hidden set is empty), and any other exit — 128 for an unusable repository, say — still raises, with git’s stderr carried into the error.
- NOTHING WAS WEAKENED: the declaration check, the “a declared member that is present must stay hidden” direction, the `.gitignore` pattern assertions and the sample/negation assertions are unchanged; `_git` still hardcodes `check=True` for its other callers (`git ls-files`, whose only success is exit 0). `.gitignore` and `.env.dev` were NOT touched — the fix is one call site, not a rule change.

### Testing

Red first in the CLEAN state, then green in both:

- **Red, clean**: a detached worktree at `609b3c26` (`git worktree add --detach … 609b3c26`) whose env-family set is the three tracked samples and whose untracked-plus-ignored listing is empty — `python3 -m pytest scripts/tests/test_gitignore_env_family.py -q` → **2 failed, 2 passed**, both failures `subprocess.CalledProcessError: Command '['git', 'check-ignore', '-v', '-z', '--stdin']' returned non-zero exit status 1` (the two cases that call `hidden_family()`).
- **Green, clean**: the fixed file copied into that same worktree → **4 passed**.
- **Green, this pod**: `python3 -m pytest scripts/tests/test_gitignore_env_family.py -q` → **4 passed in 3.32s**.
- **Not weakened**: an undeclared `.env.probe` written into the clean worktree → **1 failed, 3 passed**, the failure naming the file AND the rule — `.env.probe <- hidden by '*env.*' (.gitignore:15)`; the probe removed → **4 passed** again.
- The worktree was removed afterwards, and `.gitignore` is unmodified in both states.
