import React from "react";
import { Play } from "lucide-react";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import { Checkbox } from "./ui/checkbox";
import { Separator } from "./ui/separator";
import { Task, callAgent } from "../api";

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
                      <div>
                        <p className="font-medium text-sm">{agent.name}</p>
                        {agent.id && (
                          <p className="text-xs text-muted-foreground">ID: {agent.id}</p>
                        )}
                      </div>
                    </label>
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
                        className="cursor-pointer"
                      >
                        <p className="font-medium text-sm">{agentName}</p>
                        <p className="text-xs text-muted-foreground">From agent library</p>
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