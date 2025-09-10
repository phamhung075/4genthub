import React, { useEffect, useState } from "react";
import { Info, Loader2, Play } from "lucide-react";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import { Alert, AlertDescription, AlertTitle } from "./ui/alert";
import { callAgent } from "../api";
import { Badge } from "./ui/badge";
import RawJSONDisplay from "./ui/RawJSONDisplay";

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
    '@system-architect-agent': {
      description: 'System design and architecture specialist.',
      category: 'Architecture & Design',
      skills: ['System architecture', 'Design patterns', 'Database design', 'Scalability planning']
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
    '@task-planning-agent': {
      description: 'Task breakdown and planning specialist.',
      category: 'Project & Planning',
      skills: ['Task decomposition', 'Sprint planning', 'Dependency management', 'Resource planning']
    },
    '@uber-orchestrator-agent': {
      description: 'Complex workflow orchestration specialist.',
      category: 'Project & Planning',
      skills: ['Multi-agent coordination', 'Complex workflows', 'Strategic planning', 'Project oversight']
    }
  };

  const getAgentInfo = (name: string) => {
    const normalizedName = name.startsWith('@') ? name : `@${name}`;
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
      console.log('Calling agent:', agentName);
      const result = await callAgent(agentName);
      console.log('Agent response:', result);
      
      // Ensure we have a valid response
      if (result !== undefined && result !== null) {
        setAgentResponse(result);
      } else {
        setAgentResponse({ 
          message: 'No response from agent',
          agentName: agentName
        });
      }
    } catch (e: any) {
      console.error('Error calling agent:', e);
      setError(e.message || 'Failed to call agent');
      setAgentResponse({ 
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

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl w-[90vw] max-h-[85vh]">
        <DialogHeader>
          <DialogTitle className="text-xl flex items-center gap-2">
            <Info className="w-5 h-5" />
            Agent Information: {agentName}
          </DialogTitle>
          {taskTitle && (
            <p className="text-sm text-muted-foreground">
              Context: {taskTitle}
            </p>
          )}
        </DialogHeader>
        
        <div className="space-y-4">
          {/* Agent Description */}
          <Alert>
            <AlertTitle className="flex items-center justify-between">
              <span>{agentInfo.category}</span>
              <Badge variant="secondary">{agentName}</Badge>
            </AlertTitle>
            <AlertDescription className="mt-2">
              <p className="mb-3">{agentInfo.description}</p>
              <div className="flex flex-wrap gap-1">
                {agentInfo.skills.map((skill, idx) => (
                  <span key={idx} className="bg-blue-100 text-blue-700 px-2 py-0.5 rounded text-xs">
                    {skill}
                  </span>
                ))}
              </div>
            </AlertDescription>
          </Alert>

          {/* Call Agent Section */}
          <div className="border rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-medium text-sm">Agent Response</h3>
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
                    Call Agent
                  </>
                )}
              </Button>
            </div>

            {/* Response Display */}
            {loading && (
              <div className="flex items-center justify-center h-32 border rounded bg-gray-50">
                <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
                <span className="ml-2 text-gray-500">Calling agent...</span>
              </div>
            )}
            
            {error && !loading && (
              <Alert variant="destructive">
                <AlertTitle>Error</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            
            {agentResponse && !loading && (
              <RawJSONDisplay 
                jsonData={agentResponse}
                title="Agent Call Response"
                fileName="agent-response.json"
              />
            )}
            
            {!loading && !error && !agentResponse && (
              <div className="flex items-center justify-center h-32 border rounded bg-gray-50 text-gray-500">
                <p>Click "Call Agent" to get agent information</p>
              </div>
            )}
          </div>
        </div>
        
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default AgentInfoDialog;