import { Card } from '../../ui/card';
import RawJSONDisplay from '../../ui/RawJSONDisplay';
import { Settings, Lightbulb } from 'lucide-react';
import type { HelpSectionData } from './WhatIs4genthub';
import DeploymentTabs from '../shared/DeploymentTabs';

interface MCPConfigurationProps {
  expandedSections: Record<string, boolean>;
  toggleSection: (sectionId: string) => void;
  deploymentMode?: 'local' | 'cloud';
}

const MCPConfiguration= ({ expandedSections, toggleSection, deploymentMode = 'cloud' }: MCPConfigurationProps): HelpSectionData => {
  // Local development configuration
  const mcpConfigLocalExample = {
    mcpServers: {
        "sequential-thinking": {
            "command": "npx",
            "args": [
                "-y",
                "@modelcontextprotocol/server-sequential-thinking"
            ],
            "env": {}
        },
        "agenthub_http": {
            "type": "http",
            "url": "http://localhost:8000/mcp",
            "headers": {
                "Accept": "application/json, text/event-stream",
                "Authorization": "Bearer <generated-token>"
            }
        },
        "shadcn-ui-server": {
            "command": "npx",
            "args": [
                "-y",
                "@shadcn/ui-server"
            ],
            "env": {}
        }
    }
  };

  // Cloud production configuration
  const mcpConfigCloudExample = {
    mcpServers: {
        "sequential-thinking": {
            "command": "npx",
            "args": [
                "-y",
                "@modelcontextprotocol/server-sequential-thinking"
            ],
            "env": {}
        },
        "agenthub_http": {
            "type": "http",
            "url": "https://api.4genthub.com/mcp",
            "headers": {
                "Accept": "application/json, text/event-stream",
                "Authorization": "Bearer <your-api-key-from-dashboard>"
            }
        }
    }
  };

  const envExampleData = {
    comment: "Essential environment variables for local development",
    FASTMCP_PORT: 8000,
    FRONTEND_PORT: 3800,
    DATABASE_TYPE: "postgresql",
    DATABASE_HOST: "localhost",
    DATABASE_PORT: 5432,
    DATABASE_NAME: "agenthub_prod",
    DATABASE_USER: "agenthub_user",
    DATABASE_PASSWORD: "ChangeThisSecurePassword2025!",
    AUTH_PROVIDER: "keycloak",
    AUTH_ENABLED: true,
    EMAIL_VERIFIED_AUTO: true,
    VITE_API_URL: "http://localhost:8000",
    VITE_BACKEND_URL: "http://localhost:8000"
  };

  // Shared content (file location info)
  const fileLocationContent = (
    <div className="bg-amber-50 dark:bg-amber-950 p-4 rounded-lg border border-amber-200 dark:border-amber-800 mb-4">
      <h5 className="font-semibold text-amber-900 dark:text-amber-100 flex items-center mb-2">
        <Lightbulb className="h-4 w-4 mr-2" />
        File Location
      </h5>
      <div className="text-sm text-amber-800 dark:text-amber-200 space-y-1 font-mono">
        <div><strong>macOS:</strong> ~/Library/Application Support/Claude/claude_desktop_config.json</div>
        <div><strong>Windows:</strong> %APPDATA%\Claude\claude_desktop_config.json</div>
        <div><strong>Linux:</strong> ~/.config/claude/claude_desktop_config.json</div>
      </div>
    </div>
  );

  // Local configuration content
  const localContent = (
    <div className="space-y-6">
      <div>
        <h4 className="text-lg font-semibold mb-3">What is .mcp.json?</h4>
        <p className="text-gray-600 dark:text-gray-300 mb-4">
          The .mcp.json file is your MCP client configuration that tells Claude Desktop or other MCP clients
          how to connect to MCP servers. It defines server endpoints, authentication, and environment settings.
        </p>
        {fileLocationContent}
      </div>

      <div className="bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <p className="text-sm text-blue-800 dark:text-blue-200">
          <strong>💻 Local Development:</strong> Connect to your local 4genthub instance running on http://localhost:8000
        </p>
      </div>

      <div>
        <h4 className="text-lg font-semibold mb-3">4genthub MCP Configuration (Local)</h4>
        <p className="text-gray-600 dark:text-gray-300 mb-4">
          Configure your MCP client to connect to your local 4genthub server:
        </p>
        <RawJSONDisplay
          jsonData={mcpConfigLocalExample}
          title="MCP Configuration for Local Development"
          fileName="claude_desktop_config.json"
        />
      </div>

      <div>
        <h4 className="text-lg font-semibold mb-3">Environment Variables (Local)</h4>
        <p className="text-gray-600 dark:text-gray-300 mb-4">
          Essential environment variables for local MCP server configuration:
        </p>
        <RawJSONDisplay
          jsonData={envExampleData}
          title="Environment Configuration"
          fileName=".env.dev"
        />
      </div>

      <Card className="p-4 bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800">
        <h5 className="font-semibold text-green-900 dark:text-green-100 mb-2">Local Development Features</h5>
        <ul className="text-sm text-green-800 dark:text-green-200 space-y-1">
          <li>• Local 4genthub installation on http://localhost:8000</li>
          <li>• PostgreSQL database on localhost:5432</li>
          <li>• Direct server connection (no internet required)</li>
          <li>• Full debugging and customization access</li>
          <li>• Generated token authentication</li>
        </ul>
      </Card>
    </div>
  );

  // Cloud configuration content
  const cloudContent = (
    <div className="space-y-6">
      <div className="bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-lg p-4">
        <h4 className="text-lg font-semibold text-green-900 dark:text-green-100 mb-3">
          ☁️ Simple 3-Step Setup
        </h4>
        <p className="text-sm text-green-800 dark:text-green-200 mb-3">
          No server installation, no database setup, no configuration needed!
        </p>
        <ol className="text-sm text-green-800 dark:text-green-200 space-y-2 list-decimal list-inside">
          <li className="font-medium">Visit <a href="https://www.4genthub.com" target="_blank" rel="noopener noreferrer" className="underline">www.4genthub.com</a> and sign up</li>
          <li className="font-medium">Get your API key from Dashboard → Settings → API Keys</li>
          <li className="font-medium">Add the configuration below to your claude_desktop_config.json</li>
        </ol>
      </div>

      <div>
        <h4 className="text-lg font-semibold mb-3">Your MCP Configuration</h4>
        <p className="text-gray-600 dark:text-gray-300 mb-4">
          Copy this configuration and replace <code className="bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">&lt;your-api-key-from-dashboard&gt;</code> with your actual API key:
        </p>
        <RawJSONDisplay
          jsonData={mcpConfigCloudExample}
          title="MCP Configuration for Cloud"
          fileName="claude_desktop_config.json"
        />
      </div>

      <Card className="p-4 bg-purple-50 dark:bg-purple-950 border-purple-200 dark:border-purple-800">
        <h5 className="font-semibold text-purple-900 dark:text-purple-100 mb-2">✨ Why Cloud?</h5>
        <ul className="text-sm text-purple-800 dark:text-purple-200 space-y-1">
          <li>• No installation or setup required</li>
          <li>• No database configuration needed</li>
          <li>• Automatic updates and scaling</li>
          <li>• 24/7 availability with enterprise support</li>
          <li>• Start using in under 2 minutes</li>
        </ul>
      </Card>
    </div>
  );

  const sectionData = {
    id: 'mcp-configuration',
    title: 'MCP Configuration & Setup',
    description: 'Understanding .mcp.json configuration and connecting to 4genthub',
    icon: <Settings className="h-6 w-6 text-purple-500" />,
    content: (
      <DeploymentTabs
        localContent={localContent}
        cloudContent={cloudContent}
        defaultMode={deploymentMode}
      />
    ),
    isExpanded: expandedSections['mcp-configuration'],
    onToggle: () => toggleSection('mcp-configuration')
  };

  return sectionData;
};

export default MCPConfiguration;