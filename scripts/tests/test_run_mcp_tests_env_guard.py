"""The MCP test-mode script must not touch the owner's root `.env` when it cannot do its job.

`scripts/run-mcp-tests.sh` performs TWO writes in the repository root: it copies `.env` to
`.env.backup` (a single slot, not a history - every run replaces it), then copies `.env.testing`
over `.env`. At HEAD it had no `set -e` and no precondition, so with `.env.testing` absent - which
is its state today, and invisible because that name is gitignored - the second copy fails, nothing
stops the script, and it prints "Switched to testing configuration" and proceeds to restart the
stack for a switch it never made.

These tests run a COPY of the script in a scratch directory with synthetic `.env` family files
that this test itself writes. They never read, create, print or commit a root `.env` member, and
they never run the script against the real tree: `docker-compose`, `curl` and `sleep` are stubbed
on PATH, so the container steps are inert (and a real `docker-compose down` can never be reached).

The guard is required to sit BEFORE the backup copy, not merely before the overwrite: a refusal
placed at the failing copy would still have replaced `.env.backup` first, which is why one of the
assertions is the backup's IDENTITY - digest AND mtime - rather than only the exit status.
"""

import hashlib
import os
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "run-mcp-tests.sh"

ENV_CONTENT = "DATABASE_URL=postgres://scratch\nJWT_SECRET_KEY=scratch-not-a-secret\n"
BACKUP_CONTENT = "DATABASE_URL=postgres://anchor\n"
TESTING_CONTENT = "AUTH_ENABLED=false\nMCP_AUTH_MODE=testing\n"


def _scratch(tmp_path: Path, with_testing_env: bool) -> tuple[Path, Path]:
    """A tree the script can run in without reaching anything real: the script itself, synthetic
    `.env` members, a `docker-system/` directory for its `cd`, and stub executables that record
    being called."""
    root = tmp_path / "root"
    (root / "docker-system").mkdir(parents=True)
    shutil.copy2(SCRIPT, root / "run-mcp-tests.sh")
    (root / ".env").write_text(ENV_CONTENT)
    (root / ".env.backup").write_text(BACKUP_CONTENT)
    if with_testing_env:
        (root / ".env.testing").write_text(TESTING_CONTENT)

    bins = tmp_path / "bin"
    called = tmp_path / "called"
    bins.mkdir()
    called.mkdir()
    for name in ("docker-compose", "curl", "sleep"):
        stub = bins / name
        stub.write_text(f'#!/bin/sh\n: > "{called}/{name}"\nexit 0\n')
        stub.chmod(0o755)
    return root, bins


def _run(root: Path, bins: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PATH"] = os.pathsep.join([str(bins), env.get("PATH", "")])
    env["HOME"] = str(root)
    return subprocess.run(
        ["bash", "run-mcp-tests.sh"], cwd=root, env=env, capture_output=True, text=True
    )


def _identity(path: Path) -> tuple[str, str]:
    """The digest AND the mtime, because a silent replacement of `.env.backup` by identical
    content would change only the second one - and the release ask's interval anchor rests on it."""
    return hashlib.sha256(path.read_bytes()).hexdigest(), str(path.stat().st_mtime_ns)


def test_a_missing_testing_env_fails_loudly_and_writes_nothing(tmp_path):
    root, bins = _scratch(tmp_path, with_testing_env=False)
    env_before = _identity(root / ".env")
    backup_before = _identity(root / ".env.backup")

    result = _run(root, bins)

    assert result.returncode != 0, (
        "the script reported success for a run it could not complete:\n" + result.stdout
    )
    output = result.stdout + result.stderr
    assert ".env.testing" in output, f"the failure does not name what is missing:\n{output}"
    assert "Switched to testing configuration" not in output, (
        "the success message is unconditional:\n" + output
    )
    assert "TESTING MODE READY" not in output, (
        "the script claims the testing mode is ready for a switch it never made:\n" + output
    )
    assert _identity(root / ".env") == env_before, "the script wrote .env"
    assert _identity(root / ".env.backup") == backup_before, (
        "the script replaced .env.backup before refusing - the backup is a single slot, not a "
        "history, so this is the silent loss the guard exists to prevent"
    )
    assert not (bins.parent / "called" / "docker-compose").exists(), (
        "the script restarted the stack after a switch it never made"
    )


def test_a_present_testing_env_is_switched_in_with_the_original_backed_up(tmp_path):
    root, bins = _scratch(tmp_path, with_testing_env=True)

    result = _run(root, bins)

    assert result.returncode == 0, result.stdout + result.stderr
    assert (root / ".env").read_text() == TESTING_CONTENT, "the testing configuration is not in place"
    assert (root / ".env.backup").read_text() == ENV_CONTENT, (
        "the backup must hold the configuration that was replaced, not the testing one"
    )
    assert (bins.parent / "called" / "docker-compose").exists(), (
        "the script refused or stopped before the container step it exists to perform"
    )
    assert "TESTING MODE READY" in result.stdout
