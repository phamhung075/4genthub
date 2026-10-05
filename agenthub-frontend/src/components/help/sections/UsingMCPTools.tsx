import {
    ChevronRight,
    Code,
    Cpu,
    Globe,
    Settings,
    Terminal
} from 'lucide-react';
import { Card } from '../../ui/card';
import RawJSONDisplay from '../../ui/RawJSONDisplay';
import type { HelpSectionData } from './WhatIs4genthub';

interface UsingMCPToolsProps {
  expandedSections: Record<string, boolean>;
  toggleSection: (sectionId: string) => void;
  deploymentMode?: 'local' | 'cloud';
}

const UsingMCPTools= ({ expandedSections, toggleSection, deploymentMode }: UsingMCPToolsProps): HelpSectionData => {
  const mcpToolExamples = {
    taskManagement: {
      create: {
        action: "create",
        title: "Implement user authentication",
        assignees: ["@developer"],
        details: "Create JWT-based authentication system with login, logout, and session management",
        priority: "high",
        git_branch_id: "550e8400-e29b-41d4-a716-446655440001"
      },
      get: {
        action: "get",
        task_id: "550e8400-e29b-41d4-a716-446655440005",
        include_context: true
      },
      update: {
        action: "update",
        task_id: "550e8400-e29b-41d4-a716-446655440005",
        status: "in_progress",
        details: "Completed login UI, working on JWT integration"
      }
    },
    contextManagement: {
      create: {
        action: "create",
        level: "task",
        context_id: "task-uuid",
        data: {
          requirements: "User authentication system",
          files: ["/src/auth/login.js", "/src/auth/jwt.js"],
          dependencies: ["database setup", "security review"]
        }
      }
    }
  };

  const sectionData = {
    id: 'using-mcp-tools',
    title: 'Using MCP Tools',
    description: 'Task Management, Seat Coordination, and Context System usage',
    icon: <Cpu className="h-6 w-6 text-indigo-500" />,
    content: (
      <div className="space-y-6">
        <div>
          <h4 className="text-lg font-semibold mb-3">Task Management System</h4>
          <p className="text-gray-600 dark:text-gray-300 mb-4">
            Tasks are the foundation of 4genthub workflow. They store context and requirements, and route work to the seats that do it.
          </p>
          <RawJSONDisplay
            jsonData={mcpToolExamples.taskManagement.create}
            title="Create Task Example"
            fileName="create-task.json"
          />
        </div>

        <div>
          <h4 className="text-lg font-semibold mb-3">Rooms, Seats and Occupants</h4>
          <div className="mb-4">
            <p className="text-gray-600 dark:text-gray-300 mb-4">
              Work is done by seats. A room is a pod, a seat is a durable position keyed by member id,
              and the occupant is the runtime and model currently sitting in it. A task is assigned to a
              seat by writing its key as <code className="bg-gray-100 dark:bg-gray-800 px-1 rounded">@&lt;seat_key&gt;</code>.
            </p>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              <Card className="p-3 bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800">
                <h5 className="font-semibold text-blue-900 dark:text-blue-100 text-sm mb-2">
                  Room (pod)
                </h5>
                <p className="text-xs text-blue-800 dark:text-blue-200">
                  A context domain that groups seats and the links between them.
                </p>
              </Card>
              <Card className="p-3 bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800">
                <h5 className="font-semibold text-green-900 dark:text-green-100 text-sm mb-2">
                  Seat (member)
                </h5>
                <p className="text-xs text-green-800 dark:text-green-200">
                  A durable position with a stable key and a seat type that carries its modules.
                </p>
              </Card>
              <Card className="p-3 bg-purple-50 dark:bg-purple-950 border-purple-200 dark:border-purple-800">
                <h5 className="font-semibold text-purple-900 dark:text-purple-100 text-sm mb-2">
                  Occupant
                </h5>
                <p className="text-xs text-purple-800 dark:text-purple-200">
                  The runtime and model in the seat; it can be replaced without renaming the seat.
                </p>
              </Card>
            </div>
          </div>

          <div className="bg-green-50 dark:bg-green-950 p-4 rounded-lg border border-green-200 dark:border-green-800">
            <h5 className="font-semibold text-green-900 dark:text-green-100 mb-2">
              ✨ Automatic Routing
            </h5>
            <p className="text-sm text-green-800 dark:text-green-200">
              Seat assignment and context creation are handled automatically by the cloud and the client.
              You don't need to invoke a seat manually or create contexts - just interact naturally
              with Claude Code and the system routes and manages these operations behind the scenes.
            </p>
          </div>
        </div>

        <div>
          <h4 className="text-lg font-semibold mb-3">4-Tier Context System</h4>
          <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg mb-4">
            <div className="font-mono text-sm">
              <div className="flex items-center mb-2">
                <Globe className="h-4 w-4 mr-2 text-blue-500" />
                <span className="font-semibold">GLOBAL</span>
                <span className="text-gray-500 ml-2">(per-user)</span>
              </div>
              <div className="ml-6 flex items-center mb-2">
                <ChevronRight className="h-3 w-3 mr-1" />
                <Cpu className="h-4 w-4 mr-2 text-green-500" />
                <span className="font-semibold">PROJECT</span>
              </div>
              <div className="ml-12 flex items-center mb-2">
                <ChevronRight className="h-3 w-3 mr-1" />
                <Code className="h-4 w-4 mr-2 text-purple-500" />
                <span className="font-semibold">BRANCH</span>
              </div>
              <div className="ml-18 flex items-center">
                <ChevronRight className="h-3 w-3 mr-1" />
                <Settings className="h-4 w-4 mr-2 text-orange-500" />
                <span className="font-semibold">TASK</span>
              </div>
            </div>
          </div>

          <div className="bg-blue-50 dark:bg-blue-950 p-4 rounded-lg border border-blue-200 dark:border-blue-800">
            <p className="text-sm text-blue-800 dark:text-blue-200">
              <strong>Automatic Context Inheritance:</strong> Each level automatically inherits from its parent.
              The AI system manages context creation, updates, and inheritance without manual intervention.
            </p>
          </div>
        </div>

        <div>
          <h4 className="text-lg font-semibold mb-3">Common MCP Operations</h4>
          <div className="bg-blue-50 dark:bg-blue-950 p-4 rounded-lg border border-blue-200 dark:border-blue-800">
            <h5 className="font-semibold text-blue-900 dark:text-blue-100 flex items-center mb-2">
              <Terminal className="h-4 w-4 mr-2" />
              Typical Workflow
            </h5>
            <ol className="text-sm text-blue-800 dark:text-blue-200 space-y-1 list-decimal list-inside">
              <li>Create a project and git branch</li>
              <li>Create a task with full context and requirements</li>
              <li>Assign the task to a seat with <code className="bg-blue-100 dark:bg-blue-900 px-1 rounded">@&lt;seat_key&gt;</code></li>
              <li>The occupant receives task_id and accesses full context</li>
              <li>The occupant completes work and updates task status</li>
              <li>Review results and iterate if needed</li>
            </ol>
          </div>
        </div>
      </div>
    ),
    isExpanded: expandedSections['using-mcp-tools'],
    onToggle: () => toggleSection('using-mcp-tools')
  };

  return sectionData;
};

export default UsingMCPTools;
