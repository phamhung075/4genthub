import { Card } from '../../ui/card';
import CommandBox from '../shared/CommandBox';
import { AlertTriangle, HelpCircle } from 'lucide-react';

interface TroubleshootingProps {
  expandedSections: Record<string, boolean>;
  toggleSection: (sectionId: string) => void;
}

const Troubleshooting = ({ expandedSections, toggleSection }: TroubleshootingProps) => {
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
                <li>Run <code className="bg-yellow-100 dark:bg-yellow-900 px-1 rounded">./build-menu.sh</code> option 8 to clean Docker system</li>
                <li>Run <code className="bg-yellow-100 dark:bg-yellow-900 px-1 rounded">./build-menu.sh</code> option 9 for complete rebuild if changes aren't applying</li>
                <li>Restart Docker service: <code className="bg-yellow-100 dark:bg-yellow-900 px-1 rounded">sudo systemctl restart docker</code></li>
                <li>Check port conflicts (8000, 3800, 5432): <code className="bg-yellow-100 dark:bg-yellow-900 px-1 rounded">sudo lsof -i :8000</code></li>
                <li>Verify .env file exists and has correct DATABASE_URL, JWT_SECRET_KEY</li>
                <li>Check PostgreSQL version: Should be PostgreSQL 18 (not 15 or older)</li>
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
                <li>Check MCP server is running: <code className="bg-blue-100 dark:bg-blue-900 px-1 rounded">curl http://localhost:8000/health</code></li>
                <li>Verify agent is properly loaded with <code className="bg-blue-100 dark:bg-blue-900 px-1 rounded">mcp__agenthub_http__call_agent</code></li>
                <li>Check agent tools are available (Dynamic Tool Enforcement v2.0)</li>
                <li>Restart Claude Code application</li>
                <li>Check system resources (RAM/CPU) - agents need minimum 4GB RAM</li>
                <li>Review backend logs: <code className="bg-blue-100 dark:bg-blue-900 px-1 rounded">docker logs agenthub-backend</code></li>
              </ul>
            </div>
          </Card>

          <Card className="p-4 bg-purple-50 dark:bg-purple-950 border-purple-200 dark:border-purple-800 mb-4">
            <h5 className="font-semibold text-purple-900 dark:text-purple-100 flex items-center mb-2">
              <AlertTriangle className="h-4 w-4 mr-2" />
              Database Connection Errors
            </h5>
            <div className="text-sm text-purple-800 dark:text-purple-200 space-y-2">
              <p><strong>Problem:</strong> "Connection refused" or "Database not found" errors</p>
              <p><strong>Solutions:</strong></p>
              <ul className="list-disc list-inside ml-4 space-y-1">
                <li>Start database first: <code className="bg-purple-100 dark:bg-purple-900 px-1 rounded">./build-menu.sh</code> option B</li>
                <li>Verify DATABASE_URL in .env file (check host, port, username, password)</li>
                <li>Check PostgreSQL is running: <code className="bg-purple-100 dark:bg-purple-900 px-1 rounded">docker ps | grep postgres</code></li>
                <li>Test connection: <code className="bg-purple-100 dark:bg-purple-900 px-1 rounded">psql -h localhost -p 5432 -U agenthub_user -d agenthub</code></li>
                <li>Check database logs: <code className="bg-purple-100 dark:bg-purple-900 px-1 rounded">docker logs agenthub-postgres</code></li>
              </ul>
            </div>
          </Card>

          <Card className="p-4 bg-orange-50 dark:bg-orange-950 border-orange-200 dark:border-orange-800 mb-4">
            <h5 className="font-semibold text-orange-900 dark:text-orange-100 flex items-center mb-2">
              <AlertTriangle className="h-4 w-4 mr-2" />
              Frontend Not Loading
            </h5>
            <div className="text-sm text-orange-800 dark:text-orange-200 space-y-2">
              <p><strong>Problem:</strong> Frontend shows blank page or won't start on port 3800</p>
              <p><strong>Solutions:</strong></p>
              <ul className="list-disc list-inside ml-4 space-y-1">
                <li>Check if port 3800 is free: <code className="bg-orange-100 dark:bg-orange-900 px-1 rounded">lsof -i :3800</code></li>
                <li>Verify Node.js version 18+ is installed: <code className="bg-orange-100 dark:bg-orange-900 px-1 rounded">node --version</code></li>
                <li>Clear build cache and reinstall: <code className="bg-orange-100 dark:bg-orange-900 px-1 rounded">rm -rf node_modules .vite && npm install</code></li>
                <li>Check browser console for errors (F12)</li>
                <li>Verify Vite 7.x is being used: <code className="bg-orange-100 dark:bg-orange-900 px-1 rounded">npm list vite</code></li>
                <li>Try development mode: <code className="bg-orange-100 dark:bg-orange-900 px-1 rounded">./build-menu.sh</code> option D</li>
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
              command="python3.14 --version"
              title="Verify Python Version"
              description="Should show Python 3.14.x (upgraded from 3.12)"
            />

            <CommandBox
              command="./build-menu.sh"
              title="Access Docker Menu"
              description="Interactive menu for all Docker operations"
            />

            <CommandBox
              command="docker-compose ps"
              title="Check Service Status"
              description="Shows status of all services (backend, frontend, db)"
            />

            <CommandBox
              command="sudo lsof -i :8000 -i :3800 -i :5432"
              title="Check Port Usage"
              description="Identify processes using required ports"
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