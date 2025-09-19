import React from 'react';
import { Card } from '../../ui/card';
import CommandBox from '../shared/CommandBox';
import { AlertTriangle, HelpCircle } from 'lucide-react';

interface TroubleshootingProps {
  expandedSections: Record<string, boolean>;
  toggleSection: (sectionId: string) => void;
}

const Troubleshooting: React.FC<TroubleshootingProps> = ({ expandedSections, toggleSection }) => {
  const sectionData = {
    id: 'troubleshooting',
    title: 'Troubleshooting',
    description: 'Common issues and solutions for 4genthub development',
    icon: <HelpCircle className="h-6 w-6 text-red-500" />,
    content: (
      <div className="space-y-6">
        <div>
          <h4 className="text-lg font-semibold mb-3">Common Issues</h4>

          <Card className="p-4 bg-red-50 dark:bg-red-950 border-red-200 dark:border-red-800 mb-4">
            <h5 className="font-semibold text-red-900 dark:text-red-100 flex items-center mb-2">
              <AlertTriangle className="h-4 w-4 mr-2" />
              MCP Connection Failed
            </h5>
            <div className="text-sm text-red-800 dark:text-red-200 space-y-2">
              <p><strong>Problem:</strong> Claude Code cannot connect to 4genthub MCP server</p>
              <p><strong>Solutions:</strong></p>
              <ul className="list-disc list-inside ml-4 space-y-1">
                <li>Verify API token in .claude/.mcp.json</li>
                <li>Check internet connection</li>
                <li>Ensure server is running (for local development)</li>
                <li>Test connection manually with curl</li>
              </ul>
            </div>
          </Card>

          <Card className="p-4 bg-yellow-50 dark:bg-yellow-950 border-yellow-200 dark:border-yellow-800 mb-4">
            <h5 className="font-semibold text-yellow-900 dark:text-yellow-100 flex items-center mb-2">
              <AlertTriangle className="h-4 w-4 mr-2" />
              Docker Issues
            </h5>
            <div className="text-sm text-yellow-800 dark:text-yellow-200 space-y-2">
              <p><strong>Problem:</strong> Docker containers won't start or database connection fails</p>
              <p><strong>Solutions:</strong></p>
              <ul className="list-disc list-inside ml-4 space-y-1">
                <li>Run docker-menu.sh option 8 to clean Docker system</li>
                <li>Restart Docker service</li>
                <li>Check port conflicts (8000, 3800, 5432)</li>
                <li>Verify .env file configuration</li>
              </ul>
            </div>
          </Card>

          <Card className="p-4 bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800 mb-4">
            <h5 className="font-semibold text-blue-900 dark:text-blue-100 flex items-center mb-2">
              <AlertTriangle className="h-4 w-4 mr-2" />
              Agent Not Responding
            </h5>
            <div className="text-sm text-blue-800 dark:text-blue-200 space-y-2">
              <p><strong>Problem:</strong> AI agents don't respond or give errors</p>
              <p><strong>Solutions:</strong></p>
              <ul className="list-disc list-inside ml-4 space-y-1">
                <li>Check MCP server status</li>
                <li>Verify agent is properly loaded</li>
                <li>Restart Claude Code</li>
                <li>Check system resources (RAM/CPU)</li>
              </ul>
            </div>
          </Card>
        </div>

        <div>
          <h4 className="text-lg font-semibold mb-3">Diagnostic Commands</h4>
          <div className="space-y-3">
            <CommandBox
              command="curl -H 'Authorization: Bearer YOUR_TOKEN' http://localhost:8000/mcp/health"
              title="Test Local MCP Connection"
              description="Should return health status"
            />

            <CommandBox
              command="docker ps"
              title="Check Running Containers"
              description="List active Docker containers"
            />

            <CommandBox
              command="docker logs agenthub-backend"
              title="Check Backend Logs"
              description="View backend application logs"
            />

            <CommandBox
              command="python3.12 --version"
              title="Verify Python Version"
              description="Should show Python 3.12.x"
            />
          </div>
        </div>

        <div>
          <h4 className="text-lg font-semibold mb-3">Getting Help</h4>
          <div className="grid md:grid-cols-2 gap-4">
            <Card className="p-4 bg-gray-50 dark:bg-gray-900">
              <h5 className="font-semibold mb-2">Discord Community</h5>
              <p className="text-sm text-gray-600 dark:text-gray-300 mb-2">
                Join our community for real-time support
              </p>
              <a
                href="https://discord.gg/zmhMpK6N"
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-800 text-sm font-medium"
              >
                discord.gg/zmhMpK6N
              </a>
            </Card>

            <Card className="p-4 bg-gray-50 dark:bg-gray-900">
              <h5 className="font-semibold mb-2">GitHub Issues</h5>
              <p className="text-sm text-gray-600 dark:text-gray-300 mb-2">
                Report bugs and request features
              </p>
              <a
                href="https://github.com/phamhung075/4genthub/issues"
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-800 text-sm font-medium"
              >
                GitHub Issues
              </a>
            </Card>
          </div>
        </div>
      </div>
    ),
    isExpanded: expandedSections['troubleshooting'],
    onToggle: () => toggleSection('troubleshooting')
  };

  return sectionData;
};

export default Troubleshooting;