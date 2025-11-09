import { HardDrive } from 'lucide-react';
import { Card } from '../../ui/card';
import CommandBox from '../shared/CommandBox';

interface DockerSetupProps {
  expandedSections: Record<string, boolean>;
  toggleSection: (sectionId: string) => void;
}

const DockerSetup = ({ expandedSections, toggleSection }: DockerSetupProps) => {
  const dockerMenuOptions = [
    { key: "1", name: "🚀 Backend + Frontend Only", desc: "Start backend (port 8000) and frontend (port 3800). Requires database already running (option B)." },
    { key: "2", name: "☁️ Supabase Cloud", desc: "Use remote Supabase database without Redis. Good for cloud testing." },
    { key: "3", name: "☁️🔴 Supabase Cloud + Redis", desc: "Full production-like stack with Supabase database and Redis caching." },
    { key: "B", name: "🗄️ Database Only", desc: "Start PostgreSQL 18 database only (port 5432). Run this first before option 1." },
    { key: "C", name: "🎛️ pgAdmin UI Only", desc: "Start pgAdmin web interface for database management. Requires database running." },
    { key: "D", name: "🚀 Start Dev Mode", desc: "Run backend and frontend locally (non-Docker) with hot reload for fastest development." },
    { key: "R", name: "🔄 Restart Dev Mode", desc: "Rebuild and restart services to apply code changes. Use after modifying backend/frontend." },
    { key: "A", name: "🔓 Auth Bypass Help", desc: "Learn how to bypass Keycloak authentication for local development without external auth server." },
    { key: "P", name: "🚀 Start Optimized Mode", desc: "Performance mode with memory/CPU limits (256-512MB). Best for low-resource PCs." },
    { key: "M", name: "📊 Monitor Performance", desc: "Real-time container resource usage, memory, disk, and system statistics." },
    { key: "4", name: "📊 Show Status", desc: "Display running containers, ports, and health status for all services." },
    { key: "5", name: "🛑 Stop All Services", desc: "Stop all running Docker containers (backend, frontend, database, Redis)." },
    { key: "6", name: "📜 View Logs", desc: "View and tail logs from backend, frontend, database, or Redis containers." },
    { key: "7", name: "🗄️ Database Shell", desc: "Open PostgreSQL psql shell for direct database access and SQL queries." },
    { key: "8", name: "🧹 Clean Docker System", desc: "Remove dangling images, volumes, and build cache to free disk space." },
    { key: "9", name: "🔄 Force Complete Rebuild", desc: "Remove all images and rebuild from scratch. Use when major changes aren't applying." },
    { key: "0", name: "🚪 Exit", desc: "Exit the Docker management menu." }
  ];

  const sectionData = {
    id: 'docker-setup',
    title: 'Docker Setup with docker-menu.sh',
    description: 'Interactive Docker management for local development and testing',
    icon: <HardDrive className="h-6 w-6 text-cyan-500" />,
    content: (
      <div className="space-y-6">
        {/* Local Usage Notice */}
        <div className="bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <p className="text-sm text-blue-800 dark:text-blue-200">
            <strong>💡 Local Development Tool:</strong> This menu is designed for local development and testing only.
            For production deployments, use CapRover or your cloud platform's Docker orchestration.
          </p>
        </div>

        <div>
          <h4 className="text-lg font-semibold mb-3">Access Methods</h4>
          <div className="space-y-3">
            <CommandBox
              command="./build-menu.sh"
              title="🎯 Recommended: Convenience Wrapper (from project root)"
              description="Easy access from anywhere in the project"
            />
            <CommandBox
              command="./docker-system/docker-menu.sh"
              title="Direct Access"
              description="Access the actual implementation directly"
            />
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-3">
            💡 <strong>Tip:</strong> Both commands provide identical functionality. Use{' '}
            <code className="bg-gray-100 dark:bg-gray-800 px-1 rounded">./build-menu.sh</code>{' '}
            from the project root for convenience!
          </p>
        </div>

        <div>
          <h4 className="text-lg font-semibold mb-3">All 17 Menu Options</h4>
          <div className="space-y-3">
            <div className="grid gap-2">
              <h5 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Build Configurations</h5>
              {dockerMenuOptions.slice(0, 3).map((option) => (
                <Card key={option.key} className="p-3 bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="font-mono text-sm bg-blue-100 dark:bg-blue-900 px-2 py-1 rounded text-blue-800 dark:text-blue-200 mr-3">
                        {option.key}
                      </span>
                      <span className="font-medium text-blue-900 dark:text-blue-100">{option.name}</span>
                    </div>
                    <span className="text-xs text-blue-700 dark:text-blue-300">{option.desc}</span>
                  </div>
                </Card>
              ))}
            </div>

            <div className="grid gap-2">
              <h5 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Database Management</h5>
              {dockerMenuOptions.slice(3, 5).map((option) => (
                <Card key={option.key} className="p-3 bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="font-mono text-sm bg-green-100 dark:bg-green-900 px-2 py-1 rounded text-green-800 dark:text-green-200 mr-3">
                        {option.key}
                      </span>
                      <span className="font-medium text-green-900 dark:text-green-100">{option.name}</span>
                    </div>
                    <span className="text-xs text-green-700 dark:text-green-300">{option.desc}</span>
                  </div>
                </Card>
              ))}
            </div>

            <div className="grid gap-2">
              <h5 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Development & Performance</h5>
              {dockerMenuOptions.slice(5, 10).map((option) => (
                <Card key={option.key} className="p-3 bg-purple-50 dark:bg-purple-950 border-purple-200 dark:border-purple-800">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="font-mono text-sm bg-purple-100 dark:bg-purple-900 px-2 py-1 rounded text-purple-800 dark:text-purple-200 mr-3">
                        {option.key}
                      </span>
                      <span className="font-medium text-purple-900 dark:text-purple-100">{option.name}</span>
                    </div>
                    <span className="text-xs text-purple-700 dark:text-purple-300">{option.desc}</span>
                  </div>
                </Card>
              ))}
            </div>

            <details className="mt-4">
              <summary className="cursor-pointer font-medium text-gray-700 dark:text-gray-300 mb-3">
                Management Options (7 more)
              </summary>
              <div className="grid gap-2 mt-3">
                {dockerMenuOptions.slice(10).map((option) => (
                  <div key={option.key} className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-900 rounded text-sm">
                    <div>
                      <span className="font-mono bg-gray-200 dark:bg-gray-800 px-2 py-1 rounded text-gray-700 dark:text-gray-300 mr-3">
                        {option.key}
                      </span>
                      <span>{option.name}</span>
                    </div>
                    <span className="text-xs text-gray-500">{option.desc}</span>
                  </div>
                ))}
              </div>
            </details>
          </div>
        </div>

        <div className="bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
          <h4 className="text-lg font-semibold mb-3 text-amber-900 dark:text-amber-100">
            🔓 Authentication Bypass for Local Development
          </h4>
          <p className="text-sm text-amber-800 dark:text-amber-200 mb-3">
            Work without Keycloak by bypassing authentication. Perfect for local development and testing!
          </p>

          <div className="space-y-3">
            <div>
              <h5 className="font-semibold text-amber-900 dark:text-amber-100 text-sm mb-2">Quick Setup:</h5>
              <ol className="text-sm text-amber-800 dark:text-amber-200 space-y-1 list-decimal list-inside pl-2">
                <li>Edit <code className="bg-amber-100 dark:bg-amber-900 px-1 rounded">.env</code> or <code className="bg-amber-100 dark:bg-amber-900 px-1 rounded">.env.dev</code> file</li>
                <li>Set <code className="bg-amber-100 dark:bg-amber-900 px-1 rounded">AUTH_ENABLED=false</code> (Backend)</li>
                <li>Set <code className="bg-amber-100 dark:bg-amber-900 px-1 rounded">VITE_DISABLE_AUTH=true</code> (Frontend)</li>
                <li>Run menu option <strong>R</strong> or <strong>A</strong> to restart with new settings</li>
              </ol>
            </div>

            <div className="bg-amber-100 dark:bg-amber-900 rounded p-3">
              <h5 className="font-semibold text-amber-900 dark:text-amber-100 text-sm mb-2">What Gets Bypassed:</h5>
              <div className="grid grid-cols-2 gap-3 text-xs text-amber-800 dark:text-amber-200">
                <div>
                  <strong className="block mb-1">Backend:</strong>
                  <ul className="list-disc list-inside space-y-1 pl-2">
                    <li>No Keycloak connection needed</li>
                    <li>Default user auto-injected</li>
                    <li>All API requests allowed</li>
                  </ul>
                </div>
                <div>
                  <strong className="block mb-1">Frontend:</strong>
                  <ul className="list-disc list-inside space-y-1 pl-2">
                    <li>Login/signup forms hidden</li>
                    <li>Direct app access</li>
                    <li>No token management</li>
                  </ul>
                </div>
              </div>
            </div>

            <div className="bg-red-100 dark:bg-red-950 border border-red-300 dark:border-red-800 rounded p-2">
              <p className="text-xs text-red-800 dark:text-red-200">
                ⚠️ <strong>Production Warning:</strong> Always use <code className="bg-red-200 dark:bg-red-900 px-1 rounded">AUTH_ENABLED=true</code> and{' '}
                <code className="bg-red-200 dark:bg-red-900 px-1 rounded">VITE_DISABLE_AUTH=false</code> for production deployments!
              </p>
            </div>

            <div>
              <p className="text-xs text-amber-700 dark:text-amber-300">
                💡 <strong>Tip:</strong> Use menu option <strong>A</strong> for complete auth bypass documentation with environment variable reference.
              </p>
            </div>
          </div>
        </div>

        <div>
          <h4 className="text-lg font-semibold mb-3">Recommended Workflows</h4>
          <div className="space-y-3">
            <Card className="p-4 bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800">
              <h5 className="font-semibold text-green-900 dark:text-green-100 mb-2">
                🥇 First-Time Setup (Local Usage):
              </h5>
              <ol className="text-sm text-green-800 dark:text-green-200 space-y-1 list-decimal list-inside">
                <li>Run option <strong>B</strong> to start PostgreSQL database</li>
                <li>Run option <strong>1</strong> to start Backend + Frontend</li>
                <li>Access at http://localhost:3800 (Frontend) and http://localhost:8000 (Backend)</li>
              </ol>
            </Card>

            <Card className="p-4 bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800">
              <h5 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">
                🔄 Development Cycle (Development Mode):
              </h5>
              <ol className="text-sm text-blue-800 dark:text-blue-200 space-y-1 list-decimal list-inside">
                <li>Make code changes</li>
                <li>Run option <strong>R</strong> to restart and apply changes</li>
                <li>Test your changes</li>
                <li>Repeat as needed</li>
              </ol>
            </Card>
          </div>
        </div>
      </div>
    ),
    isExpanded: expandedSections['docker-setup'],
    onToggle: () => toggleSection('docker-setup')
  };

  return sectionData;
};

export default DockerSetup;