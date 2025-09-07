import React, { useEffect, useState } from "react";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import { Separator } from "./ui/separator";
import { Task, Subtask, getTask, getTaskContext } from "../api";
import ClickableAssignees from "./ClickableAssignees";
import { formatContextDisplay } from "../utils/contextHelpers";
import { FileText, Info, ChevronDown, ChevronRight, Hash, Calendar, Tag, Layers, Copy, Check as CheckIcon } from "lucide-react";

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

  // Fetch full task with context when dialog opens
  useEffect(() => {
    if (open && task?.id) {
      setLoading(true);
      setContextLoading(true);
      
      // Fetch task details
      getTask(task.id, true) // Include context
        .then(fetchedTask => {
          if (fetchedTask) {
            setFullTask(fetchedTask);
          } else {
            // If fetching fails, use the original task
            setFullTask(task);
          }
        })
        .catch(error => {
          console.error('Error fetching task with context:', error);
          // Fall back to using the original task
          setFullTask(task);
        })
        .finally(() => {
          setLoading(false);
        });
      
      // Fetch task context separately
      getTaskContext(task.id)
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
    } else if (!open) {
      // Clear data when dialog closes
      setFullTask(null);
      setTaskContext(null);
      setActiveTab('details');
    }
  }, [open, task?.id, task]);

  // Use fullTask if available, otherwise fall back to original task
  const displayTask = fullTask || task;
  
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
      return <span className="text-gray-400 italic">null</span>;
    }

    if (typeof data === 'boolean') {
      return <span className={`font-medium ${data ? 'text-green-600' : 'text-red-600'}`}>{String(data)}</span>;
    }

    if (typeof data === 'string') {
      // Check if it's a date string
      if (data.match(/^\d{4}-\d{2}-\d{2}/) || data.includes('T')) {
        try {
          const date = new Date(data);
          if (!isNaN(date.getTime())) {
            return (
              <span className="text-blue-600">
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
          <span className="font-mono text-xs text-purple-600">
            <Hash className="inline w-3 h-3 mr-1" />
            {data}
          </span>
        );
      }
      return <span className="text-gray-700 dark:text-gray-300">"{data}"</span>;
    }

    if (typeof data === 'number') {
      return <span className="text-blue-600 font-medium">{data}</span>;
    }

    if (Array.isArray(data)) {
      if (data.length === 0) {
        return <span className="text-gray-400 italic">[]</span>;
      }
      
      const isExpanded = expandedSections.has(path);
      
      return (
        <div className="inline-block">
          <button
            onClick={() => toggleSection(path)}
            className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1"
          >
            {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            <span className="font-medium">[{data.length} items]</span>
          </button>
          {isExpanded && (
            <div className="ml-4 mt-1 space-y-1">
              {data.map((item, index) => (
                <div key={index} className="flex items-start">
                  <span className="text-gray-400 text-xs mr-2">{index}:</span>
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
        return <span className="text-gray-400 italic">{'{}'}</span>;
      }

      const isExpanded = expandedSections.has(path);
      const isMainSection = depth === 0 || depth === 1;
      
      return (
        <div className={depth === 0 ? '' : 'inline-block'}>
          {path && (
            <button
              onClick={() => toggleSection(path)}
              className={`text-xs hover:text-gray-700 flex items-center gap-1 mb-1 ${
                isMainSection ? 'text-gray-700 font-semibold' : 'text-gray-500'
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
                let keyColor = 'text-gray-600';
                
                if (key.includes('id') || key.includes('uuid')) {
                  keyIcon = <Hash className="inline w-3 h-3 mr-1" />;
                  keyColor = 'text-purple-600';
                } else if (key.includes('date') || key.includes('time') || key.includes('_at')) {
                  keyIcon = <Calendar className="inline w-3 h-3 mr-1" />;
                  keyColor = 'text-blue-600';
                } else if (key.includes('status') || key.includes('state')) {
                  keyIcon = <Tag className="inline w-3 h-3 mr-1" />;
                  keyColor = 'text-green-600';
                }
                
                return (
                  <div 
                    key={key} 
                    className={`flex items-start ${
                      isEmpty ? 'opacity-50' : ''
                    } ${
                      isMainSection && typeof value === 'object' && !Array.isArray(value) 
                        ? 'p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700' 
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

    return <span className="text-gray-500">{String(data)}</span>;
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
                  ? 'text-blue-600 border-blue-600' 
                  : 'text-gray-500 border-transparent hover:text-gray-700'
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
                  ? 'text-blue-600 border-blue-600' 
                  : 'text-gray-500 border-transparent hover:text-gray-700'
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
              <div className="bg-background-secondary dark:bg-gray-800/50 p-4 rounded-lg">
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
                <h4 className="font-semibold text-sm mb-3 text-blue-700 dark:text-blue-300">IDs and References</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm bg-blue-50 dark:bg-blue-900/20 p-3 rounded border border-blue-200 dark:border-blue-700">
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
                <h4 className="font-semibold text-sm mb-3 text-green-700 dark:text-green-300">Time Information</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm bg-green-50 dark:bg-green-900/20 p-3 rounded border border-green-200 dark:border-green-700">
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
                <h4 className="font-semibold text-sm mb-3 text-purple-700 dark:text-purple-300">Assignment & Organization</h4>
                <div className="space-y-3 bg-purple-50 dark:bg-purple-900/20 p-3 rounded border border-purple-200 dark:border-purple-700">
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
                    <h4 className="font-semibold text-sm mb-3 text-orange-700 dark:text-orange-300">Dependencies ({displayTask.dependencies.length})</h4>
                    <div className="space-y-2 bg-orange-50 dark:bg-orange-900/20 p-3 rounded border border-orange-200 dark:border-orange-700">
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
                    <h4 className="font-semibold text-sm mb-3 text-indigo-700 dark:text-indigo-300">Subtasks Summary</h4>
                    <div className="bg-indigo-50 dark:bg-indigo-900/20 p-3 rounded border border-indigo-200 dark:border-indigo-700">
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
                      <h4 className="font-semibold text-sm mb-3 text-teal-700 dark:text-teal-300">Task Completion Details</h4>
                      <div className="bg-teal-50 dark:bg-teal-900/20 p-3 rounded space-y-3 border border-teal-200 dark:border-teal-700">
                        
                        {/* Completion Summary */}
                        {contextDisplay.completionSummary && (
                          <div>
                            <h5 className="font-medium text-xs text-teal-800 dark:text-teal-300 mb-1">
                              Completion Summary{contextDisplay.isLegacy ? ' (Legacy)' : ''}:
                            </h5>
                            <p className={`text-sm whitespace-pre-wrap p-2 rounded border ${contextDisplay.isLegacy ? 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-700' : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700'}`}>
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
                            <h5 className="font-medium text-xs text-teal-800 dark:text-teal-300 mb-1">Context Status:</h5>
                            <span className="inline-block px-2 py-1 bg-teal-200 dark:bg-teal-800/30 text-teal-800 dark:text-teal-200 text-xs font-medium rounded border border-teal-300 dark:border-teal-700">
                              {contextDisplay.taskStatus}
                            </span>
                          </div>
                        )}

                        {/* Testing Notes */}
                        {contextDisplay.testingNotes.length > 0 && (
                          <div>
                            <h5 className="font-medium text-xs text-teal-800 dark:text-teal-300 mb-1">Testing Notes & Next Steps:</h5>
                            <ul className="text-sm space-y-1">
                              {contextDisplay.testingNotes.map((step: string, index: number) => (
                                <li key={index} className="bg-white dark:bg-gray-800 p-2 rounded border border-gray-200 dark:border-gray-700 border-l-4 border-l-teal-300 dark:border-l-teal-500">
                                  {step}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Raw Context Data */}
                  <div>
                    <h4 className="font-semibold text-sm mb-3 text-teal-700 dark:text-teal-300">Raw Context Data</h4>
                    <div className="bg-teal-50 dark:bg-teal-900/20 p-3 rounded border border-teal-200 dark:border-teal-700">
                      <pre className="text-xs overflow-x-auto whitespace-pre-wrap">
                        {JSON.stringify(displayTask.context_data, null, 2)}
                      </pre>
                    </div>
                  </div>
                </>
              )}

              {/* Raw Data */}
              <Separator />
              <details className="cursor-pointer">
                <summary className="font-semibold text-sm text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100">
                  View Complete Raw Task Data (JSON)
                </summary>
                <div className="mt-3 bg-gray-100 dark:bg-gray-800 p-3 rounded border border-gray-200 dark:border-gray-700">
                  <pre className="text-xs overflow-x-auto whitespace-pre-wrap">
                    {JSON.stringify(displayTask, null, 2)}
                  </pre>
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
                  <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950/20 dark:to-indigo-950/20 p-4 rounded-lg border border-blue-200 dark:border-blue-800">
                    <h3 className="text-lg font-semibold text-blue-700 dark:text-blue-300 flex items-center gap-2">
                      <Layers className="w-5 h-5" />
                      Task Context - Complete Hierarchical View
                    </h3>
                    <p className="text-sm text-blue-600 dark:text-blue-400 mt-1">
                      Interactive nested view showing ALL context data - click to expand/collapse sections
                    </p>
                  </div>
                  
                  {/* Task Data Section */}
                  {(taskContext.task_data || taskContext.execution_context || taskContext.discovered_patterns) && (
                    <div className="bg-green-50 dark:bg-green-950/20 p-4 rounded-lg border border-green-200 dark:border-green-800">
                      <h4 className="text-md font-semibold text-green-700 dark:text-green-300 mb-3">
                        🎯 Task Execution Details
                      </h4>
                      
                      {/* Task Data */}
                      {taskContext.task_data && Object.keys(taskContext.task_data).length > 0 && (
                        <details className="mb-3">
                          <summary className="cursor-pointer text-sm font-medium text-green-600 hover:text-green-700">
                            📋 Task Data
                          </summary>
                          <div className="mt-2 ml-4 text-sm bg-white dark:bg-gray-800 p-2 rounded">
                            {renderNestedJson(taskContext.task_data)}
                          </div>
                        </details>
                      )}
                      
                      {/* Execution Context */}
                      {taskContext.execution_context && Object.keys(taskContext.execution_context).length > 0 && (
                        <details className="mb-3">
                          <summary className="cursor-pointer text-sm font-medium text-green-600 hover:text-green-700">
                            ⚡ Execution Context
                          </summary>
                          <div className="mt-2 ml-4 text-sm bg-white dark:bg-gray-800 p-2 rounded max-h-60 overflow-y-auto">
                            {renderNestedJson(taskContext.execution_context)}
                          </div>
                        </details>
                      )}
                      
                      {/* Discovered Patterns */}
                      {taskContext.discovered_patterns && Object.keys(taskContext.discovered_patterns).length > 0 && (
                        <details className="mb-3">
                          <summary className="cursor-pointer text-sm font-medium text-green-600 hover:text-green-700">
                            🔍 Discovered Patterns
                          </summary>
                          <div className="mt-2 ml-4 text-sm bg-white dark:bg-gray-800 p-2 rounded">
                            {renderNestedJson(taskContext.discovered_patterns)}
                          </div>
                        </details>
                      )}
                      
                      {/* Local Decisions */}
                      {taskContext.local_decisions && Object.keys(taskContext.local_decisions).length > 0 && (
                        <details className="mb-3">
                          <summary className="cursor-pointer text-sm font-medium text-green-600 hover:text-green-700">
                            🎯 Local Decisions
                          </summary>
                          <div className="mt-2 ml-4 text-sm bg-white dark:bg-gray-800 p-2 rounded">
                            {renderNestedJson(taskContext.local_decisions)}
                          </div>
                        </details>
                      )}
                    </div>
                  )}
                  
                  {/* Implementation Notes Section */}
                  {taskContext.implementation_notes && Object.keys(taskContext.implementation_notes).length > 0 && (
                    <div className="bg-blue-50 dark:bg-blue-950/20 p-4 rounded-lg border border-blue-200 dark:border-blue-800">
                      <h4 className="text-md font-semibold text-blue-700 dark:text-blue-300 mb-3">
                        📝 Implementation Notes
                      </h4>
                      <details open className="mb-3">
                        <summary className="cursor-pointer text-sm font-medium text-blue-600 hover:text-blue-700">
                          View Implementation Details
                        </summary>
                        <div className="mt-2 ml-4 text-sm bg-white dark:bg-gray-800 p-2 rounded max-h-60 overflow-y-auto">
                          {renderNestedJson(taskContext.implementation_notes)}
                        </div>
                      </details>
                    </div>
                  )}
                  
                  {/* Metadata Section */}
                  {taskContext.metadata && (
                    <div className="bg-purple-50 dark:bg-purple-950/20 p-4 rounded-lg border border-purple-200 dark:border-purple-800">
                      <h4 className="text-md font-semibold text-purple-700 dark:text-purple-300 mb-3">
                        📊 Metadata & System Information
                      </h4>
                      
                      <div className="grid grid-cols-2 gap-4 mb-3">
                        {taskContext.metadata.created_at && (
                          <div className="bg-white dark:bg-gray-800 p-2 rounded">
                            <span className="text-xs text-gray-500">Created</span>
                            <p className="font-medium text-sm">{new Date(taskContext.metadata.created_at).toLocaleDateString()}</p>
                          </div>
                        )}
                        {taskContext.metadata.updated_at && (
                          <div className="bg-white dark:bg-gray-800 p-2 rounded">
                            <span className="text-xs text-gray-500">Last Updated</span>
                            <p className="font-medium text-sm">{new Date(taskContext.metadata.updated_at).toLocaleDateString()}</p>
                          </div>
                        )}
                      </div>
                      
                      <details>
                        <summary className="cursor-pointer text-sm font-medium text-purple-600 hover:text-purple-700">
                          View All Metadata
                        </summary>
                        <div className="mt-2 ml-4 text-sm bg-white dark:bg-gray-800 p-2 rounded max-h-40 overflow-y-auto">
                          {renderNestedJson(taskContext.metadata)}
                        </div>
                      </details>
                    </div>
                  )}
                  
                  {/* Inheritance Information */}
                  {(taskContext._inheritance || taskContext.inheritance_metadata || taskContext.inheritance_disabled !== undefined) && (
                    <div className="bg-orange-50 dark:bg-orange-950/20 p-4 rounded-lg border border-orange-200 dark:border-orange-800">
                      <h4 className="text-md font-semibold text-orange-700 dark:text-orange-300 mb-3">
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
                          <p className="text-xs text-orange-600 italic">
                            ⚠️ This task uses local context only (inheritance bypassed)
                          </p>
                        )}
                      </div>
                    </div>
                  )}
                  
                  {/* Debug Information - Collapsed by Default */}
                  <details className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
                    <summary className="cursor-pointer text-sm font-medium text-gray-600 hover:text-gray-700">
                      🐛 Debug: View Raw Context Data
                    </summary>
                    <div className="mt-3">
                      <p className="text-xs text-gray-500 mb-2">Complete context structure for debugging purposes</p>
                      <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto max-h-96 overflow-y-auto">
                        <code className="text-xs font-mono">
                          {JSON.stringify(taskContext, null, 2)}
                        </code>
                      </pre>
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
                <div className="text-center py-8 bg-gray-50 rounded-lg">
                  <FileText className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                  <h3 className="text-lg font-medium text-gray-900">No Context Available</h3>
                  <p className="text-sm text-gray-500 mt-2">
                    This task doesn't have any context data yet.
                  </p>
                  <p className="text-xs text-gray-400 mt-4">
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