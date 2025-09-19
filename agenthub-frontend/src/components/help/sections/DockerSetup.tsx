import React from 'react';
import { Card } from '../../ui/card';
import CommandBox from '../shared/CommandBox';
import { HardDrive } from 'lucide-react';

interface DockerSetupProps {
  expandedSections: Record<string, boolean>;
  toggleSection: (sectionId: string) => void;
}

const DockerSetup: React.FC<DockerSetupProps> = ({ expandedSections, toggleSection }) => {
  const dockerMenuOptions = [
    { key: "1", name: "🚀 Backend + Frontend Only", desc: "Requires DB running" },
    { key: "2", name: "☁️ Supabase Cloud", desc: "No Redis" },
    { key: "3", name: "☁️🔴 Supabase Cloud + Redis", desc: "Full Stack" },
    { key: "B", name: "🗄️ Database Only", desc: "PostgreSQL standalone" },
    { key: "C", name: "🎛️ pgAdmin UI Only", desc: "Requires DB running" },
    { key: "D", name: "🚀 Start Dev Mode", desc: "Backend + Frontend locally" },
    { key: "R", name: "🔄 Restart Dev Mode", desc: "Apply new changes" },
    { key: "P", name: "🚀 Start Optimized Mode", desc: "Uses less RAM/CPU" },
    { key: "M", name: "📊 Monitor Performance", desc: "Live stats" },
    { key: "4", name: "📊 Show Status", desc: "" },
    { key: "5", name: "🛑 Stop All Services", desc: "" },
    { key: "6", name: "📜 View Logs", desc: "" },
    { key: "7", name: "🗄️ Database Shell", desc: "" },
    { key: "8", name: "🧹 Clean Docker System", desc: "" },
    { key: "9", name: "🔄 Force Complete Rebuild", desc: "Removes all images" },
    { key: "0", name: "🚪 Exit", desc: "" }
  ];

  const sectionData = {
    id: 'docker-setup',
    title: 'Docker Setup with docker-menu.sh',
    description: 'Complete guide to using the interactive Docker management system',
    icon: <HardDrive className="h-6 w-6 text-cyan-500" />,
    content: (
      <div className="space-y-6">
        <div>
          <h4 className="text-lg font-semibold mb-3">Starting the Docker Menu</h4>
          <CommandBox
            command="cd docker-system && ./docker-menu.sh"
            title="Launch Docker Management Menu"
            description="Interactive menu system for all Docker operations"
          />
        </div>

        <div>
          <h4 className="text-lg font-semibold mb-3">All 16 Menu Options</h4>
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
              {dockerMenuOptions.slice(5, 9).map((option) => (
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
                {dockerMenuOptions.slice(9).map((option) => (
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

        <div>
          <h4 className="text-lg font-semibold mb-3">Recommended Workflows</h4>
          <div className="space-y-3">
            <Card className="p-4 bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800">
              <h5 className="font-semibold text-green-900 dark:text-green-100 mb-2">
                🥇 First-Time Setup:
              </h5>
              <ol className="text-sm text-green-800 dark:text-green-200 space-y-1 list-decimal list-inside">
                <li>Run option <strong>B</strong> to start PostgreSQL database</li>
                <li>Run option <strong>1</strong> to start Backend + Frontend</li>
                <li>Access at http://localhost:3800 (Frontend) and http://localhost:8000 (Backend)</li>
              </ol>
            </Card>

            <Card className="p-4 bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800">
              <h5 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">
                🔄 Development Cycle:
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