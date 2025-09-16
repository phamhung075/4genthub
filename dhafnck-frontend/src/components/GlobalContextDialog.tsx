import { Check as CheckIcon, ChevronDown, ChevronRight, Code, Copy, Database, Edit, FileText, Globe, Info, Save, Settings, Shield, X, AlertCircle } from "lucide-react";
import React, { useEffect, useState } from "react";
import { getGlobalContext, updateGlobalContext } from "../api";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import { Textarea } from "./ui/textarea";
import { EnhancedJSONViewer } from "./ui/EnhancedJSONViewer";
import RawJSONDisplay from "./ui/RawJSONDisplay";

interface GlobalContextDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onClose: () => void;
}

export const GlobalContextDialog: React.FC<GlobalContextDialogProps> = ({
  open,
  onOpenChange,
  onClose
}) => {
  const [globalContext, setGlobalContext] = useState<any>(null);
  const [editMode, setEditMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [jsonCopied, setJsonCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<'view' | 'edit'>('view');

  // Store the entire nested data structure for editing
  const [editingData, setEditingData] = useState<any>(null);

  // Raw JSON editing state
  const [rawJsonText, setRawJsonText] = useState<string>('');
  const [jsonValidationError, setJsonValidationError] = useState<string>('');

  // Fetch global context when dialog opens
  useEffect(() => {
    if (open) {
      fetchGlobalContext();
    } else {
      // Reset state when dialog closes
      setEditMode(false);
      setGlobalContext(null);
      setEditingData(null);
      setActiveTab('view');
      setRawJsonText('');
      setJsonValidationError('');
    }
  }, [open]);

  const fetchGlobalContext = async () => {
    setLoading(true);
    try {
      const response = await getGlobalContext();
      console.log('Fetched global context response:', response);
      
      // Extract the actual context data from the nested structure
      let contextData = {};
      
      if (response?.global_settings) {
        contextData = response.global_settings;
      } else if (response?.data?.global_settings) {
        contextData = response.data.global_settings;
      } else if (response?.context?.global_settings) {
        contextData = response.context.global_settings;
      } else if (response) {
        contextData = response;
      }
      
      console.log('Extracted context data:', contextData);
      
      // Set a default structure if context is empty
      const defaultContext = {
        user_preferences: {},
        ai_agent_settings: { preferred_agents: [] },
        workflow_preferences: {},
        development_tools: {},
        security_settings: {},
        dashboard_settings: {},
        autonomous_rules: {},
        security_policies: {},
        coding_standards: {},
        workflow_templates: {},
        delegation_rules: {},
        version: '1.0.0'
      };
      
      // Merge with defaults to ensure we always have a structure
      const finalContextData = { ...defaultContext, ...contextData };
      
      // Store both the raw context and a copy for editing
      setGlobalContext(finalContextData);
      setEditingData(JSON.parse(JSON.stringify(finalContextData))); // Deep copy for editing

      // Initialize raw JSON text for editing
      setRawJsonText(JSON.stringify(finalContextData, null, 2));

      console.log('Final context data:', finalContextData);
    } catch (error) {
      console.error('Error fetching global context:', error);
      // Initialize with empty structure on error
      const emptyContext = {
        user_preferences: {},
        ai_agent_settings: { preferred_agents: [] },
        workflow_preferences: {},
        development_tools: {},
        security_settings: {},
        dashboard_settings: {},
        autonomous_rules: {},
        security_policies: {},
        coding_standards: {},
        workflow_templates: {},
        delegation_rules: {},
        version: '1.0.0'
      };
      setGlobalContext(emptyContext);
      setEditingData(JSON.parse(JSON.stringify(emptyContext)));
      setRawJsonText(JSON.stringify(emptyContext, null, 2));
    } finally {
      setLoading(false);
    }
  };

  // Validate JSON text and return parsed object or error
  const validateJsonText = (jsonText: string): { isValid: boolean; data?: any; error?: string } => {
    try {
      if (!jsonText.trim()) {
        return { isValid: false, error: 'JSON cannot be empty' };
      }
      const parsed = JSON.parse(jsonText);
      return { isValid: true, data: parsed };
    } catch (error) {
      return {
        isValid: false,
        error: error instanceof Error ? error.message : 'Invalid JSON format'
      };
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setJsonValidationError('');

    try {
      // Validate raw JSON if we're in edit mode
      const validation = validateJsonText(rawJsonText);
      if (!validation.isValid) {
        setJsonValidationError(validation.error || 'Invalid JSON');
        setSaving(false);
        return;
      }

      const dataToSave = {
        ...validation.data,
        last_updated: new Date().toISOString()
      };

      await updateGlobalContext(dataToSave);
      await fetchGlobalContext();
      setEditMode(false);
      setActiveTab('view');
      setJsonValidationError('');
    } catch (error) {
      console.error('Error saving global context:', error);
      alert('Failed to save global context. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    if (globalContext) {
      setEditingData(JSON.parse(JSON.stringify(globalContext)));
      setRawJsonText(JSON.stringify(globalContext, null, 2));
    }
    setEditMode(false);
    setActiveTab('view');
    setJsonValidationError('');
  };

  // Handle raw JSON text changes with live validation
  const handleRawJsonChange = (value: string) => {
    setRawJsonText(value);

    // Clear previous validation error when user starts typing
    if (jsonValidationError) {
      setJsonValidationError('');
    }
  };

  // Update nested field value for edit mode (legacy - not used in raw JSON mode)
  const updateNestedField = (path: string[], value: any) => {
    if (!editingData) return;

    const newData = { ...editingData };
    let current = newData;

    for (let i = 0; i < path.length - 1; i++) {
      if (!current[path[i]]) {
        current[path[i]] = {};
      }
      current = current[path[i]];
    }

    const lastKey = path[path.length - 1];
    if (value === '' || value === null || value === undefined) {
      delete current[lastKey];
    } else {
      current[lastKey] = value;
    }

    setEditingData(newData);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-[90vw] max-w-6xl h-[85vh] mx-auto overflow-hidden bg-white dark:bg-gray-900 rounded-lg shadow-xl flex flex-col">
        <DialogHeader className="pb-0">
          <div className="flex items-center justify-between">
            <DialogTitle className="text-xl text-left flex items-center gap-2">
              <Globe className="w-5 h-5" />
              Global Context Management
            </DialogTitle>
            <div className="flex gap-2">
              {activeTab === 'view' && globalContext && (
                <Button
                  variant="default"
                  size="sm"
                  onClick={() => {
                    setEditMode(true);
                    setActiveTab('edit');
                  }}
                >
                  <Edit className="w-4 h-4 mr-2" />
                  Edit
                </Button>
              )}
              {activeTab === 'edit' && (
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
          </div>
        </DialogHeader>
        
        {/* Tab Navigation */}
        <div className="flex gap-1 border-b px-6 -mt-2">
          <button
            onClick={() => setActiveTab('view')}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-[1px] ${
              activeTab === 'view' 
                ? 'text-blue-700 dark:text-blue-300 border-blue-400 dark:border-blue-500 bg-blue-50 dark:bg-blue-900/20' 
                : 'text-gray-500 border-transparent hover:text-gray-700'
            }`}
          >
            <Info className="w-4 h-4" />
            View
          </button>
          
          {editMode && (
            <button
              onClick={() => setActiveTab('edit')}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-[1px] ${
                activeTab === 'edit' 
                  ? 'text-blue-700 dark:text-blue-300 border-blue-400 dark:border-blue-500 bg-blue-50 dark:bg-blue-900/20' 
                  : 'text-gray-500 border-transparent hover:text-gray-700'
              }`}
            >
              <Edit className="w-4 h-4" />
              Edit
              <Badge variant="secondary" className="text-xs ml-1">Mode</Badge>
            </button>
          )}
        </div>
        
        <div className="flex-1 overflow-hidden flex flex-col">
          <div className="space-y-4 overflow-y-auto flex-1 p-4">
            {loading ? (
              <div className="text-center py-8">
                <div className="inline-block w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                <p className="mt-2 text-sm text-gray-500">Loading global context...</p>
              </div>
            ) : globalContext ? (
              <>
                {/* Context Header */}
                <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950/20 dark:to-indigo-950/20 p-4 rounded-lg border border-blue-200 dark:border-blue-800">
                  <h3 className="text-lg font-semibold text-blue-700 dark:text-blue-300 flex items-center gap-2">
                    <Database className="w-5 h-5" />
                    Global Context Data
                  </h3>
                  <p className="text-sm text-blue-600 dark:text-blue-400 mt-1">
                    User-scoped global configuration and settings across all projects
                  </p>
                </div>
                
                {activeTab === 'edit' && (
                  <div className="space-y-4">
                    <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                      <h3 className="font-semibold text-sm mb-2 dark:text-gray-200 flex items-center gap-2">
                        <Code className="w-4 h-4" />
                        Raw JSON Editor
                      </h3>
                      <p className="text-xs text-blue-600 dark:text-blue-400 mb-3">
                        Edit the complete global context data as JSON. Changes will be validated before saving.
                      </p>

                      {jsonValidationError && (
                        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 mb-3">
                          <div className="flex items-center gap-2 text-red-700 dark:text-red-300">
                            <AlertCircle className="w-4 h-4" />
                            <span className="font-medium text-sm">JSON Validation Error</span>
                          </div>
                          <p className="text-sm text-red-600 dark:text-red-400 mt-1">{jsonValidationError}</p>
                        </div>
                      )}

                      <Textarea
                        value={rawJsonText}
                        onChange={(e) => handleRawJsonChange(e.target.value)}
                        placeholder="Enter valid JSON..."
                        className="min-h-[400px] font-mono text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600"
                        style={{ fontFamily: 'Monaco, Menlo, "Ubuntu Mono", monospace' }}
                      />

                      <div className="flex items-center justify-between mt-2">
                        <div className="text-xs text-gray-500 dark:text-gray-400">
                          {rawJsonText.length} characters • {rawJsonText.split('\n').length} lines
                        </div>
                        <div className="flex gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              try {
                                const formatted = JSON.stringify(JSON.parse(rawJsonText), null, 2);
                                setRawJsonText(formatted);
                                setJsonValidationError('');
                              } catch (error) {
                                setJsonValidationError('Invalid JSON - cannot format');
                              }
                            }}
                            disabled={!rawJsonText.trim()}
                          >
                            Format JSON
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
                
                {/* Organized Context Sections */}
                <div className="space-y-4">
                  {/* User Preferences */}
                  {globalContext.user_preferences && (
                    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                      <div className="bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-950/30 dark:to-emerald-950/30 p-3 border-l-4 border-green-400 dark:border-green-600">
                        <h3 className="text-green-700 dark:text-green-300 font-semibold flex items-center gap-2">
                          <Settings className="w-4 h-4" />
                          User Preferences
                        </h3>
                      </div>
                      <div className="p-4">
                        <EnhancedJSONViewer data={globalContext.user_preferences} defaultExpanded={false} maxHeight="max-h-64" />
                      </div>
                    </div>
                  )}

                  {/* AI Agent Settings */}
                  {globalContext.ai_agent_settings && (
                    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                      <div className="bg-gradient-to-r from-purple-50 to-violet-50 dark:from-purple-950/30 dark:to-violet-950/30 p-3 border-l-4 border-purple-400 dark:border-purple-600">
                        <h3 className="text-purple-700 dark:text-purple-300 font-semibold flex items-center gap-2">
                          <Code className="w-4 h-4" />
                          AI Agent Settings
                        </h3>
                      </div>
                      <div className="p-4">
                        <EnhancedJSONViewer data={globalContext.ai_agent_settings} defaultExpanded={false} />
                      </div>
                    </div>
                  )}

                  {/* Security Settings */}
                  {globalContext.security_settings && (
                    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                      <div className="bg-gradient-to-r from-red-50 to-rose-50 dark:from-red-950/30 dark:to-rose-950/30 p-3 border-l-4 border-red-400 dark:border-red-600">
                        <h3 className="text-red-700 dark:text-red-300 font-semibold flex items-center gap-2">
                          <Shield className="w-4 h-4" />
                          Security Settings
                        </h3>
                      </div>
                      <div className="p-4">
                        <EnhancedJSONViewer data={globalContext.security_settings} defaultExpanded={false} />
                      </div>
                    </div>
                  )}

                  {/* Workflow Preferences */}
                  {globalContext.workflow_preferences && (
                    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                      <div className="bg-gradient-to-r from-orange-50 to-amber-50 dark:from-orange-950/30 dark:to-amber-950/30 p-3 border-l-4 border-orange-400 dark:border-orange-600">
                        <h3 className="text-orange-700 dark:text-orange-300 font-semibold flex items-center gap-2">
                          <Settings className="w-4 h-4" />
                          Workflow Preferences
                        </h3>
                      </div>
                      <div className="p-4">
                        <EnhancedJSONViewer data={globalContext.workflow_preferences} defaultExpanded={false} />
                      </div>
                    </div>
                  )}

                  {/* Development Tools */}
                  {globalContext.development_tools && (
                    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                      <div className="bg-gradient-to-r from-indigo-50 to-blue-50 dark:from-indigo-950/30 dark:to-blue-950/30 p-3 border-l-4 border-indigo-400 dark:border-indigo-600">
                        <h3 className="text-indigo-700 dark:text-indigo-300 font-semibold flex items-center gap-2">
                          <Code className="w-4 h-4" />
                          Development Tools
                        </h3>
                      </div>
                      <div className="p-4">
                        <EnhancedJSONViewer data={globalContext.development_tools} defaultExpanded={false} />
                      </div>
                    </div>
                  )}

                  {/* Dashboard Settings */}
                  {globalContext.dashboard_settings && (
                    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                      <div className="bg-gradient-to-r from-cyan-50 to-sky-50 dark:from-cyan-950/30 dark:to-sky-950/30 p-3 border-l-4 border-cyan-400 dark:border-cyan-600">
                        <h3 className="text-cyan-700 dark:text-cyan-300 font-semibold flex items-center gap-2">
                          <Settings className="w-4 h-4" />
                          Dashboard Settings
                        </h3>
                      </div>
                      <div className="p-4">
                        <EnhancedJSONViewer data={globalContext.dashboard_settings} defaultExpanded={false} />
                      </div>
                    </div>
                  )}

                  {/* Custom Fields / Additional Data */}
                  {(() => {
                    const knownFields = [
                      'user_preferences', 'ai_agent_settings', 'security_settings',
                      'workflow_preferences', 'development_tools', 'dashboard_settings',
                      'version', 'last_updated', 'created_at', 'updated_at', 'id', 'user_id'
                    ];
                    const customFields = Object.entries(globalContext).filter(([key]) => 
                      !knownFields.includes(key) && !key.startsWith('_')
                    );
                    
                    if (customFields.length > 0) {
                      return (
                        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                          <div className="bg-gray-100 dark:bg-gray-800 p-3 border-l-4 border-gray-400 dark:border-gray-600">
                            <h3 className="text-gray-700 dark:text-gray-300 font-semibold flex items-center gap-2">
                              <Code className="w-4 h-4" />
                              Additional Settings
                            </h3>
                          </div>
                          <div className="p-4 space-y-3">
                            {customFields.map(([key, value]) => (
                              <details key={key} className="group">
                                <summary className="cursor-pointer font-medium text-sm text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 flex items-center gap-2">
                                  <ChevronRight className="w-4 h-4 transition-transform group-open:rotate-90" />
                                  {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                                </summary>
                                <div className="mt-2 ml-6">
                                  {typeof value === 'object' ? (
                                    <EnhancedJSONViewer data={value} defaultExpanded={false} maxHeight="max-h-48" />
                                  ) : (
                                    <span className="text-gray-700 dark:text-gray-300">{String(value)}</span>
                                  )}
                                </div>
                              </details>
                            ))}
                          </div>
                        </div>
                      );
                    }
                    return null;
                  })()}

                  {/* Metadata */}
                  {(globalContext.version || globalContext.last_updated) && (
                    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                      <div className="bg-gradient-to-r from-gray-50 to-zinc-50 dark:from-gray-950/30 dark:to-zinc-950/30 p-3 border-l-4 border-gray-400 dark:border-gray-600">
                        <h3 className="text-gray-700 dark:text-gray-300 font-semibold flex items-center gap-2">
                          <Info className="w-4 h-4" />
                          Metadata
                        </h3>
                      </div>
                      <div className="p-4">
                        {globalContext.version && (
                          <div className="mb-2 text-sm">
                            <span className="text-gray-500 dark:text-gray-400">Version:</span>
                            <span className="ml-2 text-gray-700 dark:text-gray-300">{globalContext.version}</span>
                          </div>
                        )}
                        {globalContext.last_updated && (
                          <div className="text-sm">
                            <span className="text-gray-500 dark:text-gray-400">Last Updated:</span>
                            <span className="ml-2 text-gray-700 dark:text-gray-300">
                              {new Date(globalContext.last_updated).toLocaleString()}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Raw JSON View - Always at the bottom */}
                  <details className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                    <summary className="cursor-pointer">
                      <div className="bg-gradient-to-r from-gray-50 to-slate-50 dark:from-gray-950/30 dark:to-slate-950/30 p-3 border-l-4 border-gray-400 dark:border-gray-600">
                        <h3 className="text-gray-700 dark:text-gray-300 font-semibold flex items-center gap-2">
                          <FileText className="w-4 h-4" />
                          Complete Raw Context
                        </h3>
                      </div>
                    </summary>
                    <div className="p-4">
                      <RawJSONDisplay 
                        jsonData={globalContext}
                        title="Global Context Data"
                        fileName="global_context.json"
                      />
                    </div>
                  </details>
                </div>
              </>
            ) : (
              <div className="text-center py-8 bg-surface-hover rounded-lg">
                <Globe className="w-12 h-12 text-gray-400 dark:text-gray-500 mx-auto mb-3" />
                <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">No Global Context Available</h3>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                  Global context has not been initialized yet.
                </p>
                <Button 
                  variant="default" 
                  className="mt-4"
                  onClick={() => {
                    const initialData = {
                      user_preferences: {},
                      ai_agent_settings: { preferred_agents: [] },
                      workflow_preferences: {},
                      development_tools: {},
                      security_settings: {},
                      dashboard_settings: {},
                      version: '1.0.0'
                    };
                    setGlobalContext(initialData);
                    setEditingData(initialData);
                    setEditMode(true);
                    setActiveTab('edit');
                  }}
                >
                  <Edit className="w-4 h-4 mr-2" />
                  Initialize Global Context
                </Button>
              </div>
            )}
          </div>
        </div>
        
        <DialogFooter className="flex justify-between">
          <div className="flex gap-2">
            {activeTab === 'view' && globalContext && (
              <>
                <Button
                  variant="outline"
                  onClick={() => {
                    const detailsElements = document.querySelectorAll('details');
                    detailsElements.forEach(details => {
                      details.open = true;
                    });
                    window.dispatchEvent(new CustomEvent('json-expand-all', { 
                      detail: { viewerId: 'all' } 
                    }));
                  }}
                  className="flex items-center gap-2"
                >
                  <ChevronDown className="w-4 h-4" />
                  Expand All
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    const detailsElements = document.querySelectorAll('details');
                    detailsElements.forEach(details => {
                      details.open = false;
                    });
                    window.dispatchEvent(new CustomEvent('json-collapse-all', { 
                      detail: { viewerId: 'all' } 
                    }));
                  }}
                  className="flex items-center gap-2"
                >
                  <ChevronRight className="w-4 h-4" />
                  Collapse All
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    if (globalContext) {
                      const jsonString = JSON.stringify(globalContext, null, 2);
                      navigator.clipboard.writeText(jsonString).then(() => {
                        setJsonCopied(true);
                        setTimeout(() => setJsonCopied(false), 2000);
                      }).catch(err => {
                        console.error('Failed to copy JSON:', err);
                      });
                    }
                  }}
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

export default GlobalContextDialog;