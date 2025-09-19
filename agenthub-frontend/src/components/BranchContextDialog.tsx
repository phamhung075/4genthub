import React, { useEffect, useState } from "react";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import { Textarea } from "./ui/textarea";
import { GitBranch, Save, Edit, X, Copy, Check as CheckIcon, Info, Workflow, Flag, Lightbulb, FileCheck, Settings, Layers, ArrowUpDown, Zap, Globe, FolderOpen, ChevronDown, ChevronUp } from "lucide-react";
import { getBranchContext, updateBranchContext, getGlobalContext, getProjectContext } from "../api";
import logger from "../utils/logger";

interface BranchContextDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onClose: () => void;
  branchId: string;
}

// Parse markdown for Branch Settings (key: value format)
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

// Parse markdown for Feature Flags (flag_name: enabled/disabled)
const parseFeatureFlagsMarkdown = (content: string): Record<string, boolean> => {
  const result: Record<string, boolean> = {};
  const lines = content.split('\n');

  lines.forEach((line) => {
    if (line.includes(':')) {
      const [key, value] = line.split(':').map(s => s.trim());
      if (key && value) {
        result[key] = value.toLowerCase() === 'enabled' || value.toLowerCase() === 'true';
      }
    }
  });

  return result;
};

// Parse markdown for Patterns/Decisions (bullet points or numbered lists)
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

const featureFlagsToMarkdown = (data: Record<string, any>): string => {
  if (!data || Object.keys(data).length === 0) {
    return '';
  }
  
  return Object.entries(data).map(([key, value]) => {
    const status = value ? 'enabled' : 'disabled';
    return `${key}: ${status}`;
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

export const BranchContextDialog: React.FC<BranchContextDialogProps> = ({
  open,
  onOpenChange,
  onClose,
  branchId
}) => {
  const [branchContext, setBranchContext] = useState<any>(null);
  const [globalContext, setGlobalContext] = useState<any>(null);
  const [projectContext, setProjectContext] = useState<any>(null);
  const [projectId, setProjectId] = useState<string | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [jsonCopied, setJsonCopied] = useState(false);
  const [rawJsonExpanded, setRawJsonExpanded] = useState(false);
  const [activeTab, setActiveTab] = useState<'branch_info' | 'branch_workflow' | 'feature_flags' | 'discovered_patterns' | 'branch_decisions' | 'branch_settings' | 'active_patterns' | 'local_overrides' | 'delegation_rules' | 'inheritance'>('branch_info');
  
  // Separate markdown content for each section
  const [branchInfoMarkdown, setBranchInfoMarkdown] = useState('');
  const [branchWorkflowMarkdown, setBranchWorkflowMarkdown] = useState('');
  const [featureFlagsMarkdown, setFeatureFlagsMarkdown] = useState('');
  const [discoveredPatternsMarkdown, setDiscoveredPatternsMarkdown] = useState('');
  const [branchDecisionsMarkdown, setBranchDecisionsMarkdown] = useState('');
  const [branchSettingsMarkdown, setBranchSettingsMarkdown] = useState('');
  const [activePatternsMarkdown, setActivePatternsMarkdown] = useState('');
  const [localOverridesMarkdown, setLocalOverridesMarkdown] = useState('');
  const [delegationRulesMarkdown, setDelegationRulesMarkdown] = useState('');

  // Fetch branch context when dialog opens
  useEffect(() => {
    if (open && branchId) {
      fetchBranchContext();
    } else {
      setEditMode(false);
      setBranchContext(null);
      setActiveTab('branch_info');
    }
  }, [open, branchId]);

  const fetchBranchContext = async () => {
    setLoading(true);
    try {
      const context = await getBranchContext(branchId);
      logger.debug('Fetched branch context:', context);
      
      if (context) {
        setBranchContext(context);
        
        // Handle the actual API response structure
        const contextData = context.data || context;
        
        // Extract branch-specific fields
        const branchInfo = contextData.branch_info || {};
        const branchWorkflow = contextData.branch_workflow || {};
        const featureFlags = contextData.feature_flags || {};
        const discoveredPatterns = contextData.discovered_patterns || {};
        const branchDecisions = contextData.branch_decisions || {};
        const branchSettings = contextData.branch_settings || {};
        const activePatterns = contextData.active_patterns || {};
        const localOverrides = contextData.local_overrides || {};
        const delegationRules = contextData.delegation_rules || {};
        
        // Convert each section to markdown format
        setBranchInfoMarkdown(keyValueToMarkdown(branchInfo));
        setBranchWorkflowMarkdown(keyValueToMarkdown(branchWorkflow));
        setFeatureFlagsMarkdown(featureFlagsToMarkdown(featureFlags));
        setDiscoveredPatternsMarkdown(listToMarkdown(discoveredPatterns));
        setBranchDecisionsMarkdown(listToMarkdown(branchDecisions));
        setBranchSettingsMarkdown(keyValueToMarkdown(branchSettings));
        setActivePatternsMarkdown(listToMarkdown(activePatterns));
        setLocalOverridesMarkdown(keyValueToMarkdown(localOverrides));
        setDelegationRulesMarkdown(keyValueToMarkdown(delegationRules));
      }
    } catch (error) {
      logger.error('Error fetching branch context:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      // Parse markdown content from each section
      const branchInfo = parseKeyValueMarkdown(branchInfoMarkdown);
      const branchWorkflow = parseKeyValueMarkdown(branchWorkflowMarkdown);
      const featureFlags = parseFeatureFlagsMarkdown(featureFlagsMarkdown);
      const discoveredPatterns = parseListMarkdown(discoveredPatternsMarkdown);
      const branchDecisions = parseListMarkdown(branchDecisionsMarkdown);
      const branchSettings = parseKeyValueMarkdown(branchSettingsMarkdown);
      const activePatterns = parseListMarkdown(activePatternsMarkdown);
      const localOverrides = parseKeyValueMarkdown(localOverridesMarkdown);
      const delegationRules = parseKeyValueMarkdown(delegationRulesMarkdown);
      
      // Prepare the data to save
      const dataToSave = {
        branch_info: branchInfo,
        branch_workflow: branchWorkflow,
        feature_flags: featureFlags,
        discovered_patterns: discoveredPatterns,
        branch_decisions: branchDecisions,
        branch_settings: branchSettings,
        active_patterns: activePatterns,
        local_overrides: localOverrides,
        delegation_rules: delegationRules
      };

      // Call the update API
      await updateBranchContext(branchId, dataToSave);
      
      // Refresh the context
      await fetchBranchContext();
      
      // Exit edit mode
      setEditMode(false);
    } catch (error) {
      logger.error('Error saving branch context:', error);
      alert('Failed to save branch context. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    if (branchContext) {
      const contextData = branchContext.data || branchContext;
      
      setBranchInfoMarkdown(keyValueToMarkdown(contextData.branch_info || {}));
      setBranchWorkflowMarkdown(keyValueToMarkdown(contextData.branch_workflow || {}));
      setFeatureFlagsMarkdown(featureFlagsToMarkdown(contextData.feature_flags || {}));
      setDiscoveredPatternsMarkdown(listToMarkdown(contextData.discovered_patterns || {}));
      setBranchDecisionsMarkdown(listToMarkdown(contextData.branch_decisions || {}));
      setBranchSettingsMarkdown(keyValueToMarkdown(contextData.branch_settings || {}));
      setActivePatternsMarkdown(listToMarkdown(contextData.active_patterns || {}));
      setLocalOverridesMarkdown(keyValueToMarkdown(contextData.local_overrides || {}));
      setDelegationRulesMarkdown(keyValueToMarkdown(contextData.delegation_rules || {}));
    }
    setEditMode(false);
  };

  const copyJsonToClipboard = () => {
    if (branchContext) {
      const jsonString = JSON.stringify(branchContext, null, 2);
      navigator.clipboard.writeText(jsonString).then(() => {
        setJsonCopied(true);
        setTimeout(() => setJsonCopied(false), 2000);
      }).catch(err => {
        logger.error('Failed to copy JSON:', err);
      });
    }
  };

  // Get level-based styling
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
      case 'branch_info': return branchInfoMarkdown;
      case 'branch_workflow': return branchWorkflowMarkdown;
      case 'feature_flags': return featureFlagsMarkdown;
      case 'discovered_patterns': return discoveredPatternsMarkdown;
      case 'branch_decisions': return branchDecisionsMarkdown;
      case 'branch_settings': return branchSettingsMarkdown;
      case 'active_patterns': return activePatternsMarkdown;
      case 'local_overrides': return localOverridesMarkdown;
      case 'delegation_rules': return delegationRulesMarkdown;
      default: return '';
    }
  };

  // Set the appropriate markdown content based on active tab
  const setCurrentMarkdown = (value: string) => {
    switch (activeTab) {
      case 'branch_info': setBranchInfoMarkdown(value); break;
      case 'branch_workflow': setBranchWorkflowMarkdown(value); break;
      case 'feature_flags': setFeatureFlagsMarkdown(value); break;
      case 'discovered_patterns': setDiscoveredPatternsMarkdown(value); break;
      case 'branch_decisions': setBranchDecisionsMarkdown(value); break;
      case 'branch_settings': setBranchSettingsMarkdown(value); break;
      case 'active_patterns': setActivePatternsMarkdown(value); break;
      case 'local_overrides': setLocalOverridesMarkdown(value); break;
      case 'delegation_rules': setDelegationRulesMarkdown(value); break;
    }
  };

  // Get placeholder text based on active tab
  const getPlaceholder = () => {
    switch (activeTab) {
      case 'branch_info':
        return 'Add branch information:\nfeature: User authentication system\nticket: AUTH-123\nowner: John Doe\nestimated_completion: 2024-01-15';
      case 'branch_workflow':
        return 'Add branch workflow:\nstrategy: Feature branch\nmerge_policy: Squash and merge\nreview_required: true\nci_checks: All must pass';
      case 'feature_flags':
        return 'Add feature flags:\nnew_auth_flow: enabled\nbeta_features: disabled\ndebug_mode: enabled';
      case 'discovered_patterns':
        return 'Add discovered patterns:\n- Authentication hook pattern\n- Error boundary implementation\n- Custom validation utilities\n- React query integration';
      case 'branch_decisions':
        return 'Add branch decisions:\n- Use JWT for authentication tokens\n- Implement refresh token rotation\n- Store user preferences in localStorage\n- Use React Hook Form for validation';
      case 'branch_settings':
        return 'Add branch settings:\nauto_merge: false\ndelete_after_merge: true\nprotected: false\nrequire_status_checks: true';
      case 'active_patterns':
        return 'Add active patterns:\n- Custom hook for API calls\n- Error handling wrapper\n- Form validation schema\n- Component composition pattern';
      case 'local_overrides':
        return 'Add local overrides:\napi_base_url: http://localhost:3000\ndebug: true\nlog_level: verbose\nfeature_preview: enabled';
      case 'delegation_rules':
        return 'Add delegation rules:\ncode_review: senior_developer\ndeployment_approval: team_lead\narchitecture_decisions: architect\nsecurity_review: security_team';
      default:
        return '';
    }
  };

  const getTabIcon = (tab: string) => {
    switch (tab) {
      case 'branch_info': return <Info className="w-4 h-4" />;
      case 'branch_workflow': return <Workflow className="w-4 h-4" />;
      case 'feature_flags': return <Flag className="w-4 h-4" />;
      case 'discovered_patterns': return <Lightbulb className="w-4 h-4" />;
      case 'branch_decisions': return <FileCheck className="w-4 h-4" />;
      case 'branch_settings': return <Settings className="w-4 h-4" />;
      case 'active_patterns': return <Layers className="w-4 h-4" />;
      case 'local_overrides': return <ArrowUpDown className="w-4 h-4" />;
      case 'delegation_rules': return <Zap className="w-4 h-4" />;
      default: return <Settings className="w-4 h-4" />;
    }
  };

  const getTabLabel = (tab: string) => {
    switch (tab) {
      case 'branch_info': return 'Branch Info';
      case 'branch_workflow': return 'Workflow';
      case 'feature_flags': return 'Feature Flags';
      case 'discovered_patterns': return 'Patterns';
      case 'branch_decisions': return 'Decisions';
      case 'branch_settings': return 'Settings';
      case 'active_patterns': return 'Active Patterns';
      case 'local_overrides': return 'Overrides';
      case 'delegation_rules': return 'Delegation';
      default: return 'Settings';
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-[90vw] h-[90vh] max-w-[90vw] max-h-[90vh] overflow-hidden bg-white dark:bg-gray-900 rounded-lg shadow-xl flex flex-col">
        <DialogHeader>
          <DialogTitle className="text-xl text-left flex items-center gap-2">
            <GitBranch className="w-5 h-5" />
            Branch Context
          </DialogTitle>
        </DialogHeader>
        
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="text-center py-8">
              <div className="inline-block w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
              <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Loading branch context...</p>
            </div>
          ) : branchContext ? (
            <div className="space-y-4 p-4">
              {/* Context Header */}
              <div className="bg-surface-hover rounded-lg p-6">
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <GitBranch className="w-5 h-5" /> 
                  Branch Context Data
                </h3>
                
                {/* Render nested data with level-based styling */}
                <div className="space-y-2">
                  {renderNestedData(branchContext.data || branchContext)}
                </div>
                
                {/* Raw JSON Section with expand/collapse and copy */}
                <div className="mt-6 border-t pt-4">
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
                  </div>
                  
                  {rawJsonExpanded && (
                    <div className="mt-3 bg-gray-50 dark:bg-gray-800 p-3 rounded border border-gray-200 dark:border-gray-700">
                      <pre className="text-xs overflow-x-auto whitespace-pre-wrap text-gray-800 dark:text-gray-200">
                        {JSON.stringify(branchContext, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <GitBranch className="w-12 h-12 text-gray-400 dark:text-gray-500 mx-auto mb-3" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">No Branch Context Available</h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                Branch context has not been initialized yet.
              </p>
              <Button 
                variant="default" 
                className="mt-4"
                onClick={() => {
                  // Initialize with empty values
                  setBranchInfoMarkdown('');
                  setBranchWorkflowMarkdown('');
                  setFeatureFlagsMarkdown('');
                  setDiscoveredPatternsMarkdown('');
                  setBranchDecisionsMarkdown('');
                  setBranchSettingsMarkdown('');
                  setActivePatternsMarkdown('');
                  setLocalOverridesMarkdown('');
                  setDelegationRulesMarkdown('');
                  setBranchContext({ 
                    data: {
                      branch_info: {},
                      branch_workflow: {},
                      feature_flags: {},
                      discovered_patterns: {},
                      branch_decisions: {},
                      branch_settings: {},
                      active_patterns: {},
                      local_overrides: {},
                      delegation_rules: {}
                    }
                  });
                  setEditMode(true);
                }}
              >
                <Edit className="w-4 h-4 mr-2" />
                Initialize Branch Context
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

export default BranchContextDialog;