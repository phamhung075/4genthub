import React, { useEffect, useState } from "react";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import { Separator } from "./ui/separator";
import { Task, Subtask, getTask, getTaskContext } from "../api";
import ClickableAssignees from "./ClickableAssignees";
import { formatContextDisplay } from "../utils/contextHelpers";
import { FileText, Info, ChevronDown, ChevronRight, Hash, Calendar, Tag, Layers, Copy, Check as CheckIcon } from "lucide-react";
import RawJSONDisplay from "./ui/RawJSONDisplay";

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
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['data', 'resolved_context', 'task_data', 'progress']));
  const [jsonCopied, setJsonCopied] = useState(false);

  // Set initial task when it changes - but don't clear if null
  useEffect(() => {
    console.log('[TaskDetailsDialog] Task prop changed:', task);
    // Check if task is the full response object or just the task
    const taskData = task?.task || task;
    if (taskData && taskData.id) {
      console.log('[TaskDetailsDialog] Setting fullTask from prop:', taskData);
      setFullTask(taskData);
    } else {
      console.log('[TaskDetailsDialog] Task prop is null or has no ID, not clearing fullTask');
    }
  }, [task]);

  // Fetch full task with context when dialog opens
  useEffect(() => {
    // Only fetch if we have a task ID, either from prop or from fullTask
    const taskId = task?.id || fullTask?.id;
    console.log('[TaskDetailsDialog] Dialog open:', open, 'TaskID:', taskId, 'Task prop:', task, 'FullTask:', fullTask);
    
    if (open && taskId) {
      setLoading(true);
      setContextLoading(true);
      
      console.log('[TaskDetailsDialog] Fetching task details for ID:', taskId);
      // Fetch task details
      getTask(taskId) // Fixed: removed invalid second parameter
        .then(fetchedTask => {
          console.log('[TaskDetailsDialog] Fetched task:', fetchedTask);
          // Extract the task from the response structure
          const taskData = fetchedTask?.task || fetchedTask;
          if (taskData && taskData.id) {
            console.log('[TaskDetailsDialog] Setting fullTask to:', taskData);
            setFullTask(taskData);
          } else {
            console.log('[TaskDetailsDialog] No valid task data in response');
          }
          // Don't clear on failure - keep the initial task data
        })
        .catch(error => {
          console.error('[TaskDetailsDialog] Error fetching task:', error);
          // Don't overwrite with null - keep existing data
        })
        .finally(() => {
          setLoading(false);
        });
      
      // Fetch task context separately
      getTaskContext(taskId)
        .then(context => {
          console.log('Raw context response:', context);
          
          // Extract the actual context data from the response
          if (context) {
            if (context.data && context.data.resolved_context) {
              // New format: data.resolved_context contains the actual context
              console.log('Using resolved_context from data:', context.data.resolved_context);
              setTaskContext(context.data.resolved_context);
            } else if (context.resolved_context) {
              // Alternative format: resolved_context at root level
              console.log('Using resolved_context from root:', context.resolved_context);
              setTaskContext(context.resolved_context);
            } else if (context.data) {
              // Fallback: use data object if it exists
              console.log('Using data object:', context.data);
              setTaskContext(context.data);
            } else {
              // Last resort: use the whole response
              console.log('Using full response:', context);
              setTaskContext(context);
            }
          } else {
            console.log('No context data received');
            setTaskContext(null);
          }
        })
        .catch(error => {
          console.error('Error fetching task context:', error);
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
  console.log('[TaskDetailsDialog] DisplayTask being used:', displayTask, 'RawDisplayTask:', rawDisplayTask, 'FullTask:', fullTask, 'Task:', task);
  
  // Format context data using helper functions
  const contextDisplay = formatContextDisplay(displayTask?.context_data);
  
  // Toggle section expansion
  const toggleSection = (path: string) => {
    setExpandedSections(prev => {
      const newSet = new Set(prev);
      if (newSet.has(path)) {
        newSet.delete(path);
      } else {
        newSet.add(path);
      }
      return newSet;
    });
  };

  // Copy JSON to clipboard
  const copyJsonToClipboard = () => {
    if (taskContext) {
      const jsonString = JSON.stringify(taskContext, null, 2);
      navigator.clipboard.writeText(jsonString).then(() => {
        setJsonCopied(true);
        setTimeout(() => setJsonCopied(false), 2000);
      }).catch(err => {
        console.error('Failed to copy JSON:', err);
      });
    }
  };

  // Render nested JSON beautifully
  const renderNestedJson = (data: any, path: string = '', depth: number = 0): React.ReactElement => {
    if (data === null || data === undefined) {
      return <span className="text-text-tertiary italic">null</span>;
    }

    if (typeof data === 'boolean') {
      return <span className={`font-medium ${data ? 'text-success dark:text-success-dark' : 'text-error dark:text-error-dark'}`}>{String(data)}</span>;
    }

    if (typeof data === 'string') {
      // Check if it's a date string
      if (data.match(/^\d{4}-\d{2}-\d{2}/) || data.includes('T')) {
        try {
          const date = new Date(data);
          if (!isNaN(date.getTime())) {
            return (
              <span className="text-info dark:text-info-dark">
                <Calendar className="inline w-3 h-3 mr-1" />
                {date.toLocaleString()}
              </span>
            );
          }
        } catch {}
      }
      // Check if it's a UUID
      if (data.match(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i)) {
        return (
          <span className="font-mono text-xs text-secondary dark:text-secondary-dark">
            <Hash className="inline w-3 h-3 mr-1" />
            {data}
          </span>
        );
      }
      return <span className="text-text dark:text-text">"{data}"</span>;
    }

    if (typeof data === 'number') {
      return <span className="text-info dark:text-info-dark font-medium">{data}</span>;
    }

    if (Array.isArray(data)) {
      if (data.length === 0) {
        return <span className="text-text-tertiary italic">[]</span>;
      }
      
      const isExpanded = expandedSections.has(path);
      
      return (
        <div className="inline-block">
          <button
            onClick={() => toggleSection(path)}
            className="text-xs text-text-secondary hover:text-text flex items-center gap-1"
          >
            {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            <span className="font-medium">[{data.length} items]</span>
          </button>
          {isExpanded && (
            <div className="ml-4 mt-1 space-y-1">
              {data.map((item, index) => (
                <div key={index} className="flex items-start">
                  <span className="text-text-tertiary text-xs mr-2">{index}:</span>
                  {renderNestedJson(item, `${path}[${index}]`, depth + 1)}
                </div>
              ))}
            </div>
          )}
        </div>
      );
    }

    if (typeof data === 'object') {
      const keys = Object.keys(data);
      if (keys.length === 0) {
        return <span className="text-text-tertiary italic">{'{}'}</span>;
      }

      const isExpanded = expandedSections.has(path);
      const isMainSection = depth === 0 || depth === 1;
      
      return (
        <div className={depth === 0 ? '' : 'inline-block'}>
          {path && (
            <button
              onClick={() => toggleSection(path)}
              className={`text-xs hover:text-text flex items-center gap-1 mb-1 ${
                isMainSection ? 'text-text font-semibold' : 'text-text-secondary'
              }`}
            >
              {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
              <Layers className="w-3 h-3" />
              <span>{keys.length} properties</span>
            </button>
          )}
          {(!path || isExpanded) && (
            <div className={`${path ? 'ml-4 mt-1' : ''} space-y-1`}>
              {keys.map(key => {
                const value = data[key];
                const currentPath = path ? `${path}.${key}` : key;
                const isEmpty = value === null || value === undefined || 
                               (typeof value === 'object' && Object.keys(value).length === 0) ||
                               (Array.isArray(value) && value.length === 0);
                
                // Get appropriate icon and color for known keys
                let keyIcon = null;
                let keyColor = 'text-text-secondary';
                
                if (key.includes('id') || key.includes('uuid')) {
                  keyIcon = <Hash className="inline w-3 h-3 mr-1" />;
                  keyColor = 'text-secondary dark:text-secondary-dark';
                } else if (key.includes('date') || key.includes('time') || key.includes('_at')) {
                  keyIcon = <Calendar className="inline w-3 h-3 mr-1" />;
                  keyColor = 'text-info dark:text-info-dark';
                } else if (key.includes('status') || key.includes('state')) {
                  keyIcon = <Tag className="inline w-3 h-3 mr-1" />;
                  keyColor = 'text-success dark:text-success-dark';
                }
                
                return (
                  <div 
                    key={key} 
                    className={`flex items-start ${
                      isEmpty ? 'opacity-50' : ''
                    } ${
                      isMainSection && typeof value === 'object' && !Array.isArray(value) 
                        ? 'theme-context-section rounded-lg' 
                        : ''
                    }`}
                  >
                    <span className={`${keyColor} text-sm font-medium mr-2 min-w-[120px]`}>
                      {keyIcon}
                      {key}:
                    </span>
                    <div className="flex-1">
                      {renderNestedJson(value, currentPath, depth + 1)}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      );
    }

    return <span className="text-text-secondary">{String(data)}</span>;
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
      <DialogContent className="max-w-4xl max-h-[85vh] overflow-y-auto">
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
                  ? 'text-info dark:text-info-dark border-info dark:border-info-dark' 
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
                  ? 'text-info dark:text-info-dark border-info dark:border-info-dark' 
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
        
        <div className="mt-4">
          {/* Details Tab Content */}
          {activeTab === 'details' && (
            <div className="space-y-4">
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
                    <h4 className="font-semibold text-sm mb-3 text-info dark:text-info-dark">IDs and References</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm theme-context-metadata">
                      <div className="space-y-1">
                        <span className="text-muted-foreground font-medium">Task ID:</span>
                        <p className="font-mono text-xs break-all">{displayTask.id}</p>
                      </div>
                      {displayTask.git_branch_id && (
                        <div className="space-y-1">
                          <span className="text-muted-foreground font-medium">Git Branch ID:</span>
                          <p className="font-mono text-xs break-all">{displayTask.git_branch_id}</p>
                        </div>
                      )}
                      {displayTask.context_id && (
                        <div className="space-y-1">
                          <span className="text-muted-foreground font-medium">Context ID:</span>
                          <p className="font-mono text-xs break-all">{displayTask.context_id}</p>
                        </div>
                      )}
                    </div>
                  </div>

                  <Separator />

                  {/* Time Information */}
                  <div>
                    <h4 className="font-semibold text-sm mb-3 text-success dark:text-success-dark">Time Information</h4>
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
                    <h4 className="font-semibold text-sm mb-3 text-secondary dark:text-secondary-dark">Assignment & Organization</h4>
                    <div className="space-y-3 theme-context-insights">
                      {/* Details field */}
                      {displayTask.details && (
                        <div>
                          <span className="text-muted-foreground font-medium">Additional Details:</span>
                          <p className="mt-1 whitespace-pre-wrap">{displayTask.details}</p>
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
                        <h4 className="font-semibold text-sm mb-3 text-warning dark:text-warning-dark">Dependencies ({displayTask.dependencies.length})</h4>
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
                        <h4 className="font-semibold text-sm mb-3 text-info dark:text-info-dark">Subtasks Summary</h4>
                        <div className="theme-context-metadata">
                          {displayTask.subtasks.length > 0 ? (
                            <>
                              <p className="text-sm font-medium">Total subtasks: {displayTask.subtasks.length}</p>
                              <p className="text-xs text-muted-foreground mt-1">
                                View full subtask details in the Subtasks tab
                              </p>
                              {/* Only show subtask IDs if they are valid strings */}
                              {displayTask.subtasks.filter((id: any) => typeof id === 'string' && id.length > 0).length > 0 ? (
                                <div className="mt-2 space-y-1">
                                  {displayTask.subtasks
                                    .filter((id: any) => typeof id === 'string' && id.length > 0)
                                    .map((subtaskId: string, index: number) => (
                                      <div key={index} className="text-sm">
                                        <span className="text-muted-foreground">#{index + 1}:</span> 
                                        <span className="font-mono text-xs ml-1">{subtaskId}</span>
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
                          <h4 className="font-semibold text-sm mb-3 text-info dark:text-info-dark">Task Completion Details</h4>
                          <div className="theme-context-completion space-y-3">
                        
                        {/* Completion Summary */}
                        {contextDisplay.completionSummary && (
                          <div>
                            <h5 className="font-medium text-xs text-info dark:text-info-dark mb-1">
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
                            <h5 className="font-medium text-xs text-info dark:text-info-dark mb-1">Context Status:</h5>
                            <span className="inline-block px-2 py-1 theme-context-metadata text-xs font-medium">
                              {contextDisplay.taskStatus}
                            </span>
                          </div>
                        )}

                        {/* Testing Notes */}
                        {contextDisplay.testingNotes.length > 0 && (
                          <div>
                            <h5 className="font-medium text-xs text-info dark:text-info-dark mb-1">Testing Notes & Next Steps:</h5>
                            <ul className="text-sm space-y-1">
                              {contextDisplay.testingNotes.map((step: string, index: number) => (
                                <li key={index} className="theme-card p-2 rounded border-l-4 border-l-info">
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
            <div className="space-y-4">
              {contextLoading ? (
                <div className="text-center py-8">
                  <div className="inline-block w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                  <p className="mt-2 text-sm text-gray-500">Loading context...</p>
                </div>
              ) : taskContext ? (
                <>
                  {/* Context Header */}
                  <div className="theme-context-metadata p-4 rounded-lg">
                    <h3 className="text-lg font-semibold text-info dark:text-info-dark flex items-center gap-2">
                      <Layers className="w-5 h-5" />
                      Task Context - Complete Hierarchical View
                    </h3>
                    <p className="text-sm text-info dark:text-info-dark mt-1">
                      Interactive nested view showing ALL context data - click to expand/collapse sections
                    </p>
                  </div>
                  
                  {/* Task Data Section */}
                  {(taskContext.task_data || taskContext.execution_context || taskContext.discovered_patterns) && (
                    <div className="theme-context-data p-4 rounded-lg">
                      <h4 className="text-md font-semibold text-success dark:text-success-dark mb-3">
                        🎯 Task Execution Details
                      </h4>
                      
                      {/* Task Data */}
                      {taskContext.task_data && Object.keys(taskContext.task_data).length > 0 && (
                        <details className="mb-3">
                          <summary className="cursor-pointer text-sm font-medium text-success hover:text-success-dark">
                            📋 Task Data
                          </summary>
                          <div className="mt-2 ml-4 text-sm theme-card p-2 rounded">
                            {renderNestedJson(taskContext.task_data)}
                          </div>
                        </details>
                      )}
                      
                      {/* Execution Context */}
                      {taskContext.execution_context && Object.keys(taskContext.execution_context).length > 0 && (
                        <details className="mb-3">
                          <summary className="cursor-pointer text-sm font-medium text-success hover:text-success-dark">
                            ⚡ Execution Context
                          </summary>
                          <div className="mt-2 ml-4 text-sm theme-card p-2 rounded max-h-60 overflow-y-auto">
                            {renderNestedJson(taskContext.execution_context)}
                          </div>
                        </details>
                      )}
                      
                      {/* Discovered Patterns */}
                      {taskContext.discovered_patterns && Object.keys(taskContext.discovered_patterns).length > 0 && (
                        <details className="mb-3">
                          <summary className="cursor-pointer text-sm font-medium text-success hover:text-success-dark">
                            🔍 Discovered Patterns
                          </summary>
                          <div className="mt-2 ml-4 text-sm theme-card p-2 rounded">
                            {renderNestedJson(taskContext.discovered_patterns)}
                          </div>
                        </details>
                      )}
                      
                      {/* Local Decisions */}
                      {taskContext.local_decisions && Object.keys(taskContext.local_decisions).length > 0 && (
                        <details className="mb-3">
                          <summary className="cursor-pointer text-sm font-medium text-success hover:text-success-dark">
                            🎯 Local Decisions
                          </summary>
                          <div className="mt-2 ml-4 text-sm theme-card p-2 rounded">
                            {renderNestedJson(taskContext.local_decisions)}
                          </div>
                        </details>
                      )}
                    </div>
                  )}
                  
                  {/* Implementation Notes Section */}
                  {taskContext.implementation_notes && Object.keys(taskContext.implementation_notes).length > 0 && (
                    <div className="theme-context-metadata p-4 rounded-lg">
                      <h4 className="text-md font-semibold text-info dark:text-info-dark mb-3">
                        📝 Implementation Notes
                      </h4>
                      <details open className="mb-3">
                        <summary className="cursor-pointer text-sm font-medium text-info hover:text-info-dark">
                          View Implementation Details
                        </summary>
                        <div className="mt-2 ml-4 text-sm theme-card p-2 rounded max-h-60 overflow-y-auto">
                          {renderNestedJson(taskContext.implementation_notes)}
                        </div>
                      </details>
                    </div>
                  )}
                  
                  {/* Metadata Section */}
                  {taskContext.metadata && (
                    <div className="theme-context-insights p-4 rounded-lg">
                      <h4 className="text-md font-semibold text-secondary dark:text-secondary-dark mb-3">
                        📊 Metadata & System Information
                      </h4>
                      
                      <div className="grid grid-cols-2 gap-4 mb-3">
                        {taskContext.metadata.created_at && (
                          <div className="theme-card p-2 rounded">
                            <span className="text-xs text-text-secondary">Created</span>
                            <p className="font-medium text-sm">{new Date(taskContext.metadata.created_at).toLocaleDateString()}</p>
                          </div>
                        )}
                        {taskContext.metadata.updated_at && (
                          <div className="theme-card p-2 rounded">
                            <span className="text-xs text-text-secondary">Last Updated</span>
                            <p className="font-medium text-sm">{new Date(taskContext.metadata.updated_at).toLocaleDateString()}</p>
                          </div>
                        )}
                      </div>
                      
                      <details>
                        <summary className="cursor-pointer text-sm font-medium text-secondary hover:text-secondary-dark">
                          View All Metadata
                        </summary>
                        <div className="mt-2 ml-4 text-sm theme-card p-2 rounded max-h-40 overflow-y-auto">
                          {renderNestedJson(taskContext.metadata)}
                        </div>
                      </details>
                    </div>
                  )}
                  
                  {/* Inheritance Information */}
                  {(taskContext._inheritance || taskContext.inheritance_metadata || taskContext.inheritance_disabled !== undefined) && (
                    <div className="theme-context-progress p-4 rounded-lg">
                      <h4 className="text-md font-semibold text-warning dark:text-warning-dark mb-3">
                        🔗 Context Inheritance
                      </h4>
                      <div className="text-sm">
                        {(taskContext._inheritance || taskContext.inheritance_metadata) && (
                          <>
                            <p className="mb-2">
                              <span className="font-medium">Inheritance Chain:</span> {
                                (taskContext._inheritance?.chain || 
                                 taskContext.inheritance_metadata?.inheritance_chain)?.join(' → ') || 'N/A'
                              }
                            </p>
                            <p className="mb-2">
                              <span className="font-medium">Inheritance Depth:</span> {
                                taskContext._inheritance?.inheritance_depth || 
                                taskContext.inheritance_metadata?.inheritance_depth || 0
                              }
                            </p>
                          </>
                        )}
                        {taskContext.inheritance_disabled !== undefined && (
                          <p className="mb-2">
                            <span className="font-medium">Inheritance Status:</span> {
                              taskContext.inheritance_disabled ? 'Disabled' : 'Enabled'
                            }
                          </p>
                        )}
                        {taskContext.force_local_only && (
                          <p className="text-xs text-warning italic">
                            ⚠️ This task uses local context only (inheritance bypassed)
                          </p>
                        )}
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
                  
                  {/* Expand/Collapse All Controls */}
                  <div className="flex gap-2 justify-end mt-2">
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
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        // Expand all sections including HTML details elements
                        const allPaths = new Set<string>();
                        const traverse = (obj: any, path: string = '') => {
                          if (obj && typeof obj === 'object') {
                            allPaths.add(path);
                            Object.keys(obj).forEach(key => {
                              const newPath = path ? `${path}.${key}` : key;
                              traverse(obj[key], newPath);
                            });
                          }
                        };
                        traverse(taskContext);
                        setExpandedSections(allPaths);
                        
                        // Also expand all HTML details elements
                        const detailsElements = document.querySelectorAll('details');
                        detailsElements.forEach(details => {
                          details.open = true;
                        });
                      }}
                    >
                      Expand All
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        // Collapse all sections
                        setExpandedSections(new Set(['data', 'resolved_context', 'task_data', 'progress']));
                        
                        // Also collapse all HTML details elements
                        const detailsElements = document.querySelectorAll('details');
                        detailsElements.forEach(details => {
                          details.open = false;
                        });
                      }}
                    >
                      Collapse All
                    </Button>
                  </div>
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
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default TaskDetailsDialog;