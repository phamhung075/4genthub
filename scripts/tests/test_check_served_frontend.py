"""Tests for scripts/check_served_frontend.py - the served-frontend census.

WHY EACH TEST EXISTS (they are not decoration; each one pins a mistake that was actually made):
  * the 08 Oct production shape must read STALE - the defect that went unnoticed for two days,
  * a fresh build must read OK - or the instrument is a wall that always says no,
  * the stale page must be found when it is reachable ONLY through a ref inside another chunk -
    the one-hop scan that found 0 old strings and 0 new ones and looked clean,
  * the naive needle (`sync pull`) must stay documented as a false pass, so a later "simplification"
    to it fails here instead of in production,
  * a bundle holding nothing but the token must pass the census and FAIL identity - the difference
    between "newer than 08 Oct" and "is this build",
  * an unreachable origin and an incomplete closure must be exit 2, never a pass.

Everything is hermetic: a threaded http.server over a temp docroot. No test touches production.

Run with the script suite:  python3 -m pytest --noconftest -p no:cacheprovider scripts/tests -q
"""

from __future__ import annotations

import functools
import http.server
import importlib.util
import os
import subprocess
import threading
import time
from contextlib import contextmanager
from pathlib import Path

import pytest

import gitfixture

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "check_served_frontend.py"


def load_module():
    spec = importlib.util.spec_from_file_location("check_served_frontend", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


census = load_module()


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):  # keep the suite's output readable
        pass


class NoLastModifiedHandler(QuietHandler):
    """A server that does not date its files - the census must not depend on the date."""

    def send_header(self, key, value):
        if key.lower() == "last-modified":
            return
        super().send_header(key, value)


@contextmanager
def serve(docroot: Path, handler=QuietHandler):
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(handler, directory=str(docroot)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def write_tree(root: Path, files: dict[str, str]) -> Path:
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return root


# --- the two shapes ---------------------------------------------------------------------------

def production_shape() -> dict[str, str]:
    """The 08 Oct bundle, reduced: the index names the entry and a chunk map; the entry names its
    lazy pages; the fossils live in the lazy pages, never in the index."""
    return {
        "index.html": (
            '<!doctype html><script type="module" crossorigin src="/assets/index-BMd9UnWH.js"></script>\n'
        ),
        "assets/index-BMd9UnWH.js": (
            'const pages={"seat":"/assets/SeatDetailPage-BpUArPYK.js",'
            '"/assets/SeatsPage-DRldE7DQ.js":1};\n'
        ),
        "assets/SeatDetailPage-BpUArPYK.js": (
            'const c="scripts/seat_sync.py switch <room> <seat> --model <id>";\n'
            'const d="scripts/seat_sync.py pull ${room} ${seat}";\n'
        ),
        "assets/SeatsPage-DRldE7DQ.js": (
            'const e="No bridge connected. Run scripts/bridge.py on your PC.";\n'
        ),
    }


def fresh_shape(entry: str = "index-riIYPcmm.js", env: str | None = None) -> dict[str, str]:
    """A HEAD build, reduced: three panels, three verbs, no fossil. `env` is the object vite inlines
    when the tree reads `import.meta.env[key]` dynamically - the build's environment fingerprint."""
    return {
        "index.html": f'<!doctype html><script type="module" crossorigin src="/assets/{entry}"></script>\n',
        "assets/" + entry: (f"const __env={env};\n" if env else "")
        + (
            'const pages={"a":"/assets/SeatDetailPage-FRESH0001.js",'
            '"/assets/SeatsPage-FRESH0002.js":1,"/assets/MachinesPanel-FRESH0003.js":1};\n'
        ),
        "assets/SeatDetailPage-FRESH0001.js": 'const c="4genteam sync pull ops bob";\n'
                                              'const d="4genteam sync switch <room> <seat> --model <id>";\n',
        "assets/SeatsPage-FRESH0002.js": 'const e="No bridge connected. Run 4genteam bridge run on your PC.";\n',
        "assets/MachinesPanel-FRESH0003.js": 'const f="4genteam bridge run";\n',
        "assets/index-DslPL43O.css": "body{}\n",
    }


def run(base_url: str, *extra: str) -> int:
    return census.main(["--base-url", base_url, *extra])


# --- the census ------------------------------------------------------------------------------

def test_the_production_shape_reads_stale(tmp_path, capsys):
    """The 08 Oct bundle must be caught: fossils present, no verb anywhere."""
    with serve(write_tree(tmp_path, production_shape())) as base:
        assert run(base) == 1
    out = capsys.readouterr().out
    assert "STALE" in out
    assert "scripts/seat_sync.py" in out and "scripts/bridge.py" in out
    assert "live verb 'sync pull': ABSENT" in out


def test_a_fresh_build_reads_ok(tmp_path, capsys):
    """HEAD's shape must pass, or the census only ever says no."""
    with serve(write_tree(tmp_path, fresh_shape())) as base:
        assert run(base) == 0
    assert "OK" in capsys.readouterr().out


def test_a_dotted_chunk_name_is_one_ref_not_a_phantom(tmp_path, capsys):
    """`./mermaid.core-PVSKwLbE.js` is ONE name. A pattern that starts after the dot reads
    `core-PVSKwLbE.js`, fetches it, 404s, and reports INCOMPLETE on a clean surface."""
    assert census.discover_refs('import("./mermaid.core-PVSKwLbE.js")') == {
        "/assets/mermaid.core-PVSKwLbE.js"
    }
    files = fresh_shape()
    files["assets/index-riIYPcmm.js"] = (
        files["assets/index-riIYPcmm.js"]
        + 'import "./mermaid.core-PVSKwLbE.js";\n'
    )
    files["assets/mermaid.core-PVSKwLbE.js"] = "export const x=1;\n"
    with serve(write_tree(tmp_path, files)) as base:
        assert run(base) == 0
    out = capsys.readouterr().out
    assert "OK" in out
    assert "core-PVSKwLbE.js" not in out.split("entry:", 1)[1]


def test_stale_page_is_found_behind_a_ref_inside_another_chunk(tmp_path, capsys):
    """THE ONE-HOP TEST. The fossil appears in a chunk the INDEX never names - only a chunk-map in
    the entry names it. A scan of the index's own assets reports nothing stale and nothing live;
    the closure must still report the fossil."""
    files = fresh_shape()
    files["assets/index-riIYPcmm.js"] = (
        'const pages={"a":"/assets/SeatDetailPage-FRESH0001.js",'
        '"/assets/LegacyPage-FRESH0009.js":1};\n'
    )
    files["assets/LegacyPage-FRESH0009.js"] = 'const g="scripts/scrub.py";\n'
    with serve(write_tree(tmp_path, files)) as base:
        assert run(base) == 1
    out = capsys.readouterr().out
    assert "scripts/scrub.py" in out
    assert "LegacyPage-FRESH0009.js" in out  # the report names WHERE, not just that


def test_a_dotted_stem_sibling_rides_the_closure_whole(tmp_path, capsys):
    """A stem may contain dots. Production names `mermaid.core-CGIcD27U.js`; matching only its tail
    (`core-CGIcD27U.js`) fetches a name the build never had, 404s, and reads INCOMPLETE on a fresh
    surface (measured 2026-10-18, board b70278f2)."""
    files = fresh_shape()
    files["assets/index-riIYPcmm.js"] += 'const m="./mermaid.core-CGIcD27U.js";\n'
    files["assets/mermaid.core-CGIcD27U.js"] = "export const core=1;\n"
    with serve(write_tree(tmp_path, files)) as base:
        assert run(base) == 0
    assert "OK" in capsys.readouterr().out
    assert census.discover_refs('"./mermaid.core-CGIcD27U.js"') == {"/assets/mermaid.core-CGIcD27U.js"}
    assert census.discover_refs('"cytoscape.esm-CkK8FqzY.js"') == {"/assets/cytoscape.esm-CkK8FqzY.js"}


def test_a_ref_inside_a_word_is_not_a_ref():
    """`assets/` inside a longer word is not a path: the served root is `/assets/`."""
    assert census.discover_refs('const a="myassets/x.css";const b="/assets/x.css"') == {"/assets/x.css"}


def test_needle_boundary_is_the_discriminator(tmp_path):
    """Why the census keys on `4genteam` and `scripts/*.py`, and never on `sync pull`.

    The old string is `scripts/seat_sync.py pull` - it contains `sync.py pull`, NOT `sync pull`. So a
    census that used `sync pull` as the OLD-name needle finds NOTHING on the bundle that still has
    the old string, and reads as "the old string is gone" - a false pass on the exact artifact this
    exists to catch. Pinned here so a later simplification to that needle fails in the suite."""
    stale = "scripts/seat_sync.py pull ${room} ${seat}"
    fresh = "4genteam sync pull ${room} ${seat}"
    assert "sync pull" not in stale, "the naive needle cannot see the stale string - that is the trap"
    assert census.DELETED_NAME.search(stale), "the pattern DOES see it"
    assert not census.DELETED_NAME.search(fresh)
    assert census.VERB_PATTERNS["sync pull"].search(fresh)
    assert not census.VERB_PATTERNS["sync pull"].search(stale)


def test_a_deleted_name_that_is_not_one_of_the_four_is_still_a_fossil(tmp_path, capsys):
    """The pattern, not a closed list: a future retirement is covered without editing the census."""
    files = fresh_shape()
    files["assets/SeatDetailPage-FRESH0001.js"] += 'const h="scripts/summon.py";\n'
    with serve(write_tree(tmp_path, files)) as base:
        assert run(base) == 1
    assert "scripts/summon.py" in capsys.readouterr().out


# --- identity --------------------------------------------------------------------------------

def test_identity_rejects_a_bundle_that_is_only_token_deep(tmp_path, capsys):
    """The census is satisfiable by a bundle containing the token and nothing else. Identity is what
    closes that: same tree, censused OK, refused by --expect-dist."""
    mutant = {
        "index.html": '<!doctype html><script type="module" src="/assets/index-AAAAAAAA.js"></script>\n',
        "assets/index-AAAAAAAA.js": "4genteam sync pull\n",
    }
    build = write_tree(tmp_path / "build", fresh_shape())
    with serve(write_tree(tmp_path / "served", mutant)) as base:
        assert run(base) == 0  # the census alone cannot see this
        assert "OK" in capsys.readouterr().out
        assert run(base, "--expect-dist", str(build)) == 1
    assert "BUILD-MISMATCH" in capsys.readouterr().out


def test_identity_accepts_the_build_it_was_given(tmp_path, capsys):
    """And the positive direction, or identity is a wall too: a served build that IS the expected
    build passes, stylesheets included (a JS-only inventory reports a .css as absent - a false
    mismatch this test exists to catch)."""
    build = write_tree(tmp_path / "build", fresh_shape())
    with serve(build) as base:
        assert run(base, "--expect-dist", str(build)) == 0
    assert "MATCH" in capsys.readouterr().out


def test_identity_by_entry_hash_alone(tmp_path, capsys):
    with serve(write_tree(tmp_path, fresh_shape())) as base:
        assert run(base, "--expect-entry", "index-riIYPcmm.js") == 0
        assert run(base, "--expect-entry", "index-SOMETHINGELSE.js") == 1


# --- the expectation is only comparable from the same environment -------------------------------

# What vite inlines for a tree reading `import.meta.env[key]` dynamically: the box build carried six
# keys, the deployed build eighteen. Same tree, different hash - measured 2026-10-21.
BOX_ENV = ('{BASE_URL:"/",DEV:!1,MODE:"production",PROD:!0,SSR:!1,'
           'VITE_API_URL:"https://api.4genthub.com"}')
DEPLOY_ENV = ('{BASE_URL:"/",DEV:!1,MODE:"production",PROD:!0,SSR:!1,'
              'VITE_API_URL:"https://api.4genthub.com",VITE_BACKEND_URL:"https://api.4genthub.com",'
              'VITE_BUILD_SHA:"",VITE_ENV:"production",VITE_KEYCLOAK_URL:"https://keycloak.4genthub.com",'
              'VITE_LOG_LEVEL:"error",VITE_LOG_ENABLED:"true",VITE_LOG_COLORIZE:"false"}')


def test_env_signature_reads_the_inlined_object():
    """The fingerprint is the object, not a guess: keys and values, booleans included."""
    signature = census.env_signature(f"const x={BOX_ENV};console.log('VITE_WS_URL')")
    assert signature == {
        "BASE_URL": "/", "DEV": "!1", "MODE": "production", "PROD": "!0", "SSR": "!1",
        "VITE_API_URL": "https://api.4genthub.com",
    }
    assert census.env_signature("4genteam sync pull") is None
    assert census.env_signature('const s="https://api.4genthub.com";') is None


def test_a_foreign_env_build_is_refused_not_called_a_mismatch(tmp_path, capsys):
    """The defect this closes: a box-built dist compared to a deploy made by the deploy image reported
    BUILD-MISMATCH about a correct production. The environments are in both artifacts, so the check
    must read them and refuse - naming the keys - instead of accusing the site."""
    build = write_tree(tmp_path / "build", fresh_shape(entry="index-BUILT0001.js", env=BOX_ENV))
    served = write_tree(tmp_path / "served", fresh_shape(entry="index-LIVE00001.js", env=DEPLOY_ENV))
    with serve(served) as base:
        assert run(base, "--expect-dist", str(build)) == 2
    out = capsys.readouterr().out
    assert "FOREIGN-ENV" in out
    assert "NOT comparable" in out
    assert "VITE_KEYCLOAK_URL" in out  # only the served build inlined it
    assert "BUILD-MISMATCH" not in out


def test_a_differing_value_is_a_foreign_environment_too(tmp_path, capsys):
    """Same keys is not the same environment: an API URL the deploy does not use re-hashes the chunks
    that carry it, so the value is compared, not just the key set."""
    served_env = DEPLOY_ENV
    build_env = DEPLOY_ENV.replace('VITE_API_URL:"https://api.4genthub.com"',
                                   'VITE_API_URL:"http://localhost:8000"')
    build = write_tree(tmp_path / "build", fresh_shape(entry="index-BUILT0002.js", env=build_env))
    with serve(write_tree(tmp_path / "served", fresh_shape(entry="index-LIVE00002.js", env=served_env))) as base:
        assert run(base, "--expect-dist", str(build)) == 2
    out = capsys.readouterr().out
    assert "FOREIGN-ENV" in out
    assert "differing values (1): VITE_API_URL" in out


def test_a_same_env_build_is_still_compared_and_can_mismatch(tmp_path, capsys):
    """And the direction that keeps identity honest: two builds of the same environment ARE comparable,
    so a served bundle that is not the build is still a mismatch - the gate must not swallow it."""
    build = write_tree(tmp_path / "build", fresh_shape(entry="index-BUILT0003.js", env=BOX_ENV))
    served = write_tree(tmp_path / "served", fresh_shape(entry="index-LIVE00003.js", env=BOX_ENV))
    with serve(served) as base:
        assert run(base, "--expect-dist", str(build)) == 1
    out = capsys.readouterr().out
    assert "comparable" in out and "FOREIGN-ENV" not in out
    assert "BUILD-MISMATCH" in out


def test_a_served_entry_that_did_not_arrive_is_not_a_foreign_environment(tmp_path, capsys):
    """Only an env object that was READ may refuse: when the served entry 404s the closure is incomplete,
    and calling that a foreign environment would name the wrong defect."""
    build = write_tree(tmp_path / "build", fresh_shape(entry="index-BUILT0004.js", env=BOX_ENV))
    served = {"index.html": '<!doctype html><script type="module" src="/assets/index-GONE000001.js"></script>\n'}
    with serve(write_tree(tmp_path / "served", served)) as base:
        assert run(base, "--expect-dist", str(build)) == 1
    out = capsys.readouterr().out
    assert "FOREIGN-ENV" not in out
    assert "environment:" not in out


# --- the expected side is dated ---------------------------------------------------------------

def dated_frontend(tmp_path: Path, *, commit_age_days: float, build_age_days: float) -> Path:
    """A work tree whose frontend build was produced `build_age_days` ago and whose last source commit is
    `commit_age_days` ago. The commit dates are pinned through the environment, so neither side depends on
    how fast the test runs."""
    now = time.time()
    repo = tmp_path / "repo"
    repo.mkdir()
    frontend = repo / "agenthub-frontend"
    write_tree(frontend / "src", {"App.tsx": "export const x = 1\n"})
    build = write_tree(frontend / "build", fresh_shape())
    # Every git call goes through the shared fixture helper, which drops the variables that can relocate a
    # repository: a fixture must never write the caller's checkout (the 2026-10-11 incident).
    gitfixture.git(repo, "init", "-q", ".")
    gitfixture.git(repo, "config", "user.email", "fixture@test.invalid")
    gitfixture.git(repo, "config", "user.name", "fixture test")
    gitfixture.git(repo, "add", "-A")
    stamp = f"@{int(now - commit_age_days * 86400)} +0000"
    gitfixture.git(repo, "commit", "-qm", "frontend", env={"GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp})
    built = now - build_age_days * 86400
    for path in build.rglob("*"):
        if path.is_file():
            os.utime(path, (built, built))
    return build


def test_a_stale_expected_build_is_refused_not_compared(tmp_path, capsys):
    """The defect this pins: the served side was rebuilt after every frontend commit while the expected side
    came from a build ten days old, so the check reported BUILD-MISMATCH about an artifact nobody maintained.
    A dated expectation that predates the last frontend commit must refuse (exit 2, naming both ages) instead
    of comparing."""
    build = dated_frontend(tmp_path, commit_age_days=0, build_age_days=10)
    with serve(build) as base:
        assert run(base, "--expect-dist", str(build)) == 2
    out = capsys.readouterr().out
    assert "CANNOT-MEASURE" in out
    assert "the expected build is stale" in out
    assert "10.0 day" in out
    assert "BUILD-MISMATCH" not in out


def test_a_current_expected_build_is_compared(tmp_path, capsys):
    """And the direction that keeps the instrument usable: a build newer than the last frontend commit is
    dated as current and compared as before."""
    build = dated_frontend(tmp_path, commit_age_days=1, build_age_days=0)
    with serve(build) as base:
        assert run(base, "--expect-dist", str(build)) == 0
    out = capsys.readouterr().out
    assert "expected build:" in out and "current" in out
    assert "MATCH" in out


def test_an_undated_expected_build_is_compared_not_refused(tmp_path, capsys):
    """The other side of the staleness rule, and the limit the reviewer named: a build inside a git work tree
    whose frontend sources are NOT committed has no commit to be aged against, so it is undated - reported as
    absent, compared exactly as before the rule, never refused as stale."""
    repo = tmp_path / "repo"
    repo.mkdir()
    build = write_tree(repo / "agenthub-frontend" / "build", fresh_shape())
    # Sources exist and are untracked, so `git log -- . :(exclude)build` from the frontend finds no commit.
    write_tree(repo / "agenthub-frontend" / "src", {"App.tsx": "export const x = 1\n"})
    gitfixture.git(repo, "init", "-q", ".")
    gitfixture.git(repo, "config", "user.email", "fixture@test.invalid")
    gitfixture.git(repo, "config", "user.name", "fixture test")
    gitfixture.git(repo, "add", "--", "agenthub-frontend/build")
    gitfixture.git(repo, "commit", "-qm", "build only")
    with serve(build) as base:
        assert run(base, "--expect-dist", str(build)) == 0
        assert run(base, "--expect-dist", str(build), "--json") == 0
    out = capsys.readouterr().out
    assert "the expected build is stale" not in out
    assert "expected_build" not in out, "an undated build must not be reported as dated"
    assert "MATCH" in out


# --- fail-closed -----------------------------------------------------------------------------

def test_unreachable_origin_is_cannot_measure_not_a_pass(tmp_path, capsys):
    assert run("http://127.0.0.1:9", "--timeout", "2") == 2
    assert "CANNOT-MEASURE" in capsys.readouterr().out


def test_a_missing_chunk_makes_the_verdict_incomplete_not_ok(tmp_path, capsys):
    """A fetched-but-fresh surface with a 404 in the closure is NOT a pass: a stale chunk could be
    hiding in the part that did not arrive."""
    files = fresh_shape()
    files["assets/index-riIYPcmm.js"] = files["assets/index-riIYPcmm.js"].replace(
        '"/assets/SeatsPage-FRESH0002.js":1', '"/assets/SeatsPage-GONE000099.js":1'
    )
    with serve(write_tree(tmp_path, files)) as base:
        assert run(base) == 2
    assert "INCOMPLETE" in capsys.readouterr().out


def test_closure_cap_refuses_a_partial_census(tmp_path, capsys):
    with serve(write_tree(tmp_path, fresh_shape())) as base:
        assert run(base, "--max-assets", "1") == 2
    assert "CANNOT-MEASURE" in capsys.readouterr().out


def test_a_server_without_last_modified_does_not_stop_the_census(tmp_path, capsys):
    """The date is what lets the census DATE the drift; it is not a precondition for a verdict."""
    with serve(write_tree(tmp_path, fresh_shape()), handler=NoLastModifiedHandler) as base:
        assert run(base) == 0
    out = capsys.readouterr().out
    assert "Last-Modified unknown" in out


def test_json_report_carries_the_counts_and_the_date(tmp_path, capsys):
    with serve(write_tree(tmp_path, production_shape())) as base:
        assert run(base, "--json") == 1
    payload = census.json.loads(capsys.readouterr().out)
    assert payload["verdict"] == "STALE"
    assert payload["served_entry"] == "index-BMd9UnWH.js"
    assert payload["deleted_names"]["scripts/seat_sync.py"]["occurrences"] == 2
    assert payload["last_modified"]["index"]
    assert payload["verbs"]["sync pull"]["files"] == 0


def frontend_origin(tmp_path: Path) -> tuple[Path, str]:
    """A repo whose `origin/frontend` is one commit: the expected side of `--expect-build-of`.

    Real git, real `rev-parse`: the mode reads the ref through the same helper the rest of the script uses,
    so a stub here would prove nothing about the command a seat runs.
    """
    repo = tmp_path / "repo"
    write_tree(repo, {"frontend/src/App.tsx": "export const x = 1\n"})
    gitfixture.git(repo, "init", "-q", ".")
    gitfixture.git(repo, "config", "user.email", "fixture@test.invalid")
    gitfixture.git(repo, "config", "user.name", "fixture test")
    gitfixture.git(repo, "add", "-A")
    gitfixture.git(repo, "commit", "-qm", "frontend")
    gitfixture.git(repo, "update-ref", "refs/remotes/origin/frontend", "HEAD")
    sha = gitfixture.git(repo, "rev-parse", "HEAD").stdout.strip()
    return repo, sha


def stamped_env(stamp: str) -> str:
    """DEPLOY_ENV with the build stamp a `--build-arg` build writes: both keys, filled.

    The production entry carries both keys and no VITE_BUILD_TIME today (Dockerfile.frontend.production
    declares the ARGs with no default and captain-definition.frontend passes none), which is why the empty
    case is DEPLOY_ENV itself, below.
    """
    return DEPLOY_ENV.replace(
        'VITE_BUILD_SHA:""',
        f'VITE_BUILD_SHA:"{stamp}",VITE_BUILD_TIME:"2026-10-23T00:00:00Z"',
    )


def test_a_matching_build_stamp_is_ok(tmp_path, capsys, monkeypatch):
    """The one thing a seat can prove about a deploy: the served build says it read this commit. A string
    comparison, so the deploy image's node/arch/VITE_* set cannot turn it into a refusal."""
    repo, sha = frontend_origin(tmp_path)
    monkeypatch.chdir(repo)
    gitfixture.without_relocating(monkeypatch)
    with serve(write_tree(tmp_path / "served", fresh_shape(env=stamped_env(sha)))) as base:
        assert run(base, "--expect-build-of", "origin/frontend", "--json") == 0
    payload = census.json.loads(capsys.readouterr().out)
    assert payload["verdict"] == "OK"
    assert payload["served_build_sha"] == sha
    assert payload["expected_sha"] == sha
    assert payload["served_build_time"] == "2026-10-23T00:00:00Z"


def test_a_different_build_sha_is_stale(tmp_path, capsys, monkeypatch):
    """The deploy did not happen, and the stamp is the evidence: OK here would report a build nobody made."""
    repo, sha = frontend_origin(tmp_path)
    monkeypatch.chdir(repo)
    gitfixture.without_relocating(monkeypatch)
    other = "deadbeef" + sha[8:]
    with serve(write_tree(tmp_path / "served", fresh_shape(env=stamped_env(other)))) as base:
        assert run(base, "--expect-build-of", "origin/frontend") == 1
    out = capsys.readouterr().out
    assert "STALE" in out
    assert f"serves {other}" in out and f"expected {sha}" in out


def test_an_empty_or_absent_stamp_is_incomplete_never_a_pass(tmp_path, capsys, monkeypatch):
    """Today's production shape: the key is inlined and empty, because no build arg reaches the build. That is
    a refusal - nothing about the deploy has been proven - not the census's OK."""
    repo, sha = frontend_origin(tmp_path)
    monkeypatch.chdir(repo)
    gitfixture.without_relocating(monkeypatch)
    with serve(write_tree(tmp_path / "empty", fresh_shape(env=DEPLOY_ENV))) as base:
        assert run(base, "--expect-build-of", "origin/frontend") == 2
    no_key = DEPLOY_ENV.replace('VITE_BUILD_SHA:"",', "")
    with serve(write_tree(tmp_path / "absent", fresh_shape(env=no_key))) as base:
        assert run(base, "--expect-build-of", "origin/frontend") == 2
    out = capsys.readouterr().out
    assert "INCOMPLETE" in out and "not a pass" in out
    assert "VITE_BUILD_SHA" in out
    assert "OK:" not in out


def test_a_short_sha_prefix_is_accepted_at_seven_characters(tmp_path, capsys, monkeypatch):
    """`git rev-parse --short` writes 7 characters and the repo's only stamp writer uses it, so a 7-character
    prefix of the expected commit is a match - while a 6-character one names no commit and is a refusal."""
    repo, sha = frontend_origin(tmp_path)
    monkeypatch.chdir(repo)
    gitfixture.without_relocating(monkeypatch)
    with serve(write_tree(tmp_path / "seven", fresh_shape(env=stamped_env(sha[:7])))) as base:
        assert run(base, "--expect-build-of", "origin/frontend", "--json") == 0
    payload = census.json.loads(capsys.readouterr().out)
    assert payload["served_build_sha"] == sha[:7]
    assert payload["build_why"] == "the served stamp is a 7-character prefix of the expected commit"
    with serve(write_tree(tmp_path / "six", fresh_shape(env=stamped_env(sha[:6])))) as base:
        assert run(base, "--expect-build-of", "origin/frontend") == 2
    assert "shorter than 7 characters" in capsys.readouterr().out


def test_a_non_hex_stamp_is_incomplete(tmp_path, capsys, monkeypatch):
    """A stamp that is not a commit id cannot be compared at all: exit 2, never a STALE and never an OK."""
    repo, sha = frontend_origin(tmp_path)
    monkeypatch.chdir(repo)
    gitfixture.without_relocating(monkeypatch)
    with serve(write_tree(tmp_path / "served", fresh_shape(env=stamped_env("not-a-commit-id")))) as base:
        assert run(base, "--expect-build-of", "origin/frontend") == 2
    out = capsys.readouterr().out
    assert "INCOMPLETE" in out
    assert "is not a hex commit id" in out


def test_an_empty_ref_is_a_refusal_not_a_disabled_check(tmp_path, capsys, monkeypatch):
    """The gate's finding on 1c165dd4: `--expect-build-of ""` (and `=`) passed an empty string, truthiness read it
    as "no flag", and the run printed the census's OK about a deploy nothing was compared to. That is exactly the
    shape a deploy produces when `$(git rev-parse origin/frontend)` fails - a flag that silently disables its own
    proof. An empty ref is a GIVEN expectation that cannot be resolved, so exit 2."""
    repo, _sha = frontend_origin(tmp_path)
    monkeypatch.chdir(repo)
    gitfixture.without_relocating(monkeypatch)
    with serve(write_tree(tmp_path / "served", fresh_shape(env=stamped_env(_sha)))) as base:
        assert run(base, "--expect-build-of", "") == 2
        assert run(base, "--expect-build-of=") == 2
        assert run(base, "--expect-build-of", "  ") == 2
    out = capsys.readouterr().out
    assert "an empty ref is a refusal, never an absent flag" in out
    assert "OK:" not in out


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
