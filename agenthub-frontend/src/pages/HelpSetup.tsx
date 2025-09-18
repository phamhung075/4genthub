import {
  AlertTriangle,
  ArrowLeft,
  Book,
  CheckCircle,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  Code,
  Copy,
  Cpu,
  ExternalLink,
  FileText,
  Github,
  Globe,
  HardDrive,
  HelpCircle,
  Key,
  Lightbulb,
  MessageSquare,
  Monitor,
  Play,
  Search,
  Server,
  Settings,
  Shield,
  Terminal,
  Wrench,
  Zap
} from 'lucide-react';
import React, { useState } from 'react';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import RawJSONDisplay from '../components/ui/RawJSONDisplay';

interface HelpSectionProps {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  content: React.ReactNode;
  isExpanded?: boolean;
  onToggle?: () => void;
}

const HelpSection: React.FC<HelpSectionProps> = ({
  title,
  description,
  icon,
  content,
  isExpanded = false,
  onToggle
}) => (
  <Card className="mb-6">
    <CardHeader className="cursor-pointer" onClick={onToggle}>
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          {icon}
          <div>
            <CardTitle className="text-xl">{title}</CardTitle>
            <CardDescription>{description}</CardDescription>
          </div>
        </div>
        <Button variant="ghost" size="sm">
          {isExpanded ? (
            <ChevronUp className="h-4 w-4" />
          ) : (
            <ChevronDown className="h-4 w-4" />
          )}
        </Button>
      </div>
    </CardHeader>
    {isExpanded && (
      <CardContent>
        {content}
      </CardContent>
    )}
  </Card>
);

interface CommandBoxProps {
  command: string;
  title?: string;
  description?: string;
}

const CommandBox: React.FC<CommandBoxProps> = ({ command, title, description }) => {
  const [copied, setCopied] = useState(false);

  const copyToClipboard = () => {
    navigator.clipboard.writeText(command);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm">
      {title && (
        <div className="text-green-400 mb-2 font-sans font-medium">{title}</div>
      )}
      {description && (
        <div className="text-gray-400 mb-3 font-sans text-xs">{description}</div>
      )}
      <div className="flex items-center justify-between">
        <code className="flex-1">{command}</code>
        <Button
          size="sm"
          variant="ghost"
          className="text-gray-300 hover:text-white ml-2"
          onClick={copyToClipboard}
        >
          {copied ? (
            <CheckCircle className="h-4 w-4" />
          ) : (
            <Copy className="h-4 w-4" />
          )}
        </Button>
      </div>
    </div>
  );
};

export const HelpSetup: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [activeSection, setActiveSection] = useState<string | null>(null);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    'what-is-4genthub': true
  });

  const toggleSection = (sectionId: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [sectionId]: !prev[sectionId]
    }));
  };

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
                "@heilgar/shadcn-ui-mcp-server"
            ]
        },
        "browsermcp": {
            "command": "npx",
            "args": [
                "@browsermcp/mcp@latest"
            ]
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

  const helpSections: HelpSectionProps[] = [
    {
      id: 'what-is-4genthub',
      title: 'What is 4genthub MCP?',
      description: 'Overview of 4genthub as enterprise MCP platform with community links',
      icon: <Book className="h-6 w-6 text-blue-500" />,
      content: (
        <div className="space-y-6">
          <p className="text-base leading-relaxed">
            4genthub is a revolutionary enterprise MCP (Model Context Protocol) platform that enables seamless
            collaboration between AI agents and developers. It provides a structured way to manage tasks, contexts,
            and agent interactions in software development projects with 42+ specialized agents.
          </p>

          {/* Community Links as Prominent Cards */}
          <div className="grid md:grid-cols-2 gap-4">
            <Card className="p-4 bg-gradient-to-br from-gray-900 to-gray-800 text-white border-gray-700 hover:border-gray-600 transition-colors">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <Github className="h-8 w-8" />
                  <div>
                    <h4 className="font-bold text-lg">GitHub Repository</h4>
                    <p className="text-gray-300 text-sm">Open source codebase and contributions</p>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-white hover:text-gray-200"
                  onClick={() => window.open('https://github.com/phamhung075/4genthub', '_blank')}
                >
                  <ExternalLink className="h-4 w-4" />
                </Button>
              </div>
            </Card>

            <Card className="p-4 bg-gradient-to-br from-indigo-600 to-purple-700 text-white border-indigo-500 hover:border-indigo-400 transition-colors">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <MessageSquare className="h-8 w-8" />
                  <div>
                    <h4 className="font-bold text-lg">Discord Community</h4>
                    <p className="text-indigo-100 text-sm">Join our developer community</p>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-white hover:text-indigo-100"
                  onClick={() => window.open('https://discord.gg/zmhMpK6N', '_blank')}
                >
                  <ExternalLink className="h-4 w-4" />
                </Button>
              </div>
            </Card>
          </div>

          {/* Key Features and Benefits */}
          <div className="grid md:grid-cols-2 gap-4 mt-6">
            <Card className="p-4 bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800">
              <h4 className="font-semibold text-blue-900 dark:text-blue-100 flex items-center mb-2">
                <Zap className="h-4 w-4 mr-2" />
                Key Features
              </h4>
              <ul className="text-sm text-blue-800 dark:text-blue-200 space-y-1">
                <li>• 42+ specialized AI agents</li>
                <li>• Intelligent task management</li>
                <li>• 4-tier context hierarchy</li>
                <li>• Enterprise orchestration</li>
                <li>• Vision System capabilities</li>
              </ul>
            </Card>
            <Card className="p-4 bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800">
              <h4 className="font-semibold text-green-900 dark:text-green-100 flex items-center mb-2">
                <CheckCircle className="h-4 w-4 mr-2" />
                Benefits
              </h4>
              <ul className="text-sm text-green-800 dark:text-green-200 space-y-1">
                <li>• Accelerated development</li>
                <li>• Improved code quality</li>
                <li>• Parallel agent coordination</li>
                <li>• Enhanced documentation</li>
                <li>• Real-time collaboration</li>
              </ul>
            </Card>
          </div>
        </div>
      ),
      isExpanded: expandedSections['what-is-4genthub'],
      onToggle: () => toggleSection('what-is-4genthub')
    },
    {
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
    },
    {
      id: 'getting-started',
      title: 'Getting Started Guide',
      description: 'Quick start guide for 4genthub with basic .mcp.json configuration',
      icon: <Play className="h-6 w-6 text-green-500" />,
      content: (
        <div className="space-y-6">
          <div>
            <h4 className="text-lg font-semibold mb-3">Quick Start Steps</h4>
            <div className="space-y-4">
              <Card className="p-4 border-l-4 border-blue-500 bg-blue-50 dark:bg-blue-950">
                <h5 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">Step 1: Clone Repository</h5>
                <CommandBox
                  command="git clone https://github.com/phamhung075/4genthub && cd 4genthub"
                  title="Get 4genthub Source Code"
                  description="Download the complete 4genthub platform"
                />
              </Card>

              <Card className="p-4 border-l-4 border-green-500 bg-green-50 dark:bg-green-950">
                <h5 className="font-semibold text-green-900 dark:text-green-100 mb-2">Step 2: Setup Environment</h5>
                <CommandBox
                  command="cp .env.example .env.dev"
                  title="Create Environment File"
                  description="Configure your local development environment"
                />
              </Card>

              <Card className="p-4 border-l-4 border-purple-500 bg-purple-50 dark:bg-purple-950">
                <h5 className="font-semibold text-purple-900 dark:text-purple-100 mb-2">Step 3: Start Services</h5>
                <CommandBox
                  command="cd docker-system && ./docker-menu.sh"
                  title="Launch Docker Menu"
                  description="Use option B (Database) then option 1 (Backend + Frontend)"
                />
              </Card>

              <Card className="p-4 border-l-4 border-orange-500 bg-orange-50 dark:bg-orange-950">
                <h5 className="font-semibold text-orange-900 dark:text-orange-100 mb-2">Step 4: Configure MCP Client</h5>
                <p className="text-sm text-orange-800 dark:text-orange-200 mb-2">
                  Update your Claude Desktop configuration:
                </p>
                <div className="bg-orange-100 dark:bg-orange-900 p-2 rounded text-sm font-mono">
                  ~/.config/claude/claude_desktop_config.json
                </div>
              </Card>
            </div>
          </div>

          <div>
            <h4 className="text-lg font-semibold mb-3">Verify Your Setup</h4>
            <div className="space-y-3">
              <CommandBox
                command="curl http://localhost:8000/health"
                title="Test Backend Health"
                description='Should return: {"status": "healthy"}'
              />

              <div className="bg-green-50 dark:bg-green-950 p-4 rounded-lg border border-green-200 dark:border-green-800">
                <h5 className="font-semibold text-green-900 dark:text-green-100 mb-2">Service URLs:</h5>
                <div className="text-sm text-green-800 dark:text-green-200 space-y-1">
                  <div>• <strong>Frontend:</strong> http://localhost:3800</div>
                  <div>• <strong>Backend:</strong> http://localhost:8000</div>
                  <div>• <strong>API Docs:</strong> http://localhost:8000/docs</div>
                  <div>• <strong>pgAdmin:</strong> http://localhost:5050 (if enabled)</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      ),
      isExpanded: expandedSections['getting-started'],
      onToggle: () => toggleSection('getting-started')
    },
    {
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
            <h4 className="text-lg font-semibold mb-3">Agent Coordination (42 Specialized Agents)</h4>
            <div className="mb-4">
              <p className="text-gray-600 dark:text-gray-300 mb-4">
                4genthub provides 42 specialized agents organized into categories:
              </p>

              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {[
                  { category: "Development & Coding", count: 4, color: "blue", agents: ["coding-agent", "debugger-agent", "code-reviewer-agent", "prototyping-agent"] },
                  { category: "Testing & QA", count: 3, color: "green", agents: ["test-orchestrator-agent", "uat-coordinator-agent", "performance-load-tester-agent"] },
                  { category: "Architecture & Design", count: 4, color: "purple", agents: ["system-architect-agent", "design-system-agent", "ui-specialist-agent", "core-concept-agent"] },
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
    },
    {
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
                  🔄 For Development:
                </h5>
                <ol className="text-sm text-blue-800 dark:text-blue-200 space-y-1 list-decimal list-inside">
                  <li>Use option <strong>D</strong> for non-Docker development mode</li>
                  <li>Use option <strong>R</strong> to restart and apply code changes</li>
                  <li>Use option <strong>M</strong> to monitor performance</li>
                </ol>
              </Card>
            </div>
          </div>
        </div>
      ),
      isExpanded: expandedSections['docker-setup'],
      onToggle: () => toggleSection('docker-setup')
    },
    {
      id: 'troubleshooting',
      title: 'Troubleshooting',
      description: 'Common issues and solutions for MCP, authentication, and setup problems',
      icon: <AlertTriangle className="h-6 w-6 text-red-500" />,
      content: (
        <div className="space-y-6">
          <div className="grid gap-4">
            <h4 className="text-lg font-semibold">Connection & Setup Issues</h4>
            {[
              {
                issue: "MCP server connection failed",
                solution: "Check .mcp.json path and ensure server is running on correct port (8000). Verify PYTHONPATH is set correctly.",
                type: "error"
              },
              {
                issue: "Port already in use errors",
                solution: "Run docker-menu.sh option 5 to stop all services, then restart. Check if other services are using ports 8000 or 3800.",
                type: "warning"
              },
              {
                issue: "Task creation fails with validation error",
                solution: "Ensure all required fields are provided: action, title, assignees, and git_branch_id",
                type: "error"
              },
              {
                issue: "Agent call returns 'agent not found'",
                solution: "Check agent name spelling - use exact names like 'coding-agent' (no @ prefix needed)",
                type: "warning"
              },
              {
                issue: "Database connection refused",
                solution: "Ensure PostgreSQL container is running (docker-menu.sh option B first). Check DATABASE_URL in .env.dev",
                type: "error"
              },
              {
                issue: "Frontend shows API connection error",
                solution: "Check VITE_API_URL in .env.dev matches backend port (8000). Verify backend health at /health endpoint",
                type: "info"
              },
              {
                issue: "Context data not inherited properly",
                solution: "Use include_inherited: true when resolving context to access parent data",
                type: "info"
              },
              {
                issue: "Authentication not working",
                solution: "Verify AUTH_ENABLED=true and AGENTHUB_MVP_MODE=true in development. Check Keycloak configuration if using full auth",
                type: "warning"
              }
            ].map((item, index) => (
              <Card key={index} className={`p-4 border-l-4 ${
                item.type === 'error' ? 'border-red-500 bg-red-50 dark:bg-red-950' :
                item.type === 'warning' ? 'border-amber-500 bg-amber-50 dark:bg-amber-950' :
                'border-blue-500 bg-blue-50 dark:bg-blue-950'
              }`}>
                <h5 className="font-semibold mb-2 flex items-center">
                  {item.type === 'error' && <AlertTriangle className="h-4 w-4 mr-2 text-red-500" />}
                  {item.type === 'warning' && <AlertTriangle className="h-4 w-4 mr-2 text-amber-500" />}
                  {item.type === 'info' && <Lightbulb className="h-4 w-4 mr-2 text-blue-500" />}
                  {item.issue}
                </h5>
                <p className="text-sm">{item.solution}</p>
              </Card>
            ))}
          </div>

          <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg">
            <h5 className="font-semibold mb-3 flex items-center">
              <MessageSquare className="h-4 w-4 mr-2" />
              Getting Help
            </h5>
            <div className="space-y-2 text-sm">
              <p>• Check the health endpoints: backend (/health) and database connection</p>
              <p>• Review logs using docker-menu.sh option 6 or log files in development mode</p>
              <p>• Verify environment variables in .env.dev match your setup</p>
              <p>• Use include_context: true for detailed task and context information</p>
              <p>• Join our Discord community for support: https://discord.gg/zmhMpK6N</p>
            </div>
          </div>
        </div>
      ),
      isExpanded: expandedSections['troubleshooting'],
      onToggle: () => toggleSection('troubleshooting')
    },
    {
      id: 'local-development-setup',
      title: 'Local Development Setup',
      description: 'Complete guide to setting up 4genthub locally for development with Docker, database, and MCP tools',
      icon: <HardDrive className="h-6 w-6 text-green-500" />,
      content: (
        <div className="space-y-6">
          {/* Prerequisites Section */}
          <div>
            <h4 className="text-lg font-semibold mb-3">Prerequisites</h4>
            <p className="text-gray-600 dark:text-gray-300 mb-4">
              Essential software required for local development:
            </p>
            <div className="grid md:grid-cols-2 gap-6">
              <Card className="p-4 bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800">
                <h5 className="font-semibold text-blue-900 dark:text-blue-100 flex items-center mb-3">
                  <Server className="h-4 w-4 mr-2" />
                  Docker & Container Platform
                </h5>
                <ul className="text-sm text-blue-800 dark:text-blue-200 space-y-2">
                  <li>• <strong>Docker Desktop</strong> (Windows/Mac) or Docker Engine (Linux)</li>
                  <li>• <strong>Docker Compose</strong> v2.0+ (included with Desktop)</li>
                  <li>• <strong>Minimum:</strong> 8GB RAM, 20GB free disk space</li>
                  <li>• <strong>Recommended:</strong> 16GB RAM, 50GB free disk</li>
                </ul>
                <div className="mt-3">
                  <Button size="sm" variant="outline" className="text-xs">
                    <ExternalLink className="h-3 w-3 mr-1" />
                    Download Docker
                  </Button>
                </div>
              </Card>

              <Card className="p-4 bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800">
                <h5 className="font-semibold text-green-900 dark:text-green-100 flex items-center mb-3">
                  <Code className="h-4 w-4 mr-2" />
                  Development Tools
                </h5>
                <ul className="text-sm text-green-800 dark:text-green-200 space-y-2">
                  <li>• <strong>Python 3.12+</strong> with pip and venv</li>
                  <li>• <strong>Node.js 18+</strong> with npm or yarn</li>
                  <li>• <strong>Git</strong> for version control</li>
                  <li>• <strong>Optional:</strong> uv (Python package manager)</li>
                </ul>
              </Card>
            </div>

            <div className="bg-yellow-50 dark:bg-yellow-950 p-4 rounded-lg border border-yellow-200 dark:border-yellow-800 mt-4">
              <h5 className="font-semibold text-yellow-900 dark:text-yellow-100 flex items-center mb-2">
                <Lightbulb className="h-4 w-4 mr-2" />
                System Requirements
              </h5>
              <div className="grid md:grid-cols-3 gap-4 text-sm text-yellow-800 dark:text-yellow-200">
                <div>
                  <strong>Minimum:</strong>
                  <ul className="mt-1 space-y-1">
                    <li>• 8GB RAM</li>
                    <li>• 4 CPU cores</li>
                    <li>• 20GB disk space</li>
                  </ul>
                </div>
                <div>
                  <strong>Recommended:</strong>
                  <ul className="mt-1 space-y-1">
                    <li>• 16GB RAM</li>
                    <li>• 8 CPU cores</li>
                    <li>• 50GB+ SSD</li>
                  </ul>
                </div>
                <div>
                  <strong>Supported OS:</strong>
                  <ul className="mt-1 space-y-1">
                    <li>• Windows 10/11</li>
                    <li>• macOS 10.15+</li>
                    <li>• Linux (Ubuntu 20.04+)</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>

          {/* Clone and Initial Setup */}
          <div>
            <h4 className="text-lg font-semibold mb-3">Clone and Initial Setup</h4>
            <div className="space-y-4">
              <div>
                <h5 className="text-md font-semibold mb-3">1. Clone Repository</h5>
                <CommandBox
                  command="git clone https://github.com/phamhung075/4genthub"
                  title="Clone 4genthub Repository"
                  description="Download the complete source code from GitHub"
                />
                <div className="mt-2">
                  <CommandBox
                    command="cd 4genthub"
                    title="Navigate to Project Directory"
                  />
                </div>
              </div>

              <div>
                <h5 className="text-md font-semibold mb-3">2. Project Structure Overview</h5>
                <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg font-mono text-sm">
                  <div className="space-y-1 text-gray-700 dark:text-gray-300">
                    <div>📁 4genthub/</div>
                    <div className="ml-4">├── 📁 agenthub-frontend/ <span className="text-blue-500"># React/TypeScript UI</span></div>
                    <div className="ml-4">├── 📁 agenthub_main/ <span className="text-green-500"># Python backend</span></div>
                    <div className="ml-4">├── 📁 docker-system/ <span className="text-orange-500"># Docker configurations</span></div>
                    <div className="ml-4">├── 📁 ai_docs/ <span className="text-purple-500"># Documentation</span></div>
                    <div className="ml-4">├── 🗄️ .env.dev <span className="text-red-500"># Development environment</span></div>
                    <div className="ml-4">└── 📜 README.md</div>
                  </div>
                </div>
              </div>

              <div>
                <h5 className="text-md font-semibold mb-3">3. Environment Configuration</h5>
                <p className="text-gray-600 dark:text-gray-300 mb-4">
                  Create and configure your environment variables for local development:
                </p>
                <CommandBox
                  command="cp .env.example .env.dev"
                  title="Create Environment File"
                  description="Copy example environment to development config"
                />

                <div className="mt-4">
                  <RawJSONDisplay
                    jsonData={envExampleData}
                    title="Essential Environment Variables (.env.dev)"
                    fileName=".env.dev"
                  />
                </div>
              </div>

              <div className="bg-amber-50 dark:bg-amber-950 p-4 rounded-lg border border-amber-200 dark:border-amber-800">
                <h5 className="font-semibold text-amber-900 dark:text-amber-100 flex items-center mb-2">
                  <Shield className="h-4 w-4 mr-2" />
                  Important Security Notes
                </h5>
                <ul className="text-sm text-amber-800 dark:text-amber-200 space-y-1">
                  <li>• Never commit .env.dev or .env files to version control</li>
                  <li>• Change default passwords in production</li>
                  <li>• Use strong, unique passwords for database access</li>
                  <li>• Keep Keycloak credentials secure</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Using docker-menu.sh */}
          <div>
            <h4 className="text-lg font-semibold mb-3">Using docker-menu.sh</h4>
            <p className="text-gray-600 dark:text-gray-300 mb-4">
              Interactive Docker management system with multiple configurations:
            </p>

            <div>
              <h5 className="text-md font-semibold mb-3">Starting the Docker Menu</h5>
              <CommandBox
                command="cd docker-system && ./docker-menu.sh"
                title="Launch Docker Management Menu"
                description="Interactive menu system for all Docker operations"
              />
            </div>

            <div className="mt-6">
              <h5 className="text-md font-semibold mb-3">Available Menu Options</h5>
              <div className="grid gap-3">
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

                <details className="mt-4">
                  <summary className="cursor-pointer font-medium text-gray-700 dark:text-gray-300 mb-3">
                    Show All Menu Options ({dockerMenuOptions.length} total)
                  </summary>
                  <div className="grid gap-2 mt-3">
                    {dockerMenuOptions.slice(3).map((option) => (
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

            <div className="mt-6">
              <h5 className="text-md font-semibold mb-3">Recommended Workflow</h5>
              <div className="space-y-3">
                <Card className="p-4 bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800">
                  <h6 className="font-semibold text-green-900 dark:text-green-100 mb-2">
                    🥇 For First-Time Setup:
                  </h6>
                  <ol className="text-sm text-green-800 dark:text-green-200 space-y-1 list-decimal list-inside">
                    <li>Run option <strong>B</strong> to start PostgreSQL database</li>
                    <li>Run option <strong>1</strong> to start Backend + Frontend</li>
                    <li>Access at http://localhost:3800 (Frontend) and http://localhost:8000 (Backend)</li>
                  </ol>
                </Card>

                <Card className="p-4 bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800">
                  <h6 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">
                    🔄 For Development:
                  </h6>
                  <ol className="text-sm text-blue-800 dark:text-blue-200 space-y-1 list-decimal list-inside">
                    <li>Use option <strong>D</strong> for non-Docker development mode</li>
                    <li>Use option <strong>R</strong> to restart and apply code changes</li>
                    <li>Use option <strong>M</strong> to monitor performance</li>
                  </ol>
                </Card>
              </div>
            </div>
          </div>

          {/* Database Configuration */}
          <div>
            <h4 className="text-lg font-semibold mb-3">Database Configuration</h4>
            <p className="text-gray-600 dark:text-gray-300 mb-4">
              PostgreSQL setup for local development and production:
            </p>

            <div className="grid md:grid-cols-2 gap-4 mb-6">
              <Card className="p-4 bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800">
                <h5 className="font-semibold text-blue-900 dark:text-blue-100 flex items-center mb-2">
                  <HardDrive className="h-4 w-4 mr-2" />
                  Local PostgreSQL (Recommended)
                </h5>
                <ul className="text-sm text-blue-800 dark:text-blue-200 space-y-1">
                  <li>• Full control and privacy</li>
                  <li>• No internet dependency</li>
                  <li>• Fast local connections</li>
                  <li>• Use docker-menu.sh option B</li>
                </ul>
              </Card>

              <Card className="p-4 bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800">
                <h5 className="font-semibold text-green-900 dark:text-green-100 flex items-center mb-2">
                  <Globe className="h-4 w-4 mr-2" />
                  Supabase Cloud
                </h5>
                <ul className="text-sm text-green-800 dark:text-green-200 space-y-1">
                  <li>• Managed cloud database</li>
                  <li>• Built-in authentication</li>
                  <li>• Real-time features</li>
                  <li>• Use docker-menu.sh option 2 or 3</li>
                </ul>
              </Card>
            </div>

            <div>
              <h5 className="text-md font-semibold mb-3">Local PostgreSQL Setup</h5>
              <div className="space-y-3">
                <CommandBox
                  command="cd docker-system && ./docker-menu.sh"
                  title="1. Start Docker Menu"
                />
                <CommandBox
                  command="B"
                  title="2. Select Option B - Database Only"
                  description="This starts PostgreSQL container on port 5432"
                />
              </div>

              <div className="mt-4 bg-gray-50 dark:bg-gray-900 p-4 rounded-lg">
                <h6 className="font-medium mb-2">Database Connection Details:</h6>
                <div className="font-mono text-sm space-y-1">
                  <div><strong>Host:</strong> localhost</div>
                  <div><strong>Port:</strong> 5432</div>
                  <div><strong>Database:</strong> agenthub_prod</div>
                  <div><strong>User:</strong> agenthub_user</div>
                  <div><strong>Password:</strong> (from .env.dev)</div>
                </div>
              </div>
            </div>

            <div className="mt-6">
              <h5 className="text-md font-semibold mb-3">Database Management UI</h5>
              <p className="text-gray-600 dark:text-gray-300 mb-3">
                Access pgAdmin web interface for database management:
              </p>
              <CommandBox
                command="C"
                title="Select Option C - pgAdmin UI Only"
                description="Starts pgAdmin at http://localhost:5050"
              />

              <div className="mt-3 bg-blue-50 dark:bg-blue-950 p-4 rounded-lg border border-blue-200 dark:border-blue-800">
                <h6 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">pgAdmin Login:</h6>
                <div className="text-sm text-blue-800 dark:text-blue-200 space-y-1">
                  <div><strong>URL:</strong> http://localhost:5050</div>
                  <div><strong>Email:</strong> admin@example.com</div>
                  <div><strong>Password:</strong> admin123</div>
                </div>
              </div>
            </div>
          </div>

          {/* Frontend & Backend Setup */}
          <div>
            <h4 className="text-lg font-semibold mb-3">Frontend & Backend Setup</h4>
            <p className="text-gray-600 dark:text-gray-300 mb-4">
              React frontend and Python FastAPI backend configuration:
            </p>

            <div>
              <h5 className="text-md font-semibold mb-3">Backend Setup (Python FastAPI)</h5>
              <div className="space-y-3">
                <CommandBox
                  command="cd agenthub_main"
                  title="1. Navigate to Backend Directory"
                />

                <div className="bg-yellow-50 dark:bg-yellow-950 p-3 rounded-lg border border-yellow-200 dark:border-yellow-800">
                  <p className="text-sm text-yellow-800 dark:text-yellow-200">
                    <strong>Optional:</strong> Use uv (faster Python package manager)
                  </p>
                  <CommandBox
                    command="pip install uv && uv venv && source .venv/bin/activate"
                    title="Create Virtual Environment with uv"
                  />
                </div>

                <CommandBox
                  command="pip install -e ."
                  title="2. Install Dependencies"
                  description="Installs all required Python packages from pyproject.toml"
                />
              </div>
            </div>

            <div className="mt-6">
              <h5 className="text-md font-semibold mb-3">Frontend Setup (React/TypeScript)</h5>
              <div className="space-y-3">
                <CommandBox
                  command="cd agenthub-frontend"
                  title="1. Navigate to Frontend Directory"
                />
                <CommandBox
                  command="npm install"
                  title="2. Install Dependencies"
                  description="Installs all Node.js packages from package.json"
                />
              </div>
            </div>

            <div className="mt-6">
              <h5 className="text-md font-semibold mb-3">Development Server Options</h5>
              <div className="grid md:grid-cols-2 gap-4">
                <Card className="p-4 bg-purple-50 dark:bg-purple-950 border-purple-200 dark:border-purple-800">
                  <h6 className="font-semibold text-purple-900 dark:text-purple-100 flex items-center mb-3">
                    <Play className="h-4 w-4 mr-2" />
                    Docker Mode (Recommended)
                  </h6>
                  <div className="space-y-2 text-sm text-purple-800 dark:text-purple-200">
                    <p>• Consistent environment across systems</p>
                    <p>• Easy container management</p>
                    <p>• Production-like setup</p>
                  </div>
                  <CommandBox
                    command="./docker-menu.sh → Option 1"
                    title="Start with Docker"
                  />
                </Card>

                <Card className="p-4 bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800">
                  <h6 className="font-semibold text-green-900 dark:text-green-100 flex items-center mb-3">
                    <Cpu className="h-4 w-4 mr-2" />
                    Development Mode
                  </h6>
                  <div className="space-y-2 text-sm text-green-800 dark:text-green-200">
                    <p>• Hot reload for faster development</p>
                    <p>• Native debugging support</p>
                    <p>• Direct file system access</p>
                  </div>
                  <CommandBox
                    command="./docker-menu.sh → Option D"
                    title="Start Development Mode"
                  />
                </Card>
              </div>
            </div>

            <div className="mt-6">
              <h5 className="text-md font-semibold mb-3">Service URLs</h5>
              <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg">
                <div className="grid md:grid-cols-2 gap-4 text-sm">
                  <div>
                    <h6 className="font-semibold text-blue-600 dark:text-blue-400 mb-2">Frontend (React)</h6>
                    <div className="space-y-1">
                      <div><strong>URL:</strong> http://localhost:3800</div>
                      <div><strong>Technology:</strong> React + TypeScript + Vite</div>
                      <div><strong>Features:</strong> Hot Module Reload, Tailwind CSS</div>
                    </div>
                  </div>
                  <div>
                    <h6 className="font-semibold text-green-600 dark:text-green-400 mb-2">Backend (FastAPI)</h6>
                    <div className="space-y-1">
                      <div><strong>URL:</strong> http://localhost:8000</div>
                      <div><strong>API Docs:</strong> http://localhost:8000/docs</div>
                      <div><strong>Technology:</strong> Python + FastAPI + FastMCP</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Keycloak Authentication */}
          <div>
            <h4 className="text-lg font-semibold mb-3">Keycloak Authentication</h4>
            <p className="text-gray-600 dark:text-gray-300 mb-4">
              Configure JWT-based authentication with Keycloak:
            </p>

            <div>
              <h5 className="text-md font-semibold mb-3">Authentication Architecture</h5>
              <div className="bg-blue-50 dark:bg-blue-950 p-4 rounded-lg border border-blue-200 dark:border-blue-800">
                <p className="text-sm text-blue-800 dark:text-blue-200 mb-3">
                  4genthub uses Keycloak as the source of truth for user authentication, supporting both traditional login and JWT token-based access.
                </p>
                <div className="space-y-2 text-sm text-blue-800 dark:text-blue-200">
                  <div>• <strong>Keycloak:</strong> Identity and access management</div>
                  <div>• <strong>JWT Tokens:</strong> Secure API authentication</div>
                  <div>• <strong>Dual Auth:</strong> Web UI and API token support</div>
                  <div>• <strong>Auto-verification:</strong> Email verification bypassed in dev</div>
                </div>
              </div>
            </div>

            <div className="mt-6">
              <h5 className="text-md font-semibold mb-3">Local Development Authentication</h5>
              <div className="bg-green-50 dark:bg-green-950 p-4 rounded-lg border border-green-200 dark:border-green-800">
                <h6 className="font-semibold text-green-900 dark:text-green-100 mb-2">
                  MVP Mode (Development)
                </h6>
                <p className="text-sm text-green-800 dark:text-green-200 mb-3">
                  For local development, authentication can be bypassed using MVP mode:
                </p>
                <div className="space-y-2 text-sm font-mono bg-green-100 dark:bg-green-900 p-2 rounded">
                  <div>AGENTHUB_MVP_MODE=true</div>
                  <div>AUTH_ENABLED=true</div>
                  <div>EMAIL_VERIFIED_AUTO=true</div>
                </div>
              </div>
            </div>

            <div className="mt-6">
              <h5 className="text-md font-semibold mb-3">Keycloak Configuration</h5>
              <p className="text-gray-600 dark:text-gray-300 mb-4">
                For production or full authentication testing, configure these Keycloak variables in your .env.dev:
              </p>

              <RawJSONDisplay
                jsonData={{
                  KEYCLOAK_URL: "https://your-keycloak-server.com",
                  KEYCLOAK_REALM: "agenthub",
                  KEYCLOAK_CLIENT_ID: "agenthub-client",
                  KEYCLOAK_CLIENT_SECRET: "your-client-secret",
                  KEYCLOAK_REDIRECT_URI: "http://localhost:3800/auth/callback"
                }}
                title="Keycloak Configuration Variables"
                fileName="keycloak-config.json"
              />
            </div>

            <div className="mt-6">
              <h5 className="text-md font-semibold mb-3">Testing Authentication</h5>
              <div className="space-y-3">
                <Card className="p-4 bg-yellow-50 dark:bg-yellow-950 border-yellow-200 dark:border-yellow-800">
                  <h6 className="font-semibold text-yellow-900 dark:text-yellow-100 flex items-center mb-2">
                    <Key className="h-4 w-4 mr-2" />
                    Testing User Registration
                  </h6>
                  <ol className="text-sm text-yellow-800 dark:text-yellow-200 space-y-1 list-decimal list-inside">
                    <li>Navigate to http://localhost:3800/signup</li>
                    <li>Create a new account (email verification auto-bypassed in dev)</li>
                    <li>Login with your credentials</li>
                    <li>Access protected routes like /dashboard</li>
                  </ol>
                </Card>

                <Card className="p-4 bg-purple-50 dark:bg-purple-950 border-purple-200 dark:border-purple-800">
                  <h6 className="font-semibold text-purple-900 dark:text-purple-100 flex items-center mb-2">
                    <Terminal className="h-4 w-4 mr-2" />
                    API Token Access
                  </h6>
                  <ol className="text-sm text-purple-800 dark:text-purple-200 space-y-1 list-decimal list-inside">
                    <li>Visit /tokens page to generate API tokens</li>
                    <li>Use tokens in Authorization header for API calls</li>
                    <li>Test with: <code>curl -H "Authorization: Bearer your-token" http://localhost:8000/api/projects</code></li>
                  </ol>
                </Card>
              </div>
            </div>
          </div>

          {/* Verification & Testing */}
          <div>
            <h4 className="text-lg font-semibold mb-3">Verification & Testing</h4>
            <p className="text-gray-600 dark:text-gray-300 mb-4">
              Verify your local setup is working correctly:
            </p>

            <div>
              <h5 className="text-md font-semibold mb-3">Health Check Endpoints</h5>
              <div className="space-y-3">
                <Card className="p-4 bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800">
                  <h6 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">Backend Health</h6>
                  <CommandBox
                    command="curl http://localhost:8000/health"
                    title="Test Backend API"
                  />
                  <div className="mt-2 text-sm text-blue-800 dark:text-blue-200">
                    Expected: <code>{"{"}"status": "healthy"{"}"}</code>
                  </div>
                </Card>

                <Card className="p-4 bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800">
                  <h6 className="font-semibold text-green-900 dark:text-green-100 mb-2">Frontend Access</h6>
                  <div className="text-sm text-green-800 dark:text-green-200 space-y-1">
                    <div>• Visit: <a href="http://localhost:3800" className="underline">http://localhost:3800</a></div>
                    <div>• Should load the 4genthub dashboard</div>
                    <div>• Navigation and authentication should work</div>
                  </div>
                </Card>

                <Card className="p-4 bg-purple-50 dark:bg-purple-950 border-purple-200 dark:border-purple-800">
                  <h6 className="font-semibold text-purple-900 dark:text-purple-100 mb-2">Database Connection</h6>
                  <CommandBox
                    command="docker exec agenthub-postgres pg_isready -U agenthub_user"
                    title="Test Database Connection"
                  />
                  <div className="mt-2 text-sm text-purple-800 dark:text-purple-200">
                    Expected: <code>accepting connections</code>
                  </div>
                </Card>
              </div>
            </div>

            <div className="mt-6">
              <h5 className="text-md font-semibold mb-3">Feature Testing Checklist</h5>
              <div className="space-y-2">
                {[
                  "✅ Backend API responds to /health endpoint",
                  "✅ Frontend loads at http://localhost:3800",
                  "✅ Database accepts connections",
                  "✅ User registration and login work",
                  "✅ Protected routes redirect to login",
                  "✅ MCP tools are accessible",
                  "✅ Task creation and management function",
                  "✅ Agent calling works via MCP",
                  "✅ API documentation available at /docs"
                ].map((item, index) => (
                  <div key={index} className="flex items-center space-x-2 p-2 bg-gray-50 dark:bg-gray-900 rounded">
                    <span className="text-sm">{item}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-6">
              <h5 className="text-md font-semibold mb-3">Running Test Suites</h5>
              <div className="space-y-3">
                <CommandBox
                  command="cd agenthub_main && python -m pytest src/tests/"
                  title="Run Backend Tests"
                  description="Execute Python test suite"
                />
                <CommandBox
                  command="cd agenthub-frontend && npm test"
                  title="Run Frontend Tests"
                  description="Execute React component tests"
                />
              </div>
            </div>

            <div className="mt-6">
              <h5 className="text-md font-semibold mb-3">Troubleshooting Common Issues</h5>
              <div className="space-y-3">
                {[
                  {
                    issue: "Port already in use errors",
                    solution: "Run docker-menu.sh option 5 to stop all services, then restart",
                    type: "error"
                  },
                  {
                    issue: "Database connection refused",
                    solution: "Ensure PostgreSQL container is running (docker-menu.sh option B first)",
                    type: "warning"
                  },
                  {
                    issue: "Frontend shows API connection error",
                    solution: "Check VITE_API_URL in .env.dev matches backend port (8000)",
                    type: "info"
                  },
                  {
                    issue: "Authentication not working",
                    solution: "Verify AUTH_ENABLED=true and AGENTHUB_MVP_MODE=true in development",
                    type: "warning"
                  }
                ].map((item, index) => (
                  <Card key={index} className={`p-4 border-l-4 ${
                    item.type === 'error' ? 'border-red-500 bg-red-50 dark:bg-red-950' :
                    item.type === 'warning' ? 'border-amber-500 bg-amber-50 dark:bg-amber-950' :
                    'border-blue-500 bg-blue-50 dark:bg-blue-950'
                  }`}>
                    <h6 className="font-semibold mb-2 flex items-center">
                      {item.type === 'error' && <AlertTriangle className="h-4 w-4 mr-2 text-red-500" />}
                      {item.type === 'warning' && <AlertTriangle className="h-4 w-4 mr-2 text-amber-500" />}
                      {item.type === 'info' && <Lightbulb className="h-4 w-4 mr-2 text-blue-500" />}
                      {item.issue}
                    </h6>
                    <p className="text-sm">{item.solution}</p>
                  </Card>
                ))}
              </div>
            </div>
          </div>

          {/* Development Workflow */}
          <div>
            <h4 className="text-lg font-semibold mb-3">Development Workflow</h4>
            <p className="text-gray-600 dark:text-gray-300 mb-4">
              Best practices for daily development with 4genthub:
            </p>

            <div className="grid md:grid-cols-2 gap-4 mb-6">
              <Card className="p-4 bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800">
                <h6 className="font-semibold text-green-900 dark:text-green-100 flex items-center mb-3">
                  <Play className="h-4 w-4 mr-2" />
                  Starting Your Day
                </h6>
                <ol className="text-sm text-green-800 dark:text-green-200 space-y-1 list-decimal list-inside">
                  <li>Start database: <code>./docker-menu.sh → B</code></li>
                  <li>Start dev mode: <code>./docker-menu.sh → D</code></li>
                  <li>Open frontend: http://localhost:3800</li>
                  <li>Check backend: http://localhost:8000/docs</li>
                </ol>
              </Card>

              <Card className="p-4 bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800">
                <h6 className="font-semibold text-blue-900 dark:text-blue-100 flex items-center mb-3">
                  <Wrench className="h-4 w-4 mr-2" />
                  Making Changes
                </h6>
                <ol className="text-sm text-blue-800 dark:text-blue-200 space-y-1 list-decimal list-inside">
                  <li>Edit code in your favorite editor</li>
                  <li>Frontend: Hot reload automatically</li>
                  <li>Backend: Restart with <code>R</code> option</li>
                  <li>Database: Changes persist in volumes</li>
                </ol>
              </Card>
            </div>

            <div>
              <h5 className="text-md font-semibold mb-3">Performance Optimization</h5>
              <div className="space-y-3">
                <Card className="p-4 bg-yellow-50 dark:bg-yellow-950 border-yellow-200 dark:border-yellow-800">
                  <h6 className="font-semibold text-yellow-900 dark:text-yellow-100 flex items-center mb-2">
                    <Monitor className="h-4 w-4 mr-2" />
                    Low-Resource Development
                  </h6>
                  <div className="text-sm text-yellow-800 dark:text-yellow-200 space-y-1">
                    <p>For systems with limited resources:</p>
                    <ul className="mt-2 space-y-1 list-disc list-inside">
                      <li>Use option <strong>P</strong> for optimized mode</li>
                      <li>Use option <strong>M</strong> to monitor performance</li>
                      <li>Close unnecessary browser tabs</li>
                      <li>Stop other Docker containers</li>
                    </ul>
                  </div>
                </Card>

                <Card className="p-4 bg-purple-50 dark:bg-purple-950 border-purple-200 dark:border-purple-800">
                  <h6 className="font-semibold text-purple-900 dark:text-purple-100 flex items-center mb-2">
                    <Zap className="h-4 w-4 mr-2" />
                    Performance Monitoring
                  </h6>
                  <CommandBox
                    command="./docker-menu.sh → M"
                    title="Launch Performance Monitor"
                    description="Live stats for containers, CPU, and memory usage"
                  />
                </Card>
              </div>
            </div>

            <div className="mt-6">
              <h5 className="text-md font-semibold mb-3">Log Management</h5>
              <div className="space-y-3">
                <CommandBox
                  command="./docker-menu.sh → 6"
                  title="View Application Logs"
                  description="Interactive log viewer for all services"
                />

                <div className="grid md:grid-cols-2 gap-3">
                  <div className="bg-gray-50 dark:bg-gray-900 p-3 rounded-lg">
                    <h6 className="font-medium mb-2">Development Mode Logs:</h6>
                    <div className="text-sm font-mono space-y-1">
                      <div>Backend: <code>tail -f logs/backend.log</code></div>
                      <div>Frontend: <code>tail -f logs/frontend.log</code></div>
                    </div>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-900 p-3 rounded-lg">
                    <h6 className="font-medium mb-2">Docker Mode Logs:</h6>
                    <div className="text-sm font-mono space-y-1">
                      <div>Backend: <code>docker logs agenthub-backend</code></div>
                      <div>Frontend: <code>docker logs agenthub-frontend</code></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-6">
              <h5 className="text-md font-semibold mb-3">Best Practices</h5>
              <div className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-950 dark:to-purple-950 p-4 rounded-lg border border-blue-200 dark:border-blue-800">
                <div className="grid md:grid-cols-2 gap-4 text-sm">
                  <div>
                    <h6 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">Development</h6>
                    <ul className="text-blue-800 dark:text-blue-200 space-y-1">
                      <li>• Use development mode for active coding</li>
                      <li>• Restart services after major changes</li>
                      <li>• Run tests before committing</li>
                      <li>• Monitor logs for errors</li>
                    </ul>
                  </div>
                  <div>
                    <h6 className="font-semibold text-purple-900 dark:text-purple-100 mb-2">Debugging</h6>
                    <ul className="text-purple-800 dark:text-purple-200 space-y-1">
                      <li>• Check health endpoints first</li>
                      <li>• Verify environment variables</li>
                      <li>• Use performance monitor for issues</li>
                      <li>• Clean Docker system if problems persist</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      ),
      isExpanded: expandedSections['local-development-setup'],
      onToggle: () => toggleSection('local-development-setup')
    },
    {
      id: 'advanced-features',
      title: 'Advanced Features',
      description: 'Vision System, Enterprise orchestration, and performance optimization',
      icon: <Zap className="h-6 w-6 text-yellow-500" />,
      content: (
        <div className="space-y-6">
          <div>
            <h4 className="text-lg font-semibold mb-3">Vision System Capabilities</h4>
            <div className="bg-purple-50 dark:bg-purple-950 p-4 rounded-lg border border-purple-200 dark:border-purple-800">
              <p className="text-sm text-purple-800 dark:text-purple-200 mb-3">
                4genthub's Vision System provides AI-enhanced insights, workflow guidance, and intelligent automation:
              </p>
              <div className="grid md:grid-cols-2 gap-4 text-sm text-purple-800 dark:text-purple-200">
                <div>
                  <strong>AI Enrichment:</strong>
                  <ul className="mt-1 space-y-1 list-disc list-inside">
                    <li>Task enrichment with context</li>
                    <li>Priority and effort estimation</li>
                    <li>Workflow hints and suggestions</li>
                    <li>Progress tracking automation</li>
                  </ul>
                </div>
                <div>
                  <strong>Intelligence Features:</strong>
                  <ul className="mt-1 space-y-1 list-disc list-inside">
                    <li>Blocker identification</li>
                    <li>Impact analysis</li>
                    <li>Milestone detection</li>
                    <li>Context updates automation</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>

          <div>
            <h4 className="text-lg font-semibold mb-3">Enterprise Orchestration</h4>
            <div className="bg-blue-50 dark:bg-blue-950 p-4 rounded-lg border border-blue-200 dark:border-blue-800">
              <h5 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">Master Orchestrator Workflow</h5>
              <div className="text-sm text-blue-800 dark:text-blue-200 space-y-2">
                <p>The master-orchestrator-agent coordinates complex, multi-agent workflows:</p>
                <ol className="list-decimal list-inside space-y-1 ml-4">
                  <li>Analyzes complex requirements and breaks them down</li>
                  <li>Creates MCP tasks with full context and specifications</li>
                  <li>Delegates to appropriate specialized agents</li>
                  <li>Coordinates parallel agent execution</li>
                  <li>Monitors progress and handles blockers</li>
                  <li>Integrates results and ensures quality</li>
                </ol>
              </div>
            </div>
          </div>

          <div>
            <h4 className="text-lg font-semibold mb-3">Parallel Agent Coordination</h4>
            <div className="space-y-3">
              <p className="text-gray-600 dark:text-gray-300">
                4genthub supports parallel execution of independent tasks using multiple agents simultaneously:
              </p>

              <Card className="p-4 bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800">
                <h5 className="font-semibold text-green-900 dark:text-green-100 mb-2">Example: Feature Development</h5>
                <div className="text-sm text-green-800 dark:text-green-200 space-y-1">
                  <p>For a new authentication feature, tasks can run in parallel:</p>
                  <ul className="mt-2 space-y-1 list-disc list-inside ml-4">
                    <li>Backend implementation (coding-agent)</li>
                    <li>Frontend UI design (ui-specialist-agent)</li>
                    <li>Test planning (test-orchestrator-agent)</li>
                    <li>Security review (security-auditor-agent)</li>
                    <li>Documentation (documentation-agent)</li>
                  </ul>
                </div>
              </Card>
            </div>
          </div>

          <div>
            <h4 className="text-lg font-semibold mb-3">Context Delegation</h4>
            <p className="text-gray-600 dark:text-gray-300 mb-4">
              Advanced context management allows delegation of data between hierarchy levels:
            </p>

            <div className="bg-orange-50 dark:bg-orange-950 p-4 rounded-lg border border-orange-200 dark:border-orange-800">
              <h5 className="font-semibold text-orange-900 dark:text-orange-100 mb-2">Delegation Patterns</h5>
              <div className="text-sm text-orange-800 dark:text-orange-200 space-y-1">
                <p>• <strong>Upward Delegation:</strong> Task learnings → Project knowledge base</p>
                <p>• <strong>Downward Delegation:</strong> Project standards → Task specifications</p>
                <p>• <strong>Cross-Branch:</strong> Reusable patterns between feature branches</p>
                <p>• <strong>Global Sharing:</strong> Best practices across all user projects</p>
              </div>
            </div>
          </div>

          <div>
            <h4 className="text-lg font-semibold mb-3">Performance Optimization</h4>
            <div className="grid md:grid-cols-2 gap-4">
              <Card className="p-4 bg-yellow-50 dark:bg-yellow-950 border-yellow-200 dark:border-yellow-800">
                <h5 className="font-semibold text-yellow-900 dark:text-yellow-100 mb-2">Token Economy</h5>
                <div className="text-sm text-yellow-800 dark:text-yellow-200 space-y-1">
                  <p>• Store context once in MCP tasks</p>
                  <p>• Reference by task_id only (95% token savings)</p>
                  <p>• Efficient parallel delegation</p>
                  <p>• Smart context inheritance</p>
                </div>
              </Card>
              <Card className="p-4 bg-cyan-50 dark:bg-cyan-950 border-cyan-200 dark:border-cyan-800">
                <h5 className="font-semibold text-cyan-900 dark:text-cyan-100 mb-2">Smart Caching</h5>
                <div className="text-sm text-cyan-800 dark:text-cyan-200 space-y-1">
                  <p>• Intelligent context caching</p>
                  <p>• Automatic invalidation on updates</p>
                  <p>• Performance monitoring tools</p>
                  <p>• Optimized Docker configurations</p>
                </div>
              </Card>
            </div>
          </div>
        </div>
      ),
      isExpanded: expandedSections['advanced-features'],
      onToggle: () => toggleSection('advanced-features')
    }
  ];

  const filteredSections = helpSections.filter(section =>
    section.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    section.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (activeSection) {
    const section = helpSections.find(s => s.id === activeSection);
    if (section) {
      return (
        <div className="container mx-auto py-8 px-4 max-w-6xl">
          <div className="mb-6">
            <Button
              variant="outline"
              onClick={() => setActiveSection(null)}
              className="mb-4"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Help Topics
            </Button>
            <div className="flex items-center space-x-3 mb-4">
              {section.icon}
              <div>
                <h1 className="text-3xl font-bold">{section.title}</h1>
                <p className="text-gray-600 dark:text-gray-300">{section.description}</p>
              </div>
            </div>
          </div>

          <div className="prose prose-gray dark:prose-invert max-w-none">
            {section.content}
          </div>
        </div>
      );
    }
  }

  return (
    <div className="container mx-auto py-8 px-4 max-w-6xl">
      {/* Header */}
      <div className="text-center mb-12">
        <div className="flex justify-center mb-4">
          <div className="p-4 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl">
            <HelpCircle className="h-12 w-12 text-white" />
          </div>
        </div>
        <h1 className="text-4xl font-bold mb-4">4genthub MCP - Help & Setup</h1>
        <p className="text-xl text-gray-600 dark:text-gray-300 max-w-3xl mx-auto">
          Complete guide to using 4genthub MCP platform with 42+ specialized AI agents,
          enterprise orchestration, and development workflow acceleration
        </p>
      </div>

      {/* Search */}
      <Card className="mb-8">
        <CardContent className="pt-6">
          <div className="relative max-w-md mx-auto">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              placeholder="Search help topics..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
        </CardContent>
      </Card>

      {/* Quick Stats */}
      <div className="grid md:grid-cols-4 gap-6 mb-12">
        <Card className="p-6 text-center bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-950 dark:to-blue-900 border-blue-200 dark:border-blue-800">
          <Server className="h-8 w-8 text-blue-600 mx-auto mb-3" />
          <h3 className="text-2xl font-bold text-blue-900 dark:text-blue-100">43+</h3>
          <p className="text-blue-700 dark:text-blue-300">MCP Tools Available</p>
        </Card>
        <Card className="p-6 text-center bg-gradient-to-br from-green-50 to-green-100 dark:from-green-950 dark:to-green-900 border-green-200 dark:border-green-800">
          <Cpu className="h-8 w-8 text-green-600 mx-auto mb-3" />
          <h3 className="text-2xl font-bold text-green-900 dark:text-green-100">42</h3>
          <p className="text-green-700 dark:text-green-300">Specialized Agents</p>
        </Card>
        <Card className="p-6 text-center bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-950 dark:to-purple-900 border-purple-200 dark:border-purple-800">
          <Shield className="h-8 w-8 text-purple-600 mx-auto mb-3" />
          <h3 className="text-2xl font-bold text-purple-900 dark:text-purple-100">4-Tier</h3>
          <p className="text-purple-700 dark:text-purple-300">Context Hierarchy</p>
        </Card>
        <Card className="p-6 text-center bg-gradient-to-br from-orange-50 to-orange-100 dark:from-orange-950 dark:to-orange-900 border-orange-200 dark:border-orange-800">
          <Terminal className="h-8 w-8 text-orange-600 mx-auto mb-3" />
          <h3 className="text-2xl font-bold text-orange-900 dark:text-orange-100">16</h3>
          <p className="text-orange-700 dark:text-orange-300">Docker Menu Options</p>
        </Card>
      </div>

      {/* Help Sections */}
      <div className="space-y-4">
        {filteredSections.map((section) => (
          <HelpSection
            key={section.id}
            {...section}
          />
        ))}
      </div>

      {/* Additional Resources */}
      <Card className="mt-12 bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-950 dark:to-purple-950 border-blue-200 dark:border-blue-800">
        <CardHeader>
          <CardTitle className="flex items-center">
            <ExternalLink className="h-5 w-5 mr-2" />
            Additional Resources
          </CardTitle>
          <CardDescription>
            Explore more ways to learn and get support for 4genthub
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <h4 className="font-semibold flex items-center">
                <Github className="h-4 w-4 mr-2" />
                Open Source
              </h4>
              <p className="text-sm text-gray-600 dark:text-gray-300">
                Contribute to 4genthub development on GitHub and access the complete source code
              </p>
              <Button
                size="sm"
                variant="outline"
                onClick={() => window.open('https://github.com/phamhung075/4genthub', '_blank')}
              >
                View Repository
              </Button>
            </div>
            <div className="space-y-2">
              <h4 className="font-semibold flex items-center">
                <MessageSquare className="h-4 w-4 mr-2" />
                Community
              </h4>
              <p className="text-sm text-gray-600 dark:text-gray-300">
                Join our Discord community for real-time help and discussions
              </p>
              <Button
                size="sm"
                variant="outline"
                onClick={() => window.open('https://discord.gg/zmhMpK6N', '_blank')}
              >
                Join Discord
              </Button>
            </div>
            <div className="space-y-2">
              <h4 className="font-semibold flex items-center">
                <FileText className="h-4 w-4 mr-2" />
                Documentation
              </h4>
              <p className="text-sm text-gray-600 dark:text-gray-300">
                Access comprehensive guides and best practices in the ai_docs directory
              </p>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setActiveSection('local-development-setup')}
              >
                Local Setup Guide
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};