import React from "react";
import { Play, Info, Search } from "lucide-react";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import { Checkbox } from "./ui/checkbox";
import { Separator } from "./ui/separator";
import { Input } from "./ui/input";
import { Task } from "../api";
import AgentInfoDialog from "./AgentInfoDialog";

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
  const [selectedAgentForInfo, setSelectedAgentForInfo] = React.useState<string | null>(null);
  const [agentInfoDialogOpen, setAgentInfoDialogOpen] = React.useState(false);
  const [agentSearchQuery, setAgentSearchQuery] = React.useState("");

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
    onClose();
  };

  const handleAgentInfoClick = (agentName: string) => {
    setSelectedAgentForInfo(agentName);
    setAgentInfoDialogOpen(true);
  };

  // Filter available agents based on search query
  const filteredAvailableAgents = React.useMemo(() => {
    if (!agentSearchQuery.trim()) {
      return availableAgents;
    }
    const query = agentSearchQuery.toLowerCase();
    return availableAgents.filter(agentName => 
      agentName.toLowerCase().includes(query)
    );
  }, [availableAgents, agentSearchQuery]);


  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-5xl w-[90vw]">
          <DialogHeader>
            <DialogTitle className="text-xl text-left">Assign Agents to Task</DialogTitle>
          </DialogHeader>
        
        <div className="space-y-4">
          {/* Task Information */}
          <div className="bg-gray-50 dark:bg-gray-800 p-3 rounded">
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
              <div className="space-y-2 max-h-[200px] overflow-y-auto border dark:border-gray-700 rounded p-2">
                {agents.map((agent) => (
                  <div key={agent.id || agent.name} className="flex items-center space-x-2 p-2 hover:bg-gray-50 dark:hover:bg-gray-800 rounded">
                    <Checkbox
                      id={`agent-${agent.id || agent.name}`}
                      checked={selectedAgents.includes(agent.id || agent.name)}
                      onCheckedChange={() => toggleAgentSelection(agent.id || agent.name)}
                    />
                    <label
                      htmlFor={`agent-${agent.id || agent.name}`}
                      className="flex-1 cursor-pointer"
                    >
                      <div className="flex-1">
                        <p className="font-medium text-sm">{agent.name}</p>
                        {agent.id && (
                          <p className="text-xs text-muted-foreground">ID: {agent.id}</p>
                        )}
                      </div>
                    </label>
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-8 w-8"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleAgentInfoClick(agent.name);
                      }}
                      title="View agent information"
                    >
                      <Info className="w-4 h-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>
          
          <Separator />
          
          {/* Available Agents from Library */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-medium text-sm">Available Agents from Library ({filteredAvailableAgents.length})</h4>
              <div className="relative w-64">
                <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input
                  type="text"
                  placeholder="Search agents..."
                  value={agentSearchQuery}
                  onChange={(e) => setAgentSearchQuery(e.target.value)}
                  className="pl-8 pr-3 h-8 text-sm"
                />
              </div>
            </div>
            <div className="space-y-2 max-h-[300px] overflow-y-auto border dark:border-gray-700 rounded p-2">
              {filteredAvailableAgents.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">
                  {agentSearchQuery ? `No agents found matching "${agentSearchQuery}"` : "No agents available"}
                </p>
              ) : (
                filteredAvailableAgents.map((agentName) => (
                <div key={agentName} className="border dark:border-gray-700 rounded p-2 hover:bg-gray-50 dark:hover:bg-gray-800">
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
                        <div>
                          <p className="font-medium text-sm">{agentName}</p>
                          <p className="text-xs text-muted-foreground">From agent library</p>
                        </div>
                      </label>
                    </div>
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-8 w-8"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleAgentInfoClick(agentName);
                      }}
                      title="View agent information"
                    >
                      <Info className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              )))
              }
            </div>
          </div>
          
          {/* Selected Agents Summary */}
          {selectedAgents.length > 0 && (
            <>
              <Separator />
              <div className="bg-blue-50 dark:bg-blue-900/20 p-3 rounded">
                <h4 className="font-medium text-sm mb-2">Selected Agents ({selectedAgents.length}):</h4>
                <div className="flex flex-wrap gap-1">
                  {selectedAgents.map((agent, index) => (
                    <span 
                      key={index} 
                      className="text-xs bg-blue-200 dark:bg-blue-800 text-blue-800 dark:text-blue-200 px-2 py-1 rounded"
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

    {/* Agent Info Dialog */}
    {selectedAgentForInfo && (
      <AgentInfoDialog
        open={agentInfoDialogOpen}
        onOpenChange={setAgentInfoDialogOpen}
        agentName={selectedAgentForInfo}
        taskTitle={task?.title}
        onClose={() => {
          setAgentInfoDialogOpen(false);
          setSelectedAgentForInfo(null);
        }}
      />
    )}
    </>
  );
};

export default AgentAssignmentDialog;