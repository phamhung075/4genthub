import React, { useEffect, useState } from "react";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import { Separator } from "./ui/separator";
import { Task, Subtask, getTask, getTaskContext } from "../api";
import ClickableAssignees from "./ClickableAssignees";
import { formatContextDisplay } from "../utils/contextHelpers";
import logger from "../utils/logger";
import { FileText, Info, ChevronDown, ChevronRight, Hash, Calendar, Tag, Layers, Copy, Check as CheckIcon, Settings, Shield, Database, Globe, FolderOpen, Code, GitBranch } from "lucide-react";
import RawJSONDisplay from "./ui/RawJSONDisplay";
import { EnhancedJSONViewer } from "./ui/EnhancedJSONViewer";
import { CopyableId } from "./ui/CopyableId";
import { ProgressHistoryTimeline } from "./ProgressHistoryTimeline";

interface TaskDetailsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  task: Task | null;
  onClose: () => void;
  onAgentClick: (agentName: string, task: Task | Subtask) => void;
}

export const TaskDetailsDialog: React.FC<TaskDetailsDialogProps> = ({
  open,
  onOpenChange,
  task,
  onClose,
  onAgentClick
}) => {
  const [fullTask, setFullTask] = useState<Task | null>(null);
  const [taskContext, setTaskContext] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [contextLoading, setContextLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'details' | 'context'>('details');
  const [jsonCopied, setJsonCopied] = useState(false);

  // Set initial task when it changes - but don't clear if null
  useEffect(() => {
    logger.debug('[TaskDetailsDialog] Task prop changed:', task);
    // Check if task is the full response object or just the task
    const taskData = task?.task || task;
    if (taskData && taskData.id) {
      logger.debug('[TaskDetailsDialog] Setting fullTask from prop:', taskData);
      setFullTask(taskData);
    } else {
      logger.debug('[TaskDetailsDialog] Task prop is null or has no ID, not clearing fullTask');
    }
  }, [task]);

  // Fetch full task with context when dialog opens
  useEffect(() => {
    // Only fetch if we have a task ID, either from prop or from fullTask
    const taskId = task?.id || fullTask?.id;
    logger.debug('[TaskDetailsDialog] Dialog open:', open, 'TaskID:', taskId, 'Task prop:', task, 'FullTask:', fullTask);
    
    if (open && taskId) {
      setLoading(true);
      setContextLoading(true);
      
      logger.debug('[TaskDetailsDialog] Fetching task details for ID:', taskId);
      // Fetch task details
      getTask(taskId) // Fixed: removed invalid second parameter
        .then(fetchedTask => {
          logger.debug('[TaskDetailsDialog] Fetched task:', fetchedTask);
          // Extract the task from the response structure
          const taskData = fetchedTask?.task || fetchedTask;
          if (taskData && taskData.id) {
            logger.debug('[TaskDetailsDialog] Setting fullTask to:', taskData);
            setFullTask(taskData);
          } else {
            logger.warn('[TaskDetailsDialog] No valid task data in response');
          }
          // Don't clear on failure - keep the initial task data
        })
        .catch(error => {
          logger.error('[TaskDetailsDialog] Error fetching task:', error);
          // Don't overwrite with null - keep existing data
        })
        .finally(() => {
          setLoading(false);
        });
      
      // Fetch task context separately
      getTaskContext(taskId)
        .then(context => {
          logger.debug('Raw context response:', context);
          
          // Extract the actual context data from the response
          if (context) {
            if (context.data && context.data.resolved_context) {
              // New format: data.resolved_context contains the actual context
              logger.debug('Using resolved_context from data:', context.data.resolved_context);
              setTaskContext(context.data.resolved_context);
            } else if (context.resolved_context) {
              // Alternative format: resolved_context at root level
              logger.debug('Using resolved_context from root:', context.resolved_context);
              setTaskContext(context.resolved_context);
            } else if (context.data) {
              // Fallback: use data object if it exists
              logger.debug('Using data object:', context.data);
              setTaskContext(context.data);
            } else {
              // Last resort: use the whole response
              logger.debug('Using full response:', context);
              setTaskContext(context);
            }
          } else {
            logger.warn('No context data received');
            setTaskContext(null);
          }
        })
        .catch(error => {
          logger.error('Error fetching task context:', error);
          setTaskContext(null);
        })
        .finally(() => {
          setContextLoading(false);
        });
    }
  }, [open, task?.id]);

  // Clear data when dialog closes
  useEffect(() => {
    if (!open) {
      // Delay clearing to avoid flashing when dialog quickly reopens
      const timer = setTimeout(() => {
        setFullTask(null);
        setTaskContext(null);
        setActiveTab('details');
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [open]);

  // Use fullTask if available, otherwise fall back to original task
  // Handle both response object and direct task object
  const rawDisplayTask = fullTask || task;
  const displayTask = rawDisplayTask?.task || rawDisplayTask;
  logger.debug('[TaskDetailsDialog] DisplayTask being used:', displayTask, 'RawDisplayTask:', rawDisplayTask, 'FullTask:', fullTask, 'Task:', task);
  
  // Format context data using helper functions
  const contextDisplay = formatContextDisplay(displayTask?.context_data);
  

  // Copy JSON to clipboard
  const copyJsonToClipboard = () => {
    if (taskContext) {
      const jsonString = JSON.stringify(taskContext, null, 2);
      navigator.clipboard.writeText(jsonString).then(() => {
        setJsonCopied(true);
        setTimeout(() => setJsonCopied(false), 2000);
      }).catch(err => {
        logger.error('Failed to copy JSON:', err);
      });
    }
  };

  
  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent': return 'destructive';
      case 'high': return 'default';
      case 'medium': return 'secondary';
      case 'low': return 'outline';
      default: return 'outline';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'done': return 'default';
      case 'in_progress': return 'secondary';
      case 'review': return 'secondary';
      case 'testing': return 'secondary';
      case 'todo': return 'outline';
      case 'blocked': return 'destructive';
      case 'cancelled': return 'destructive';
      case 'archived': return 'outline';
      default: return 'outline';
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-[90vw] max-w-6xl h-[85vh] mx-auto overflow-hidden rounded-lg shadow-xl flex flex-col bg-[var(--color-surface)]">
        <DialogHeader>
          <DialogTitle className="text-xl text-left">
            {displayTask?.title || 'Task Details'}
          </DialogTitle>
          
          {/* Tab Navigation */}
          <div className="flex gap-1 mt-4 border-b">
            <button
              onClick={() => setActiveTab('details')}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors border-b-2 ${
                activeTab === 'details'
                  ? 'text-text dark:text-text border-text dark:border-text'
                  : 'text-text-secondary border-transparent hover:text-text'
              }`}
            >
              <Info className="w-4 h-4" />
              Details
              {loading && <span className="text-xs">(Loading...)</span>}
            </button>
            
            <button
              onClick={() => setActiveTab('context')}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors border-b-2 ${
                activeTab === 'context'
                  ? 'text-text dark:text-text border-text dark:border-text'
                  : 'text-text-secondary border-transparent hover:text-text'
              }`}
            >
              <FileText className="w-4 h-4" />
              Context
              {contextLoading && <span className="text-xs">(Loading...)</span>}
              {!contextLoading && taskContext && Object.keys(taskContext).length > 0 && (
                <Badge variant="secondary" className="text-xs">Available</Badge>
              )}
            </button>
          </div>
        </DialogHeader>
        
        <div className="flex-1 overflow-hidden flex flex-col">
          {/* Details Tab Content */}
          {activeTab === 'details' && (
            <div className="space-y-4 overflow-y-auto flex-1 p-4" style={{backgroundColor: 'var(--color-background)'}}>
              {/* Task Information Header */}
              <div className="theme-context-section p-4 rounded-lg">
                <div className="flex gap-2 mt-3 flex-wrap">
                  <Badge variant={getStatusColor(displayTask?.status || 'pending')} className="px-3 py-1">
                    Status: {displayTask?.status?.replace('_', ' ') || 'pending'}
                  </Badge>
                  <Badge variant={getPriorityColor(displayTask?.priority || 'medium')} className="px-3 py-1">
                    Priority: {displayTask?.priority || 'medium'}
                  </Badge>
                </div>
                {displayTask?.description && (
                  <p className="text-sm text-muted-foreground mt-2">{displayTask.description}</p>
                )}
                {displayTask?.assignees && displayTask.assignees.length > 0 && (
                  <div className="mt-3">
                    <span className="text-sm text-muted-foreground">Assigned to: </span>
                    <span className="text-sm font-medium">{displayTask.assignees.join(', ')}</span>
                  </div>
                )}
              </div>

              {/* All Task Details */}
              {displayTask && (
                <div className="space-y-4">
                  {/* IDs and References */}
                  <div>
                    <h4 className="font-semibold text-sm mb-3 text-text dark:text-text">IDs and References</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm theme-context-metadata">
                      <div className="space-y-1">
                        <span className="text-muted-foreground font-medium">Task ID:</span>
                        <CopyableId
                          id={displayTask.id}
                          variant="block"
                          size="xs"
                          abbreviated={false}
                          showCopyButton={true}
                        />
                      </div>
                      {displayTask.git_branch_id && (
                        <div className="space-y-1">
                          <span className="text-muted-foreground font-medium">Git Branch ID:</span>
                          <CopyableId
                            id={displayTask.git_branch_id}
                            variant="block"
                            size="xs"
                            abbreviated={true}
                            showCopyButton={true}
                          />
                        </div>
                      )}
                      {displayTask.context_id && (
                        <div className="space-y-1">
                          <span className="text-muted-foreground font-medium">Context ID:</span>
                          <CopyableId
                            id={displayTask.context_id}
                            variant="block"
                            size="xs"
                            abbreviated={true}
                            showCopyButton={true}
                          />
                        </div>
                      )}
                    </div>
                  </div>

                  <Separator />

                  {/* Time Information */}
                  <div>
                    <h4 className="font-semibold text-sm mb-3 text-text dark:text-text">Time Information</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm theme-context-data">
                      {displayTask.estimated_effort && (
                        <div>
                          <span className="text-muted-foreground font-medium">Estimated Effort:</span>
                          <p className="font-semibold">{displayTask.estimated_effort}</p>
                        </div>
                      )}
                      {displayTask.due_date && (
                        <div>
                          <span className="text-muted-foreground font-medium">Due Date:</span>
                          <p>{new Date(displayTask.due_date).toLocaleDateString()} ({new Date(displayTask.due_date).toLocaleTimeString()})</p>
                        </div>
                      )}
                      {displayTask.created_at && (
                        <div>
                          <span className="text-muted-foreground font-medium">Created:</span>
                          <p>{new Date(displayTask.created_at).toLocaleDateString()} at {new Date(displayTask.created_at).toLocaleTimeString()}</p>
                        </div>
                      )}
                      {displayTask.updated_at && (
                        <div>
                          <span className="text-muted-foreground font-medium">Last Updated:</span>
                          <p>{new Date(displayTask.updated_at).toLocaleDateString()} at {new Date(displayTask.updated_at).toLocaleTimeString()}</p>
                        </div>
                      )}
                    </div>
                  </div>

                  <Separator />

                  {/* Assignment & Organization */}
                  <div>
                    <h4 className="font-semibold text-sm mb-3 text-text dark:text-text">Assignment & Organization</h4>
                    <div className="space-y-3 theme-context-insights">
                      {/* Progress History Timeline */}
                      {displayTask.progress_history && (
                        <div>
                          <ProgressHistoryTimeline
                            progressHistory={displayTask.progress_history}
                            progressCount={displayTask.progress_count}
                            variant="full"
                            className="mt-1"
                          />
                        </div>
                      )}
                      
                      {/* Assignees */}
                      {displayTask.assignees && displayTask.assignees.length > 0 && (
                        <div>
                          <span className="text-muted-foreground font-medium">Assignees:</span>
                          <div className="mt-1">
                            <ClickableAssignees
                              assignees={displayTask.assignees}
                              task={displayTask}
                              onAgentClick={onAgentClick}
                              variant="secondary"
                            />
                          </div>
                        </div>
                      )}
                      
                      {/* Labels */}
                      {displayTask.labels && displayTask.labels.length > 0 && (
                        <div>
                          <span className="text-muted-foreground font-medium">Labels:</span>
                          <div className="mt-1 flex flex-wrap gap-1">
                            {displayTask.labels.map((label: string, index: number) => (
                              <Badge key={index} variant="outline" className="px-2">
                                {label}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Dependencies */}
                  {displayTask.dependencies && displayTask.dependencies.length > 0 && (
                    <>
                      <Separator />
                      <div>
                        <h4 className="font-semibold text-sm mb-3 text-text dark:text-text">Dependencies ({displayTask.dependencies.length})</h4>
                        <div className="space-y-2 theme-context-progress">
                          {displayTask.dependencies.map((dep: string, index: number) => (
                            <div key={index} className="text-sm flex items-start">
                              <span className="text-muted-foreground font-medium mr-2">#{index + 1}:</span>
                              <span className="font-mono text-xs break-all">{dep}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </>
                  )}

                  {/* Subtasks Summary */}
                  {displayTask.subtasks && Array.isArray(displayTask.subtasks) && (
                    <>
                      <Separator />
                      <div>
                        <h4 className="font-semibold text-sm mb-3 text-text dark:text-text">Subtasks Summary</h4>
                        <div className="theme-context-metadata">
                          {displayTask.subtasks.length > 0 ? (
                            <>
                              <p className="text-sm font-medium">Total subtasks: {displayTask.subtasks.length}</p>
                              <p className="text-xs text-muted-foreground mt-1">
                                View full subtask details in the Subtasks tab
                              </p>
                              {/* Enhanced subtask ID display with copy functionality */}
                              {displayTask.subtasks.filter((id: any) => typeof id === 'string' && id.length > 0).length > 0 ? (
                                <div className="mt-3 space-y-2">
                                  {displayTask.subtasks
                                    .filter((id: any) => typeof id === 'string' && id.length > 0)
                                    .map((subtaskId: string, index: number) => (
                                      <div key={index} className="flex items-center gap-2">
                                        <span className="text-xs text-muted-foreground">#{index + 1}:</span>
                                        <CopyableId
                                          id={subtaskId}
                                          variant="badge"
                                          size="xs"
                                          abbreviated={true}
                                          showCopyButton={true}
                                          className="flex-1"
                                        />
                                      </div>
                                    ))}
                                </div>
                              ) : (
                                <p className="text-xs text-muted-foreground mt-2 italic">
                                  Subtask IDs not available. View Subtasks tab for details.
                                </p>
                              )}
                            </>
                          ) : (
                            <p className="text-sm text-muted-foreground">
                              No subtasks associated with this task.
                            </p>
                          )}
                        </div>
                      </div>
                    </>
                  )}

                  {/* Context Data - Moved to Context Tab */}
                  {displayTask.context_data && (
                    <>
                      <Separator />
                      
                      {/* Enhanced Context Display */}
                      {contextDisplay.hasInfo && (
                        <div>
                          <h4 className="font-semibold text-sm mb-3 text-text dark:text-text">Task Completion Details</h4>
                          <div className="theme-context-completion space-y-3">
                        
                        {/* Completion Summary */}
                        {contextDisplay.completionSummary && (
                          <div>
                            <h5 className="font-medium text-xs text-text-secondary dark:text-text-secondary mb-1">
                              Completion Summary{contextDisplay.isLegacy ? ' (Legacy)' : ''}:
                            </h5>
                            <p className={`text-sm whitespace-pre-wrap p-2 rounded border ${contextDisplay.isLegacy ? 'theme-context-progress' : 'theme-card'}`}>
                              {contextDisplay.completionSummary}
                            </p>
                            {contextDisplay.completionPercentage && (
                              <p className="text-xs text-muted-foreground mt-1">
                                Completion: {contextDisplay.completionPercentage}%
                              </p>
                            )}
                            {contextDisplay.isLegacy && (
                              <p className="text-xs text-muted-foreground mt-1 italic">
                                Note: Using legacy completion_summary format
                              </p>
                            )}
                          </div>
                        )}

                        {/* Task Status */}
                        {contextDisplay.taskStatus && (
                          <div>
                            <h5 className="font-medium text-xs text-text-secondary dark:text-text-secondary mb-1">Context Status:</h5>
                            <span className="inline-block px-2 py-1 theme-context-metadata text-xs font-medium">
                              {contextDisplay.taskStatus}
                            </span>
                          </div>
                        )}

                        {/* Testing Notes */}
                        {contextDisplay.testingNotes.length > 0 && (
                          <div>
                            <h5 className="font-medium text-xs text-text-secondary dark:text-text-secondary mb-1">Testing Notes & Next Steps:</h5>
                            <ul className="text-sm space-y-1">
                              {contextDisplay.testingNotes.map((step: string, index: number) => (
                                <li key={index} className="theme-card p-2 rounded border-l-4 border-l-text-secondary">
                                  {step}
                                </li>
                              ))}
                            </ul>
                            </div>
                          )}
                          </div>
                        </div>
                      )}

                    </>
                  )}

                  {/* Raw Data */}
                  <Separator />
                  <details className="cursor-pointer">
                    <summary className="font-semibold text-sm text-text hover:text-text">
                      View Complete Raw Task Data (JSON)
                    </summary>
                    <div className="mt-3">
                      <RawJSONDisplay 
                        jsonData={displayTask}
                        title="Task Data"
                        fileName="task.json"
                      />
                    </div>
                  </details>
                </div>
              )}
            </div>
          )}
          
          {/* Context Tab Content */}
          {activeTab === 'context' && (
            <div className="space-y-4 overflow-y-auto flex-1 p-4">
              {contextLoading ? (
                <div className="text-center py-8">
                  <div className="inline-block w-8 h-8 border-3 border-indigo-600 dark:border-indigo-400 border-t-transparent rounded-full animate-spin"></div>
                  <p className="mt-2 text-sm" style={{color: 'var(--color-text-secondary)'}}>Loading context...</p>
                </div>
              ) : taskContext ? (
                <>
                  {/* Context Header */}
                  <div className="p-4 rounded-lg border" style={{backgroundColor: 'var(--color-background-secondary)', borderColor: 'var(--color-surface-border)'}}>
                    <h3 className="text-lg font-semibold flex items-center gap-2" style={{color: 'var(--color-text)'}}>
                      <Layers className="w-5 h-5" />
                      Task Context Data
                    </h3>
                    <p className="text-sm mt-1" style={{color: 'var(--color-text-secondary)'}}>
                      Complete hierarchical view of task context and inherited data
                    </p>
                  </div>
                  
                  {/* Task Execution Section */}
                  {(taskContext.task_data || taskContext.execution_context || taskContext.discovered_patterns || taskContext.local_decisions) && (
                    <div className="rounded-lg border overflow-hidden" style={{backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-surface-border)'}}>
                      <div className="p-3 border-l-4" style={{backgroundColor: 'var(--color-background-tertiary)', borderLeftColor: 'var(--color-success)'}}>
                        <h3 className="font-semibold flex items-center gap-2" style={{color: 'var(--color-text)'}}>
                          <Settings className="w-4 h-4" />
                          Task Execution Details
                        </h3>
                      </div>
                      <div className="p-4 space-y-3">
                        {/* Task Data */}
                        {taskContext.task_data && Object.keys(taskContext.task_data).length > 0 && (
                          <details className="group">
                            <summary className="cursor-pointer font-medium text-sm flex items-center gap-2 hover:opacity-80 transition-opacity" style={{color: 'var(--color-text-secondary)'}}>
                              <ChevronRight className="w-4 h-4 transition-transform group-open:rotate-90" />
                              Task Data
                            </summary>
                            <div className="mt-2 ml-6">
                              <EnhancedJSONViewer data={taskContext.task_data} defaultExpanded={false} maxHeight="max-h-64" />
                            </div>
                          </details>
                        )}
                      
                        {/* Execution Context */}
                        {taskContext.execution_context && Object.keys(taskContext.execution_context).length > 0 && (
                          <details className="group">
                            <summary className="cursor-pointer font-medium text-sm flex items-center gap-2 hover:opacity-80 transition-opacity" style={{color: 'var(--color-text-secondary)'}}>
                              <ChevronRight className="w-4 h-4 transition-transform group-open:rotate-90" />
                              Execution Context
                            </summary>
                            <div className="mt-2 ml-6">
                              <EnhancedJSONViewer data={taskContext.execution_context} defaultExpanded={false} maxHeight="max-h-64" />
                            </div>
                          </details>
                        )}
                      
                        {/* Discovered Patterns */}
                        {taskContext.discovered_patterns && Object.keys(taskContext.discovered_patterns).length > 0 && (
                          <details className="group">
                            <summary className="cursor-pointer font-medium text-sm flex items-center gap-2 hover:opacity-80 transition-opacity" style={{color: 'var(--color-text-secondary)'}}>
                              <ChevronRight className="w-4 h-4 transition-transform group-open:rotate-90" />
                              Discovered Patterns
                            </summary>
                            <div className="mt-2 ml-6">
                              <EnhancedJSONViewer data={taskContext.discovered_patterns} defaultExpanded={false} maxHeight="max-h-64" />
                            </div>
                          </details>
                        )}
                      
                        {/* Local Decisions */}
                        {taskContext.local_decisions && Object.keys(taskContext.local_decisions).length > 0 && (
                          <details className="group">
                            <summary className="cursor-pointer font-medium text-sm flex items-center gap-2 hover:opacity-80 transition-opacity" style={{color: 'var(--color-text-secondary)'}}>
                              <ChevronRight className="w-4 h-4 transition-transform group-open:rotate-90" />
                              Local Decisions
                            </summary>
                            <div className="mt-2 ml-6">
                              <EnhancedJSONViewer data={taskContext.local_decisions} defaultExpanded={false} maxHeight="max-h-64" />
                            </div>
                          </details>
                        )}
                      </div>
                    </div>
                  )}
                  
                  {/* Implementation Notes Section */}
                  {taskContext.implementation_notes && Object.keys(taskContext.implementation_notes).length > 0 && (
                    <div className="rounded-lg border overflow-hidden" style={{backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-surface-border)'}}>
                      <div className="p-3 border-l-4" style={{backgroundColor: 'var(--color-background-tertiary)', borderLeftColor: 'var(--color-secondary)'}}>
                        <h3 className="font-semibold flex items-center gap-2" style={{color: 'var(--color-text)'}}>
                          <FileText className="w-4 h-4" />
                          Implementation Notes
                        </h3>
                      </div>
                      <div className="p-4">
                        <EnhancedJSONViewer data={taskContext.implementation_notes} defaultExpanded={false} maxHeight="max-h-64" />
                      </div>
                    </div>
                  )}
                  
                  {/* Metadata Section */}
                  {taskContext.metadata && (
                    <div className="rounded-lg border overflow-hidden" style={{backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-surface-border)'}}>
                      <div className="p-3 border-l-4" style={{backgroundColor: 'var(--color-background-tertiary)', borderLeftColor: 'var(--color-warning)'}}>
                        <h3 className="font-semibold flex items-center gap-2" style={{color: 'var(--color-text)'}}>
                          <Info className="w-4 h-4" />
                          Metadata & System Information
                        </h3>
                      </div>
                      <div className="p-4">
                        <EnhancedJSONViewer data={taskContext.metadata} defaultExpanded={false} maxHeight="max-h-64" />
                      </div>
                    </div>
                  )}
                  
                  {/* Inheritance Information */}
                  {(taskContext._inheritance || taskContext.inheritance_metadata || taskContext.inheritance_disabled !== undefined) && (
                    <div className="rounded-lg border overflow-hidden" style={{backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-surface-border)'}}>
                      <div className="p-3 border-l-4" style={{backgroundColor: 'var(--color-background-tertiary)', borderLeftColor: 'var(--color-info)'}}>
                        <h3 className="font-semibold flex items-center gap-2" style={{color: 'var(--color-text)'}}>
                          <Layers className="w-4 h-4" />
                          Context Inheritance
                        </h3>
                      </div>
                      <div className="p-4">
                        <EnhancedJSONViewer data={{
                          inheritance_chain: (taskContext._inheritance?.chain || taskContext.inheritance_metadata?.inheritance_chain)?.join(' → ') || 'N/A',
                          inheritance_depth: taskContext._inheritance?.inheritance_depth || taskContext.inheritance_metadata?.inheritance_depth || 0,
                          inheritance_status: taskContext.inheritance_disabled !== undefined ? (taskContext.inheritance_disabled ? 'Disabled' : 'Enabled') : 'Unknown',
                          force_local_only: taskContext.force_local_only || false,
                          ...(taskContext._inheritance || {}),
                          ...(taskContext.inheritance_metadata || {})
                        }} defaultExpanded={false} maxHeight="max-h-64" />
                      </div>
                    </div>
                  )}
                  
                  {/* Debug Information - Collapsed by Default */}
                  <details className="theme-context-raw p-4 rounded-lg">
                    <summary className="cursor-pointer text-sm font-medium text-text-secondary hover:text-text">
                      🐛 Debug: View Raw Context Data
                    </summary>
                    <div className="mt-3">
                      <p className="text-xs text-text-secondary mb-2">Complete context structure for debugging purposes</p>
                      <RawJSONDisplay 
                        jsonData={taskContext}
                        title="Task Context"
                        fileName="task_context.json"
                      />
                    </div>
                  </details>
                  
                </>
              ) : (
                <div className="text-center py-8 theme-context-section rounded-lg">
                  <FileText className="w-12 h-12 text-text-tertiary mx-auto mb-3" />
                  <h3 className="text-lg font-medium text-text">No Context Available</h3>
                  <p className="text-sm text-text-secondary mt-2">
                    This task doesn't have any context data yet.
                  </p>
                  <p className="text-xs text-text-tertiary mt-4">
                    Context is created when tasks are updated or completed with additional information.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
        <DialogFooter className="flex justify-between">
          <div className="flex gap-2">
            {activeTab === 'context' && taskContext && (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    // Expand all HTML details elements
                    const detailsElements = document.querySelectorAll('details');
                    detailsElements.forEach(details => {
                      details.open = true;
                    });
                    
                    // Dispatch custom event for EnhancedJSONViewer components
                    window.dispatchEvent(new CustomEvent('json-expand-all', { 
                      detail: { viewerId: 'all' }
                    }));
                  }}
                >
                  Expand All
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    // Collapse all HTML details elements
                    const detailsElements = document.querySelectorAll('details');
                    detailsElements.forEach(details => {
                      details.open = false;
                    });
                    
                    // Dispatch custom event for EnhancedJSONViewer components
                    window.dispatchEvent(new CustomEvent('json-collapse-all', { 
                      detail: { viewerId: 'all' }
                    }));
                  }}
                >
                  Collapse All
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={copyJsonToClipboard}
                  className="flex items-center gap-2"
                >
                  {jsonCopied ? (
                    <>
                      <CheckIcon className="w-4 h-4" />
                      Copied!
                    </>
                  ) : (
                    <>
                      <Copy className="w-4 h-4" />
                      Copy JSON
                    </>
                  )}
                </Button>
              </>
            )}
          </div>
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default TaskDetailsDialog;