## A trial runner builds and serves the caveman proxy from the pinned submodule

### Added
- `scripts/caveman-proxy.sh` (`build`, `start`, `stop`, `stats`): builds `caveman-proxy` and `caveman-mcp` from `scripts/caveman` (tag `v3.2.0`) into `~/.caveman/bin`, serves the proxy on `127.0.0.1:8787` in `compress` mode with `subscription_compress: live_zone`. No seat uses it yet.

### Verified
- Trial on a one-off `claude -p`: a 28 KB log through Bash `cat` went from 10,839 to 1,244 tokens, but the maximum value in the answer was wrong (88 instead of 89). A Read of a 263 KB file was not compressed. The rollout to seats waits for a single-seat trial.
- Only Claude Code seats can use the proxy; omp/DeepSeek seats cannot.
