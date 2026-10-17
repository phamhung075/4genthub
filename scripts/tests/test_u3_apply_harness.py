"""Tests for scripts/u3-apply-harness.sh - the install path for the U3 acceptance harness.

WHY EACH TEST EXISTS (each pins a way the live harness path was actually written, or could have been):
  * the refusals are the tool's whole point - a missing announcement, bytes that moved after the
    announcement, a syntax error and a no-op install must all stop BEFORE anything is written;
  * the predecessor aside is what makes an install reversible, and its NAME (the predecessor sha) is what
    makes it findable; an install that overwrote the only copy would be unrecoverable;
  * the APPLY-LOG line is the only after-the-fact record of which revision the live path holds - the
    2026-10-15 window held three unannounced revisions in 3 minutes, so a silent install is the failure;
  * --current is the read the next seat takes before installing: it must name the stage file by bytes,
    never by timestamps or names that can disagree;
  * a dry run must leave the directory byte-identical.

Hermetic: every test builds its own live/staged pair in tmp_path. Nothing here reads or writes u3-run.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "u3-apply-harness.sh"

LIVE_NAME = "ACCEPTANCE-cutover-lab-U3.sh"
LIVE_BODY = "#!/usr/bin/env bash\nset -u\necho harness-v1\n"
STAGED_BODY = "#!/usr/bin/env bash\nset -u\necho harness-v2\n# staged revision\n"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_pair(tmp_path: Path, live_body: str = LIVE_BODY, staged_body: str = STAGED_BODY):
    live = tmp_path / LIVE_NAME
    live.write_text(live_body)
    live.chmod(0o755)
    staged = tmp_path / "fe-stage99.sh"
    staged.write_text(staged_body)
    staged.chmod(0o755)
    return live, staged


def run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["AGENTHUB_SEAT"] = "fe-dev"
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=str(cwd or SCRIPT.parent),
        env=env,
    )


def test_refuses_without_live_path():
    r = run()
    assert r.returncode == 3
    assert "--live" in r.stderr


def test_refuses_without_announced_sha(tmp_path):
    live, staged = make_pair(tmp_path)
    before = sha(live)
    r = run("--live", str(live), str(staged))
    assert r.returncode == 3
    assert "--expect-sha is required" in r.stderr
    assert sha(live) == before
    assert not (tmp_path / "APPLY-LOG").exists()


def test_refuses_bytes_that_moved_after_the_announcement(tmp_path):
    live, staged = make_pair(tmp_path)
    staged.write_text(STAGED_BODY + "# moved\n")
    announced = sha(staged)
    staged.write_text(STAGED_BODY)
    before = sha(live)
    r = run("--live", str(live), str(staged), "--expect-sha", announced)
    assert r.returncode == 3
    assert "not the announced" in r.stderr
    assert sha(live) == before
    assert not (tmp_path / "APPLY-LOG").exists()


def test_refuses_a_noop_install(tmp_path):
    live, staged = make_pair(tmp_path, staged_body=LIVE_BODY)
    r = run("--live", str(live), str(staged), "--expect-sha", sha(staged))
    assert r.returncode == 3
    assert "nothing to apply" in r.stderr


def test_refuses_bytes_bash_cannot_parse(tmp_path):
    broken = "#!/usr/bin/env bash\nif then fi (\n"
    live, staged = make_pair(tmp_path, staged_body=broken)
    before = sha(live)
    r = run("--live", str(live), str(staged), "--expect-sha", sha(staged))
    assert r.returncode == 3
    assert "bash -n refused" in r.stderr
    assert sha(live) == before
    assert not (tmp_path / "APPLY-LOG").exists()


def test_installs_atomically_and_records_before_after(tmp_path):
    live, staged = make_pair(tmp_path)
    before, after = sha(live), sha(staged)
    r = run("--live", str(live), str(staged), "--expect-sha", after, "--note", "stage99 smoke")
    assert r.returncode == 0, r.stderr
    assert sha(live) == after
    assert live.stat().st_mode & 0o777 == 0o755
    assert (tmp_path / f"{LIVE_NAME}.{before}").read_text() == LIVE_BODY
    log = (tmp_path / "APPLY-LOG").read_text().splitlines()
    assert len(log) == 1
    assert log[0].endswith(
        f'live {before} -> {after} bytes={len(STAGED_BODY)} composed=fe-stage99.sh '
        f'note="stage99 smoke" by=fe-dev'
    )
    assert f"ANNOUNCE harness {after}" in r.stderr
    assert f"predecessor {before}" in r.stderr


def test_a_second_install_cannot_reuse_the_same_staged_bytes(tmp_path):
    live, staged = make_pair(tmp_path)
    first = run("--live", str(live), str(staged), "--expect-sha", sha(staged))
    assert first.returncode == 0, first.stderr
    second = run("--live", str(live), str(staged), "--expect-sha", sha(staged))
    assert second.returncode == 3
    assert "nothing to apply" in second.stderr
    assert len((tmp_path / "APPLY-LOG").read_text().splitlines()) == 1


def test_dry_run_writes_nothing(tmp_path):
    live, staged = make_pair(tmp_path)
    before = sha(live)
    r = run("--live", str(live), str(staged), "--expect-sha", sha(staged), "--dry-run")
    assert r.returncode == 0, r.stderr
    assert "DRY RUN" in r.stderr
    assert sha(live) == before
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted([LIVE_NAME, "fe-stage99.sh"])


def test_current_names_the_stage_file_by_bytes_and_the_last_log_line(tmp_path):
    live, staged = make_pair(tmp_path)
    r = run("--live", str(live), str(staged), "--expect-sha", sha(staged))
    assert r.returncode == 0, r.stderr
    cur = run("--live", str(live), "--current")
    assert cur.returncode == 0, cur.stderr
    assert sha(live) in cur.stdout
    assert "stage   fe-stage99.sh" in cur.stdout  # the staged bytes ARE the live bytes after the install
    assert "apply-log (last line):" in cur.stdout
    log_line = (tmp_path / "APPLY-LOG").read_text().splitlines()[-1]
    assert log_line in cur.stdout


def test_log_verb_prints_the_append_only_record(tmp_path):
    live, staged = make_pair(tmp_path)
    r = run("--live", str(live), str(staged), "--expect-sha", sha(staged))
    assert r.returncode == 0, r.stderr
    out = run("--live", str(live), "--log")
    assert out.returncode == 0
    assert out.stdout.splitlines() == (tmp_path / "APPLY-LOG").read_text().splitlines()
