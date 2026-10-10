## The frontend validation doc names the mechanism, not a hook that never existed

### Changed
- **`agenthub-frontend/RESPONSE_VALIDATION.md:16`**: the sentence said WebSocket messages are validated *"via the `useWebSocketV2` hook"* — and **the symbol does not exist in any revision**: `src/hooks/useWebSocketV2.ts` exports `useWebSocket` (`:28`) and `useBranchWebSocket` (`:234`) only, `git log --all -S 'useWebSocketV2'` finds only tonight's removal of the mocked key (`6b908d51`), and the name is exported nowhere (`grep -rn 'export .*useWebSocketV2' src` → 0). The sentence now names what validates: the file `src/hooks/useWebSocketV2.ts`, whose two hooks call `validateWebSocketMessage` (`src/utils/websocketValidator.ts:22`) at `:113` and `:128`, each gated by `import.meta.env.DEV || VITE_VALIDATE_RESPONSES === 'true'`.
- **`:185` was checked rather than swept**: it cites the same **file** (`src/hooks/useWebSocketV2.ts — Added WebSocket message validation`), which exists and does exactly that, so it is correct and unchanged. A phantom symbol sharing a name with a real file is why the two lines were read one by one instead of by a whole-file rewrite.

### Verified
- `grep -n '^export ' agenthub-frontend/src/hooks/useWebSocketV2.ts` → `useWebSocket` at `:28`, `useBranchWebSocket` at `:234`; `grep -rn 'export .*useWebSocketV2' agenthub-frontend/src` → **0**: the name is exported nowhere.
- The call sites were **read**, not inferred: `sed -n '110,132p'` shows `validateWebSocketMessage(message)` inside `client.on('update', …)` and `client.on('userAction', …)`, each behind the dev/env gate.
