### Fixed

**`place_agent` links a file or a directory, with no copy fallback** (2026-10-03)

- `scripts/openrig_seat_sync.py`: `place_agent` tried a symlink and fell back to `shutil.copytree`, which cannot copy the file `install-checker` links (the seatcheck binary). It now makes one relative symlink for a file or a directory, replaces a real directory or an older link at the target, and a failing symlink is a `SyncError` (exit 2, `cannot link <target> to <source>`) that leaves nothing behind.
