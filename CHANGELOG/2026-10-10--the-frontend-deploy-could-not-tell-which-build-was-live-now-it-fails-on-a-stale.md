## The frontend deploy could not tell which build was live; now it fails on a stale one

### Changed
- `scripts/deploy-frontend.sh`: after its reachability checks it now verifies **WHICH** build is live and **EXITS 1** on a stale or mismatched bundle. Every check it had asked whether a URL ANSWERS — `curl -f` reachability, a favicon/assets path sweep, a response-time threshold — and none asked which build answers, which is how it printed `Frontend deployment completed successfully!` against a bundle built two days and 165 commits earlier while production's API read `0.0.29`. With `agenthub-frontend/build` present it asserts identity through the census (`--expect-dist`: the served entry chunk must be this build's entry chunk, and every file the served app is composed of must exist in it). With `SKIP_BUILD=true` there is no local build to compare against, so it falls back to the census alone — the weaker test — and says so rather than passing it off as the same thing.

### Verified
- **The added block was smoke-tested by running its OWN BYTES**, extracted from the file (`sed -n '182,215p' scripts/deploy-frontend.sh`), not a copy: production → identity `MISMATCH` → exit 1; a fresh local serve of a HEAD build → `MATCH` → exit 0; with `build/` absent, production → exit 1 and the fresh serve → exit 0; and with the target unreachable → it **FAILS rather than passing**, which is the direction a deploy gate has to fail in. `bash -n scripts/deploy-frontend.sh` → clean.
- The assertion itself is the census, not shell: `scripts/check_served_frontend.py` carries 13 hermetic cases in `scripts/tests`, and this script only calls it.

### Found by
- The measured root cause in row `b70278f2`: a two-day-old bundle survived a deploy that reported success.
