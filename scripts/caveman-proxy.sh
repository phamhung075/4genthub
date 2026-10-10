#!/usr/bin/env bash
# Trial runner for the caveman proxy (built from the scripts/caveman submodule, pinned tag).
#   scripts/caveman-proxy.sh build    build caveman-proxy and caveman-mcp into ~/.caveman/bin
#   scripts/caveman-proxy.sh start    serve on 127.0.0.1:8787, compress mode, subscription live_zone
#   scripts/caveman-proxy.sh stop
#   scripts/caveman-proxy.sh stats     token totals (compression_tokens_before/after/saved)
# A trial seat starts with ANTHROPIC_BASE_URL=http://127.0.0.1:8787 and the caveman MCP server
# (command: ~/.caveman/bin/caveman-mcp). Only Claude Code seats can use it; omp/DeepSeek seats cannot.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
bin="$HOME/.caveman/bin"
home="$HOME/.caveman/home"
case "${1:-}" in
  build)
    git -C "$root" submodule update --init scripts/caveman
    mkdir -p "$bin"
    (cd "$root/scripts/caveman" && go build -o "$bin/caveman-proxy" ./proxy/cmd/... && go build -o "$bin/caveman-mcp" ./mcp/cmd/...)
    ;;
  start)
    mkdir -p "$home"
    printf 'label: local\nmode: compress\nlisten: 127.0.0.1:8787\nsubscription_compress: live_zone\n' > "$home/caveman.yaml"
    CAVEMAN_CONFIG="$home/caveman.yaml" CAVEMAN_HOME="$home" nohup "$bin/caveman-proxy" > "$home/proxy.log" 2>&1 &
    ;;
  stop) kill "$(pgrep -x caveman-proxy)" ;;
  stats) CAVEMAN_HOME="$home" "$bin/caveman-proxy" stats ;;
  *) echo "usage: $0 build|start|stop|stats" >&2; exit 2 ;;
esac
