"""The client's Python tree, read out of the pin the superproject records - never the pod's checkout.

`agenthub_client` is a gitlink, and the commit it pins still carries the client's Python
implementation, while this superproject's own tree does not and the submodule's working tree does not
either (`src/` is absent from both). Two files in this directory import that implementation at
module level, so whichever checkout a machine happened to hold decided whether they could be
collected at all: at the deployed tip the working submodule has no `src/`, both files failed at
COLLECTION, and the whole directory yielded no verdict rather than a red one.

What is done instead: read the pinned commit out of the gitlink, materialise its `src/` read-only
with `git archive` into a temporary directory, and put that directory at the FRONT of `sys.path`
before the first import. `git archive` reads committed objects, so an uncommitted edit in the
checkout cannot leak into what is imported and the submodule's own HEAD is irrelevant; the front of
the path means a stale working copy lying around on the pod cannot shadow the pin.

This is a module rather than a conftest on purpose: the canonical run carries `--noconftest` and
`scripts/tests/pytest.ini` says why, so a conftest would never execute for these files.
"""

import io
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

# The gitlink whose pinned revision carries the client's Python implementation, and the directory
# inside it that those modules are imported from.
GITLINK = "agenthub_client"
SOURCE_DIR = "src"


class ClientTreeUnavailable(Exception):
    """The pinned client tree could not be read. The message names the step that refused and why."""


_materialised: Path = None


def _pinned_commit(root: Path) -> str:
    """The commit `root`'s gitlink records for the client, or a reason it cannot be read."""
    try:
        listed = subprocess.run(
            ["git", "-C", str(root), "ls-tree", "HEAD", GITLINK], capture_output=True
        )
    except OSError as refused:
        raise ClientTreeUnavailable(f"git is unavailable: {refused}") from None
    if listed.returncode != 0:
        detail = listed.stderr.decode("utf-8", "replace").strip().splitlines()
        raise ClientTreeUnavailable(
            f"git ls-tree failed in {root}: {detail[-1] if detail else listed.returncode}"
        )
    fields = listed.stdout.decode("utf-8", "replace").split()
    if len(fields) < 3 or fields[1] != "commit":
        raise ClientTreeUnavailable(f"{root} records no commit for {GITLINK}: {fields!r}")
    return fields[2]


def ensure_on_path(root: Path) -> Path:
    """Put `root`'s pinned client `src/` at the front of `sys.path`, and return it.

    Materialised once per session: every file in this directory wants the same revision, so a second
    copy would only be a second thing to disagree with. A caller that cannot get the tree must say
    so LOUDLY - a skip that reads as a pass is the silence this exists to end, one level down.
    """
    global _materialised
    if _materialised is None:
        commit = _pinned_commit(root)
        checkout = root / GITLINK
        archive = subprocess.run(
            ["git", "-C", str(checkout), "archive", commit, "--", SOURCE_DIR],
            capture_output=True,
        )
        if archive.returncode != 0:
            detail = archive.stderr.decode("utf-8", "replace").strip().splitlines()
            raise ClientTreeUnavailable(
                f"{checkout} cannot read {commit} "
                f"({detail[-1] if detail else archive.returncode}) - fetch the submodule at that "
                "commit, or the client's Python modules cannot be read here at all"
            )
        into = Path(tempfile.mkdtemp(prefix="pinned-client-"))
        with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
            tar.extractall(into)
        _materialised = into / SOURCE_DIR
    text = str(_materialised)
    if text in sys.path:
        sys.path.remove(text)
    sys.path.insert(0, text)
    return _materialised
