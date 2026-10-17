# Connect Your Machine

Your seats run on your own machine, in 4genteam. The **4genteam** client dials *out* to 4genthub, so the server never connects into your machine and you open no inbound port. A session appears on the [Sessions](/sessions) page only after the client has sent it.

## 1. Create two tokens

1. Open [API Tokens](/tokens).
2. Press **Client connector**, name the token and generate it: it holds only `sessions:write`.
3. Press **Client MCP**, name the token and generate it: it holds every scope except `sessions:write`.
4. Copy each token once; it is not shown again. A popup after each one shows the steps below with your token filled in.

They are two tokens on purpose: the connector token can publish terminal sessions and nothing else, and the MCP key cannot. Without the connector scope the server accepts the connection and closes it with code 1008.

## 2. Install the client and store the tokens

Check the client is on `PATH` (build and install it with `agenthub_client/scripts/build.sh`):

```bash
4genteam --help
```

Paste these lines into `~/.config/4genthub/.env`, then run `chmod 600` on the file. Never put a token in a command line or a committed file.

```bash
AGENTHUB_URL={{API_ORIGIN}}
AGENTHUB_CONNECTOR_TOKEN=<your connector token>
AGENTHUB_TOKEN=<your MCP token>
```

The **4genteam agent** reads the connector token to open one outbound socket and publish your sessions. It cannot call MCP tools, so the MCP key stays separate. Seats and Claude Code use the MCP key to call the MCP tools.

A seat reads the file and its MCP config only when it starts, so after changing a token run `4genteam room reseat <room> <seat>` for each running seat.

## 3. Start the room and check the connection

```bash
4genteam up <room> --team <team-dir>
4genteam heal <room> --check
```

`heal --check` prints `<room>: clean` once the server accepts the agent. A `Missing scope sessions:write` line means the token is not a Client connector token.

## 4. Send a single session

```bash
4genteam sync connector --session <session-name>
```

It redacts secrets locally first, then sends the newest 50 transcript lines (`--lines` changes that). Open the Sessions page, press Refresh, and select the session to follow its stream. It shows only the sessions of the signed-in account.

`sync connector` sends one session once and exits. To keep every local session live, start the room with `4genteam up`: its agent daemon reconnects on its own.
