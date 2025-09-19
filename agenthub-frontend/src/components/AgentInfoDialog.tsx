import { AlertCircle, CheckCircle, ChevronDown, ChevronRight, Copy, FileText, Info, Loader2, Play, Wrench } from "lucide-react";
import React, { useEffect, useState } from "react";
import { callAgent } from "../api";
import { Alert, AlertDescription, AlertTitle } from "./ui/alert";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import RawJSONDisplay from "./ui/RawJSONDisplay";
import logger from "../utils/logger";

interface AgentInfoDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  agentName: string;
  taskTitle?: string;
  onClose: () => void;
}

export const AgentInfoDialog: React.FC<AgentInfoDialogProps> = ({
  open,
  onOpenChange,
  agentName,
  taskTitle,
  onClose
}) => {
  const [loading, setLoading] = useState(false);
  const [agentResponse, setAgentResponse] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['basic', 'description']));
  const [copiedSections, setCopiedSections] = useState<Set<string>>(new Set());

  // Agent descriptions mapping (using kebab-case without @ prefix)
  const agentDescriptions: Record<string, { description: string; category: string; skills: string[] }> = {
    'coding-agent': {
      description: 'Implementation and feature development specialist. Transforms specifications into production-ready code.',
      category: 'Development & Coding',
      skills: ['Feature implementation', 'Code refactoring', 'Multiple languages/frameworks', 'Test creation']
    },
    'debugger-agent': {
      description: 'Bug fixing and troubleshooting expert. Identifies and resolves complex issues.',
      category: 'Development & Coding',
      skills: ['Bug diagnosis', 'Error resolution', 'Performance debugging', 'Memory leak detection']
    },
    'code-reviewer-agent': {
      description: 'Code quality and review specialist. Ensures code standards and best practices.',
      category: 'Development & Coding',
      skills: ['Code review', 'Quality assurance', 'Best practices', 'Standards enforcement']
    },
    'prototyping-agent': {
      description: 'Rapid prototyping and proof of concept specialist.',
      category: 'Development & Coding',
      skills: ['Rapid prototyping', 'POC development', 'Quick validation', 'Experimental builds']
    },
    'test-orchestrator-agent': {
      description: 'Comprehensive test management specialist. Creates and manages test suites.',
      category: 'Testing & QA',
      skills: ['Unit testing', 'Integration testing', 'E2E testing', 'Test automation']
    },
    'uat-coordinator-agent': {
      description: 'User acceptance testing coordinator. Manages testing with stakeholders.',
      category: 'Testing & QA',
      skills: ['User acceptance testing', 'Stakeholder coordination', 'Test planning', 'User feedback']
    },
    'performance-load-tester-agent': {
      description: 'Performance and load testing specialist.',
      category: 'Testing & QA',
      skills: ['Load testing', 'Performance analysis', 'Stress testing', 'Benchmarking']
    },
    'security-auditor-agent': {
      description: 'Security audits and vulnerability assessment expert.',
      category: 'Security & Compliance',
      skills: ['Security audits', 'Vulnerability scanning', 'Penetration testing', 'Compliance checks']
    },
    'compliance-scope-agent': {
      description: 'Regulatory compliance and scope assessment specialist.',
      category: 'Security & Compliance',
      skills: ['Compliance assessment', 'Regulatory requirements', 'Risk assessment', 'Audit preparation']
    },
    'ethical-review-agent': {
      description: 'Ethical considerations and responsible development specialist.',
      category: 'Security & Compliance',
      skills: ['Ethics assessment', 'Responsible AI', 'Bias detection', 'Social impact analysis']
    },
    'devops-agent': {
      description: 'CI/CD and infrastructure specialist. Manages deployment pipelines.',
      category: 'DevOps & Infrastructure',
      skills: ['CI/CD pipelines', 'Container orchestration', 'Cloud deployment', 'Infrastructure as code']
    },
    'system-architect-agent': {
      description: 'System design and architecture specialist.',
      category: 'Architecture & Design',
      skills: ['System architecture', 'Design patterns', 'Database design', 'Scalability planning']
    },
    'design-system-agent': {
      description: 'Design system and UI pattern specialist.',
      category: 'Architecture & Design',
      skills: ['Design systems', 'Component libraries', 'UI patterns', 'Design tokens']
    },
    'ui-specialist-agent': {
      description: 'UI/UX design and frontend development specialist.',
      category: 'Architecture & Design',
      skills: ['React components', 'Tailwind CSS', 'Responsive design', 'User experience']
    },
    'core-concept-agent': {
      description: 'Core concepts and fundamental principles specialist.',
      category: 'Architecture & Design',
      skills: ['Fundamental concepts', 'Theoretical frameworks', 'Concept development', 'Abstract thinking']
    },
    'documentation-agent': {
      description: 'Technical documentation specialist. Creates comprehensive documentation.',
      category: 'Documentation',
      skills: ['API documentation', 'User guides', 'Technical writing', 'Knowledge management']
    },
    'project-initiator-agent': {
      description: 'Project setup and initialization specialist.',
      category: 'Project & Planning',
      skills: ['Project setup', 'Initial planning', 'Foundation building', 'Team coordination']
    },
    'task-planning-agent': {
      description: 'Task breakdown and planning specialist.',
      category: 'Project & Planning',
      skills: ['Task decomposition', 'Sprint planning', 'Dependency management', 'Resource planning']
    },
    'master-orchestrator-agent': {
      description: 'Complex workflow orchestration specialist.',
      category: 'Project & Planning',
      skills: ['Multi-agent coordination', 'Complex workflows', 'Strategic planning', 'Project oversight']
    },
    'elicitation-agent': {
      description: 'Requirements gathering and analysis specialist.',
      category: 'Project & Planning',
      skills: ['Requirements elicitation', 'Stakeholder analysis', 'Needs assessment', 'Scope definition']
    },
    'analytics-setup-agent': {
      description: 'Analytics and tracking setup specialist.',
      category: 'Analytics & Optimization',
      skills: ['Analytics implementation', 'Data tracking', 'Performance monitoring', 'Metrics setup']
    },
    'efficiency-optimization-agent': {
      description: 'Process optimization and efficiency improvement specialist.',
      category: 'Analytics & Optimization',
      skills: ['Process optimization', 'Workflow improvement', 'Performance tuning', 'Resource optimization']
    },
    'health-monitor-agent': {
      description: 'System health monitoring and alerting specialist.',
      category: 'Analytics & Optimization',
      skills: ['System monitoring', 'Health checks', 'Alerting', 'Status tracking']
    },
    'marketing-strategy-orchestrator-agent': {
      description: 'Marketing strategy and campaign orchestration specialist.',
      category: 'Marketing & Branding',
      skills: ['Marketing strategy', 'Campaign management', 'Growth hacking', 'SEO/SEM']
    },
    'community-strategy-agent': {
      description: 'Community building and engagement specialist.',
      category: 'Marketing & Branding',
      skills: ['Community building', 'User engagement', 'Social strategy', 'Relationship management']
    },
    'branding-agent': {
      description: 'Brand identity and strategy specialist.',
      category: 'Marketing & Branding',
      skills: ['Brand development', 'Visual identity', 'Brand strategy', 'Brand guidelines']
    },
    'deep-research-agent': {
      description: 'In-depth research and analysis specialist.',
      category: 'Research & Analysis',
      skills: ['Research methodology', 'Data analysis', 'Literature review', 'Insights generation']
    },
    'llm-ai-agents-research': {
      description: 'AI/ML research and innovation specialist.',
      category: 'Research & Analysis',
      skills: ['AI research', 'ML innovations', 'LLM development', 'AI engineering']
    },
    'root-cause-analysis-agent': {
      description: 'Problem investigation and root cause analysis specialist.',
      category: 'Research & Analysis',
      skills: ['Root cause analysis', 'Problem investigation', 'Issue diagnosis', 'Systematic analysis']
    },
    'technology-advisor-agent': {
      description: 'Technology recommendations and advisory specialist.',
      category: 'Research & Analysis',
      skills: ['Technology evaluation', 'Stack recommendations', 'Technical advisory', 'Innovation guidance']
    },
    'ml-specialist-agent': {
      description: 'Machine learning implementation and optimization specialist.',
      category: 'AI & Machine Learning',
      skills: ['ML model development', 'Neural networks', 'Data preprocessing', 'Model optimization']
    },
    'creative-ideation-agent': {
      description: 'Creative idea generation and brainstorming specialist.',
      category: 'Creative & Ideation',
      skills: ['Creative thinking', 'Idea generation', 'Brainstorming', 'Innovation workshops']
    }
  };

  // Normalize agent name for consistent display and lookup
  const normalizeAgentName = (name: string): string => {
    // Remove @ prefix and convert underscores to hyphens
    let normalizedName = name.startsWith('@') ? name.slice(1) : name;
    normalizedName = normalizedName.replace(/_/g, '-').toLowerCase();
    return normalizedName;
  };

  const getAgentInfo = (name: string) => {
    const normalizedName = normalizeAgentName(name);
    
    return agentDescriptions[normalizedName] || {
      description: 'Specialized agent for various development tasks.',
      category: 'General',
      skills: ['Task automation', 'Specialized workflows']
    };
  };

  const handleCallAgent = async () => {
    setLoading(true);
    setError(null);
    setAgentResponse(null);
    
    try {
      logger.info('Calling agent:', agentName);
      const result = await callAgent(agentName);
      logger.debug('Agent response:', result);
      
      // Check if we have a successful response
      if (result && result.success) {
        logger.debug('Successfully received agent data');
        setAgentResponse(result);
        setError(null);
      } else if (result && result.success === false) {
        logger.warn('Agent call failed:', result.message);
        setError(result.message || 'Failed to fetch agent information');
        setAgentResponse(result);
      } else if (result !== undefined && result !== null) {
        // Response without explicit success field - treat as success
        logger.debug('Response without success field, treating as valid');
        setAgentResponse(result);
        setError(null);
      } else {
        setAgentResponse({ 
          success: false,
          message: 'No response from agent',
          agentName: agentName
        });
        setError('No response from agent');
      }
    } catch (e: any) {
      logger.error('Error calling agent:', e);
      setError(e.message || 'Failed to call agent');
      setAgentResponse({ 
        success: false,
        error: 'Failed to activate agent', 
        details: e.message || e.toString() 
      });
    } finally {
      setLoading(false);
    }
  };


  // Auto-call agent when dialog opens
  useEffect(() => {
    if (open && agentName && !agentResponse && !loading) {
      handleCallAgent();
    }
  }, [open, agentName]);

  // Reset state when dialog closes
  useEffect(() => {
    if (!open) {
      setAgentResponse(null);
      setError(null);
    }
  }, [open]);

  const agentInfo = getAgentInfo(agentName);

  const toggleSection = (section: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(section)) {
      newExpanded.delete(section);
    } else {
      newExpanded.add(section);
    }
    setExpandedSections(newExpanded);
  };

  const copyToClipboard = async (data: any, sectionId: string) => {
    try {
      const jsonString = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
      await navigator.clipboard.writeText(jsonString);
      setCopiedSections(new Set([...copiedSections, sectionId]));
      setTimeout(() => {
        setCopiedSections(prev => {
          const newSet = new Set(prev);
          newSet.delete(sectionId);
          return newSet;
        });
      }, 2000);
    } catch (err) {
      logger.error('Failed to copy:', err);
    }
  };

  const renderCollapsibleSection = (
    title: string, 
    icon: React.ReactNode, 
    sectionId: string, 
    content: React.ReactNode,
    className?: string,
    copyData?: any
  ) => {
    const isExpanded = expandedSections.has(sectionId);
    const isCopied = copiedSections.has(sectionId);
    
    return (
      <div className={`border rounded-lg ${className || ''}`}>
        <div className="flex items-center justify-between p-3 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors rounded-t-lg">
          <button
            onClick={() => toggleSection(sectionId)}
            className="flex-1 flex items-center gap-2"
          >
            {icon}
            <h3 className="font-medium text-sm">{title}</h3>
          </button>
          <div className="flex items-center gap-2">
            {copyData && isExpanded && (
              <Button
                size="sm"
                variant="ghost"
                onClick={(e) => {
                  e.stopPropagation();
                  copyToClipboard(copyData, sectionId);
                }}
                className="h-7 px-2"
              >
                {isCopied ? (
                  <>
                    <CheckCircle className="h-3 w-3 mr-1 text-green-600" />
                    <span className="text-xs">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="h-3 w-3 mr-1" />
                    <span className="text-xs">Copy</span>
                  </>
                )}
              </Button>
            )}
            <button onClick={() => toggleSection(sectionId)}>
              {isExpanded ? (
                <ChevronDown className="h-4 w-4 text-gray-500" />
              ) : (
                <ChevronRight className="h-4 w-4 text-gray-500" />
              )}
            </button>
          </div>
        </div>
        {isExpanded && (
          <div className="border-t p-4">
            {content}
          </div>
        )}
      </div>
    );
  };

  const renderAgentResponse = () => {
    if (!agentResponse) return null;

    // Handle error response
    if (agentResponse.error || agentResponse.success === false) {
      return (
        <div className="space-y-3">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>
              {agentResponse.message || agentResponse.error || 'Failed to fetch agent information'}
            </AlertDescription>
          </Alert>
          
          {agentResponse.available_agents && (
            <Alert>
              <AlertTitle>Available Agents</AlertTitle>
              <AlertDescription>
                <div className="flex flex-wrap gap-2 mt-2">
                  {agentResponse.available_agents.map((agent: string) => (
                    <Badge key={agent} variant="secondary" className="text-xs">
                      {agent}
                    </Badge>
                  ))}
                </div>
              </AlertDescription>
            </Alert>
          )}
        </div>
      );
    }

    // Handle successful response with agent data
    const agent = agentResponse.json || agentResponse.agent || agentResponse;
    
    return (
      <div className="space-y-3">
        {/* Basic Information Section */}
        {(agent.name || agent.description || agent.category) && 
          renderCollapsibleSection(
            'Basic Information',
            <Info className="h-4 w-4 text-blue-500" />,
            'basic',
            <div className="space-y-2">
              {agent.name && (
                <div>
                  <span className="text-xs font-medium text-gray-600 dark:text-gray-400">Name:</span>
                  <p className="text-sm font-mono">{agent.name}</p>
                </div>
              )}
              {agent.description && (
                <div>
                  <span className="text-xs font-medium text-gray-600 dark:text-gray-400">Description:</span>
                  <p className="text-sm">{agent.description}</p>
                </div>
              )}
              {agent.category && (
                <div>
                  <span className="text-xs font-medium text-gray-600 dark:text-gray-400">Category:</span>
                  <p className="text-sm">{agent.category}</p>
                </div>
              )}
              {agent.version && (
                <div>
                  <span className="text-xs font-medium text-gray-600 dark:text-gray-400">Version:</span>
                  <p className="text-sm">{agent.version}</p>
                </div>
              )}
              {agentResponse.source && (
                <div>
                  <span className="text-xs font-medium text-gray-600 dark:text-gray-400">Source:</span>
                  <p className="text-sm">{agentResponse.source}</p>
                </div>
              )}
              {agentResponse.called_by && (
                <div>
                  <span className="text-xs font-medium text-gray-600 dark:text-gray-400">Called By:</span>
                  <p className="text-sm">{agentResponse.called_by}</p>
                </div>
              )}
            </div>,
            undefined,
            {
              name: agent.name,
              description: agent.description,
              category: agent.category,
              version: agent.version,
              source: agentResponse.source,
              called_by: agentResponse.called_by
            }
          )
        }

        {/* Tools Section */}
        {agent.tools && 
          renderCollapsibleSection(
            'Available Tools',
            <Wrench className="h-4 w-4 text-green-500" />,
            'tools',
            <div className="max-h-64 overflow-y-auto">
              {Array.isArray(agent.tools) ? (
                <div className="flex flex-wrap gap-1">
                  {agent.tools.map((tool: string, index: number) => (
                    <Badge key={index} variant="outline" className="text-xs px-2 py-0.5">
                      {tool}
                    </Badge>
                  ))}
                </div>
              ) : (
                <p className="text-sm">{agent.tools}</p>
              )}
            </div>,
            undefined,
            agent.tools
          )
        }

        {/* System Prompt Section */}
        {agent.system_prompt && 
          renderCollapsibleSection(
            'System Prompt',
            <FileText className="h-4 w-4 text-purple-500" />,
            'system_prompt',
            <div className="bg-gray-50 dark:bg-gray-900 rounded p-4 max-h-80 overflow-y-auto">
              <pre className="text-xs whitespace-pre-wrap font-mono text-gray-700 dark:text-gray-300">
                {agent.system_prompt}
              </pre>
            </div>,
            undefined,
            agent.system_prompt
          )
        }

        {/* Raw JSON Response Section */}
        {renderCollapsibleSection(
          'Raw JSON Response',
          <FileText className="h-4 w-4 text-gray-500" />,
          'raw_json',
          <div className="max-h-96 overflow-y-auto">
            <RawJSONDisplay 
              jsonData={agentResponse}
              title=""
              fileName="agent-response.json"
            />
          </div>,
          undefined,
          agentResponse
        )}
      </div>
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl w-[90vw] max-h-[85vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="text-xl flex items-center gap-2">
            <Info className="w-5 h-5" />
            Agent Information: {normalizeAgentName(agentName)}
          </DialogTitle>
          {taskTitle && (
            <p className="text-sm text-muted-foreground">
              Context: {taskTitle}
            </p>
          )}
        </DialogHeader>
        
        <div className="flex-1 overflow-y-auto py-4">
          <div className="space-y-4">
            {/* Agent Description */}
            {renderCollapsibleSection(
              'Agent Description',
              <Info className="h-4 w-4 text-blue-500" />,
              'description',
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium">{agentInfo.category}</span>
                  <Badge variant="secondary">{normalizeAgentName(agentName)}</Badge>
                </div>
                <p className="text-sm mb-3">{agentInfo.description}</p>
                <div className="flex flex-wrap gap-1">
                  {agentInfo.skills.map((skill, idx) => (
                    <span key={idx} className="bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 px-2 py-0.5 rounded text-xs">
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Agent Response Section */}
            <div className="border rounded-lg">
              <div className="flex items-center justify-between p-3 border-b">
                <h3 className="font-medium text-sm">Agent API Response</h3>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleCallAgent}
                  disabled={loading}
                  className="h-8"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                      Calling...
                    </>
                  ) : (
                    <>
                      <Play className="w-3 h-3 mr-1" />
                      Refresh
                    </>
                  )}
                </Button>
              </div>

              {/* Response Display */}
              <div className="p-4">
                {loading && (
                  <div className="flex items-center justify-center h-32 border rounded bg-gray-50 dark:bg-gray-900">
                    <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
                    <span className="ml-2 text-gray-500 dark:text-gray-400">Fetching agent information...</span>
                  </div>
                )}
                
                {!loading && renderAgentResponse()}
              </div>
            </div>
          </div>
        </div>
        
        <DialogFooter className="mt-4">
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default AgentInfoDialog;