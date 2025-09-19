import React from 'react';
import { Card } from '../../ui/card';
import RawJSONDisplay from '../../ui/RawJSONDisplay';
import { Settings, Lightbulb } from 'lucide-react';

interface MCPConfigurationProps {
  expandedSections: Record<string, boolean>;
  toggleSection: (sectionId: string) => void;
}

const MCPConfiguration: React.FC<MCPConfigurationProps> = ({ expandedSections, toggleSection }) => {
  const mcpConfigExample = {
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

  const sectionData = {
    id: 'mcp-configuration',
    title: 'MCP Configuration & Setup',
    description: 'Understanding .mcp.json configuration and connecting to 4genthub',
    icon: <Settings className="h-6 w-6 text-purple-500" />,
    content: (
      <div className="space-y-6">
        <div>
          <h4 className="text-lg font-semibold mb-3">What is .mcp.json?</h4>
          <p className="text-gray-600 dark:text-gray-300 mb-4">
            The .mcp.json file is your MCP client configuration that tells Claude Desktop or other MCP clients
            how to connect to MCP servers. It defines server endpoints, authentication, and environment settings.
          </p>

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
        </div>

        <div>
          <h4 className="text-lg font-semibold mb-3">4genthub MCP Configuration</h4>
          <p className="text-gray-600 dark:text-gray-300 mb-4">
            Configure your MCP client to connect to the 4genthub server:
          </p>
          <RawJSONDisplay
            jsonData={mcpConfigExample}
            title="MCP Configuration for 4genthub"
            fileName="claude_desktop_config.json"
          />
        </div>

        <div>
          <h4 className="text-lg font-semibold mb-3">Development vs Production Setup</h4>
          <div className="grid md:grid-cols-2 gap-4">
            <Card className="p-4 bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800">
              <h5 className="font-semibold text-green-900 dark:text-green-100 mb-2">Development</h5>
              <ul className="text-sm text-green-800 dark:text-green-200 space-y-1">
                <li>• Local 4genthub installation</li>
                <li>• PostgreSQL database</li>
                <li>• Direct server connection</li>
                <li>• Full debugging access</li>
              </ul>
            </Card>
            <Card className="p-4 bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800">
              <h5 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">Production</h5>
              <ul className="text-sm text-blue-800 dark:text-blue-200 space-y-1">
                <li>• Hosted 4genthub instance</li>
                <li>• Cloud database (Supabase)</li>
                <li>• API token authentication</li>
                <li>• Managed infrastructure</li>
              </ul>
            </Card>
          </div>
        </div>

        <div>
          <h4 className="text-lg font-semibold mb-3">Environment Variables</h4>
          <p className="text-gray-600 dark:text-gray-300 mb-4">
            Essential environment variables for MCP server configuration:
          </p>
          <RawJSONDisplay
            jsonData={envExampleData}
            title="Environment Configuration"
            fileName=".env.dev"
          />
        </div>
      </div>
    ),
    isExpanded: expandedSections['mcp-configuration'],
    onToggle: () => toggleSection('mcp-configuration')
  };

  return sectionData;
};

export default MCPConfiguration;