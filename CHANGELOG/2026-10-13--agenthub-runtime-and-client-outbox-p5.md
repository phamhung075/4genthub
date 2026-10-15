# Rust agenthub-runtime, Agy Watch & Client Outbox P5

Delivered the NEXT-GEN2 architecture foundation replacing OpenRig:

1. **Rust Core Runtime (`agenthub_client/rust/agenthub-runtime`):**
   - High-performance headless PTY runner and bracketed paste delivery (`\x1b[200~` ... `\x1b[201~`).
   - Sub-millisecond token estimation and active context compaction.
   - 4-tier skill resolution (`share/`, `rooms/<room>/`, `rooms/<room>/<seat>/`, `client/`).
   - Zero-allocation `RegexSet` command railguards and pre-execution tool denials.
   - Non-blocking async event bus with `audit.jsonl` append logging.
   - Multi-room supervisor under `~/.config/4genthub/rooms/<room>/`.
   - Local IPC Unix domain socket server (`/run/user/$UID/agenthub.sock`).

2. **Native Agy Watch & Feed Integration (`internal/clientwatch`):**
   - Instant discovery of Gemini Antigravity transcripts (`~/.gemini/antigravity-cli/brain/`).
   - Accurate token counting (`input_tokens + cache_read_tokens + output_tokens`).
   - Streaming transformer `agyToOMP` for `4genteam watch` and `4genteam feed`.

3. **Client Outbox & Ledger Sync P5 (`internal/clientoutbox`):**
   - Persistent on-disk outbox and cursor storage (`~/.config/4genthub/ledger/outbox.json`).
   - Reconnection workflow: drains outbox intents in strict order (facts first, then decisions with base_seq).
   - Pulls cross-task ledger events from `GET /api/v2/ledger?after=<cursor>`.
   - Ledger-based seat wakeups via `clientruntime.SendTextToSeat`.
   - CLI subcommands `4genteam outbox` and `4genteam ledger`.
