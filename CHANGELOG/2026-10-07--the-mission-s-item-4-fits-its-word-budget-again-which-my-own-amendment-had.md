## The mission's item 4 fits its word budget again, which my own amendment had broken

- **What broke:** the `mission-4genthub` context file is held to **350–520 words** by a test in
  `test_openrig_team_setup.py` (`test_context_files_respect_word_limits[mission-4genthub]`), and the item-4
  rewrite that removed the dead cleanups took the file to **614** — so the fix for a stale entry broke a live
  budget. Caught by running the script suite rather than by the change's own gates, which is the only place it
  could be caught: nothing about a Markdown edit looks like a word count.
- **The repair, and why trimming rather than de-duplicating:** the same sentence states the live set, strikes
  both cleanups as measured gone, and points at the measurements by line — shortened to 22 words while keeping
  every clause, because the point of the entry is that a reader can tell dead work from live work **without
  running `gofmt` and `tsc`**, and dropping the pointer would restore the problem it fixed. The file is **516
  words** and `pytest -k word_limits` reports **7 passed**.
- Files: `scripts/team/4genthub/mission.md`, `CHANGELOG.md`.
