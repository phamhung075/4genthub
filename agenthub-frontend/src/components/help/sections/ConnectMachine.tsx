import React from 'react';
import { Card } from '../../ui/card';
import { Cable } from 'lucide-react';
import CommandBox from '../shared/CommandBox';
import { ConnectorTokenGuide, McpTokenGuide } from '../../tokens/ClientTokenGuides';
import type { HelpSectionData } from './WhatIs4genthub';

interface ConnectMachineProps {
  expandedSections: Record<string, boolean>;
  toggleSection: (sectionId: string) => void;
  deploymentMode?: 'local' | 'cloud';
}

const ConnectMachine = ({ expandedSections, toggleSection }: ConnectMachineProps): HelpSectionData => {
  const sectionData = {
    id: 'connect-machine',
    title: 'Connect your machine',
    description: 'Send a local session to 4genthub with the 4genteam client and watch it on the Sessions page',
    icon: <Cable className="h-6 w-6 text-teal-500" />,
    content: (
      <div className="space-y-6">
        <p className="text-base leading-relaxed">
          Your seats run on your own machine, in 4genteam. The <strong>4genteam</strong> client dials <em>out</em> to
          4genthub, so the server never connects into your machine and you open no inbound port. A session
          appears on the <a href="/sessions" className="underline font-semibold">Sessions</a> page only after
          the client has sent it.
        </p>

        <div className="space-y-4">
          <Card className="p-4 border-l-4 border-blue-500 bg-blue-50 dark:bg-blue-950">
            <h5 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">Step 1: Create two tokens</h5>
            <ol className="list-decimal list-inside text-sm text-blue-800 dark:text-blue-200 space-y-1 ml-4">
              <li>Open <a href="/tokens" className="underline font-semibold">API Tokens</a></li>
              <li>Press <strong>Client connector</strong>, name the token and generate it: it holds only <code className="bg-blue-100 dark:bg-blue-900 px-1 rounded">sessions:write</code></li>
              <li>Press <strong>Client MCP</strong>, name the token and generate it: it holds every scope except <code className="bg-blue-100 dark:bg-blue-900 px-1 rounded">sessions:write</code></li>
              <li>Copy each token once; it is not shown again. A popup after each one shows the steps below with your token filled in</li>
            </ol>
            <p className="text-xs text-blue-800 dark:text-blue-200 mt-3">
              They are two tokens on purpose: the connector token can publish terminal sessions and nothing else,
              and the MCP key cannot. Without the connector scope the server accepts the connection and closes it
              with code 1008.
            </p>
          </Card>

          <Card className="p-4 border-l-4 border-green-500 bg-green-50 dark:bg-green-950">
            <h5 className="font-semibold text-green-900 dark:text-green-100 mb-2">Step 2: Install the client and store the tokens</h5>
            <div className="space-y-6">
              <CommandBox
                command="4genteam --help"
                title="Check the client is on PATH"
                description="Needs the 4genteam client built and installed (agenthub_client/scripts/build.sh)"
              />
              <ConnectorTokenGuide />
              <McpTokenGuide />
            </div>
          </Card>

          <Card className="p-4 border-l-4 border-purple-500 bg-purple-50 dark:bg-purple-950">
            <h5 className="font-semibold text-purple-900 dark:text-purple-100 mb-2">Step 3: Send a session</h5>
            <div className="space-y-3">
              <CommandBox
                command="4genteam sync connector --session <session-name>"
                title="Send one local session once"
                description="Redacts secrets locally first, then sends the newest 50 transcript lines. Add --lines to change that"
              />
              <p className="text-sm text-purple-800 dark:text-purple-200">
                Open the Sessions page, press Refresh, and select the session to follow its stream. It shows only
                the sessions of the signed-in account.
              </p>
            </div>
          </Card>
        </div>

        <Card className="p-4 border-l-4 border-yellow-500 bg-yellow-50 dark:bg-yellow-950">
          <h5 className="font-semibold text-yellow-900 dark:text-yellow-100 mb-2">What it does not do yet</h5>
          <ul className="list-disc list-inside text-sm text-yellow-800 dark:text-yellow-200 space-y-1 ml-4">
            <li>The <code>sync connector</code> command sends one session once and exits. To keep every local session
              live, start the room with <code>4genteam up</code>: its agent daemon reconnects on its own.</li>
            <li>Messages from the browser to a seat are not available yet.</li>
          </ul>
        </Card>
      </div>
    ),
    isExpanded: expandedSections['connect-machine'],
    onToggle: () => toggleSection('connect-machine')
  };

  return sectionData;
};

export default ConnectMachine;
