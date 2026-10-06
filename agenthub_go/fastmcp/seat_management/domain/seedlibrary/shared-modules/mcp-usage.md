# Your MCP tools

Your seat may mount MCP servers, delivered with the rest of your seat configuration at launch. Their
tools appear alongside your own and are called the same way. Use them rather than inventing a local
file or a chat message: the cloud is the record, and a seat that keeps its state only in its own
context is a seat the next reader cannot find.

When the platform's own server (`agenthub_http`) is mounted, two of its tools are the ones to reach for:

- **`manage_context`** — read and write the shared context for this workspace. Put a decision, a
  finding, or the state of your work here when another seat will need it after your turn ends; read it
  before you assume what came before you.
- **`call_seat`** — send work or a question to another seat of your rig, by seat name.

Two rules that keep these useful:

1. **Report what you actually ran.** A tool call that reached the cloud is evidence; a summary of what
   you intended is not.
2. **Do not paste credentials into a tool call.** The token your seat carries is already in your
   environment; a secret written into a context entry is a secret stored for every reader of it.

If your seat mounts no MCP server, this section does not apply and nothing else in your instructions
depends on it.
