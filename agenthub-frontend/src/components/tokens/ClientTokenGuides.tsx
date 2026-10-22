import React from 'react';
import { API_BASE_URL } from '../../config/environment';
import { Card } from '../ui/card';
import CommandBox from './CommandBox';

// The scope that opens the connector websocket and publishes terminal sessions. A token holding only this
// scope is a "Client connector" token; every other token is the MCP key.
export const CONNECTOR_SCOPE = 'sessions:write';

export const isConnectorToken = (scopes: string[]): boolean =>
  scopes.length === 1 && scopes[0] === CONNECTOR_SCOPE;

interface GuideProps {
  // The token just generated; the help page passes none and shows a placeholder.
  token?: string | null;
}

const ENV_FILE = '~/.config/4genthub/.env';

// What to do with a Client connector token: the agent daemon reads it, nothing else does.
export const ConnectorTokenGuide: React.FC<GuideProps> = ({ token }) => (
  <div className="space-y-4">
    <Card className="p-4 border-l-4 border-blue-500 bg-blue-50 dark:bg-blue-950">
      <h5 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">Client connector token</h5>
      <p className="text-sm text-blue-800 dark:text-blue-200">
        It holds only <code className="bg-blue-100 dark:bg-blue-900 px-1 rounded">{CONNECTOR_SCOPE}</code>. The
        <strong> 4genteam agent</strong> on your machine uses it to open one outbound socket and publish your
        sessions to the Sessions page. It cannot call MCP tools: keep your MCP key (Client MCP) separate.
      </p>
    </Card>
    <div className="space-y-3">
      <CommandBox
        command={`AGENTHUB_CONNECTOR_TOKEN=${token || '<your connector token>'}`}
        title={`Step 1: paste this line into ${ENV_FILE}`}
        description="Never put the token in a command line or a committed file. Run chmod 600 on the file."
      />
      <CommandBox
        command="4genteam up <room> --team <team-dir>"
        title="Step 2: start the room"
        description="Starts the agent, which reads the connector token and keeps the connector socket up"
      />
      <CommandBox
        command="4genteam heal <room> --check"
        title="Step 3: check the connection"
        description="Prints '<room>: clean' once the server accepts the agent. A 'Missing scope sessions:write' line means the token is not a Client connector token"
      />
    </div>
    <p className="text-sm text-base-secondary">
      Step 4: open <a href="/sessions" className="underline font-semibold">Sessions</a>, press Refresh and select a
      session to follow its stream. To send one session once without the agent, run{' '}
      <code>4genteam sync connector --session &lt;session-name&gt;</code>.
    </p>
  </div>
);

// What to do with a Client MCP token: it is the seats' and Claude Code's key to the MCP tools.
export const McpTokenGuide: React.FC<GuideProps> = ({ token }) => (
  <div className="space-y-4">
    <Card className="p-4 border-l-4 border-purple-500 bg-purple-50 dark:bg-purple-950">
      <h5 className="font-semibold text-purple-900 dark:text-purple-100 mb-2">Client MCP token</h5>
      <p className="text-sm text-purple-800 dark:text-purple-200">
        It is the key your seats and Claude Code use to call the MCP tools (tasks, subtasks, contexts, projects,
        branches). It never carries <code className="bg-purple-100 dark:bg-purple-900 px-1 rounded">{CONNECTOR_SCOPE}</code>:
        publishing sessions takes a separate Client connector token.
      </p>
    </Card>
    <div className="space-y-3">
      <CommandBox
        command={`AGENTHUB_URL=${API_BASE_URL}`}
        title={`Step 1: put this line in ${ENV_FILE}`}
        description="The server the client talks to"
      />
      <CommandBox
        command={`AGENTHUB_TOKEN=${token || '<your MCP token>'}`}
        title="Step 2: and this one under it"
        description="Never put the token in a command line or a committed file. Run chmod 600 on the file."
      />
      <CommandBox
        command="4genteam room reseat <room> <seat>"
        title="Step 3: reseat each running seat"
        description="A seat reads the file and its MCP config only when it starts, so a running seat keeps the old key until it is reseated"
      />
    </div>
    <p className="text-sm text-base-secondary">
      Step 4, Claude Code outside a team: add the MCP configuration above to your Claude Code settings and restart
      it.
    </p>
  </div>
);
