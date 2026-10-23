#!/usr/bin/env python3
"""check_served_frontend.py - the acceptance census for "is the live frontend a build of HEAD?"

WHY IT EXISTS
    On 2026-10-10 production served a frontend built on 2026-10-08 19:26:51Z: two days and 165
    commits behind main, with the composer work missing and the deleted `scripts/*.py`
    names still on screen as instructions. Two seats measured that BY HAND, with a shape of
    command neither could hand to a successor. This is the one command.

WHAT IT ASSERTS (default mode, the deploy gate)
    A witness must be supplied, and any one of them failing refuses the deploy:
    - `--expect-dist <dir>` or `--expect-entry <hash>`: the served build must BE that build;
    - `--expect-build-of <ref>`: the stamp the served build carries must name that ref's commit (below);
    - the token witness, on by default from this checkout's `agenthub-frontend/src/styles/theme.css`
      (`--expect-tokens` to point elsewhere): every custom property that file declares must be in the
      served stylesheet's same block. `theme.css` passes through the bundler verbatim, so a served CSS
      from an older tree cannot carry a token added since - which is what a local build is for, minus
      the environment the hash cannot compare across.
    With no witness at all the verdict is CANNOT-MEASURE (exit 2), never OK: on 2026-10-23 this
    script read OK against index-Dd1FoJ_2.js, a bundle whose /login threw `MUI error #9` and left
    #root empty, because the two-token census below is satisfied by any build after the rename.
    So the gate has no opt-out: without a witness the verdict is CANNOT-MEASURE, and the two-token
    census is never a verdict by itself. The token witness names a stale STYLESHEET, not a rendered
    page: the /login probe is the arm that catches a build which throws at render.

    The census itself, which every mode also runs:
    1. at least one `4genteam` verb is served  - `4genteam sync pull`, `4genteam sync switch`,
       `4genteam bridge` are the replacements, and every panel that carried a deleted script name
       now carries one of them.
    2. ZERO deleted-script names are served - matched as a PATTERN (`scripts/<name>.py`), not as a
       closed list of four, so the next deletion is covered without editing this file.

THE TWO MISTAKES THIS IS BUILT TO NOT MAKE
    * THE ONE-HOP MISTAKE. index.html names only what loads eagerly; the app lazy-loads its pages,
      so the stale strings live in chunks the index never names. A census over the index's own
      assets reports 0 old strings AND 0 new ones - which reads like a clean surface and is really
      a scan that sees nothing. So the walk takes the CLOSURE: the index's refs, then the refs
      found inside those, to a fixpoint.
    * THE NAIVE NEEDLE. The old string is `scripts/seat_sync.py pull`; the new one is
      `4genteam sync pull`. A census keyed on `sync pull` therefore returns ZERO on the stale build
      as well as on the fresh one - a false pass, on the exact artifact this exists to catch.
      `4genteam` and `scripts/*.py` are the discriminators; `sync pull` is not one, and
      test_needle_boundary_is_documented pins that down.

WHAT THE CENSUS DOES *NOT* PROVE, AND THE MODE THAT CLOSES IT
    A two-token census is satisfied by ANY build after the rename landed (75f81494, 2026-10-09
    21:05+0200) - a window that tonight was 24 frontend commits wide. Passing the census means
    "newer than 08 Oct", not "is this build". When you HAVE the build - which a deploy step does,
    because it just made one - pass `--expect-dist <dir>` (or `--expect-entry <hash>`) and the
    verdict becomes identity: the served entry chunk hash must be the built entry chunk hash, and
    every script the served app is composed of must exist in that build. Then OK means "the build I
    just made is the build being served", which is the claim a deploy actually needs.

    THE MODE A SEAT CAN TAKE, because a hash cannot be reproduced across environments but a STRING can be
    compared. `--expect-build-of <ref>` (the ref defaults to origin/frontend) reads the stamp the served entry
    carries - VITE_BUILD_SHA and VITE_BUILD_TIME, inlined because environment.ts:32 reads the env object
    dynamically - and compares it to `git rev-parse <ref>`. It says which commit the build read, so the environment cannot
    matter. OK/0 when the stamp is that commit or a hex PREFIX of at least 7 characters (the only in-repo
    writer, scripts/deploy-frontend.sh:86-87, stamps `git rev-parse --short`), STALE/1 when it names another
    commit, INCOMPLETE/2 when it is empty, absent, shorter than 7 hex characters or not hex at all. A missing
    git, an unresolvable ref, and a ref that was GIVEN but is empty are all exit 2: the flag is read by presence,
    never by truthiness, so a deploy line's failed `$(git rev-parse origin/frontend)` refuses instead of turning
    the check off.

    WHERE THE STAMP MUST COME FROM, measured 2026-10-23: not from a docker build arg. CapRover's
    captain-definition schemaVersion 2 has no build-args field and its build context is the uploaded project
    with no .git, so `ARG VITE_BUILD_SHA` (Dockerfile.frontend.production:77-78 until 2026-10-23) never reached
    the build, and the live entry inlined VITE_BUILD_SHA:"". Every run of this mode on that bundle is
    INCOMPLETE/2 - the truth about what the build says about itself, never a pass. A stamp FILE in the pushed
    tree (agenthub-frontend/BUILD-SHA) is the shape that reaches that build: the bundle has to inline it as
    VITE_BUILD_SHA, and this mode reads only what the bundle inlined.

    AND ONLY FROM THE SAME ENVIRONMENT. A hash is an identity only between builds made the same way:
    the deploy builds docker-system/docker/Dockerfile.frontend.production (node:20-alpine, arm64)
    from the `frontend` branch, while a seat or CI build is a different node, arch and VITE_* set -
    and environment.ts reads `import.meta.env[key]` dynamically, so vite inlines the whole object and
    re-hashes every chunk that carries it. Measured 2026-10-21: the box dist inlined 6 keys, the
    served build 30, and a stale-dist comparison read BUILD-MISMATCH about a correct deploy. So the
    environment object is read from both entries and compared first: when they differ, the verdict is
    FOREIGN-ENV (exit 2, a refusal) instead of a mismatch about production.

USAGE
    python3 scripts/check_served_frontend.py [--base-url https://www.4genthub.com] [--json]
    python3 scripts/check_served_frontend.py --expect-build-of origin/frontend
    python3 scripts/check_served_frontend.py                       # the token witness, from this checkout
    python3 scripts/check_served_frontend.py --expect-dist agenthub-frontend/build
    python3 scripts/check_served_frontend.py --expect-entry index-CUR-9phy.js
    python3 scripts/check_served_frontend.py --expect-tokens agenthub-frontend/src/styles/theme.css \
        [--base-url https://www.4genthub.com] [--json]
EXIT
    0 = every witness that ran passed: the census is fresh; in identity mode the served build IS the expected
        build; in build mode the served stamp names the expected commit; the token witness finds no drift
    1 = stale, a build mismatch, a token drift, or a build stamp naming another commit - the served app is not
        the tree's build
    2 = nothing was compared (no witness at all), or the census or a comparison could not be taken (fetch/parse/
        cap failure, a missing git, an unresolvable or given-but-empty ref, an empty/absent/short/non-hex build
        stamp, a stale or foreign-env expectation) - NEVER reported as a pass
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

# The replacements, per src/components/seats/SeatPreview.tsx:37 (sync pull), SeatLlmPanel.tsx:99
# (sync switch) and MachinesPanel.tsx:179 (bridge run).
VERB_PATTERNS = {
    "sync pull": re.compile(r"4genteam sync pull"),
    "sync switch": re.compile(r"4genteam sync switch"),
    "bridge": re.compile(r"4genteam bridge"),
}
# The deleted names, as a PATTERN: every `scripts/<something>.py` reference is a fossil, whether or
# not it is one of the four names that happened to appear in the 08 Oct bundle.
DELETED_NAME = re.compile(r"scripts/[a-z0-9_]+\.py", re.IGNORECASE)

# Refs to other assets: the queued form the HTML uses, and the bare hashed file name a chunk uses
# to name its lazy siblings (`./SeatDetailPage-BpUArPYK.js`).
ASSET_REF = re.compile(r"""(?:\.?/)?assets/[A-Za-z0-9_.-]+\.(?:js|css)""")
# A bare hashed name inside a chunk (`./SeatDetailPage-BpUArPYK.js`) - optional dotted segments
# included, because vite keeps a plugin prefix (`mermaid.core-PVSKwLbE.js`), and a left boundary,
# because without it the match starts after the dot (`core-PVSKwLbE.js`) and fetches a phantom 404.
HASHED_REF = re.compile(
    r"""(?<![A-Za-z0-9_.-])(?:[A-Za-z0-9_-]+\.)*[A-Za-z0-9_-]+-[A-Za-z0-9_-]{8,}\.(?:js|css)"""
)
ENTRY_REF = re.compile(r"""/assets/(index-[A-Za-z0-9_-]+\.js)""")
# The entry is the one the page LOADS, not merely the first /assets/index-*.js mentioned: vite emits
# modulepreload links for the entry's siblings, so a bare first-match can name a lazy chunk and the
# identity check would then compare the wrong hash.
ENTRY_SCRIPT = re.compile(r'<script[^>]+src="/assets/(index-[A-Za-z0-9_-]+\.js)"')

DEFAULT_MAX_ASSETS = 400
# The checkout this script lives in, so the token witness needs no argument and no build.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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


def dist_expectation(dist_dir: str) -> tuple[str, set[str], str]:
    """Read the build's own identity: its entry chunk hash, every name it shipped, and the entry's text
    (the environment object it inlined, which is the evidence the hash is comparable to the served one)."""
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
    try:
        entry_text = (root / "assets" / entry).read_text(encoding="utf-8", errors="replace")
    except OSError:
        # The name is in `shipped` from the directory listing; a dist whose entry cannot be opened is a
        # broken dist, and the environment comparison refuses rather than guessing comparability.
        entry_text = ""
    return entry, shipped, entry_text


# The tree's token source. `theme.css` passes through the bundler verbatim (plain `:root` / `.dark`
# blocks, no `@theme` tree-shaking), so a served stylesheet from a tree that declares a token MUST
# carry it - and a served one that predates that tree cannot. That makes the declaration set a
# build witness that needs no local build and no environment match.
TOKEN_SOURCE = "agenthub-frontend/src/styles/theme.css"
# A mode block is named by a selector LIST (`:root, :host` is the same block); a compound like
# `.dark .card` is a rule, not the mode block. The block's extent comes from brace matching, never
# from `find("}")`: a `}` inside a comment or a nested rule closed the block early (measured
# 2026-10-23: 88 declarations read as 3).
TOKEN_SELECTORS = {":root": "root", ".dark": "dark"}
TOKEN_DECL = re.compile(r"(--[\w-]+)\s*:\s*([^;}]+)")
# The SUBJECT of a mode block may carry a type or universal prefix: `html.dark`, `*:root` and the
# bare spellings are one block on one element. Matching the exact strings read `html.dark {` as no
# block at all, so the declared set held ONE block and a served sheet missing every token of the
# other returned missing=[] drifted=[] - a pass on the defect this witness exists to catch
# (measured 2026-10-23: `html.dark` read as {'root': 88}, and the real 76 dark tokens went unwitnessed).
MODE_SUBJECT = re.compile(r"^(?:[a-z][a-z0-9-]*|\*)?(:root|\.dark)$")
# A depth-0 prelude that NAMES a mode must yield that mode's block; a name the subject pattern
# cannot read (`.x.dark`, a functional selector) is a refusal, never a silent skip.
MODE_NAME = re.compile(r"(:root|\.dark)(?![\w-])")


def normalise_value(value: str) -> str:
    """A token value in the form the comparison can hold equal across the authored CSS and the bundler's
    output. Measured on the live stylesheet: the minifier drops the leading zero of a decimal
    (`rgba(…, 0.15)` -> `rgba(…, .15)`) and rewrites a duration in seconds (`240ms` -> `.24s`), and it
    leaves hex alone. Everything else is compared exactly - a changed token value is drift."""
    text = " ".join(value.split()).lower()
    # Punctuation carries no meaning in the spacing: `rgba(0, 0, 0, .5)` and `rgba(0,0,0,.5)` are the
    # same value, and the minifier picks the tight spelling. A space between two words stays one space.
    text = re.sub(r"\s*([(),/])\s*", r"\1", text)

    def milliseconds(match: re.Match) -> str:
        return f"{int(match.group(1)) / 1000:g}".lstrip("0") + "s"

    text = re.sub(r"(?<![\w.])(\d+)ms\b", milliseconds, text)
    # One spelling for a number: `.10` and `.1` are the same channel, and the minifier picks either.
    text = re.sub(r"(?<![\w.])\d*\.\d+", lambda m: m.group(0).rstrip("0").rstrip(".") or "0", text)
    text = re.sub(r"(?<![\w.])0\.(\d+)", r".\1", text)
    text = re.sub(r"#([0-9a-f])([0-9a-f])([0-9a-f])\b", r"#\1\1\2\2\3\3", text)
    return text


def _strip_comments(css: str) -> str:
    """Comments out, before any brace counting: a `}` inside one is not a block end.

    An UNTERMINATED comment refuses. The regex cannot remove it, so whatever follows reads as
    declarations of the block before it - a parse that is wrong in the direction of a pass, reported
    as a measurement (measured 2026-10-23: an unclosed `/*` left the stylesheet after it unread)."""
    stripped = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    if "/*" in stripped:
        raise CannotMeasure("unterminated /* comment - the stylesheet after it cannot be read as blocks")
    return stripped


def _top_level_rules(css: str):
    """(prelude, body) for every rule at brace depth 0, in source order.

    Nested rules are skipped whole, which is what makes an `@media (prefers-reduced-motion)` restatement
    an override rather than a declaration; a quoted brace never opens or closes a block; an at-rule
    statement (`@import ...;`) leaves no pending prelude."""
    depth, prelude, block, quote, i = 0, 0, 0, "", 0
    while i < len(css):
        ch = css[i]
        if quote:
            if ch == "\\":
                i += 1
            elif ch == quote:
                quote = ""
        elif ch in "\"'":
            quote = ch
        elif ch == "{":
            if depth == 0:
                block = i
            depth += 1
        elif ch == "}":
            if depth == 0:
                prelude = i + 1
            else:
                depth -= 1
                if depth == 0:
                    yield css[prelude:block].strip(), css[block + 1:i]
                    prelude = i + 1
        elif ch == ";" and depth == 0:
            prelude = i + 1
        i += 1


def parse_token_blocks(css: str) -> dict[str, dict[str, str]]:
    """{block: {name: value}} for the two blocks `theme.css` authors, in the authored form and in the
    minifier's - values normalised, so a build is not asked to spell its colours the way the source does.

    Only a depth-0 rule whose selector list's SUBJECT is `:root` or `.dark` (type or universal
    prefix allowed) is a mode block. A token inside `@supports`, `@media` or a comment is not a
    declaration of that block, so it is not served. A depth-0 prelude that NAMES a mode while no
    block parses for it is a CannotMeasure - the alternatives are a witness comparing one block and
    a pass on the other."""
    blocks: dict[str, dict[str, str]] = {}
    named: dict[str, str] = {}
    for prelude, body in _top_level_rules(_strip_comments(css)):
        if prelude.startswith("@"):
            continue
        for selector in prelude.split(","):
            subject = selector.strip().split()[-1] if selector.strip() else ""
            match = MODE_SUBJECT.match(subject)
            if match:
                name = TOKEN_SELECTORS[match.group(1)]
                for token, value in TOKEN_DECL.findall(body):
                    blocks.setdefault(name, {})[token] = normalise_value(value)
        for mentioned in MODE_NAME.findall(prelude):
            named.setdefault(TOKEN_SELECTORS[mentioned], prelude.strip())
    for name, prelude in sorted(named.items()):
        if name not in blocks:
            raise CannotMeasure(
                f"the prelude {prelude!r} names the {name} block but no block parses from it - the stylesheet "
                "and the parser disagree, and comparing one block would pass the other silently"
            )
    return blocks


def token_census(texts: dict[str, str], source_path: str) -> dict:
    """Every custom property `source_path` declares must be in the served stylesheet's same block."""
    try:
        with open(source_path, encoding="utf-8") as handle:
            declared = parse_token_blocks(handle.read())
    except OSError as exc:
        raise CannotMeasure(f"cannot read the token source ({source_path}): {exc}") from exc
    if not declared:
        raise CannotMeasure(f"{source_path} declares no ':root'/'.dark' token block - the parser and the file disagree")
    served: dict[str, dict[str, str]] = {}
    for path, text in texts.items():
        if path.endswith(".css"):
            for block, names in parse_token_blocks(text).items():
                served.setdefault(block, {}).update(names)
    missing: dict[str, list[str]] = {}
    drifted: dict[str, dict[str, list[str]]] = {}
    for block, names in declared.items():
        absent = sorted(set(names) - set(served.get(block, {})))
        if absent:
            missing[block] = absent
        changed = {
            name: [served[block][name], value]
            for name, value in sorted(names.items())
            if name in served.get(block, {}) and served[block][name] != value
        }
        if changed:
            drifted[block] = changed
    return {
        "source": source_path,
        "declared": {block: len(names) for block, names in declared.items()},
        "served": {block: len(served.get(block, {})) for block in declared},
        "missing": missing,
        "drifted": drifted,
    }


def git(*args: str, cwd: str) -> str | None:
    """git's stdout, or None when it fails - a check that cannot date a tree says so, never guesses."""
    try:
        done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def dist_staleness(dist_dir: str) -> dict | None:
    """Date the expected build against the last commit that touched the frontend sources.

    A dist that nobody rebuilds is not an expectation, it is a fossil: on 2026-10-21 the served entry was
    index-CulHwbQI.js (Last-Modified 23:54Z, after every frontend commit) while the expected side was
    index-3rbprdLk.js from a build dated 2026-10-11, so the check reported MISMATCH about an artifact that
    had not been produced in ten days. When the build predates the last source commit, the expectation is
    refused (exit 2, CannotMeasure) instead of being compared: a refusal names the age, a MISMATCH sends
    someone looking at production.

    None means undated, and there are three ways to be undated: the path is not a directory, it is not
    inside a git work tree the command can query, or `git log` returns no commit for the frontend
    sources beside it (untracked sources, a work tree whose history does not reach them, a
    git that fails). An undated dist is compared exactly as before this rule existed - the check does
    not guess an age. The real call (`--expect-dist agenthub-frontend/build` from the repo) is dated
    because `agenthub-frontend/` has commits; a build directory whose sources are uncommitted is not.
    """
    from pathlib import Path

    root = Path(dist_dir).resolve()
    if not root.is_dir():
        return None
    repo = git("rev-parse", "--show-toplevel", cwd=str(root))
    if not repo:
        return None
    source = root.parent
    raw = git("log", "-1", "--format=%ct", "--", ".", f":(exclude){root.name}", cwd=str(source))
    if not raw:
        return None
    committed = int(raw)
    built = max((p.stat().st_mtime for p in root.rglob("*") if p.is_file()), default=root.stat().st_mtime)
    return {
        "dist": str(root),
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(built)),
        "source_commit_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(committed)),
        "age_days": round((committed - built) / 86400, 1),
        "stale": built < committed - 1,
    }


# The environment object vite writes into a build that reads `import.meta.env[key]` dynamically
# (agenthub-frontend/src/config/environment.ts:32). Its KEY SET is the build's fingerprint: the dist
# built on this box carries six keys, the deployed build thirty - and vite hashes every chunk that
# carries the object, so two builds of ONE tree in two environments cannot share an entry hash.
ENV_PAIR = re.compile(
    r'([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(?:"((?:[^"\\]|\\.)*)"|(!0|!1|true|false|-?\d+(?:\.\d+)?))'
)


def env_object(text: str) -> str | None:
    """The `{BASE_URL:...}` literal, brace-matched, or None when the build inlines no environment.

    The anchor is vite's own first key, `BASE_URL`, unquoted - which is how vite emits it. A build whose
    object began with another key, or with a quoted key, would read as "no environment" and then as
    "different build shapes": a refusal, never a false OK, so the assumption fails safe.
    """
    start = text.find('{BASE_URL:"')
    if start < 0:
        return None
    depth = 0
    in_string = False
    index = start
    while index < len(text):
        char = text[index]
        if in_string:
            if char == "\\":
                index += 2
                continue
            if char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
        index += 1
    return None


def env_signature(text: str) -> dict[str, str] | None:
    """Every key/value the build inlined, or None: the evidence that says WHICH environment built it."""
    literal = env_object(text)
    if literal is None:
        return None
    signature = {key: (quoted if quoted or not bare else bare) for key, quoted, bare in ENV_PAIR.findall(literal)}
    return signature or None


def env_comparison(expected: dict[str, str] | None, served: dict[str, str] | None) -> dict:
    """Can the two entry hashes be compared at all?

    A hash is an identity only when both sides were built in the SAME environment. When they were
    not, the honest answer is a refusal: on 2026-10-21 a box-built dist was compared to the live site
    and read BUILD-MISMATCH about a deploy that was correct - same tree, different node, arch and
    VITE_* set, so every chunk carrying the env object hashed differently. Byte equality is not
    something a seat can obtain (the local-frontend-build rule forbids the build), and it is not
    needed: the environment is in the artifact, so the check can say whether it is even measuring.
    """
    if expected is None and served is None:
        return {"comparable": True, "why": "neither side inlines an environment object",
                "expected_keys": 0, "served_keys": 0,
                "only_in_expected": [], "only_in_served": [], "differing_values": []}
    if expected is None or served is None:
        absent = "expected build" if expected is None else "served build"
        return {"comparable": False,
                "why": f"the {absent} inlines no environment object and the other does - different build shapes",
                "expected_keys": len(expected or {}), "served_keys": len(served or {}),
                "only_in_expected": [], "only_in_served": [], "differing_values": []}
    only_expected = sorted(set(expected) - set(served))
    only_served = sorted(set(served) - set(expected))
    differing = sorted(k for k in set(expected) & set(served) if expected[k] != served[k])
    same = not (only_expected or only_served or differing)
    return {"comparable": same,
            "why": "" if same else "the two builds inlined different environments",
            "expected_keys": len(expected), "served_keys": len(served),
            "only_in_expected": only_expected, "only_in_served": only_served,
            "differing_values": differing}


# The stamp's own floor. `git rev-parse --short` writes 7 characters or more - the one in-repo writer
# (scripts/deploy-frontend.sh:86-87) writes exactly `--short` - and a shorter string names no commit on its
# own, so it is a refusal rather than a comparison.
BUILD_SHA_PREFIX_MIN = 7
HEX_SHA = re.compile(r"^[0-9a-f]+$")


def expected_sha(ref: str) -> str:
    """The commit a ref names, or a refusal - a build check with no expected side cannot measure.

    Resolved from the tree the command runs in: the deploy builds from the `frontend` branch, so
    `--expect-build-of origin/frontend` compares the served stamp to the commit that branch names. A missing
    git or an unresolvable ref is exit 2 and never 0: an unproven deploy is not a proven one.

    An EMPTY ref is a refusal of its own, not an absent flag: `--expect-build-of "$(git rev-parse ...)"` whose
    expansion failed passes an empty string, and treating that as "no expectation" would print the census's OK
    about a deploy nothing was compared to - a flag that silently disables its own proof.
    """
    if not ref.strip():
        raise CannotMeasure(
            "--expect-build-of was given an empty ref, so there is nothing to compare the served build's stamp to; "
            "an empty ref is a refusal, never an absent flag"
        )
    repo = git("rev-parse", "--show-toplevel", cwd=".")
    if not repo:
        raise CannotMeasure(f"cannot resolve {ref}: this is not a git work tree, or git is not installed")
    sha = git("rev-parse", "--verify", f"{ref}^{{commit}}", cwd=repo)
    if not sha:
        raise CannotMeasure(f"cannot resolve {ref} to a commit in {repo}")
    return sha.lower()


def build_stamp(entry_text: str, expected: str) -> dict:
    """The stamp the served build carries, against the commit it must name - a STRING compare.

    A hash is comparable only between builds of one environment (env_comparison), but the stamp is a string
    the build wrote: it names the commit the build read, so the environment cannot matter. The stamp is read
    with the env object the census already parses, never with a second parser.

    The result carries served_build_sha, served_build_time and expected_sha, which main lifts to the top
    level of the report; `state` is OK/STALE/INCOMPLETE and `why` the sentence behind it.
    """
    signature = env_signature(entry_text) or {}
    stamp = (signature.get("VITE_BUILD_SHA") or "").strip().lower()
    built = (signature.get("VITE_BUILD_TIME") or "").strip()
    report = {"served_build_sha": stamp, "served_build_time": built, "expected_sha": expected}
    if not entry_text:
        return {**report, "state": "INCOMPLETE", "why": "the served entry chunk did not arrive"}
    if not stamp:
        absent = "VITE_BUILD_SHA" not in signature
        return {**report, "state": "INCOMPLETE",
                "why": f"the served entry inlines {'no' if absent else 'an empty'} VITE_BUILD_SHA - "
                       "the build was passed no --build-arg"}
    if not HEX_SHA.match(stamp):
        return {**report, "state": "INCOMPLETE",
                "why": f"the served VITE_BUILD_SHA {stamp!r} is not a hex commit id"}
    if stamp == expected:
        return {**report, "state": "OK", "why": ""}
    if len(stamp) >= BUILD_SHA_PREFIX_MIN and expected.startswith(stamp):
        return {**report, "state": "OK",
                "why": f"the served stamp is a {len(stamp)}-character prefix of the expected commit"}
    if len(stamp) < BUILD_SHA_PREFIX_MIN:
        return {**report, "state": "INCOMPLETE",
                "why": f"the served VITE_BUILD_SHA {stamp!r} is shorter than {BUILD_SHA_PREFIX_MIN} characters, "
                       "so it names no commit on its own"}
    return {**report, "state": "STALE",
            "why": f"the served build names {stamp}, the expected commit is {expected}"}


def entry_text(texts: dict[str, str], served_entry: str | None) -> str:
    """The served entry chunk's own text - the file that carries the build's env object and stamp.

    The closure names one entry, so the first match is that entry. A same-named file at the root as well as
    under assets/ would resolve to whichever the closure saw first; none exists today, and the served tree is
    walked from the index outward.
    """
    return next((t for path, t in texts.items() if served_entry and path.endswith("/" + served_entry)), "")


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
    parser.add_argument("--expect-build-of", nargs="?", const="origin/frontend", default=None,
                        metavar="REF", help="a ref whose commit the served build's VITE_BUILD_SHA must name "
                                            "(default ref: origin/frontend) - the deploy proof that survives "
                                            "a different build environment; an empty REF is refused, never "
                                            "read as no flag")
    parser.add_argument(
        "--expect-tokens",
        default=None,
        help="the tree's token source (default: agenthub-frontend/src/styles/theme.css of this checkout) - "
        "every token it declares must be in the served stylesheet; needs no build",
    )
    parser.add_argument("--max-assets", type=int, default=DEFAULT_MAX_ASSETS)
    args = parser.parse_args(argv)

    report: dict = {"origin": args.base_url, "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    try:
        # The expectation is dated BEFORE it is used: a build older than the last frontend commit is not an
        # expectation, and comparing to it turns "nobody rebuilt" into "production is wrong".
        if args.expect_dist:
            dated = dist_staleness(args.expect_dist)
            if dated:
                report["expected_build"] = dated
                if dated["stale"]:
                    raise CannotMeasure(
                        f"the expected build is stale: {dated['dist']} was built {dated['built_at']}, "
                        f"{dated['age_days']} day(s) before the last frontend commit ({dated['source_commit_at']}); "
                        "rebuild it (cd agenthub-frontend && npm run build) or pass --expect-entry"
                    )
        # The expected side of the build check is resolved before anything is fetched: an unresolvable ref
        # must cost a refusal, never a pass on a census that had nothing to compare against. The test is
        # `is not None`, not truthiness: an empty ref is a GIVEN expectation that cannot be resolved, and
        # reading it as "no flag" would silently switch the proof off and print the census's OK.
        expected_build = expected_sha(args.expect_build_of) if args.expect_build_of is not None else None
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
        if expected_build:
            stamp = build_stamp(entry_text(texts, served_entry), expected_build)
            report.update({k: v for k, v in stamp.items() if k not in ("state", "why")})
            report["build_state"] = stamp["state"]
            report["build_why"] = stamp["why"]

        expected_entry, shipped, expected_text = None, None, None
        comparable = True
        if args.expect_dist:
            expected_entry, shipped, expected_text = dist_expectation(args.expect_dist)
            # Comparability is decided BEFORE identity: if the expectation was built in another
            # environment, its hash says nothing about the served one and a MISMATCH would be a lie
            # about production. The served side's own entry carries its environment too.
            served_text = entry_text(texts, served_entry)
            # A served entry that did not arrive is an INCOMPLETE closure, never a foreign environment:
            # with no text to read, comparability is left alone and the failure is reported as itself.
            if served_text:
                report["environment"] = env_comparison(env_signature(expected_text), env_signature(served_text))
                comparable = report["environment"]["comparable"]
        elif args.expect_entry:
            expected_entry = args.expect_entry
        if expected_entry and comparable:
            report["identity"] = identity_check(served_entry, set(texts), expected_entry, shipped)

        # The token witness: independent of any local build, so it runs on a plain checkout. A token
        # the tree declares and the served stylesheet omits names a stylesheet from an older tree -
        # measured live on 2026-10-23, where the served CSS was the pre-contrast-token one.
        token_source = args.expect_tokens
        if token_source is None:
            auto = os.path.join(REPO_ROOT, TOKEN_SOURCE)
            token_source = auto if os.path.isfile(auto) else None
        if token_source:
            report["tokens"] = token_census(texts, token_source)

        stale = result["deleted_names"] or result["verbs_present"] == 0
        build_state = report.get("build_state")
        # A witness is any comparison the caller asked for and this run could make: build mode counts, or a
        # deploy whose only proof is `--expect-build-of` would be refused as "nothing compared".
        witnessed = bool(expected_entry) or "tokens" in report or build_state is not None
        if stale:
            report["verdict"] = "STALE"
            exit_code = 1
        elif build_state == "INCOMPLETE":
            # A stamp that names no commit is not a mismatch and not a pass: nothing about the deploy has
            # been proven, so the census's own OK would be a lie about the build.
            report["verdict"] = "INCOMPLETE"
            exit_code = 2
        elif not comparable:
            report["verdict"] = "FOREIGN-ENV"
            exit_code = 2
        elif build_state == "STALE":
            report["verdict"] = "STALE"
            exit_code = 1
        elif "identity" in report and not report["identity"]["matches"]:
            report["verdict"] = "BUILD-MISMATCH"
            exit_code = 1
        elif report.get("tokens", {}).get("missing") or report.get("tokens", {}).get("drifted"):
            report["verdict"] = "TOKEN-DRIFT"
            exit_code = 1
        elif fetcher.failures:
            # Every assertion that could be made passed, but the closure was incomplete: a stale
            # chunk could be hiding in the part that did not arrive. Incomplete is not a pass.
            report["verdict"] = "INCOMPLETE"
            exit_code = 2
        elif not witnessed:
            # THE DEPLOY GATE, measured the hard way on 2026-10-23: this script read OK against
            # index-Dd1FoJ_2.js, a build whose /login threw MUI error #9 and rendered an empty #root.
            # A two-token census is satisfied by any build after the 08 Oct rename (75f81494), so it
            # cannot witness a push, and no flag accepts it: without an expectation the honest verdict
            # is that nothing was compared.
            report["verdict"] = "CANNOT-MEASURE"
            report["error"] = (
                "no expectation to compare against: pass --expect-dist <agenthub-frontend/build> (the "
                "build the deploy just made), --expect-entry <hash>, --expect-build-of <ref>, or "
                "--expect-tokens <agenthub-frontend/src/styles/theme.css>"
            )
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
    expected = report.get("expected_build")
    if expected:
        print(f"expected build: built {expected['built_at']} | last frontend commit {expected['source_commit_at']}"
              f" | {'STALE' if expected['stale'] else 'current'}")
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
    if "environment" in report:
        environment = report["environment"]
        state = "comparable" if environment["comparable"] else "NOT comparable"
        print(f"  environment: build inlined {environment['expected_keys']} key(s), served {environment['served_keys']}"
              f" -> {state}")
        if not environment["comparable"]:
            if environment.get("why"):
                print(f"    {environment['why']}")
            for label, keys in (
                ("only in the build", environment["only_in_expected"]),
                ("only in the served build", environment["only_in_served"]),
                ("differing values", environment["differing_values"]),
            ):
                if keys:
                    shown = ", ".join(keys[:5]) + (f", +{len(keys) - 5} more" if len(keys) > 5 else "")
                    print(f"    {label} ({len(keys)}): {shown}")
    if "tokens" in report:
        tokens = report["tokens"]
        source = tokens["source"]
        if source.startswith(REPO_ROOT + os.sep):
            source = os.path.relpath(source, REPO_ROOT)
        print(f"  tokens: {source} declares {tokens['declared']}, served {tokens['served']}")
        for block, names in tokens["missing"].items():
            shown = ", ".join(names[:6]) + (f", +{len(names) - 6} more" if len(names) > 6 else "")
            print(f"  MISSING from the served {block} block ({len(names)}): {shown}")
        for block, changed in tokens["drifted"].items():
            shown = ", ".join(f"{name} served {pair[0]} != {pair[1]}" for name, pair in list(changed.items())[:4])
            print(f"  DRIFTED in the served {block} block ({len(changed)}): {shown}")
    if "identity" in report:
        ident = report["identity"]
        print(f"  identity: served entry {ident['served_entry']} vs expected {ident['expected_entry']}"
              f" -> {'MATCH' if ident['entry_matches'] else 'MISMATCH'}")
        if ident["served_assets_absent_from_build"]:
            absent = ident["served_assets_absent_from_build"]
            shown = ", ".join(absent[:5]) + (f", +{len(absent) - 5} more" if len(absent) > 5 else "")
            print(f"  served assets absent from the build ({len(absent)}): {shown}")
    build_state = report.get("build_state")
    if build_state:
        print(f"  build: serves {report['served_build_sha'] or 'NO STAMP'}"
              f" (built {report['served_build_time'] or 'unknown'})"
              f" vs expected {report['expected_sha']} -> {build_state}")
        if report.get("build_why"):
            print(f"    {report['build_why']}")
    verdict = report.get("verdict")
    if verdict == "OK":
        # A deploy log must show WHICH witness produced the pass: the census reading alone is never the
        # verdict, and the token witness and the identity arm prove different things.
        witnesses = [
            name
            for name, present in (
                ("the build stamp", build_state is not None),
                ("identity", "identity" in report),
                ("tokens", "tokens" in report),
            )
            if present
        ]
        print(
            f"OK: witnessed by {', '.join(witnesses)} - the served frontend names the live client and no"
            f" deleted script"
        )
        return
    messages = {
        "STALE": "STALE: the served frontend is not a build of HEAD - the pre-fix bundle is still live",
        "BUILD-MISMATCH": "BUILD-MISMATCH: the live frontend is NOT the build it was supposed to be",
        "TOKEN-DRIFT": "TOKEN-DRIFT: the served stylesheet does not carry the tokens this tree declares (or"
                       " carries other values), so it is not this tree's stylesheet",
        "FOREIGN-ENV": "FOREIGN-ENV: the expected build was made in a different environment, so its hash cannot"
                       " be compared - pass --expect-entry, or compare a build the deploy image made",
        "INCOMPLETE": "INCOMPLETE: assertions passed on the part that arrived, but the closure did not - not a pass",
        "CANNOT-MEASURE": f"CANNOT-MEASURE: the census could not be taken ({report.get('error')})",
    }
    if build_state == "STALE" and verdict == "STALE":
        print("STALE: the served build names a different commit than the one expected - not a pass")
    elif build_state == "INCOMPLETE" and verdict == "INCOMPLETE":
        print(f"INCOMPLETE: the served build's stamp cannot be read ({report.get('build_why')}) - not a pass")
    else:
        print(messages.get(verdict, verdict))


if __name__ == "__main__":
    sys.exit(main())
