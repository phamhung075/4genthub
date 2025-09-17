import React, { useEffect, useState } from "react";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import { Textarea } from "./ui/textarea";
import { FileText, Save, Edit, X, Copy, Check as CheckIcon, Info, CheckSquare, GitBranch, History, Settings, Lightbulb, AlertCircle, Layers, Globe, FolderOpen, ChevronDown, ChevronUp, ChevronRight } from "lucide-react";
import { Task } from "../api";
import { getTaskContext, updateTaskContext, getBranchContext, getProjectContext, getGlobalContext } from "../api";
import { EnhancedJSONViewer } from "./ui/EnhancedJSONViewer";

interface TaskContextDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  task: Task | null;
  context?: any | null;
  onClose: () => void;
  loading?: boolean;
}

// Parse markdown for key-value format
const parseKeyValueMarkdown = (content: string): Record<string, string> => {
  const result: Record<string, string> = {};
  const lines = content.split('\n');
  let currentKey = '';
  let currentValue: string[] = [];

  lines.forEach((line) => {
    if (line.includes(':') && !currentKey) {
      if (currentKey && currentValue.length > 0) {
        result[currentKey] = currentValue.join('\n').trim();
      }
      
      const [key, ...valueParts] = line.split(':');
      currentKey = key.trim();
      const value = valueParts.join(':').trim();
      
      if (value) {
        result[currentKey] = value;
        currentKey = '';
        currentValue = [];
      } else {
        currentValue = [];
      }
    } else if (currentKey) {
      if (line.trim()) {
        currentValue.push(line);
      } else if (currentValue.length > 0) {
        result[currentKey] = currentValue.join('\n').trim();
        currentKey = '';
        currentValue = [];
      }
    }
  });

  if (currentKey && currentValue.length > 0) {
    result[currentKey] = currentValue.join('\n').trim();
  }

  return result;
};

// Parse markdown for list format (bullet points or numbered)
const parseListMarkdown = (content: string): string[] => {
  const result: string[] = [];
  const lines = content.split('\n');

  lines.forEach((line) => {
    const trimmed = line.trim();
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ') || trimmed.startsWith('• ') || /^\d+\./.test(trimmed)) {
      const cleanItem = trimmed.replace(/^[-*•]\s*|\d+\.\s*/, '').trim();
      if (cleanItem) {
        result.push(cleanItem);
      }
    } else if (trimmed && !trimmed.includes(':')) {
      // Also include plain lines without bullets
      result.push(trimmed);
    }
  });

  return result;
};

// Convert to markdown format for each section
const keyValueToMarkdown = (data: Record<string, any>): string => {
  if (!data || Object.keys(data).length === 0) {
    return '';
  }
  
  return Object.entries(data).map(([key, value]) => {
    if (typeof value === 'object' && value !== null) {
      if (Array.isArray(value)) {
        return `${key}: ${value.join(', ')}`;
      } else {
        return `${key}: ${JSON.stringify(value, null, 2)}`;
      }
    }
    return `${key}: ${value}`;
  }).join('\n');
};

const listToMarkdown = (data: string[] | Record<string, any>): string => {
  if (!data) {
    return '';
  }
  
  if (Array.isArray(data)) {
    return data.map(item => `- ${item}`).join('\n');
  }
  
  if (typeof data === 'object') {
    return Object.entries(data).map(([key, value]) => `- ${key}: ${value}`).join('\n');
  }
  
  return '';
};

export const TaskContextDialog: React.FC<TaskContextDialogProps> = ({
  open,
  onOpenChange,
  task,
  context: initialContext,
  onClose,
  loading: initialLoading = false
}) => {
  const [taskContext, setTaskContext] = useState<any>(null);
  const [branchContext, setBranchContext] = useState<any>(null);
  const [projectContext, setProjectContext] = useState<any>(null);
  const [globalContext, setGlobalContext] = useState<any>(null);
  const [editMode, setEditMode] = useState(false);
  const [loading, setLoading] = useState(initialLoading);
  const [saving, setSaving] = useState(false);
  const [jsonCopied, setJsonCopied] = useState(false);
  const [rawJsonExpanded, setRawJsonExpanded] = useState(false);
  const [activeTab, setActiveTab] = useState<'task_info' | 'task_progress' | 'completion_summary' | 'testing_notes' | 'blockers' | 'insights' | 'next_steps' | 'task_metadata' | 'inheritance'>('task_info');
  
  // Separate markdown content for each section
  const [taskInfoMarkdown, setTaskInfoMarkdown] = useState('');
  const [taskProgressMarkdown, setTaskProgressMarkdown] = useState('');
  const [completionSummaryMarkdown, setCompletionSummaryMarkdown] = useState('');
  const [testingNotesMarkdown, setTestingNotesMarkdown] = useState('');
  const [blockersMarkdown, setBlockersMarkdown] = useState('');
  const [insightsMarkdown, setInsightsMarkdown] = useState('');
  const [nextStepsMarkdown, setNextStepsMarkdown] = useState('');
  const [taskMetadataMarkdown, setTaskMetadataMarkdown] = useState('');

  // Fetch context when dialog opens
  useEffect(() => {
    if (open && task?.id) {
      fetchTaskContext();
      fetchInheritedContexts();
    } else {
      setEditMode(false);
      setTaskContext(null);
      setActiveTab('task_info');
    }
  }, [open, task?.id]);

  const fetchInheritedContexts = async () => {
    if (!task) return;
    
    try {
      // Fetch branch context if available
      if (task.git_branch_id) {
        const branch = await getBranchContext(task.git_branch_id);
        if (branch) setBranchContext(branch.data || branch);
      }
      
      // Fetch project context if available
      if (task.project_id) {
        const project = await getProjectContext(task.project_id);
        if (project) setProjectContext(project.data || project);
      }
      
      // Fetch global context
      const global = await getGlobalContext();
      if (global) setGlobalContext(global.data || global);
    } catch (error) {
      console.error('Error fetching inherited contexts:', error);
    }
  };

  const fetchTaskContext = async () => {
    if (!task?.id) return;
    
    setLoading(true);
    try {
      const context = await getTaskContext(task.id);
      console.log('Fetched task context:', context);
      
      if (context) {
        setTaskContext(context);
        
        // Handle the actual API response structure
        const contextData = context.data || context;
        
        // Extract task-specific fields
        const taskInfo = contextData.task_info || contextData.task_data || {};
        const taskProgress = contextData.task_progress || contextData.progress || {};
        const completionSummary = contextData.completion_summary || '';
        const testingNotes = contextData.testing_notes || contextData.test_notes || '';
        const blockers = contextData.blockers || [];
        const insights = contextData.insights || [];
        const nextSteps = contextData.next_steps || [];
        const taskMetadata = contextData.task_metadata || contextData.metadata || {};
        
        // Convert each section to markdown format
        setTaskInfoMarkdown(keyValueToMarkdown(taskInfo));
        setTaskProgressMarkdown(keyValueToMarkdown(taskProgress));
        setCompletionSummaryMarkdown(typeof completionSummary === 'string' ? completionSummary : keyValueToMarkdown(completionSummary));
        setTestingNotesMarkdown(typeof testingNotes === 'string' ? testingNotes : listToMarkdown(testingNotes));
        setBlockersMarkdown(listToMarkdown(blockers));
        setInsightsMarkdown(listToMarkdown(insights));
        setNextStepsMarkdown(listToMarkdown(nextSteps));
        setTaskMetadataMarkdown(keyValueToMarkdown(taskMetadata));
      } else if (initialContext) {
        // Use initial context if provided
        setTaskContext(initialContext);
        const contextData = initialContext.data || initialContext;
        
        setTaskInfoMarkdown(keyValueToMarkdown(contextData.task_info || contextData.task_data || {}));
        setTaskProgressMarkdown(keyValueToMarkdown(contextData.task_progress || contextData.progress || {}));
        setCompletionSummaryMarkdown(contextData.completion_summary || '');
        setTestingNotesMarkdown(contextData.testing_notes || '');
        setBlockersMarkdown(listToMarkdown(contextData.blockers || []));
        setInsightsMarkdown(listToMarkdown(contextData.insights || []));
        setNextStepsMarkdown(listToMarkdown(contextData.next_steps || []));
        setTaskMetadataMarkdown(keyValueToMarkdown(contextData.task_metadata || contextData.metadata || {}));
      }
    } catch (error) {
      console.error('Error fetching task context:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!task?.id) return;
    
    setSaving(true);
    try {
      // Parse markdown content from each section
      const taskInfo = parseKeyValueMarkdown(taskInfoMarkdown);
      const taskProgress = parseKeyValueMarkdown(taskProgressMarkdown);
      const completionSummary = completionSummaryMarkdown.trim();
      const testingNotes = testingNotesMarkdown.trim();
      const blockers = parseListMarkdown(blockersMarkdown);
      const insights = parseListMarkdown(insightsMarkdown);
      const nextSteps = parseListMarkdown(nextStepsMarkdown);
      const taskMetadata = parseKeyValueMarkdown(taskMetadataMarkdown);
      
      // Prepare the data to save
      const dataToSave = {
        task_info: taskInfo,
        task_progress: taskProgress,
        completion_summary: completionSummary,
        testing_notes: testingNotes,
        blockers: blockers,
        insights: insights,
        next_steps: nextSteps,
        task_metadata: taskMetadata
      };

      // Call the update API
      await updateTaskContext(task.id, dataToSave);
      
      // Refresh the context
      await fetchTaskContext();
      
      // Exit edit mode
      setEditMode(false);
    } catch (error) {
      console.error('Error saving task context:', error);
      alert('Failed to save task context. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    if (taskContext) {
      const contextData = taskContext.data || taskContext;
      
      setTaskInfoMarkdown(keyValueToMarkdown(contextData.task_info || contextData.task_data || {}));
      setTaskProgressMarkdown(keyValueToMarkdown(contextData.task_progress || contextData.progress || {}));
      setCompletionSummaryMarkdown(contextData.completion_summary || '');
      setTestingNotesMarkdown(contextData.testing_notes || '');
      setBlockersMarkdown(listToMarkdown(contextData.blockers || []));
      setInsightsMarkdown(listToMarkdown(contextData.insights || []));
      setNextStepsMarkdown(listToMarkdown(contextData.next_steps || []));
      setTaskMetadataMarkdown(keyValueToMarkdown(contextData.task_metadata || contextData.metadata || {}));
    }
    setEditMode(false);
  };

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

  // Get level-based styling for nested data visualization
  const getLevelStyling = (depth: number) => {
    const styles = [
      { // Level 0 - Root level fields
        bg: 'bg-blue-50 dark:bg-blue-900/10',
        border: 'border-l-4 border-blue-500',
        text: 'text-blue-900 dark:text-blue-100',
        keySize: 'text-base font-semibold',
        padding: 'pl-3',
      },
      { // Level 1
        bg: 'bg-green-50 dark:bg-green-900/10',
        border: 'border-l-4 border-green-500',
        text: 'text-green-900 dark:text-green-100',
        keySize: 'text-sm font-medium',
        padding: 'pl-6',
      },
      { // Level 2
        bg: 'bg-purple-50 dark:bg-purple-900/10',
        border: 'border-l-4 border-purple-500',
        text: 'text-purple-900 dark:text-purple-100',
        keySize: 'text-sm',
        padding: 'pl-9',
      },
      { // Level 3+
        bg: 'bg-orange-50 dark:bg-orange-900/10',
        border: 'border-l-4 border-orange-500',
        text: 'text-orange-900 dark:text-orange-100',
        keySize: 'text-xs',
        padding: 'pl-12',
      },
    ];
    
    return styles[Math.min(depth, styles.length - 1)];
  };

  // Render nested data with level-based styling
  const renderNestedData = (data: any, depth: number = 0): JSX.Element => {
    const style = getLevelStyling(depth);
    
    if (data === null || data === undefined) {
      return <span className="text-gray-400 italic">null</span>;
    }
    
    if (typeof data === 'string' || typeof data === 'number' || typeof data === 'boolean') {
      return <span className={style.text}>{String(data)}</span>;
    }
    
    if (Array.isArray(data)) {
      return (
        <div className="space-y-1">
          {data.map((item, index) => (
            <div key={index} className={`${style.padding} py-1`}>
              <span className={`${style.text} ${style.keySize}`}>[{index}]:</span>
              <div className="ml-4">
                {renderNestedData(item, depth + 1)}
              </div>
            </div>
          ))}
        </div>
      );
    }
    
    if (typeof data === 'object') {
      return (
        <div className="space-y-2">
          {Object.entries(data).map(([key, value]) => (
            <div
              key={key}
              className={`${style.bg} ${style.border} ${style.padding} py-2 rounded-r transition-colors hover:opacity-90`}
            >
              <div>
                <span className={`${style.text} ${style.keySize} capitalize`}>
                  {key.replace(/_/g, ' ')}:
                </span>
                {typeof value === 'object' && value !== null ? (
                  <div className="mt-2">
                    {renderNestedData(value, depth + 1)}
                  </div>
                ) : (
                  <span className="ml-2">{renderNestedData(value, depth + 1)}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      );
    }
    
    return <span>{String(data)}</span>;
  };

  // Get the appropriate markdown content based on active tab
  const getCurrentMarkdown = () => {
    switch (activeTab) {
      case 'task_info': return taskInfoMarkdown;
      case 'task_progress': return taskProgressMarkdown;
      case 'completion_summary': return completionSummaryMarkdown;
      case 'testing_notes': return testingNotesMarkdown;
      case 'blockers': return blockersMarkdown;
      case 'insights': return insightsMarkdown;
      case 'next_steps': return nextStepsMarkdown;
      case 'task_metadata': return taskMetadataMarkdown;
      case 'inheritance': return ''; // Inheritance tab doesn't have markdown
      default: return '';
    }
  };

  // Set the appropriate markdown content based on active tab
  const setCurrentMarkdown = (value: string) => {
    switch (activeTab) {
      case 'task_info': setTaskInfoMarkdown(value); break;
      case 'task_progress': setTaskProgressMarkdown(value); break;
      case 'completion_summary': setCompletionSummaryMarkdown(value); break;
      case 'testing_notes': setTestingNotesMarkdown(value); break;
      case 'blockers': setBlockersMarkdown(value); break;
      case 'insights': setInsightsMarkdown(value); break;
      case 'next_steps': setNextStepsMarkdown(value); break;
      case 'task_metadata': setTaskMetadataMarkdown(value); break;
      case 'inheritance': break; // Inheritance tab is read-only
    }
  };

  // Get placeholder text based on active tab
  const getPlaceholder = () => {
    switch (activeTab) {
      case 'task_info':
        return 'Add task information:\ntitle: Implement user authentication\ndescription: Add JWT-based authentication\nassignee: John Doe\npriority: high\nstatus: in_progress';
      case 'task_progress':
        return 'Add progress updates:\npercentage: 75\ncurrent_step: Implementing token refresh\ncompleted_items: Login UI, JWT validation\nremaining_work: Refresh token, logout';
      case 'completion_summary':
        return 'Add completion summary:\nImplemented full JWT authentication with refresh tokens, secure cookie storage, and automatic token renewal. Added comprehensive error handling and user feedback.';
      case 'testing_notes':
        return 'Add testing notes:\n- Unit tests for auth service\n- Integration tests for login flow\n- Manual testing of token expiry\n- Verified refresh token rotation';
      case 'blockers':
        return 'Add blockers:\n- Waiting for API documentation\n- CORS configuration needed\n- Database migration pending';
      case 'insights':
        return 'Add insights discovered:\n- Found existing auth utility that can be reused\n- Token refresh pattern needs optimization\n- Consider implementing SSO in future';
      case 'next_steps':
        return 'Add next steps:\n- Add password reset flow\n- Implement remember me feature\n- Add 2FA support\n- Create admin authentication';
      case 'task_metadata':
        return 'Add metadata:\nestimated_hours: 8\nactual_hours: 10\ncomplexity: medium\ntags: authentication, security\ndependencies: user-service';
      default:
        return '';
    }
  };

  const getTabIcon = (tab: string) => {
    switch (tab) {
      case 'task_info': return <Info className="w-4 h-4" />;
      case 'task_progress': return <History className="w-4 h-4" />;
      case 'completion_summary': return <CheckSquare className="w-4 h-4" />;
      case 'testing_notes': return <FileText className="w-4 h-4" />;
      case 'blockers': return <AlertCircle className="w-4 h-4" />;
      case 'insights': return <Lightbulb className="w-4 h-4" />;
      case 'next_steps': return <GitBranch className="w-4 h-4" />;
      case 'task_metadata': return <Settings className="w-4 h-4" />;
      case 'inheritance': return <Layers className="w-4 h-4" />;
      default: return <Settings className="w-4 h-4" />;
    }
  };

  const getTabLabel = (tab: string) => {
    switch (tab) {
      case 'task_info': return 'Task Info';
      case 'task_progress': return 'Progress';
      case 'completion_summary': return 'Completion';
      case 'testing_notes': return 'Testing';
      case 'blockers': return 'Blockers';
      case 'insights': return 'Insights';
      case 'next_steps': return 'Next Steps';
      case 'task_metadata': return 'Metadata';
      case 'inheritance': return 'Inheritance';
      default: return 'Info';
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="text-xl text-left flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText className="w-5 h-5" />
              Task Context Management
            </div>
            <div className="flex gap-2">
              {!editMode && taskContext && (
                <>
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
                    variant="default"
                    size="sm"
                    onClick={() => setEditMode(true)}
                  >
                    <Edit className="w-4 h-4 mr-2" />
                    Edit
                  </Button>
                </>
              )}
              {editMode && (
                <>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleCancel}
                    disabled={saving}
                  >
                    <X className="w-4 h-4 mr-2" />
                    Cancel
                  </Button>
                  <Button
                    variant="default"
                    size="sm"
                    onClick={handleSave}
                    disabled={saving}
                  >
                    <Save className="w-4 h-4 mr-2" />
                    {saving ? 'Saving...' : 'Save All'}
                  </Button>
                </>
              )}
            </div>
          </DialogTitle>
        </DialogHeader>
        
        {/* Tab Navigation */}
        <div className="flex gap-1 border-b pb-2 overflow-x-auto">
          {(['task_info', 'task_progress', 'completion_summary', 'testing_notes', 'blockers', 'insights', 'next_steps', 'task_metadata', 'inheritance'] as const).map((tab) => (
            <Button
              key={tab}
              variant={activeTab === tab ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setActiveTab(tab)}
              className="flex items-center gap-2 whitespace-nowrap"
              disabled={editMode && tab === 'inheritance'} // Disable inheritance tab in edit mode
            >
              {getTabIcon(tab)}
              {getTabLabel(tab)}
            </Button>
          ))}
        </div>
        
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="text-center py-8">
              <div className="inline-block w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
              <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Loading task context...</p>
            </div>
          ) : taskContext || editMode ? (
            <div className="h-full flex flex-col p-4">
              {editMode ? (
                // Edit Mode - Markdown Editor for active tab
                <>
                  <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3 mb-4">
                    <h3 className="font-semibold text-sm mb-2 dark:text-gray-200">
                      {getTabLabel(activeTab)} Format
                    </h3>
                    <div className="text-xs text-gray-600 dark:text-gray-400">
                      {activeTab === 'completion_summary' ? (
                        <p>Write a detailed summary of what was accomplished.</p>
                      ) : activeTab === 'blockers' || activeTab === 'insights' || activeTab === 'next_steps' || activeTab === 'testing_notes' ? (
                        <p>Use bullet points (<code className="bg-white dark:bg-gray-700 px-1 rounded">-</code>) for list items.</p>
                      ) : (
                        <p>Use <code className="bg-white dark:bg-gray-700 px-1 rounded">key: value</code> format. Each setting on a new line.</p>
                      )}
                    </div>
                  </div>
                  <Textarea
                    value={getCurrentMarkdown()}
                    onChange={(e) => setCurrentMarkdown(e.target.value)}
                    className="flex-1 font-mono text-sm min-h-[400px] resize-none"
                    placeholder={getPlaceholder()}
                  />
                </>
              ) : (
                // View Mode - Display current tab content or inheritance view
                <div className="space-y-4">
                  {activeTab === 'inheritance' ? (
                    // Inheritance View - Show context hierarchy
                    <div className="space-y-4">
                      {/* Global Context */}
                      <details className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                        <summary className="cursor-pointer">
                          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950/30 dark:to-indigo-950/30 p-3 border-l-4 border-blue-400 dark:border-blue-600">
                            <h3 className="text-gray-700 dark:text-gray-300 font-semibold flex items-center gap-2">
                              <Globe className="w-5 h-5" />
                              Global Context
                            </h3>
                          </div>
                        </summary>
                        <div className="p-4">
                          {globalContext ? (
                            <EnhancedJSONViewer data={globalContext} defaultExpanded={false} maxHeight="max-h-64" />
                          ) : (
                            <p className="text-sm text-gray-500 dark:text-gray-400 italic">No global context available.</p>
                          )}
                        </div>
                      </details>

                      {/* Project Context */}
                      <details className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                        <summary className="cursor-pointer">
                          <div className="bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-950/30 dark:to-emerald-950/30 p-3 border-l-4 border-green-400 dark:border-green-600">
                            <h3 className="text-gray-700 dark:text-gray-300 font-semibold flex items-center gap-2">
                              <FolderOpen className="w-5 h-5" />
                              Project Context
                            </h3>
                          </div>
                        </summary>
                        <div className="p-4">
                          {projectContext ? (
                            <EnhancedJSONViewer data={projectContext} defaultExpanded={false} maxHeight="max-h-64" />
                          ) : (
                            <p className="text-sm text-gray-500 dark:text-gray-400 italic">No project context available.</p>
                          )}
                        </div>
                      </details>

                      {/* Branch Context */}
                      <details className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                        <summary className="cursor-pointer">
                          <div className="bg-gradient-to-r from-purple-50 to-violet-50 dark:from-purple-950/30 dark:to-violet-950/30 p-3 border-l-4 border-purple-400 dark:border-purple-600">
                            <h3 className="text-gray-700 dark:text-gray-300 font-semibold flex items-center gap-2">
                              <GitBranch className="w-5 h-5" />
                              Branch Context
                            </h3>
                          </div>
                        </summary>
                        <div className="p-4">
                          {branchContext ? (
                            <EnhancedJSONViewer data={branchContext} defaultExpanded={false} maxHeight="max-h-64" />
                          ) : (
                            <p className="text-sm text-gray-500 dark:text-gray-400 italic">No branch context available.</p>
                          )}
                        </div>
                      </details>

                      {/* Task Context (Current) */}
                      <details open className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                        <summary className="cursor-pointer">
                          <div className="bg-gradient-to-r from-orange-50 to-amber-50 dark:from-orange-950/30 dark:to-amber-950/30 p-3 border-l-4 border-orange-400 dark:border-orange-600">
                            <h3 className="text-gray-700 dark:text-gray-300 font-semibold flex items-center gap-2">
                              <FileText className="w-5 h-5" />
                              Task Context (Current Level)
                            </h3>
                          </div>
                        </summary>
                        <div className="p-4">
                          <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                            This is the current context level for this task.
                          </p>
                        </div>
                      </details>

                      {/* Information about inheritance */}
                      <details open className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                        <summary className="cursor-pointer">
                          <div className="bg-gradient-to-r from-gray-50 to-slate-50 dark:from-gray-950/30 dark:to-slate-950/30 p-3 border-l-4 border-gray-400 dark:border-gray-600">
                            <h4 className="text-gray-700 dark:text-gray-300 font-semibold text-sm flex items-center gap-2">
                              <Layers className="w-4 h-4" />
                              How Inheritance Works
                            </h4>
                          </div>
                        </summary>
                        <div className="p-4">
                          <ul className="text-xs text-gray-600 dark:text-gray-400 space-y-1">
                            <li>• Task context inherits from Branch context</li>
                            <li>• Branch context inherits from Project context</li>
                            <li>• Project context inherits from Global context</li>
                            <li>• Lower levels can override inherited values</li>
                          </ul>
                        </div>
                      </details>
                    </div>
                  ) : (
                    // Regular tab content - Show nested data visualization
                    <div className="space-y-4">
                      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                        <div className="bg-gradient-to-r from-indigo-50 to-blue-50 dark:from-indigo-950/30 dark:to-blue-950/30 p-3 border-l-4 border-indigo-400 dark:border-indigo-600">
                          <h3 className="text-gray-700 dark:text-gray-300 font-semibold flex items-center gap-2">
                            {getTabIcon(activeTab)}
                            {getTabLabel(activeTab)}
                          </h3>
                        </div>
                        <div className="p-4">
                          {/* Render nested data with level-based styling */}
                          {(() => {
                          const contextData = taskContext?.data || taskContext || {};
                          let dataToRender = null;
                          
                          switch (activeTab) {
                            case 'task_info':
                              dataToRender = contextData.task_info || contextData.task_data || null;
                              break;
                            case 'task_progress':
                              dataToRender = contextData.task_progress || contextData.progress || null;
                              break;
                            case 'completion_summary':
                              dataToRender = contextData.completion_summary ? { summary: contextData.completion_summary } : null;
                              break;
                            case 'testing_notes':
                              dataToRender = contextData.testing_notes ? 
                                (typeof contextData.testing_notes === 'string' ? 
                                  { notes: contextData.testing_notes } : 
                                  contextData.testing_notes) : null;
                              break;
                            case 'blockers':
                              dataToRender = contextData.blockers && contextData.blockers.length > 0 ? 
                                contextData.blockers : null;
                              break;
                            case 'insights':
                              dataToRender = contextData.insights && contextData.insights.length > 0 ? 
                                contextData.insights : null;
                              break;
                            case 'next_steps':
                              dataToRender = contextData.next_steps && contextData.next_steps.length > 0 ? 
                                contextData.next_steps : null;
                              break;
                            case 'task_metadata':
                              dataToRender = contextData.task_metadata || contextData.metadata || null;
                              break;
                          }
                          
                          if (dataToRender && (
                            (typeof dataToRender === 'object' && Object.keys(dataToRender).length > 0) ||
                            (Array.isArray(dataToRender) && dataToRender.length > 0) ||
                            (typeof dataToRender === 'string' && dataToRender.trim())
                          )) {
                            return (
                              <div className="space-y-2">
                                <EnhancedJSONViewer data={dataToRender} defaultExpanded={true} maxHeight="max-h-96" />
                              </div>
                            );
                          } else {
                            return (
                              <p className="text-sm text-gray-500 dark:text-gray-400 italic">
                                No {getTabLabel(activeTab).toLowerCase()} defined yet.
                              </p>
                            );
                          }
                        })()}
                        </div>
                      </div>
                      
                      {/* Raw JSON Section with expand/collapse and copy */}
                      <div className="border-t pt-4">
                        <div className="flex items-center justify-between mb-2">
                          <button
                            onClick={() => setRawJsonExpanded(!rawJsonExpanded)}
                            className="flex items-center gap-2 text-sm font-semibold text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100"
                          >
                            {rawJsonExpanded ? (
                              <ChevronUp className="w-4 h-4" />
                            ) : (
                              <ChevronDown className="w-4 h-4" />
                            )}
                            View Complete JSON Context
                          </button>
                        </div>
                        
                        {rawJsonExpanded && (
                          <div className="mt-3 bg-gray-50 dark:bg-gray-800 p-3 rounded border border-gray-200 dark:border-gray-700">
                            <pre className="text-xs overflow-x-auto whitespace-pre-wrap text-gray-800 dark:text-gray-200">
                              {JSON.stringify(taskContext, null, 2)}
                            </pre>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-8 bg-gray-50 dark:bg-gray-800 rounded-lg m-4">
              <FileText className="w-12 h-12 text-gray-400 dark:text-gray-500 mx-auto mb-3" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">No Task Context Available</h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                Task context has not been initialized yet.
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Task: {task?.title} (ID: {task?.id})
              </p>
              <Button 
                variant="default" 
                className="mt-4"
                onClick={() => {
                  // Initialize with empty values
                  setTaskInfoMarkdown('');
                  setTaskProgressMarkdown('');
                  setCompletionSummaryMarkdown('');
                  setTestingNotesMarkdown('');
                  setBlockersMarkdown('');
                  setInsightsMarkdown('');
                  setNextStepsMarkdown('');
                  setTaskMetadataMarkdown('');
                  setTaskContext({ 
                    data: {
                      task_info: {},
                      task_progress: {},
                      completion_summary: '',
                      testing_notes: '',
                      blockers: [],
                      insights: [],
                      next_steps: [],
                      task_metadata: {}
                    }
                  });
                  setEditMode(true);
                }}
              >
                <Edit className="w-4 h-4 mr-2" />
                Initialize Task Context
              </Button>
            </div>
          )}
        </div>
        <DialogFooter>
          {!editMode && (
            <Button variant="outline" onClick={onClose}>
              Close
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default TaskContextDialog;