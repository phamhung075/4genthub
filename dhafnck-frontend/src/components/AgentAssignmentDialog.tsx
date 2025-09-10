import React from "react";
import { Play, Info } from "lucide-react";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import { Checkbox } from "./ui/checkbox";
import { Separator } from "./ui/separator";
import { Task, callAgent } from "../api";
import { Alert, AlertDescription, AlertTitle } from "./ui/alert";

interface AgentAssignmentDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  task: Task | null;
  onClose: () => void;
  onAssign: (agents: string[]) => void;
  agents: any[]; // Project registered agents
  availableAgents: string[]; // Available agents from library
  saving?: boolean;
}

export const AgentAssignmentDialog: React.FC<AgentAssignmentDialogProps> = ({
  open,
  onOpenChange,
  task,
  onClose,
  onAssign,
  agents,
  availableAgents,
  saving = false
}) => {
  const [selectedAgents, setSelectedAgents] = React.useState<string[]>([]);
  const [callingAgent, setCallingAgent] = React.useState(false);
  const [agentResponses, setAgentResponses] = React.useState<Record<string, any>>({});
  const [selectedAgentInfo, setSelectedAgentInfo] = React.useState<string | null>(null);

  // Update selected agents when task changes
  React.useEffect(() => {
    if (task) {
      setSelectedAgents(task.assignees || []);
    }
  }, [task]);

  const toggleAgentSelection = (agentId: string) => {
    setSelectedAgents(prev => 
      prev.includes(agentId) 
        ? prev.filter(id => id !== agentId)
        : [...prev, agentId]
    );
  };

  const handleAssign = () => {
    onAssign(selectedAgents);
  };

  const handleCancel = () => {
    // Reset to original task assignees
    setSelectedAgents(task?.assignees || []);
    setAgentResponses({});
    onClose();
  };

  const handleCallAgent = async (agentName: string) => {
    setCallingAgent(true);
    try {
      const result = await callAgent(agentName);
      setAgentResponses(prev => ({
        ...prev,
        [agentName]: result
      }));
    } catch (e) {
      console.error('Error calling agent:', e);
      setAgentResponses(prev => ({
        ...prev,
        [agentName]: { error: 'Failed to activate agent', details: e }
      }));
    } finally {
      setCallingAgent(false);
    }
  };

  const handleAgentInfoClick = (agentName: string) => {
    setSelectedAgentInfo(agentName === selectedAgentInfo ? null : agentName);
  };

  // Agent descriptions mapping
  const agentDescriptions: Record<string, { description: string; category: string; skills: string[] }> = {
    '@coding-agent': {
      description: 'Implementation and feature development specialist. Transforms specifications into production-ready code.',
      category: 'Development & Coding',
      skills: ['Feature implementation', 'Code refactoring', 'Multiple languages/frameworks', 'Test creation']
    },
    '@debugger-agent': {
      description: 'Bug fixing and troubleshooting expert. Identifies and resolves complex issues.',
      category: 'Development & Coding',
      skills: ['Bug diagnosis', 'Error resolution', 'Performance debugging', 'Memory leak detection']
    },
    '@test-orchestrator-agent': {
      description: 'Comprehensive test management specialist. Creates and manages test suites.',
      category: 'Testing & QA',
      skills: ['Unit testing', 'Integration testing', 'E2E testing', 'Test automation']
    },
    '@security-auditor-agent': {
      description: 'Security audits and vulnerability assessment expert.',
      category: 'Security & Compliance',
      skills: ['Security audits', 'Vulnerability scanning', 'Penetration testing', 'Compliance checks']
    },
    '@devops-agent': {
      description: 'CI/CD and infrastructure specialist. Manages deployment pipelines.',
      category: 'DevOps & Deployment',
      skills: ['CI/CD pipelines', 'Container orchestration', 'Cloud deployment', 'Infrastructure as code']
    },
    '@ui-designer-expert-shadcn-agent': {
      description: 'Shadcn/UI components and frontend design specialist.',
      category: 'Architecture & Design',
      skills: ['React components', 'Tailwind CSS', 'Responsive design', 'Design systems']
    },
    '@documentation-agent': {
      description: 'Technical documentation specialist. Creates comprehensive documentation.',
      category: 'Documentation & Specs',
      skills: ['API documentation', 'User guides', 'Technical writing', 'Knowledge management']
    },
    '@system-architect-agent': {
      description: 'System design and architecture specialist.',
      category: 'Architecture & Design',
      skills: ['System architecture', 'Design patterns', 'Database design', 'Scalability planning']
    },
    '@performance-load-tester-agent': {
      description: 'Performance testing and optimization specialist.',
      category: 'Testing & QA',
      skills: ['Load testing', 'Performance metrics', 'Bottleneck analysis', 'Scalability testing']
    },
    '@task-planning-agent': {
      description: 'Task breakdown and planning specialist.',
      category: 'Project & Planning',
      skills: ['Task decomposition', 'Sprint planning', 'Dependency management', 'Resource planning']
    },
    '@code-reviewer-agent': {
      description: 'Code quality and review specialist. Ensures code standards and best practices.',
      category: 'Development & Coding',
      skills: ['Code review', 'Quality checks', 'Standards enforcement', 'Refactoring guidance']
    },
    '@prototyping-agent': {
      description: 'Rapid prototyping and proof-of-concept specialist.',
      category: 'Development & Coding',
      skills: ['Quick prototypes', 'POC development', 'Iterative design', 'Concept validation']
    },
    '@uat-coordinator-agent': {
      description: 'User acceptance testing coordination specialist.',
      category: 'Testing & QA',
      skills: ['UAT planning', 'User testing', 'Acceptance criteria', 'Feedback collection']
    },
    '@adaptive-deployment-strategist-agent': {
      description: 'Deployment strategies and release management specialist.',
      category: 'DevOps & Deployment',
      skills: ['Deployment planning', 'Release management', 'Blue-green deployment', 'Rollout strategies']
    },
    '@swarm-scaler-agent': {
      description: 'Distributed systems scaling and orchestration specialist.',
      category: 'DevOps & Deployment',
      skills: ['Container orchestration', 'Docker Swarm', 'Horizontal scaling', 'Load distribution']
    },
    '@design-system-agent': {
      description: 'Design system and UI patterns specialist.',
      category: 'Architecture & Design',
      skills: ['Component libraries', 'UI patterns', 'Design tokens', 'Style guides']
    },
    '@core-concept-agent': {
      description: 'Core concepts and fundamentals specialist.',
      category: 'Architecture & Design',
      skills: ['Concept definition', 'Theoretical framework', 'Fundamental principles', 'Abstract concepts']
    },
    '@tech-spec-agent': {
      description: 'Technical specifications and documentation specialist.',
      category: 'Documentation & Specs',
      skills: ['Tech specs', 'API documentation', 'System specifications', 'Implementation guides']
    },
    '@prd-architect-agent': {
      description: 'Product requirements documentation specialist.',
      category: 'Documentation & Specs',
      skills: ['PRD creation', 'Requirements analysis', 'Feature specifications', 'User stories']
    },
    '@project-initiator-agent': {
      description: 'Project setup and kickoff specialist.',
      category: 'Project & Planning',
      skills: ['Project bootstrap', 'Initial setup', 'Team onboarding', 'Environment configuration']
    },
    '@uber-orchestrator-agent': {
      description: 'Complex workflow orchestration specialist.',
      category: 'Project & Planning',
      skills: ['Multi-agent coordination', 'Complex workflows', 'Strategic planning', 'Project oversight']
    },
    '@elicitation-agent': {
      description: 'Requirements gathering and analysis specialist.',
      category: 'Project & Planning',
      skills: ['Requirements elicitation', 'Stakeholder interviews', 'Needs assessment', 'Scope definition']
    },
    '@compliance-scope-agent': {
      description: 'Regulatory compliance and scope assessment specialist.',
      category: 'Security & Compliance',
      skills: ['Compliance audits', 'Regulatory requirements', 'Risk assessment', 'Governance framework']
    },
    '@ethical-review-agent': {
      description: 'Ethical considerations and responsible development specialist.',
      category: 'Security & Compliance',
      skills: ['Ethics assessment', 'Bias detection', 'Privacy review', 'Responsible AI']
    },
    '@analytics-setup-agent': {
      description: 'Analytics and tracking setup specialist.',
      category: 'Analytics & Optimization',
      skills: ['Analytics implementation', 'Event tracking', 'Dashboard creation', 'KPI monitoring']
    },
    '@efficiency-optimization-agent': {
      description: 'Process optimization and efficiency improvement specialist.',
      category: 'Analytics & Optimization',
      skills: ['Process improvement', 'Workflow optimization', 'Performance tuning', 'Resource allocation']
    },
    '@health-monitor-agent': {
      description: 'System health monitoring and alerting specialist.',
      category: 'Analytics & Optimization',
      skills: ['Health checks', 'Performance metrics', 'Alerting setup', 'Incident detection']
    },
    '@marketing-strategy-orchestrator-agent': {
      description: 'Marketing strategy and campaign management specialist.',
      category: 'Marketing & Growth',
      skills: ['Marketing campaigns', 'Strategy planning', 'Customer acquisition', 'Brand marketing']
    },
    '@seo-sem-agent': {
      description: 'SEO and SEM optimization specialist.',
      category: 'Marketing & Growth',
      skills: ['Search optimization', 'Keyword research', 'PPC campaigns', 'SERP rankings']
    },
    '@growth-hacking-idea-agent': {
      description: 'Growth strategies and viral marketing specialist.',
      category: 'Marketing & Growth',
      skills: ['Growth hacking', 'Viral loops', 'User acquisition', 'Conversion optimization']
    },
    '@content-strategy-agent': {
      description: 'Content planning and editorial strategy specialist.',
      category: 'Marketing & Growth',
      skills: ['Content planning', 'Editorial calendar', 'Content marketing', 'Brand messaging']
    },
    '@community-strategy-agent': {
      description: 'Community building and engagement specialist.',
      category: 'Marketing & Growth',
      skills: ['Community management', 'User engagement', 'Social strategy', 'Community growth']
    },
    '@branding-agent': {
      description: 'Brand identity and strategy specialist.',
      category: 'Marketing & Growth',
      skills: ['Brand development', 'Visual identity', 'Brand guidelines', 'Market positioning']
    },
    '@deep-research-agent': {
      description: 'In-depth research and analysis specialist.',
      category: 'Research & Analysis',
      skills: ['Market research', 'Technical research', 'Competitive analysis', 'Data analysis']
    },
    '@mcp-researcher-agent': {
      description: 'MCP and tool research specialist.',
      category: 'Research & Analysis',
      skills: ['Tool evaluation', 'Platform research', 'Integration assessment', 'Technology stack']
    },
    '@root-cause-analysis-agent': {
      description: 'Problem analysis and root cause identification specialist.',
      category: 'Research & Analysis',
      skills: ['Problem investigation', 'Failure analysis', 'Incident investigation', 'Causal analysis']
    },
    '@technology-advisor-agent': {
      description: 'Technology recommendations and advisory specialist.',
      category: 'Research & Analysis',
      skills: ['Tech evaluation', 'Framework comparison', 'Stack optimization', 'Architecture advice']
    },
    '@brainjs-ml-agent': {
      description: 'Machine learning with Brain.js specialist.',
      category: 'AI & Machine Learning',
      skills: ['Neural networks', 'ML implementation', 'Model training', 'Predictive models']
    },
    '@mcp-configuration-agent': {
      description: 'MCP setup and configuration specialist.',
      category: 'Configuration & Integration',
      skills: ['MCP setup', 'Server configuration', 'Protocol implementation', 'Integration management']
    },
    '@idea-generation-agent': {
      description: 'Creative idea generation and brainstorming specialist.',
      category: 'Creative & Ideation',
      skills: ['Brainstorming', 'Creative thinking', 'Innovation methods', 'Concept creation']
    },
    '@idea-refinement-agent': {
      description: 'Idea improvement and iteration specialist.',
      category: 'Creative & Ideation',
      skills: ['Idea enhancement', 'Concept refinement', 'Proposal development', 'Vision polishing']
    },
    '@remediation-agent': {
      description: 'Issue remediation and corrective action specialist.',
      category: 'Problem Resolution',
      skills: ['Issue resolution', 'Corrective measures', 'Recovery procedures', 'Fix implementation']
    }
  };

  const getAgentInfo = (agentName: string) => {
    // Normalize agent name (add @ if missing)
    const normalizedName = agentName.startsWith('@') ? agentName : `@${agentName}`;
    return agentDescriptions[normalizedName] || {
      description: 'Specialized agent for various development tasks.',
      category: 'General',
      skills: ['Task automation', 'Specialized workflows']
    };
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl w-[90vw]">
        <DialogHeader>
          <DialogTitle className="text-xl text-left">Assign Agents to Task</DialogTitle>
        </DialogHeader>
        
        <div className="space-y-4">
          {/* Task Information */}
          <div className="bg-gray-50 p-3 rounded">
            <h4 className="font-medium text-sm mb-1">Task: {task?.title}</h4>
            {task?.assignees && task.assignees.length > 0 && (
              <p className="text-xs text-muted-foreground">
                Currently assigned: {task.assignees.join(', ')}
              </p>
            )}
          </div>
          
          <Separator />
          
          {/* Project Registered Agents */}
          <div>
            <h4 className="font-medium text-sm mb-3">Project Registered Agents</h4>
            {agents.length === 0 ? (
              <p className="text-sm text-muted-foreground">No agents registered in this project</p>
            ) : (
              <div className="space-y-2 max-h-[200px] overflow-y-auto border rounded p-2">
                {agents.map((agent) => (
                  <div key={agent.id || agent.name} className="flex items-center space-x-2 p-2 hover:bg-gray-50 rounded">
                    <Checkbox
                      id={`agent-${agent.id || agent.name}`}
                      checked={selectedAgents.includes(agent.id || agent.name)}
                      onCheckedChange={() => toggleAgentSelection(agent.id || agent.name)}
                    />
                    <label
                      htmlFor={`agent-${agent.id || agent.name}`}
                      className="flex-1 cursor-pointer"
                    >
                      <div
                        className="group"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleAgentInfoClick(agent.name);
                        }}
                      >
                        <p className="font-medium text-sm flex items-center gap-1 hover:text-blue-600">
                          {agent.name}
                          <Info className="w-3 h-3 opacity-50 group-hover:opacity-100" />
                        </p>
                        {agent.id && (
                          <p className="text-xs text-muted-foreground">ID: {agent.id}</p>
                        )}
                      </div>
                    </label>
                    {selectedAgentInfo === agent.name && (
                      <div className="col-span-2 mt-2">
                        <Alert>
                          <AlertTitle className="text-sm">{getAgentInfo(agent.name).category}</AlertTitle>
                          <AlertDescription className="text-xs">
                            <p className="mb-2">{getAgentInfo(agent.name).description}</p>
                            <div className="flex flex-wrap gap-1">
                              {getAgentInfo(agent.name).skills.map((skill, idx) => (
                                <span key={idx} className="bg-blue-100 text-blue-700 px-2 py-0.5 rounded text-xs">
                                  {skill}
                                </span>
                              ))}
                            </div>
                          </AlertDescription>
                        </Alert>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
          
          <Separator />
          
          {/* Available Agents from Library */}
          <div>
            <h4 className="font-medium text-sm mb-3">Available Agents from Library</h4>
            <div className="space-y-2 max-h-[300px] overflow-y-auto border rounded p-2">
              {availableAgents.map((agentName) => (
                <div key={agentName} className="border rounded p-2 hover:bg-gray-50">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id={`lib-${agentName}`}
                        checked={selectedAgents.includes(agentName)}
                        onCheckedChange={() => toggleAgentSelection(agentName)}
                      />
                      <label
                        htmlFor={`lib-${agentName}`}
                        className="cursor-pointer flex-1"
                      >
                        <div
                          className="group"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleAgentInfoClick(agentName);
                          }}
                        >
                          <p className="font-medium text-sm flex items-center gap-1 hover:text-blue-600">
                            {agentName}
                            <Info className="w-3 h-3 opacity-50 group-hover:opacity-100" />
                          </p>
                          <p className="text-xs text-muted-foreground">From agent library</p>
                        </div>
                      </label>
                    </div>
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-8 w-8"
                      onClick={() => handleCallAgent(agentName)}
                      disabled={callingAgent}
                      title="Activate this agent"
                    >
                      <Play className="w-4 h-4" />
                    </Button>
                  </div>
                  {selectedAgentInfo === agentName && (
                    <div className="mt-2">
                      <Alert>
                        <AlertTitle className="text-sm">{getAgentInfo(agentName).category}</AlertTitle>
                        <AlertDescription className="text-xs">
                          <p className="mb-2">{getAgentInfo(agentName).description}</p>
                          <div className="flex flex-wrap gap-1">
                            {getAgentInfo(agentName).skills.map((skill, idx) => (
                              <span key={idx} className="bg-blue-100 text-blue-700 px-2 py-0.5 rounded text-xs">
                                {skill}
                              </span>
                            ))}
                          </div>
                        </AlertDescription>
                      </Alert>
                    </div>
                  )}
                  {agentResponses[agentName] && (
                    <div className="mt-2 p-2 bg-gray-100 rounded">
                      <p className="text-xs font-medium mb-1">Call Agent Response:</p>
                      <pre className="text-xs overflow-x-auto whitespace-pre-wrap bg-white p-2 rounded border">
                        {JSON.stringify(agentResponses[agentName], null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
          
          {/* Selected Agents Summary */}
          {selectedAgents.length > 0 && (
            <>
              <Separator />
              <div className="bg-blue-50 p-3 rounded">
                <h4 className="font-medium text-sm mb-2">Selected Agents ({selectedAgents.length}):</h4>
                <div className="flex flex-wrap gap-1">
                  {selectedAgents.map((agent, index) => (
                    <span 
                      key={index} 
                      className="text-xs bg-blue-200 text-blue-800 px-2 py-1 rounded"
                    >
                      {agent}
                    </span>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
        
        <DialogFooter>
          <Button variant="outline" onClick={handleCancel} disabled={saving}>
            Cancel
          </Button>
          <Button 
            variant="default" 
            onClick={handleAssign}
            disabled={saving}
          >
            {saving ? "Assigning..." : "Assign Agents"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default AgentAssignmentDialog;