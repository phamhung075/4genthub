import {
    ChevronRight,
    Code,
    Cpu,
    Globe,
    Settings,
    Terminal
} from 'lucide-react';
import React from 'react';
import { Card } from '../../ui/card';
import RawJSONDisplay from '../../ui/RawJSONDisplay';

interface UsingMCPToolsProps {
  expandedSections: Record<string, boolean>;
  toggleSection: (sectionId: string) => void;
}

const UsingMCPTools: React.FC<UsingMCPToolsProps> = ({ expandedSections, toggleSection }) => {
  const mcpToolExamples = {
    taskManagement: {
      create: {
        action: "create",
        title: "Implement user authentication",
        assignees: ["coding-agent"],
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
    agentManagement: {
      callAgent: {
        name_agent: "coding-agent"
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
    description: 'Task Management, Agent Coordination, and Context System usage',
    icon: <Cpu className="h-6 w-6 text-indigo-500" />,
    content: (
      <div className="space-y-6">
        <div>
          <h4 className="text-lg font-semibold mb-3">Task Management System</h4>
          <p className="text-gray-600 dark:text-gray-300 mb-4">
            Tasks are the foundation of 4genthub workflow. They store context, requirements, and coordinate agent work.
          </p>
          <RawJSONDisplay
            jsonData={mcpToolExamples.taskManagement.create}
            title="Create Task Example"
            fileName="create-task.json"
          />
        </div>

        <div>
          <h4 className="text-lg font-semibold mb-3">Agent Coordination (32 Specialized Agents)</h4>
          <div className="mb-4">
            <p className="text-gray-600 dark:text-gray-300 mb-4">
              4genthub provides 32 specialized agents organized into categories:
            </p>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[
                { category: "Development & Coding", count: 4, color: "blue", agents: ["coding-agent", "debugger-agent", "code-reviewer-agent", "prototyping-agent"] },
                { category: "Testing & QA", count: 3, color: "green", agents: ["test-orchestrator-agent", "uat-coordinator-agent", "performance-load-tester-agent"] },
                { category: "Architecture & Design", count: 4, color: "purple", agents: ["system-architect-agent", "design-system-agent", "shadcn-ui-expert-agent", "core-concept-agent"] },
                { category: "Project & Planning", count: 4, color: "orange", agents: ["project-initiator-agent", "task-planning-agent", "master-orchestrator-agent", "elicitation-agent"] },
                { category: "Security & Compliance", count: 3, color: "red", agents: ["security-auditor-agent", "compliance-scope-agent", "ethical-review-agent"] },
                { category: "Research & Analysis", count: 4, color: "teal", agents: ["deep-research-agent", "llm-ai-agents-research", "root-cause-analysis-agent", "technology-advisor-agent"] }
              ].map(cat => (
                <Card key={cat.category} className={`p-3 bg-${cat.color}-50 dark:bg-${cat.color}-950 border-${cat.color}-200 dark:border-${cat.color}-800`}>
                  <h5 className={`font-semibold text-${cat.color}-900 dark:text-${cat.color}-100 text-sm mb-2`}>
                    {cat.category} ({cat.count})
                  </h5>
                  <div className="space-y-1">
                    {cat.agents.slice(0, 2).map(agent => (
                      <div key={agent} className={`text-xs text-${cat.color}-800 dark:text-${cat.color}-200 font-mono`}>
                        {agent}
                      </div>
                    ))}
                    {cat.agents.length > 2 && (
                      <div className={`text-xs text-${cat.color}-600 dark:text-${cat.color}-400`}>
                        +{cat.agents.length - 2} more
                      </div>
                    )}
                  </div>
                </Card>
              ))}
            </div>
          </div>

          <div>
            <h5 className="text-md font-semibold mb-3">Calling an Agent</h5>
            <RawJSONDisplay
              jsonData={mcpToolExamples.agentManagement.callAgent}
              title="Call Agent Example"
              fileName="call-agent.json"
            />
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

          <RawJSONDisplay
            jsonData={mcpToolExamples.contextManagement.create}
            title="Create Context Example"
            fileName="create-context.json"
          />
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
              <li>Call the appropriate agent for the task type</li>
              <li>Agent receives task_id and accesses full context</li>
              <li>Agent completes work and updates task status</li>
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
