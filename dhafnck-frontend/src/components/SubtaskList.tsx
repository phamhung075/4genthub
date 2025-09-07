import { Check, Eye, Pencil, Play, Plus, Trash2, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { deleteSubtask, listSubtasks, createSubtask as newSubtask, updateSubtask as saveSubtask, Subtask, Task, listAgents, getAvailableAgents, callAgent } from "../api";
import { Badge } from "./ui/badge";
import { HolographicStatusBadge, HolographicPriorityBadge } from "./ui/holographic-badges";
import { ShimmerButton } from "./ui/shimmer-button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import { Input } from "./ui/input";
import { Separator } from "./ui/separator";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./ui/table";
import { Checkbox } from "./ui/checkbox";
import ClickableAssignees from "./ClickableAssignees";
import AgentResponseDialog from "./AgentResponseDialog";
import { RefreshButton } from "./ui/refresh-button";
import SubtaskCompleteDialog from "./SubtaskCompleteDialog";

interface SubtaskListProps {
  projectId: string;
  taskTreeId: string;
  parentTaskId: string;
}

const statusColor: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  done: "default",
  in_progress: "secondary",
  review: "secondary",
  testing: "secondary",
  todo: "outline",
  blocked: "destructive",
  cancelled: "destructive",
  archived: "outline"
};

const priorityColor: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  low: "outline",
  medium: "secondary",
  high: "default",
  urgent: "destructive"
};

export function SubtaskList({ projectId, taskTreeId, parentTaskId }: SubtaskListProps) {
  const [subtasks, setSubtasks] = useState<Subtask[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [showEdit, setShowEdit] = useState<Subtask | null>(null);
  const [showDelete, setShowDelete] = useState<Subtask | null>(null);
  const [showDetails, setShowDetails] = useState<Subtask | null>(null);
  const [showComplete, setShowComplete] = useState<Subtask | null>(null);
  const [form, setForm] = useState<Partial<Subtask>>({ title: "", description: "", priority: "medium", status: "todo" });
  const [saving, setSaving] = useState(false);
  const [agents, setAgents] = useState<any[]>([]);
  const [availableAgents, setAvailableAgents] = useState<string[]>([]);
  const [showAssignDialog, setShowAssignDialog] = useState(false);
  const [selectedAgents, setSelectedAgents] = useState<string[]>([]);
  const [assigningSubtask, setAssigningSubtask] = useState<Subtask | null>(null);
  const [callingAgent, setCallingAgent] = useState(false);
  const [agentResponses, setAgentResponses] = useState<Record<string, any>>({});
  const [showAgentResponse, setShowAgentResponse] = useState(false);
  const [currentAgentResponse, setCurrentAgentResponse] = useState<{
    agent: string;
    task: string;
    response?: any;
    error?: string;
    timestamp: string;
  } | null>(null);

  const fetchSubtasks = () => {
    setLoading(true);
    listSubtasks(parentTaskId)
      .then(data => {
        console.log('Fetched subtasks:', data);
        data.forEach((subtask, index) => {
          console.log(`Subtask ${index} assignees:`, {
            raw: subtask.assignees,
            type: typeof subtask.assignees,
            isArray: Array.isArray(subtask.assignees),
            stringified: JSON.stringify(subtask.assignees)
          });
        });
        setSubtasks(data);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchSubtasks();
  }, [projectId, taskTreeId, parentTaskId]);

  // Lazy load agents only when needed
  const loadAgentsIfNeeded = async () => {
    if (agents.length === 0) {
      try {
        const [projectAgents, availableAgentsList] = await Promise.all([
          listAgents(),
          getAvailableAgents()
        ]);
        setAgents(projectAgents);
        setAvailableAgents(availableAgentsList);
      } catch (e) {
        console.error('Error fetching agents:', e);
      }
    }
  };

  const handleCreate = async () => {
    setSaving(true);
    try {
      await newSubtask(parentTaskId, { ...form });
      setShowCreate(false);
      setForm({ title: "", description: "", priority: "medium", status: "todo" });
      fetchSubtasks();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (subtask: Subtask) => {
    setShowEdit(subtask);
    setForm({
      title: subtask.title,
      description: subtask.description || "",
      priority: subtask.priority || "medium",
      status: subtask.status || "todo"
    });
  };

  const handleDelete = async (subtaskId: string) => {
    if (!subtaskId) return;
    setSaving(true);
    try {
      await deleteSubtask(subtaskId);
      setShowDelete(null);
      fetchSubtasks();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const openAssignDialog = async (subtask: Subtask) => {
    console.log('Opening assign dialog for subtask:', subtask);
    setAssigningSubtask(subtask);
    
    // Clean existing assignees to avoid invalid data
    const existingAssignees = Array.isArray(subtask.assignees) 
      ? subtask.assignees.filter(a => {
          const trimmed = (a || '').toString().trim();
          return trimmed && trimmed !== '[' && trimmed !== ']' && trimmed !== '[]';
        })
      : [];
    
    console.log('Existing assignees after cleaning:', existingAssignees);
    setSelectedAgents(existingAssignees);
    await loadAgentsIfNeeded(); // Load agents only when needed
    setShowAssignDialog(true);
  };

  const handleAssignAgents = async () => {
    if (!assigningSubtask) return;
    
    setSaving(true);
    
    // Clean selected agents to ensure no invalid data
    const cleanedAgents = selectedAgents.filter(agent => {
      const trimmed = agent.trim();
      return trimmed && trimmed !== '[' && trimmed !== ']' && trimmed !== '[]';
    });
    
    console.log('Assigning agents to subtask:', assigningSubtask.id, 'Agents:', cleanedAgents);
    
    try {
      const result = await saveSubtask(assigningSubtask.id, { assignees: cleanedAgents });
      console.log('Assignment result:', result);
      
      if (!result) {
        throw new Error('No response from server');
      }
      
      // Verify the update was successful
      if (result.assignees) {
        console.log('Successfully updated assignees to:', result.assignees);
      }
      
      setShowAssignDialog(false);
      setAssigningSubtask(null);
      setSelectedAgents([]);
      setAgentResponses({});
      await fetchSubtasks();
    } catch (e) {
      console.error('Error assigning agents:', e);
      console.error('Error details:', {
        error: e,
        taskId: parentTaskId,
        subtaskId: assigningSubtask?.id,
        agents: cleanedAgents
      });
      alert(`Failed to assign agents: ${e instanceof Error ? e.message : 'Unknown error'}`);
    } finally {
      setSaving(false);
    }
  };

  const toggleAgentSelection = (agentId: string) => {
    setSelectedAgents(prev => 
      prev.includes(agentId) 
        ? prev.filter(id => id !== agentId)
        : [...prev, agentId]
    );
  };

  const handleCallAgent = async (agentName: string, subtask: Subtask) => {
    try {
      console.log('Calling agent:', agentName, 'for subtask:', subtask.title);
      const result = await callAgent(agentName, {});
      
      // Set response data and show dialog
      setCurrentAgentResponse({
        agent: agentName,
        task: subtask.title,
        response: result,
        timestamp: new Date().toISOString()
      });
      setShowAgentResponse(true);
      
    } catch (e) {
      console.error('Error calling agent:', e);
      
      // Set error data and show dialog
      setCurrentAgentResponse({
        agent: agentName,
        task: subtask.title,
        error: e instanceof Error ? e.message : 'Unknown error',
        timestamp: new Date().toISOString()
      });
      setShowAgentResponse(true);
    }
  };

  const closeAgentResponseDialog = () => {
    setShowAgentResponse(false);
    setCurrentAgentResponse(null);
  };

  const handleSubtaskComplete = async (completedSubtask: any) => {
    // Update the subtask in the list
    setSubtasks(prevSubtasks => 
      prevSubtasks.map(s => s.id === completedSubtask.id ? { ...s, status: 'done' } : s)
    );
    setShowComplete(null);
    // Refresh the list
    fetchSubtasks();
  };

  if (loading) return <div className="text-xs text-muted-foreground px-2 py-1">Loading subtasks...</div>;
  if (error) return <div className="text-xs text-destructive px-2 py-1">Error: {error}</div>;

  return (
    <div className="overflow-x-auto theme-context-section rounded-lg p-4 border border-surface-border">
      <div className="flex justify-between items-center mb-2">
        <h3 className="text-sm font-semibold">Subtasks</h3>
        <div className="flex gap-2">
          <RefreshButton 
            onClick={fetchSubtasks} 
            loading={loading}
            size="sm"
          />
          <ShimmerButton size="sm" variant="default" className="flex items-center gap-1" onClick={() => { setShowCreate(true); setForm({ title: "", description: "", priority: "medium", status: "pending" }); }}>
            <Plus className="w-4 h-4" /> New Subtask
          </ShimmerButton>
        </div>
      </div>
      <Table className="bg-surface rounded-lg shadow-md border border-surface-border">
        <TableHeader>
          <TableRow>
            <TableHead>Title</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Priority</TableHead>
            <TableHead>Assignees</TableHead>
            <TableHead>Due Date</TableHead>
            <TableHead className="w-24">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {subtasks.length === 0 ? (
            <TableRow>
              <TableCell colSpan={6} className="text-center text-xs text-muted-foreground">No subtasks found.</TableCell>
            </TableRow>
          ) : (
            subtasks.map((subtask) => (
              <TableRow key={subtask.id} className="hover:bg-accent/30 transition-all">
                <TableCell className="font-medium max-w-xs truncate" title={subtask.title}>{String(subtask.title)}</TableCell>
                <TableCell>
                  <HolographicStatusBadge 
                    status={(subtask.status || "todo") as any}
                    size="xs"
                  />
                </TableCell>
                <TableCell>
                  <HolographicPriorityBadge 
                    priority={(subtask.priority || "medium") as any}
                    size="xs"
                  />
                </TableCell>
                <TableCell className="max-w-xs">
                  <ClickableAssignees
                    assignees={subtask.assignees || []}
                    task={subtask}
                    onAgentClick={handleCallAgent}
                    variant="secondary"
                  />
                </TableCell>
                <TableCell>
                  {subtask.due_date ? (
                    <span className="text-xs">{String(subtask.due_date)}</span>
                  ) : (
                    <span className="text-muted-foreground text-xs">—</span>
                  )}
                </TableCell>
                <TableCell>
                  <div className="flex gap-1">
                    <ShimmerButton size="icon" variant="ghost" className="hover:bg-primary/10" onClick={() => setShowDetails(subtask)} title="View details">
                      <Eye className="w-4 h-4 text-muted-foreground" />
                    </ShimmerButton>
                    <ShimmerButton size="icon" variant="ghost" className="hover:bg-primary/10" onClick={() => openAssignDialog(subtask)} title="Assign agents">
                      <Users className="w-4 h-4 text-muted-foreground" />
                    </ShimmerButton>
                    <ShimmerButton size="icon" variant="ghost" className="hover:bg-primary/10" onClick={() => handleEdit(subtask)} title="Edit subtask">
                      <Pencil className="w-4 h-4 text-muted-foreground" />
                    </ShimmerButton>
                    {subtask.status !== 'done' && (
                      <ShimmerButton size="icon" variant="ghost" className="hover:bg-primary/10" onClick={() => setShowComplete(subtask)} title="Complete subtask">
                        <Check className="w-4 h-4 text-muted-foreground" />
                      </ShimmerButton>
                    )}
                    <ShimmerButton size="icon" variant="ghost" className="hover:text-destructive" onClick={() => setShowDelete(subtask)} title="Delete subtask">
                      <Trash2 className="w-4 h-4" />
                    </ShimmerButton>
                  </div>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
      {/* Create Subtask Dialog */}
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>New Subtask</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-3">
            <div>
              <label className="text-sm font-medium mb-2 block">Title</label>
              <Input
                placeholder="Subtask title"
                value={form.title || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setForm(f => ({ ...f, title: e.target.value }))}
                disabled={saving}
                autoFocus
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Description</label>
              <Input
                placeholder="Subtask description"
                value={form.description || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setForm(f => ({ ...f, description: e.target.value }))}
                disabled={saving}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Status</label>
              <select
                className="w-full p-2 border border-gray-300 rounded-md"
                value={form.status || "todo"}
                onChange={(e) => setForm(f => ({ ...f, status: e.target.value }))}
                disabled={saving}
              >
                <option value="todo">Todo</option>
                <option value="in_progress">In Progress</option>
                <option value="review">Review</option>
                <option value="testing">Testing</option>
                <option value="done">Done</option>
                <option value="blocked">Blocked</option>
                <option value="cancelled">Cancelled</option>
                <option value="archived">Archived</option>
              </select>
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Priority</label>
              <select
                className="w-full p-2 border border-gray-300 rounded-md"
                value={form.priority || "medium"}
                onChange={(e) => setForm(f => ({ ...f, priority: e.target.value }))}
                disabled={saving}
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
            </div>
          </div>
          <DialogFooter>
            <ShimmerButton variant="secondary" onClick={() => setShowCreate(false)} disabled={saving}>Cancel</ShimmerButton>
            <ShimmerButton variant="default" onClick={handleCreate} disabled={saving || !form.title?.trim()}>
              {saving ? <Check className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />} Create
            </ShimmerButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      {/* Edit Subtask Dialog */}
      <Dialog open={!!showEdit} onOpenChange={v => { if (!v) setShowEdit(null); }}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Edit Subtask</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-3">
            <div>
              <label className="text-sm font-medium mb-2 block">Title</label>
              <Input
                placeholder="Subtask title"
                value={form.title || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setForm(f => ({ ...f, title: e.target.value }))}
                disabled={saving}
                autoFocus
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Description</label>
              <Input
                placeholder="Subtask description"
                value={form.description || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setForm(f => ({ ...f, description: e.target.value }))}
                disabled={saving}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Status</label>
              <select
                className="w-full p-2 border border-gray-300 rounded-md"
                value={form.status || "todo"}
                onChange={(e) => setForm(f => ({ ...f, status: e.target.value }))}
                disabled={saving}
              >
                <option value="todo">Todo</option>
                <option value="in_progress">In Progress</option>
                <option value="review">Review</option>
                <option value="testing">Testing</option>
                <option value="done">Done</option>
                <option value="blocked">Blocked</option>
                <option value="cancelled">Cancelled</option>
                <option value="archived">Archived</option>
              </select>
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Priority</label>
              <select
                className="w-full p-2 border border-gray-300 rounded-md"
                value={form.priority || "medium"}
                onChange={(e) => setForm(f => ({ ...f, priority: e.target.value }))}
                disabled={saving}
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
            </div>
          </div>
          <DialogFooter>
            <ShimmerButton variant="secondary" onClick={() => setShowEdit(null)} disabled={saving}>Cancel</ShimmerButton>
            <ShimmerButton variant="default" onClick={() => {
              setSaving(true);
              const updateData = {
                title: form.title,
                description: form.description,
                priority: form.priority,
                status: form.status
              };
              saveSubtask(showEdit!.id, updateData)
                .then(() => {
                  setShowEdit(null);
                  setForm({ title: "", description: "", priority: "medium", status: "todo" });
                  fetchSubtasks();
                })
                .catch((e) => {
                  setError(e.message);
                })
                .finally(() => setSaving(false));
            }} disabled={saving || !form.title?.trim()}>
              {saving ? <Check className="w-4 h-4 animate-spin" /> : <Pencil className="w-4 h-4" />} Save
            </ShimmerButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      {/* Delete Subtask Dialog */}
      <Dialog open={!!showDelete} onOpenChange={v => { if (!v) setShowDelete(null); }}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Delete Subtask</DialogTitle>
          </DialogHeader>
          <p>Are you sure you want to delete this subtask: <strong>{showDelete?.title}</strong>?</p>
          <DialogFooter>
            <ShimmerButton variant="secondary" onClick={() => setShowDelete(null)} disabled={saving}>Cancel</ShimmerButton>
            <ShimmerButton variant="default" className="bg-destructive text-destructive-foreground hover:bg-destructive/90" onClick={() => handleDelete(showDelete!.id)} disabled={saving}>
              {saving ? <Check className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />} Delete
            </ShimmerButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      {/* Subtask Details Dialog */}
      <Dialog open={!!showDetails} onOpenChange={v => { if (!v) setShowDetails(null); }}>
        <DialogContent className="max-w-4xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-xl text-left">Subtask Details - Complete Information</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {/* Subtask Information Header */}
            <div className="theme-context-section p-4 rounded-lg">
              <h3 className="text-lg font-semibold">{showDetails?.title}</h3>
              {showDetails?.description && (
                <p className="text-sm text-muted-foreground mt-2">{showDetails.description}</p>
              )}
              <div className="flex gap-2 mt-3 flex-wrap items-center">
                <span className="text-sm text-muted-foreground">Status:</span>
                <HolographicStatusBadge 
                  status={(showDetails?.status || "todo") as any}
                  size="sm"
                />
                <span className="text-sm text-muted-foreground ml-2">Priority:</span>
                <HolographicPriorityBadge 
                  priority={(showDetails?.priority || "medium") as any}
                  size="sm"
                />
                {showDetails?.completed !== undefined && (
                  <Badge 
                    variant={showDetails.completed ? "default" : "secondary"} 
                    className="px-3 py-1"
                  >
                    {showDetails.completed ? "Completed" : "Not Completed"}
                  </Badge>
                )}
              </div>
            </div>

            <Separator />

            {/* IDs and References */}
            <div>
              <h4 className="font-semibold text-sm mb-3 text-blue-700">IDs and References</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm bg-surface-hover p-3 rounded">
                <div className="space-y-1">
                  <span className="text-muted-foreground font-medium">Subtask ID:</span>
                  <p className="font-mono text-xs break-all">{showDetails?.id}</p>
                </div>
                <div className="space-y-1">
                  <span className="text-muted-foreground font-medium">Parent Task ID:</span>
                  <p className="font-mono text-xs break-all">{showDetails?.parent_task_id || parentTaskId}</p>
                </div>
              </div>
            </div>

            <Separator />

            {/* Time Information */}
            <div>
              <h4 className="font-semibold text-sm mb-3 text-green-700">Time Information</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm bg-surface-hover p-3 rounded">
                {showDetails?.estimated_effort && (
                  <div>
                    <span className="text-muted-foreground font-medium">Estimated Effort:</span>
                    <p className="font-semibold">{showDetails.estimated_effort}</p>
                  </div>
                )}
                {showDetails?.due_date && (
                  <div>
                    <span className="text-muted-foreground font-medium">Due Date:</span>
                    <p>{new Date(showDetails.due_date).toLocaleDateString()} ({new Date(showDetails.due_date).toLocaleTimeString()})</p>
                  </div>
                )}
                {showDetails?.created_at && (
                  <div>
                    <span className="text-muted-foreground font-medium">Created:</span>
                    <p>{new Date(showDetails.created_at).toLocaleDateString()} at {new Date(showDetails.created_at).toLocaleTimeString()}</p>
                  </div>
                )}
                {showDetails?.updated_at && (
                  <div>
                    <span className="text-muted-foreground font-medium">Last Updated:</span>
                    <p>{new Date(showDetails.updated_at).toLocaleDateString()} at {new Date(showDetails.updated_at).toLocaleTimeString()}</p>
                  </div>
                )}
              </div>
            </div>

            <Separator />

            {/* Progress and Assignment */}
            <div>
              <h4 className="font-semibold text-sm mb-3 text-purple-700">Progress & Assignment</h4>
              <div className="space-y-3 bg-surface-hover p-3 rounded">
                {/* Progress */}
                {(showDetails?.progress !== undefined || showDetails?.progress_percentage !== undefined) && (
                  <div>
                    <span className="text-muted-foreground font-medium">Progress:</span>
                    <div className="mt-2">
                      <div className="flex items-center gap-2">
                        <div className="flex-1 theme-context-section rounded-full h-2">
                          <div 
                            className="bg-blue-600 h-2 rounded-full transition-all"
                            style={{ width: `${showDetails?.progress || showDetails?.progress_percentage || 0}%` }}
                          />
                        </div>
                        <span className="text-sm font-medium">{showDetails?.progress || showDetails?.progress_percentage || 0}%</span>
                      </div>
                    </div>
                  </div>
                )}
                
                {/* Assignees */}
                {showDetails?.assignees && showDetails.assignees.length > 0 && (
                  <div>
                    <span className="text-muted-foreground font-medium">Assignees:</span>
                    <div className="mt-1">
                      <ClickableAssignees
                        assignees={Array.isArray(showDetails.assignees) ? showDetails.assignees : [showDetails.assignees]}
                        task={showDetails}
                        onAgentClick={handleCallAgent}
                        variant="secondary"
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Additional Properties */}
            <Separator />
            <div>
              <h4 className="font-semibold text-sm mb-3 text-orange-700">Additional Properties</h4>
              <div className="bg-surface-hover p-3 rounded">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                  {/* Check for any additional fields */}
                  {Object.entries(showDetails || {}).map(([key, value]) => {
                    // Skip already displayed fields
                    const skipFields = ['id', 'title', 'description', 'status', 'priority', 'assignees', 
                                      'due_date', 'created_at', 'updated_at', 'estimated_effort', 
                                      'progress', 'progress_percentage', 'parent_task_id', 'completed'];
                    if (skipFields.includes(key) || value === null || value === undefined) return null;
                    
                    return (
                      <div key={key} className="space-y-1">
                        <span className="text-muted-foreground font-medium capitalize">
                          {key.replace(/_/g, ' ')}:
                        </span>
                        <p className="text-sm break-all">
                          {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                        </p>
                      </div>
                    );
                  }).filter(Boolean)}
                </div>
              </div>
            </div>

            {/* Raw Data */}
            <Separator />
            <details className="cursor-pointer">
              <summary className="font-semibold text-sm text-text hover:text-text">
                View Complete Raw Subtask Data (JSON)
              </summary>
              <div className="mt-3 theme-context-section p-3 rounded">
                <pre className="text-xs overflow-x-auto whitespace-pre-wrap">
                  {JSON.stringify(showDetails, null, 2)}
                </pre>
              </div>
            </details>
          </div>
          <DialogFooter>
            <ShimmerButton variant="outline" onClick={() => setShowDetails(null)}>
              Close
            </ShimmerButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Assign Agents Dialog */}
      <Dialog open={showAssignDialog} onOpenChange={(v) => { 
        if (!v) { 
          setShowAssignDialog(false); 
          setAssigningSubtask(null);
          setSelectedAgents([]);
          setAgentResponses({});
        }
      }}>
        <DialogContent className="max-w-5xl w-[90vw]">
          <DialogHeader>
            <DialogTitle className="text-xl text-left">Assign Agents to Subtask</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="theme-context-section p-3 rounded">
              <h4 className="font-medium text-sm mb-1">Subtask: {assigningSubtask?.title}</h4>
              {assigningSubtask?.assignees && assigningSubtask.assignees.length > 0 && (
                <p className="text-xs text-muted-foreground">
                  Currently assigned: {assigningSubtask.assignees.join(', ')}
                </p>
              )}
            </div>
            
            <Separator />
            
            <div>
              <h4 className="font-medium text-sm mb-3">Project Registered Agents</h4>
              {agents.length === 0 ? (
                <p className="text-sm text-muted-foreground">No agents registered in this project</p>
              ) : (
                <div className="space-y-2 max-h-[350px] overflow-y-auto border rounded p-2">
                  {agents.map((agent) => (
                    <div key={agent.id || agent.name} className="flex items-center space-x-2 p-2 hover:theme-context-section rounded">
                      <Checkbox
                        id={`subtask-${agent.id || agent.name}`}
                        checked={selectedAgents.includes(agent.id || agent.name)}
                        onCheckedChange={() => toggleAgentSelection(agent.id || agent.name)}
                      />
                      <label
                        htmlFor={`subtask-${agent.id || agent.name}`}
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
            
            <div>
              <h4 className="font-medium text-sm mb-3">Available Agents from Library</h4>
              <div className="space-y-2 max-h-[500px] overflow-y-auto border rounded p-2">
                {availableAgents.map((agentName) => (
                  <div key={agentName} className="border rounded p-2 hover:theme-context-section">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <Checkbox
                          id={`subtask-lib-${agentName}`}
                          checked={selectedAgents.includes(agentName)}
                          onCheckedChange={() => toggleAgentSelection(agentName)}
                        />
                        <label
                          htmlFor={`subtask-lib-${agentName}`}
                          className="cursor-pointer"
                        >
                          <p className="font-medium text-sm">{agentName}</p>
                          <p className="text-xs text-muted-foreground">From agent library</p>
                        </label>
                      </div>
                      <ShimmerButton
                        size="icon"
                        variant="ghost"
                        className="h-8 w-8"
                        onClick={async () => {
                          setCallingAgent(true);
                          try {
                            const result = await callAgent(agentName, {});
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
                        }}
                        disabled={callingAgent}
                        title="Activate this agent"
                      >
                        <Play className="w-4 h-4" />
                      </ShimmerButton>
                    </div>
                    {agentResponses[agentName] && (
                      <div className="mt-2 p-2 theme-context-section rounded">
                        <p className="text-xs font-medium mb-1">Call Agent Response:</p>
                        <pre className="text-xs overflow-x-auto whitespace-pre-wrap bg-surface p-2 rounded border border-surface-border text-text">
                          {JSON.stringify(agentResponses[agentName], null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
          <DialogFooter>
            <ShimmerButton variant="outline" onClick={() => { setShowAssignDialog(false); setAssigningSubtask(null); }}>
              Cancel
            </ShimmerButton>
            <ShimmerButton 
              variant="default" 
              onClick={handleAssignAgents}
              disabled={saving}
            >
              {saving ? "Saving..." : "Assign Agents"}
            </ShimmerButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Agent Response Dialog */}
      <AgentResponseDialog
        open={showAgentResponse}
        onOpenChange={setShowAgentResponse}
        agentResponse={currentAgentResponse}
        onClose={closeAgentResponseDialog}
      />
      
      {/* Subtask Complete Dialog */}
      <SubtaskCompleteDialog
        open={!!showComplete}
        onOpenChange={(v) => { if (!v) setShowComplete(null); }}
        subtask={showComplete}
        parentTaskId={parentTaskId}
        onClose={() => setShowComplete(null)}
        onComplete={handleSubtaskComplete}
      />
    </div>
  );
} 