#!/usr/bin/env python3
"""check_served_frontend.py - the acceptance census for "is the live frontend a build of HEAD?"

WHY IT EXISTS
    On 2026-10-10 production served a frontend built on 2026-10-08 19:26:51Z: two days and 165
    commits behind main, with the composer work missing and the deleted `scripts/openrig_*.py`
    names still on screen as instructions. Two seats measured that BY HAND, with a shape of
    command neither could hand to a successor. This is the one command.

WHAT IT ASSERTS (default mode, the census)
    1. at least one `4genteam` verb is served  - `4genteam sync pull`, `4genteam sync switch`,
       `4genteam bridge` are the replacements, and every panel that carried a deleted script name
       now carries one of them.
    2. ZERO deleted-script names are served - matched as a PATTERN (`openrig_<name>.py`), not as a
       closed list of four, so the next deletion is covered without editing this file.

THE TWO MISTAKES THIS IS BUILT TO NOT MAKE
    * THE ONE-HOP MISTAKE. index.html names only what loads eagerly; the app lazy-loads its pages,
      so the stale strings live in chunks the index never names. A census over the index's own
      assets reports 0 old strings AND 0 new ones - which reads like a clean surface and is really
      a scan that sees nothing. So the walk takes the CLOSURE: the index's refs, then the refs
      found inside those, to a fixpoint.
    * THE NAIVE NEEDLE. The old string is `openrig_seat_sync.py pull`; the new one is
      `4genteam sync pull`. A census keyed on `sync pull` therefore returns ZERO on the stale build
      as well as on the fresh one - a false pass, on the exact artifact this exists to catch.
      `4genteam` and `openrig_*.py` are the discriminators; `sync pull` is not one, and
      test_needle_boundary_is_documented pins that down.

WHAT THE CENSUS DOES *NOT* PROVE, AND THE MODE THAT CLOSES IT
    A two-token census is satisfied by ANY build after the rename landed (75f81494, 2026-10-09
    21:05+0200) - a window that tonight was 24 frontend commits wide. Passing the census means
    "newer than 08 Oct", not "is this build". When you HAVE the build - which a deploy step does,
    because it just made one - pass `--expect-dist <dir>` (or `--expect-entry <hash>`) and the
    verdict becomes identity: the served entry chunk hash must be the built entry chunk hash, and
    every script the served app is composed of must exist in that build. Then OK means "the build I
    just made is the build being served", which is the claim a deploy actually needs.

USAGE
    python3 scripts/check_served_frontend.py [--base-url https://www.4genthub.com] [--json]
    python3 scripts/check_served_frontend.py --expect-dist agenthub-frontend/build
EXIT
    0 = fresh (and, in identity mode, the served build IS the expected build)
    1 = stale or a build mismatch - the served app is not the expected build
    2 = the census could not be taken (fetch/parse/cap failure) - NEVER reported as a pass
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request

# The replacements, per src/components/seats/SeatPreview.tsx:37 (sync pull), SeatLlmPanel.tsx:99
# (sync switch) and MachinesPanel.tsx:179 (bridge register / bridge run).
VERB_PATTERNS = {
    "sync pull": re.compile(r"4genteam sync pull"),
    "sync switch": re.compile(r"4genteam sync switch"),
    "bridge": re.compile(r"4genteam bridge"),
}
# The deleted names, as a PATTERN: every `openrig_<something>.py` reference is a fossil, whether or
# not it is one of the four names that happened to appear in the 08 Oct bundle.
DELETED_NAME = re.compile(r"openrig_[a-z0-9_]+\.py", re.IGNORECASE)

# Refs to other assets: the queued form the HTML uses, and the bare hashed file name a chunk uses
# to name its lazy siblings (`./SeatDetailPage-BpUArPYK.js`).
ASSET_REF = re.compile(r"""(?:\.?/)?assets/[A-Za-z0-9_.-]+\.(?:js|css)""")
HASHED_REF = re.compile(r"""[A-Za-z0-9_-]+-[A-Za-z0-9_-]{8,}\.(?:js|css)""")
ENTRY_REF = re.compile(r"""/assets/(index-[A-Za-z0-9_-]+\.js)""")
# The entry is the one the page LOADS, not merely the first /assets/index-*.js mentioned: vite emits
# modulepreload links for the entry's siblings, so a bare first-match can name a lazy chunk and the
# identity check would then compare the wrong hash.
ENTRY_SCRIPT = re.compile(r'<script[^>]+src="/assets/(index-[A-Za-z0-9_-]+\.js)"')

DEFAULT_MAX_ASSETS = 400


class CannotMeasure(Exception):
    """The census could not be taken. Distinct from 'stale': this one is never a pass."""


class Fetcher:
    """HTTP with the two properties the census needs: a cache-busted GET, and Last-Modified.

    The index is fetched with a unique query string because a cached index would hide a rebuild
    behind a stale reference - and a stale reference is indistinguishable, from the outside, from a
    bundle that was never rebuilt. The census is only allowed to say that if it has ruled the
    cache out (this script also prints the dates, so the two are comparable).
    """

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self.base = base_url.rstrip("/")
        self.timeout = timeout
        self.failures: list[str] = []

    def _request(self, path: str, method: str = "GET") -> urllib.request.Request:
        url = path if path.startswith("http") else self.base + path
        return urllib.request.Request(url, method=method, headers={"User-Agent": "check-served-frontend"})

    def get(self, path: str) -> bytes:
        try:
            with urllib.request.urlopen(self._request(path), timeout=self.timeout) as response:
                return response.read()
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
            raise CannotMeasure(f"cannot fetch {path}: {exc}") from exc

    def get_or_note(self, path: str) -> bytes | None:
        """Best effort, for the closure walk: a missing chunk is noted, not fatal."""
        try:
            return self.get(path)
        except CannotMeasure as exc:
            self.failures.append(str(exc))
            return None

    def last_modified(self, path: str) -> str | None:
        try:
            with urllib.request.urlopen(self._request(path, "HEAD"), timeout=self.timeout) as response:
                return response.headers.get("Last-Modified")
        except Exception:  # noqa: BLE001 - a missing date must not stop a census
            return None


def find_entry(html: str) -> str | None:
    """The entry chunk: the script the page loads, else the first /assets/index-*.js mentioned."""
    match = ENTRY_SCRIPT.search(html) or ENTRY_REF.search(html)
    return match.group(1) if match else None


def normalize_ref(ref: str) -> str:
    """Resolve a reference found inside another asset to an absolute URL path.

    Chunk names are relative to the chunk that names them (`./X.js` inside `/assets/Y.js`), while
    index.html uses the queued `/assets/X.js` form. Both are reduced to the path the server has.
    """
    name = ref.rsplit("/", 1)[-1]
    return "/assets/" + name


def discover_refs(text: str) -> set[str]:
    refs = {normalize_ref(m) for m in ASSET_REF.findall(text)}
    refs |= {normalize_ref(m) for m in HASHED_REF.findall(text)}
    return refs


def walk_closure(fetcher: Fetcher, entry_refs: set[str], max_assets: int) -> dict[str, str]:
    """Fetch the index's refs, then the refs found inside those, to a fixpoint.

    Returns {path: decoded text}. Any text asset can name more assets, so each fetched text is
    scanned again - that is the whole difference between this and a one-hop scan.
    """
    pending = sorted(entry_refs)
    seen: set[str] = set()
    texts: dict[str, str] = {}
    while pending:
        path = pending.pop(0)
        if path in seen:
            continue
        seen.add(path)
        if len(seen) > max_assets:
            raise CannotMeasure(f"closure exceeded {max_assets} assets - refusing to census a partial set")
        raw = fetcher.get_or_note(path)
        if raw is None:
            continue
        text = raw.decode("utf-8", "replace")
        texts[path] = text
        for ref in discover_refs(text):
            if ref not in seen:
                pending.append(ref)
    return texts


def census(texts: dict[str, str]) -> dict:
    verbs: dict[str, dict] = {}
    for label, pattern in VERB_PATTERNS.items():
        carriers = [path for path, text in texts.items() if pattern.search(text)]
        verbs[label] = {"files": len(carriers), "examples": sorted(carriers)[:2]}
    deleted: dict[str, dict] = {}
    deleted_files: list[str] = []
    for path, text in texts.items():
        names = DELETED_NAME.findall(text)
        for name in set(names):
            record = deleted.setdefault(name, {"occurrences": 0, "files": []})
            record["occurrences"] += names.count(name)
            record["files"].append(path)
            if path not in deleted_files:
                deleted_files.append(path)
    for record in deleted.values():
        record["files"] = sorted(record["files"])
    return {
        "verbs": verbs,
        "verbs_present": sum(1 for v in verbs.values() if v["files"]),
        "deleted_names": dict(sorted(deleted.items())),
        "deleted_files": sorted(deleted_files),
    }


def dist_expectation(dist_dir: str) -> tuple[str, set[str]]:
    """Read the build's own identity: its entry chunk hash, and every script name it shipped."""
    index = f"{dist_dir.rstrip('/')}/index.html"
    try:
        with open(index, encoding="utf-8") as handle:
            html = handle.read()
    except OSError as exc:
        raise CannotMeasure(f"cannot read the expected build's index ({index}): {exc}") from exc
    entry = find_entry(html)
    if not entry:
        raise CannotMeasure(f"{index} names no /assets/index-*.js entry")
    from pathlib import Path

    root = Path(dist_dir)
    shipped: set[str] = set()
    # EVERY file the build produced, not just the .js: the served set is scripts AND stylesheets, and
    # a JS-only inventory reports a stylesheet as "absent from the build" - a false mismatch.
    for directory in (root, root / "assets"):
        if directory.is_dir():
            shipped |= {p.name for p in directory.iterdir() if p.is_file()}
    return entry, shipped


def identity_check(served_entry: str | None, served_paths: set[str], expect_entry: str, shipped: set[str] | None) -> dict:
    served_names = {p.rsplit("/", 1)[-1] for p in served_paths}
    absent = sorted(n for n in served_names if shipped and n not in shipped)
    entry_matches = served_entry == expect_entry
    return {
        "expected_entry": expect_entry,
        "served_entry": served_entry,
        "entry_matches": entry_matches,
        "served_assets": len(served_names),
        "served_assets_absent_from_build": absent,
        "shipped_assets_not_reached": len(shipped - served_names) if shipped else None,
        "matches": entry_matches and not absent,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Is the live frontend a build of HEAD?")
    parser.add_argument("--base-url", default="https://www.4genthub.com")
    parser.add_argument("--json", action="store_true", help="emit the report as JSON")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--expect-dist", default=None, help="a built vite outDir (agenthub-frontend/build) - the build the served app must BE")
    parser.add_argument("--expect-entry", default=None, help="the entry chunk hash the served app must serve")
    parser.add_argument("--max-assets", type=int, default=DEFAULT_MAX_ASSETS)
    args = parser.parse_args(argv)

    report: dict = {"origin": args.base_url, "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    try:
        fetcher = Fetcher(args.base_url, args.timeout)
        bust = f"?cb={int(time.time())}"
        html = fetcher.get("/" + bust).decode("utf-8", "replace")
        report["last_modified"] = {
            "index": fetcher.last_modified("/"),
        }
        served_entry = find_entry(html)
        report["served_entry"] = served_entry

        entry_refs = discover_refs(html)
        if not entry_refs:
            raise CannotMeasure("the index names no /assets/*.js - nothing to census")
        texts = walk_closure(fetcher, entry_refs, args.max_assets)
        report["last_modified"]["entry"] = fetcher.last_modified(f"/assets/{served_entry}") if served_entry else None
        report["assets"] = {"fetched": len(texts), "bytes": sum(len(t.encode()) for t in texts.values())}
        report["fetch_failures"] = fetcher.failures[:10]

        result = census(texts)
        report.update(result)

        expected_entry, shipped = None, None
        if args.expect_dist:
            expected_entry, shipped = dist_expectation(args.expect_dist)
        elif args.expect_entry:
            expected_entry = args.expect_entry
        if expected_entry:
            report["identity"] = identity_check(served_entry, set(texts), expected_entry, shipped)

        stale = result["deleted_names"] or result["verbs_present"] == 0
        if stale:
            report["verdict"] = "STALE"
            exit_code = 1
        elif "identity" in report and not report["identity"]["matches"]:
            report["verdict"] = "BUILD-MISMATCH"
            exit_code = 1
        elif fetcher.failures:
            # Every assertion that could be made passed, but the closure was incomplete: a stale
            # chunk could be hiding in the part that did not arrive. Incomplete is not a pass.
            report["verdict"] = "INCOMPLETE"
            exit_code = 2
        else:
            report["verdict"] = "OK"
            exit_code = 0
    except CannotMeasure as exc:
        report["verdict"] = "CANNOT-MEASURE"
        report["error"] = str(exc)
        exit_code = 2

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_report(report)
    return exit_code


def print_report(report: dict) -> None:
    print(f"origin: {report['origin']}")
    modified = report.get("last_modified", {})
    print(f"served build: index Last-Modified {modified.get('index') or 'unknown'}"
          f" | entry Last-Modified {modified.get('entry') or 'unknown'}")
    print(f"entry: {report.get('served_entry')}")
    if "assets" in report:
        print(f"closure: {report['assets']['fetched']} assets, {report['assets']['bytes']} bytes")
    for label, info in report.get("verbs", {}).items():
        state = f"{info['files']} file(s)" if info["files"] else "ABSENT"
        print(f"  live verb {label!r}: {state}")
    for name, record in report.get("deleted_names", {}).items():
        where = ", ".join(record["files"][:3])
        if len(record["files"]) > 3:
            where += f", +{len(record['files']) - 3} more"
        print(f"  DELETED name {name}: {record['occurrences']} occurrence(s) in {len(record['files'])} file(s) -> {where}")
    if report.get("fetch_failures"):
        print(f"  fetch failures: {report['fetch_failures']}")
    if "identity" in report:
        ident = report["identity"]
        print(f"  identity: served entry {ident['served_entry']} vs expected {ident['expected_entry']}"
              f" -> {'MATCH' if ident['entry_matches'] else 'MISMATCH'}")
        if ident["served_assets_absent_from_build"]:
            absent = ident["served_assets_absent_from_build"]
            shown = ", ".join(absent[:5]) + (f", +{len(absent) - 5} more" if len(absent) > 5 else "")
            print(f"  served assets absent from the build ({len(absent)}): {shown}")
    verdict = report.get("verdict")
    messages = {
        "OK": "OK: the served frontend names the live client and no deleted script",
        "STALE": "STALE: the served frontend is not a build of HEAD - the pre-fix bundle is still live",
        "BUILD-MISMATCH": "BUILD-MISMATCH: the live frontend is NOT the build it was supposed to be",
        "INCOMPLETE": "INCOMPLETE: assertions passed on the part that arrived, but the closure did not - not a pass",
        "CANNOT-MEASURE": f"CANNOT-MEASURE: the census could not be taken ({report.get('error')})",
    }
    print(messages.get(verdict, verdict))


if __name__ == "__main__":
    sys.exit(main())
