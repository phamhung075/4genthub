## A seat trailer on every commit made from a seat (architect's decision note, 2026-10-08)

- **Why**: every commit in this tree carries one machine identity, so git cannot name the seat that made
  it. Eleven attribution instruments across five seats failed on 2026-10-08 to name the author of a file we
  all needed to name, and the answer turned out to be a trailer in a commit BODY that nobody had opened -
  every search read the header, because that is where authorship usually lives.
- **What landed**: `scripts/git-hooks/prepare-commit-msg`, a versioned `prepare-commit-msg` hook running
  `git interpret-trailers --in-place --if-exists doNothing --trailer "Seat: $OPENRIG_SESSION_NAME"`, and
  ONLY when that variable is set, so a commit made by a human from the host is untouched.
  **`OPENRIG_SESSION_NAME` is the `rig send` address**, so a reader who finds the trailer can message the
  seat directly - the reach-back no other attribution instrument had. **And the absence reads positively:**
  the owner commits from the host where the variable is unset, so a commit with no `Seat:` trailer says
  "not a seat", which would have answered the whole question in one `git log`.
- **What it does not fix**, in the note's words: a trailer names the seat that RAN `git commit`, not the
  author of every line - `0c8122a9` is the counterexample, where a trailer would have said go-dev while the
  commit carried the architect's two staged lines. The hook and the pre-commit ladder are ONE FIX IN TWO
  PARTS, and the script's own comment says so rather than implying more.
- **Not installed here**: `.git/hooks` belongs to the owner's environment and is not versioned, so the
  install is one approved step. The script carries a read-only `--check` mode that reports whether the path
  is already occupied, so nobody overwrites another seat's hook. Measured today: the path is free.
- **Verified**: red first (7 failed with the script absent), then green (7 passed); a CONTROL in which a
  do-nothing hook replaced the script turned the positive case red with the trailer absent, and the script
  was restored byte-identical before the final green run.
