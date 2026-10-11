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
import threading
from contextlib import contextmanager
from pathlib import Path

import pytest

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
            'const c="openrig_seat_sync.py switch <room> <seat> --model <id>";\n'
            'const d="scripts/openrig_seat_sync.py pull ${room} ${seat}";\n'
        ),
        "assets/SeatsPage-DRldE7DQ.js": (
            'const e="No bridge connected. Run scripts/openrig_bridge.py on your PC.";\n'
        ),
    }


def fresh_shape(entry: str = "index-riIYPcmm.js") -> dict[str, str]:
    """A HEAD build, reduced: three panels, three verbs, no fossil."""
    return {
        "index.html": f'<!doctype html><script type="module" crossorigin src="/assets/{entry}"></script>\n',
        "assets/" + entry: (
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
    assert "openrig_seat_sync.py" in out and "openrig_bridge.py" in out
    assert "live verb 'sync pull': ABSENT" in out


def test_a_fresh_build_reads_ok(tmp_path, capsys):
    """HEAD's shape must pass, or the census only ever says no."""
    with serve(write_tree(tmp_path, fresh_shape())) as base:
        assert run(base) == 0
    assert "OK" in capsys.readouterr().out


def test_stale_page_is_found_behind_a_ref_inside_another_chunk(tmp_path, capsys):
    """THE ONE-HOP TEST. The fossil appears in a chunk the INDEX never names - only a chunk-map in
    the entry names it. A scan of the index's own assets reports nothing stale and nothing live;
    the closure must still report the fossil."""
    files = fresh_shape()
    files["assets/index-riIYPcmm.js"] = (
        'const pages={"a":"/assets/SeatDetailPage-FRESH0001.js",'
        '"/assets/LegacyPage-FRESH0009.js":1};\n'
    )
    files["assets/LegacyPage-FRESH0009.js"] = 'const g="scripts/openrig_scrub.py";\n'
    with serve(write_tree(tmp_path, files)) as base:
        assert run(base) == 1
    out = capsys.readouterr().out
    assert "openrig_scrub.py" in out
    assert "LegacyPage-FRESH0009.js" in out  # the report names WHERE, not just that


def test_needle_boundary_is_the_discriminator(tmp_path):
    """Why the census keys on `4genteam` and `openrig_*.py`, and never on `sync pull`.

    The old string is `openrig_seat_sync.py pull` - it contains `sync.py pull`, NOT `sync pull`. So a
    census that used `sync pull` as the OLD-name needle finds NOTHING on the bundle that still has
    the old string, and reads as "the old string is gone" - a false pass on the exact artifact this
    exists to catch. Pinned here so a later simplification to that needle fails in the suite."""
    stale = "scripts/openrig_seat_sync.py pull ${room} ${seat}"
    fresh = "4genteam sync pull ${room} ${seat}"
    assert "sync pull" not in stale, "the naive needle cannot see the stale string - that is the trap"
    assert census.DELETED_NAME.search(stale), "the pattern DOES see it"
    assert not census.DELETED_NAME.search(fresh)
    assert census.VERB_PATTERNS["sync pull"].search(fresh)
    assert not census.VERB_PATTERNS["sync pull"].search(stale)


def test_a_deleted_name_that_is_not_one_of_the_four_is_still_a_fossil(tmp_path, capsys):
    """The pattern, not a closed list: a future retirement is covered without editing the census."""
    files = fresh_shape()
    files["assets/SeatDetailPage-FRESH0001.js"] += 'const h="scripts/openrig_summon.py";\n'
    with serve(write_tree(tmp_path, files)) as base:
        assert run(base) == 1
    assert "openrig_summon.py" in capsys.readouterr().out


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
    assert payload["deleted_names"]["openrig_seat_sync.py"]["occurrences"] == 2
    assert payload["last_modified"]["index"]
    assert payload["verbs"]["sync pull"]["files"] == 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
