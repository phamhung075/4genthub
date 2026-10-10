# rigd boundaries: socket frames, command authorization, redaction

Decision note by the architect, 2026-10-11. It answers the lead's request `qitem-20261010222721-557596c2630798bc` (owner priority: build NEXT_GEN F4 in two phases). It binds go-dev and fe-dev for phase 1. Phase 2 is designed here and NOT implemented.

rigd is the always-on local client. It holds one outbound WebSocket to `/ws/connector` under the user's token, registers every local rig session, uploads redacted events (phase 1), and later receives commands that it runs locally as `rig send` (phase 2). The cloud never connects to the user's machine.

## 0. What exists today (measured at HEAD, 2026-10-11)

- Server: `agenthub_go/fastmcp/server/httpapp/ws_mount.go` (`handleConnector`) requires the `sessions:write` scope and serves these frames: `hello` → `ready`, `session` → `session_ack {session_id, last_seq}`, `events` → `events_ack {session_id, last_seq}`, and `error {message}`. An unknown `type` is answered with `error "unknown type"` and the socket stays open. On disconnect the server marks the connector's sessions offline (`session_stream.MarkOffline`).
- The server assigns `seq` (`session_stream/repository.go`, `AppendEvents`; at most 200 events per batch, `MaxEventsPerBatch`). An event carries no client key, so a batch resent after a lost ack is stored twice. The client comment `internal/clientsync/connector.go:321` makes deduplication the client's job, and nothing does it today.
- Client: `internal/clientsync/connector.go` and `connectorverb.go` send ONE session ONE time (`sync connector`). Redaction is a fixed regex list (`Redact`, `redactionPatterns`) with no failure path. The same files exist in BOTH `agenthub_client` (pin `80cc766d`) and `agenthub_go/internal/clientsync`. The duplication is the seatcheck case again.
- `agent_sessions` has `status`, `last_seq`, `last_seen` and the seat pair, and no client cursor column.

## 1. Where rigd lives

**Ruling: rigd is built in `agenthub_client`, as a long-running verb of the client binary (`4genteam rigd`).** It extends `internal/clientsync/connector.go`; it is not a new program.

- Reason: the client module is the one that ships to operators and the one the seat is pulled from. That is the same rule that made the client's `cmd/seatcheck` canonical (CHANGELOG `2026-10-10--the-second-seatcheck-copy-leaves-the-tree-the-client-module-is-canonical.md`).
- Follow-on, not phase-1 work: retire `agenthub_go/internal/clientsync/connector*.go` the way the server's seatcheck copy was retired. Until then, NO rigd change goes into the `agenthub_go` copy.

## 2. Boundary 1: the socket frames

### 2.1 Options for resume after reconnect

| | A. The server stores the client's source cursor | B. The client deduplicates from `last_seq` |
|---|---|---|
| Mechanism | `events` carries `cursor`, an opaque client position (for example a transcript byte offset). The server stores it on `agent_sessions` in the SAME transaction as the events, and returns it in `session_ack`. | The client persists `(cursor, last_seq)` locally, with a write-ahead record of the in-flight batch, and after a reconnect infers whether that batch landed by comparing the server's `last_seq`. |
| Lost ack | Exact: the stored cursor says where to resume. | Exact only if the write-ahead record survived. A crash between the send and the local write duplicates or skips. |
| Reinstall or new disk | Resumes, because the cloud is the record. | Starts over and re-uploads history (duplicates). |
| Cost | One nullable column `agent_sessions.client_cursor TEXT` and two frame fields. | No schema change, but a local journal plus its crash cases. |

**Ruling: A.** The cursor and the events commit together, so "stored" and "resumable from" cannot disagree. The column goes into the ORM table definition (`models.go`, agent_sessions) and `init_schema_postgresql.sql` together, per the schema rule.

### 2.2 Phase-1 vocabulary

The existing frame names are kept: renaming them buys nothing and breaks the C4 tests. Each frame is JSON with a `type` field. New fields are marked **NEW**.

Client → server:

| type | fields | notes |
|---|---|---|
| `hello` | `connector_id`; **NEW** `protocol` (int, `1`), `client_version` (string), `capabilities` (array of strings; phase 1 sends `["ingest"]`) | Must be the first frame. A missing `protocol` means 1. |
| `session` | `session_key`, `name`, `project?`, `room?`, `seat?`; **NEW** `state` (`running` \| `stopped`), `source` (`transcript` \| `capture`) | This is registration. It is re-sent on every reconnect, and whenever `rig ps --json` shows a state change. A seat that leaves `rig ps` is sent once with `state: stopped`. |
| `events` | `session_key`, `events: [{type, payload, ts?}]` (at most 200); **NEW** `cursor` (string, at most 512 bytes, opaque to the server) | Send exactly ONE `events` frame per session and wait for its `events_ack` before sending the next for that session (stop-and-wait). That ordering is what makes the cursor exact. |
| **NEW** `ping` | `t` (client unix ms) | Sent every `heartbeat_s` seconds. |

Server → client:

| type | fields | notes |
|---|---|---|
| `ready` | `connector_id`; **NEW** `protocol` (the version the server will speak = min(client, server)), `heartbeat_s` (int, 25), `capabilities` (the subset of the client's list that the server enables) | |
| `session_ack` | `session_key`, `session_id`, `last_seq`; **NEW** `cursor` (the stored cursor, or null) | The client resumes reading its source from `cursor`. A null cursor means start from the source's beginning, bounded by the client's own backfill limit. |
| `events_ack` | `session_id`, `last_seq`; **NEW** `cursor` (echo of the stored value) | |
| **NEW** `pong` | `t` (echo) | |
| `error` | `message`; **NEW** `code` (string, stable), `fatal` (bool) | On `fatal: true` the server closes the socket next. On anything else the client logs and continues. |

Heartbeat: the client closes and reconnects after 3 heartbeats without a `pong`, or with no frame at all. The server closes a socket after 3 × `heartbeat_s` seconds with no frame. Both sides stay under the production proxy's `proxy_read_timeout` (C5).

Reconnect: exponential backoff from 1 s, doubling, capped at 60 s, with ±20 % jitter, reset after 60 s connected. A close with 1008 (scope missing) or 4401 (authentication) is NOT retried. rigd reports it locally and exits non-zero, because retrying a refused credential is load, not recovery.

### 2.3 The forward-compatibility rule

1. **Capabilities gate which kinds are sent.** A peer never sends a frame kind that belongs to a capability the other side did not advertise and the server did not echo in `ready`. Phase-2 command frames are therefore impossible on a phase-1 client.
2. **The client ignores an unknown server `type`.** It logs it once per type and does nothing else: it does not close, retry or act. An unknown kind can never cause an action.
3. **The server answers an unknown client `type` with `error {code: "unknown_type", fatal: false}`** and keeps the socket (current behaviour, kept).
4. **Capabilities named so far:** `ingest` (phase 1), `commands` (phase 2), `ledger` (P4's `ledger_tip` nudge, NEXT_GEN P4). A new server frame kind always comes with a new capability name.
5. **Unknown FIELDS are ignored on both sides.** A field can be added without bumping `protocol`. Changing a field's meaning or removing one bumps `protocol`.

### 2.3a The browser surface (ruled 2026-10-11, answering fe-dev's question on section 5 step 3)

The frames above run between rigd and the server. The browser never sees them. Here is what the browser gets:

- **Read:** the `GET /api/v2/sessions` row gains **`seat_state`** (`"running"` | `"stopped"` | `null`), stored in a NEW column, `agent_sessions.seat_state TEXT NULL`. The server writes it from `session.state` on every `session` frame. `null` means no rigd has reported a state, for example an old one-shot `sync connector` upload.
  - It is NOT `status`. `status` (`active` | `offline`) stays the connection fact: `MarkOffline` sets it when the socket closes.
  - The two are independent. A seat can be `running` while its connector is `offline`; that is the last reported state, and it may be stale.
  - Rendering precedence: `status: offline` shows as offline, with the last `seat_state` as secondary text. Otherwise `seat_state` decides: `stopped` shows as stopped, and `running` or `null` shows as live.
- **Push:** the server emits the existing realtime data-change frame (`routes.BroadcastDataChange`, the same path seats use through `seatBroadcastFn`), with **entity `agent_session`**. The name is not `session`, which reads as an auth session. Each frame has `data: {id, seat_state, status}`, where `id` is the `agent_sessions.id` of the row. Actions:
  - `created`: the first `session` frame for a new `(user, connector_id, session_key)`;
  - `updated`: a `seat_state` change, or a `status` change, including `MarkOffline`, which emits one frame per session it marks.
- **No push per `events` batch:** live events stay on `/ws/sessions/{id}`.
- **The browser** handles `agent_session` by invalidating `['sessions']` (`sessionKeys.list`) in each branch, the same placing as `handleSeatUpdate`. It does not parse the row out of the frame: the GET stays the single read path.

### 2.4 Phase-2 frames (designed now, NOT implemented)

These are enabled only by the `commands` capability (see 3.2 for who may enable it).

| direction | type | fields |
|---|---|---|
| server → client | `command` | `command_id` (UUID), `kind` (closed enum; the only value is `send_to_seat`), `session_key`, `text`, `created_by` (the Keycloak user id of the human), `created_at`, `expires_at` |
| client → server | `command_accepted` | `command_id` |
| client → server | `command_refused` | `command_id`, `reason` (`not_enabled` \| `target_not_allowed` \| `expired` \| `duplicate` \| `unknown_kind` \| `session_not_running`) |
| client → server | `command_result` | `command_id`, `outcome` (`delivered` \| `failed`), `detail` (at most 1 KiB, redacted), `exit_code?` |

- The server re-offers every unresolved, unexpired command after a reconnect. `command_id` makes this idempotent, because the client refuses a `command_id` it already recorded (`duplicate`).
- A client that receives an unknown `kind` refuses it with `unknown_kind`. It does NOT ignore it: a command is answered, never left hanging.

## 3. Boundary 2: command authorization (phase 2)

This is remote execution by design. The question is who may cause a `rig send` on a user's machine, and what proves it.

### 3.1 Does `sessions:write` authorize inbound commands?

**No.** `sessions:write` means "this credential may upload my sessions", which is a write OUT of the machine. A command is a write INTO a terminal. If one scope covered both, any token minted for upload (C2's dashboard flow) would become a remote-typing credential, and a leaked upload token would be remote code execution.

### 3.2 Options

| | A. A distinct scope on the socket | B. A distinct scope, a human-only issuer, and local consent |
|---|---|---|
| Who may create a command | Any credential with `sessions:command` | Only an interactive Keycloak browser session (the Sessions page). An API or MCP token is refused, with or without any scope. |
| Who may deliver | A socket whose token has `sessions:command` | The same, AND the machine's local rigd config has commands enabled for that target |
| A leaked API token | Can type into the user's terminals | Cannot create a command |
| A compromised cloud | Can type anything into any connected machine | Limited to the targets the machine's owner allowlisted locally |

**Ruling: B.**

1. **Issuer:** `POST /api/v2/sessions/{id}/commands` accepts only a Keycloak user token (a human in a browser). API and MCP tokens are refused with 403 `human_session_required`. The command's `user_id` must own the target session.
2. **Delivery scope:** the server offers commands only on a socket whose token grants the NEW scope `sessions:command`, and only when that socket's `hello` advertised `commands`. `sessions:write` alone gets ingest only.
3. **Local consent, which the cloud cannot widen:** rigd delivers commands only when its LOCAL config (`<seat store>/rigd.json`, mode 0600, written by the user on that machine) has `commands.enabled: true` and lists the target `session_key`s, or `room/seat` pairs, in `commands.allow`. The default is off. The server never writes this file, so cloud-side compromise cannot enable a machine that the user did not enable.
4. **Execution shape:** the only action is `send_to_seat`, executed as `exec("rig", "send", <target>, <text>)` with an argv list and NO shell, so the text is data and never a command line. The `<text>` is sent as-is. rigd does not interpret it.
5. **What the user sees first:**
   - On the machine, enabling commands is a deliberate local edit, and `4genteam rigd status` lists the allowed targets.
   - On the Sessions page, the chat input is shown only for a session whose connector is online with `commands` enabled for that target. It names the machine (`connector_id`) that will deliver.
   - The delivered text then appears in that session's event stream, attributed `human:<user>`.
   - A per-command confirmation on the machine is NOT required: it would defeat the purpose, because the user is not at the machine. Consent is per machine and per target.
6. **Audit, two records that must agree:**
   - Server: a `session_commands` row (`id`, `user_id`, `session_id`, `created_by`, `text_sha256`, `text`, `created_at`, `expires_at`, `state` from offered to accepted or refused to delivered or failed, `reason`, `updated_at`).
   - Client: one JSON line per received command in `<seat store>/rigd-audit.jsonl` (`command_id`, decision, reason, outcome, exit code, ts), with the same append-before-act discipline as `seatcheck` (G3 C4).
   - A server row with no matching client line, or the reverse, is a finding.
7. **Expiry:** a command not accepted within 5 minutes expires, and the client refuses an expired one. Nothing queues indefinitely and then fires hours later.

Open for the owner before phase 2 starts, NOT for dev seats: whether a delivered command should ALSO pass through `seatcheck send`, so that G3's link policy applies to human→seat messages. The default if the owner says nothing is no: a human is not a seat, and `seat_links` has no human end.

## 4. Boundary 3: the redaction point

### 4.1 Where it runs

The cloud must never receive an unredacted byte, so redaction is a **precondition of building the `events` frame**, inside rigd. The server's `MaxPayloadChars` truncation is a size guard, not redaction, and it must not be counted as redaction.

### 4.2 Where the rule set lives

| | A. Compiled into the client | B. Pushed by the cloud |
|---|---|---|
| Who can weaken it | Only a client release (reviewed, pinned) | Anyone who controls the server or its policy row |
| Offline | Works | Needs the last pushed copy |
| Update speed | A release | Immediate |

**Ruling: A, plus a local ADD-ONLY extension.** The built-in patterns live in the client (`internal/clientsync`, next to `Redact`). A local file, `<seat store>/redact.local.json`, may ADD patterns and may never remove or relax one. The cloud never sends redaction rules: a server that could switch redaction off would make the redactor protect nothing against a compromised server.

### 4.3 What is redacted (phase-1 minimum)

1. Everything `redactionPatterns` already matches, kept as is: bearer headers, the named env assignments, `gh*_`, `xox*-`, `sk-`, and JWTs.
2. ADD:
   - AWS access key ids (`AKIA`/`ASIA` + 16 characters).
   - PEM private-key blocks (`-----BEGIN ... PRIVATE KEY-----` through `-----END ... PRIVATE KEY-----`, the whole block).
   - URL userinfo (`scheme://user:pass@` → `scheme://[redacted]@`).
   - Generic assignments whose name ends in `TOKEN`, `SECRET`, `PASSWORD`, `PASSWD`, `API_KEY` or `PRIVATE_KEY` (any case, `=` or `:`).
   - Command-line flags `--token`, `--password`, `--secret` and `--api-key`, in both the `=` and the space form.
3. **`.env` content is WITHHELD, not pattern-redacted.** An event whose tool input names a path matching `(^|/)\.env(\..*)?$` (Read, cat, or similar), and the tool result paired with it, is replaced by the withheld placeholder in 4.4. Patterns cannot be trusted to recognise every value in an env file.

### 4.4 When redaction fails or is unsure: FAIL CLOSED, per event

I agree with the lead's fail-closed preference, and make one granularity choice explicit.

| | A. Fail closed per SESSION | B. Fail closed per EVENT |
|---|---|---|
| On one bad event | The session stops uploading until a human acts | That event is withheld, and the stream continues |
| Visibility of the gap | The whole session goes dark | The gap is shown where it happened |
| Risk | None uploaded | None uploaded: the raw bytes never leave |

**Ruling: B.** A failure is withheld, never sent. Every one of these cases WITHHOLDS the event:
- the redactor panics or returns an error;
- the event is not valid UTF-8 or not the expected transcript shape;
- the event exceeds the client's scan limit (64 KiB);
- the `.env` rule in 4.3 matches;
- the "unsure" detector fires: after redaction, a token of 32 or more characters from `[A-Za-z0-9+/=_-]` with Shannon entropy at or above 4.0 bits per character is still present.

A withheld event is uploaded ONLY as a placeholder, `{type: "redaction_withheld", payload: {reason, bytes}}`. `reason` is one of `redactor_error`, `not_utf8`, `bad_shape`, `too_large`, `env_file` or `unsure`. The placeholder carries no content and no hash of the content.

The raw event is surfaced locally: it is written to `<seat store>/rigd-withheld/<session>/<ts>.json` (mode 0600, kept 7 days), and `4genteam rigd status` shows a per-session withheld count. The upload continues past it, and the cursor advances past it, because the placeholder records the gap.

If the redactor fails on EVERY event of a session for 5 minutes, rigd stops that session's upload (A, as a backstop) and reports it locally. That case means a broken redactor, not one bad line.

## 5. Phase 1: what to build first (one shippable slice)

In order, each step with its own check:

1. **Server, go-dev:**
   - `hello.protocol` / `capabilities` → `ready.protocol` / `heartbeat_s` / `capabilities`;
   - `ping` / `pong`;
   - `session.state` / `source`;
   - `events.cursor` stored atomically with the events, in the new `agent_sessions.client_cursor` column (ORM and SQL together), and returned in `session_ack` and `events_ack`;
   - `error.code` / `fatal`;
   - `agent_sessions.seat_state` on the `GET /api/v2/sessions` row, plus the `agent_session` realtime frame (2.3a).

   Check: a PG test that sends a batch, drops the socket before reading the ack, reconnects, and receives `session_ack.cursor` equal to that batch's cursor, with the event count stored exactly once.
2. **Client, go-dev:**
   - `4genteam rigd`: the long-running loop over `rig ps --json`, a per-session tail of `rig transcript`, stop-and-wait `events`, reconnect with backoff, and no retry on 1008 or 4401;
   - redaction per 4.3 and 4.4, with withheld placeholders;
   - `rigd status`.

   Check: on a throwaway rig with 2 seats, kill the network for 60 s mid-stream; after recovery the cloud holds each event exactly once. A seeded `.env` read and a seeded 40-character high-entropy string each arrive as `redaction_withheld`, and the raw file exists locally.
3. **Frontend, fe-dev:**
   - render `redaction_withheld` as a visible gap ("withheld locally: <reason>");
   - render sessions with `seat_state: "stopped"` as stopped, and invalidate `['sessions']` on the `agent_session` realtime frame (2.3a).

   NO chat input: that is phase 2.

   Check: vitest on the event renderer plus one browser look at the Sessions page against a stack that ingested step 2's rig.

Phase 1 ships when steps 1–3 pass. Phase 2 (the `sessions:command` scope, `session_commands`, the human-only issuer, `rigd.json` consent, and the command frames in 2.4) starts only after that.

## 6. Anything a dev seat finds unruled

Hold the frame name or field and ask the architect. Do not invent it. The lead has said this to go-dev and fe-dev, and this note is the reference.
