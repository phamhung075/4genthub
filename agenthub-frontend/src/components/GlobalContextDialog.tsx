import { AlertCircle, ChevronDown, ChevronRight, Code, Copy, Database, Edit, FileText, Globe, Info, Package, Save, X } from "lucide-react";
import React, { useEffect, useState } from "react";
import { getGlobalContext, updateGlobalContext } from "../api";
import { GlobalContext } from "../types/context.types";
import logger from "../utils/logger";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import { EnhancedJSONViewer } from "./ui/EnhancedJSONViewer";
import RawJSONDisplay from "./ui/RawJSONDisplay";
import { Textarea } from "./ui/textarea";

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
  const [globalContext, setGlobalContext] = useState<GlobalContext | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState<'view' | 'edit'>('view');
  const [isExpanded, setIsExpanded] = useState(true); // Track expansion state

  // Store the entire nested data structure for editing
  const [editingData, setEditingData] = useState<GlobalContext | null>(null);

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

  // Helper function to check if a value has actual data (non-recursive for objects)
  const hasData = (value: any): boolean => {
    if (value === null || value === undefined) return false;
    if (typeof value === 'string') return value.trim().length > 0;
    if (typeof value === 'number' || typeof value === 'boolean') return true;
    if (Array.isArray(value)) return value.length > 0;
    if (typeof value === 'object') {
      // For objects, just check if they have keys - don't recurse
      return Object.keys(value).length > 0;
    }
    return false;
  };

  // Helper function to recursively filter out properties with no data
  const filterEmptyProperties = (obj: any): any => {
    if (!obj || typeof obj !== 'object') return obj;

    if (Array.isArray(obj)) {
      // Filter out null/undefined/empty arrays
      return obj
        .filter(item => item !== null && item !== undefined)
        .map(filterEmptyProperties)
        .filter(item => {
          if (Array.isArray(item)) return item.length > 0;
          if (typeof item === 'object') return Object.keys(item).length > 0;
          return true;
        });
    }

    const filtered: any = {};
    Object.entries(obj).forEach(([key, value]) => {
      // Skip null and undefined
      if (value === null || value === undefined) {
        return;
      }

      // Handle strings - keep if not empty
      if (typeof value === 'string') {
        if (value.trim().length > 0) {
          filtered[key] = value;
        }
        return;
      }

      // Always keep numbers and booleans
      if (typeof value === 'number' || typeof value === 'boolean') {
        filtered[key] = value;
        return;
      }

      // Handle arrays - recurse and keep if not empty
      if (Array.isArray(value)) {
        const arrayFiltered = filterEmptyProperties(value);
        if (arrayFiltered.length > 0) {
          filtered[key] = arrayFiltered;
        }
        return;
      }

      // Handle objects - recurse and keep if not empty
      if (typeof value === 'object') {
        const nestedFiltered = filterEmptyProperties(value);
        if (Object.keys(nestedFiltered).length > 0) {
          filtered[key] = nestedFiltered;
        }
        return;
      }

      // Default: keep the value
      filtered[key] = value;
    });

    return filtered;
  };

  const fetchGlobalContext = async () => {
    setLoading(true);
    try {
      const response = await getGlobalContext();
      logger.debug('Fetched global context response:', response);

      // If response is null, undefined, or error, show empty
      if (!response || response === null) {
        logger.warn('No global context data available');
        setGlobalContext(null);
        setEditingData(null);
        setRawJsonText('{}');
        return;
      }

      // Extract the actual context data from the nested structure
      let contextData = response;

      // Try different nested paths for context data
      if (response?.global_settings) {
        contextData = response.global_settings;
      } else if (response?.data?.global_settings) {
        contextData = response.data.global_settings;
      } else if (response?.context?.global_settings) {
        contextData = response.context.global_settings;
      } else if (response?.data) {
        contextData = response.data;
      } else if (response?.context) {
        contextData = response.context;
      }

      logger.debug('Extracted context data:', contextData);
      logger.debug('Context data type:', typeof contextData);
      logger.debug('Context data keys:', contextData ? Object.keys(contextData) : 'none');

      // Filter out empty properties to only show data that exists
      const filteredContextData = filterEmptyProperties(contextData);

      logger.debug('Filtered context data:', filteredContextData);
      logger.debug('Filtered data keys:', filteredContextData ? Object.keys(filteredContextData) : 'none');

      // Check if filtered data is truly empty
      const hasAnyData = filteredContextData &&
                         typeof filteredContextData === 'object' &&
                         Object.keys(filteredContextData).length > 0;

      logger.debug('Has any data:', hasAnyData);

      if (!hasAnyData) {
        logger.info('Global context exists but contains no data after filtering');
        // Set to null to show "No data" message, but keep empty object for editing
        setGlobalContext(null);
        setEditingData({});
        setRawJsonText('{}');
      } else {
        // Store both the raw context and a copy for editing
        setGlobalContext(filteredContextData);
        setEditingData(JSON.parse(JSON.stringify(filteredContextData))); // Deep copy for editing
        setRawJsonText(JSON.stringify(filteredContextData, null, 2));
      }

      logger.debug('Final context data:', filteredContextData);
    } catch (error) {
      logger.error('Error fetching global context:', error);
      // Initialize with empty object on error (no defaults)
      setGlobalContext(null);
      setEditingData({});
      setRawJsonText('{}');
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
      logger.error('Error saving global context:', error);
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


  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-[90vw] max-w-6xl h-[85vh] mx-auto overflow-hidden bg-background rounded-lg shadow-xl flex flex-col">
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
                ? 'text-primary border-primary bg-primary/10'
                : 'text-muted-foreground border-transparent hover:text-foreground'
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
                  ? 'text-primary border-primary bg-primary/10'
                  : 'text-muted-foreground border-transparent hover:text-foreground'
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
                <div className="inline-block w-8 h-8 border-3 border-primary border-t-transparent rounded-full animate-spin"></div>
                <p className="mt-2 text-sm text-muted-foreground">Loading global context...</p>
              </div>
            ) : globalContext ? (
              <>
                {/* Context Header */}
                <div className="bg-muted/50 p-4 rounded-lg border border-primary/20">
                  <h3 className="text-lg font-semibold text-primary flex items-center gap-2">
                    <Database className="w-5 h-5" />
                    Global Context Data
                  </h3>
                  <p className="text-sm text-primary/80 mt-1">
                    User-scoped global configuration and settings across all projects
                  </p>
                </div>
                
                {activeTab === 'edit' && (
                  <div className="space-y-6">
                    {/* Enhanced JSON Editor Card */}
                    <Card className="border-2 border-primary/20 bg-muted/30">
                      <CardHeader className="bg-muted/50 p-4 border-l-4 border-primary/60">
                        <CardTitle className="flex items-center gap-2 text-foreground">
                          <Code className="w-5 h-5" />
                          Advanced JSON Editor
                          <Badge variant="secondary" className="ml-2 text-xs">Live Validation</Badge>
                        </CardTitle>
                        <CardDescription className="text-muted-foreground">
                          Edit the complete global context data as JSON with syntax highlighting and real-time validation feedback.
                        </CardDescription>
                      </CardHeader>

                      <CardContent className="p-4 space-y-4">
                        {/* Validation Status */}
                        <div className="flex items-center justify-between bg-background rounded-lg border p-3">
                          <div className="flex items-center gap-2">
                            {jsonValidationError ? (
                              <>
                                <div className="w-2 h-2 bg-destructive rounded-full animate-pulse"></div>
                                <span className="text-sm text-destructive font-medium">Invalid JSON</span>
                              </>
                            ) : (
                              <>
                                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                                <span className="text-sm text-green-600 dark:text-green-400 font-medium">Valid JSON</span>
                              </>
                            )}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {rawJsonText.length.toLocaleString()} chars • {rawJsonText.split('\n').length} lines
                          </div>
                        </div>

                        {/* Validation Error Display */}
                        {jsonValidationError && (
                          <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
                            <div className="flex items-start gap-2">
                              <AlertCircle className="w-5 h-5 text-destructive mt-0.5 flex-shrink-0" />
                              <div>
                                <h4 className="font-medium text-sm text-destructive mb-1">
                                  JSON Syntax Error
                                </h4>
                                <p className="text-sm text-destructive/80 mb-2">{jsonValidationError}</p>
                                <div className="text-xs text-destructive/60">
                                  Fix the syntax error above to enable saving. Use the "Format JSON" button to auto-format valid JSON.
                                </div>
                              </div>
                            </div>
                          </div>
                        )}

                        {/* JSON Editor Textarea */}
                        <div className="relative">
                          <Textarea
                            value={rawJsonText}
                            onChange={(e) => handleRawJsonChange(e.target.value)}
                            placeholder="Enter valid JSON..."
                            className={`min-h-[500px] font-mono text-sm resize-none ${
                              jsonValidationError
                                ? 'border-destructive/50 bg-destructive/5'
                                : 'border-green-500/50 bg-background'
                            }`}
                            style={{
                              fontFamily: 'Monaco, Menlo, "Ubuntu Mono", "Cascadia Code", "Fira Code", monospace',
                              lineHeight: '1.5',
                              tabSize: 2
                            }}
                          />

                          {/* Line numbers overlay - visual enhancement */}
                          <div className="absolute left-2 top-2 text-xs text-muted-foreground/50 pointer-events-none select-none font-mono leading-6">
                            {rawJsonText.split('\n').map((_, i) => (
                              <div key={i} className="h-6">
                                {(i + 1).toString().padStart(3, ' ')}
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Enhanced Toolbar */}
                        <div className="flex items-center justify-between bg-muted rounded-lg p-3">
                          <div className="flex items-center gap-2">
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
                              className="flex items-center gap-1"
                            >
                              <Code className="w-3 h-3" />
                              Format JSON
                            </Button>

                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                const minified = JSON.stringify(JSON.parse(rawJsonText));
                                setRawJsonText(minified);
                                setJsonValidationError('');
                              }}
                              disabled={!rawJsonText.trim() || !!jsonValidationError}
                              className="flex items-center gap-1"
                            >
                              <Package className="w-3 h-3" />
                              Minify
                            </Button>

                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                navigator.clipboard.writeText(rawJsonText);
                              }}
                              disabled={!rawJsonText.trim()}
                              className="flex items-center gap-1"
                            >
                              <Copy className="w-3 h-3" />
                              Copy
                            </Button>
                          </div>

                          {/* JSON Structure Preview */}
                          <div className="text-xs text-gray-600 dark:text-gray-400">
                            {!jsonValidationError && rawJsonText.trim() && (
                              <span>
                                {(() => {
                                  try {
                                    const parsed = JSON.parse(rawJsonText);
                                    const keys = Object.keys(parsed);
                                    return `${keys.length} top-level field${keys.length !== 1 ? 's' : ''}`;
                                  } catch {
                                    return '';
                                  }
                                })()}
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Quick Templates for Common Structures */}
                        <details className="bg-white dark:bg-gray-800 rounded-lg border">
                          <summary className="p-3 cursor-pointer text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg">
                            <div className="flex items-center gap-2">
                              <FileText className="w-4 h-4" />
                              Quick Templates
                            </div>
                          </summary>
                          <div className="p-3 pt-0 space-y-2">
                            <div className="grid grid-cols-2 gap-2">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  const template = {
                                    claude_md_rules: {
                                      clean_code: "NO compatibility code allowed - make clean breaks",
                                      test_hierarchy: "ORM Model > Database > Tests - ORM is source of truth"
                                    },
                                    user_preferences: {},
                                    ai_agent_settings: {
                                      preferred_agents: []
                                    }
                                  };
                                  setRawJsonText(JSON.stringify(template, null, 2));
                                  setJsonValidationError('');
                                }}
                                className="text-xs justify-start"
                              >
                                CLAUDE.md Template
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  const template = {
                                    security_settings: {
                                      two_factor_enabled: false,
                                      session_timeout: 120,
                                      audit_logging: true
                                    }
                                  };
                                  setRawJsonText(JSON.stringify(template, null, 2));
                                  setJsonValidationError('');
                                }}
                                className="text-xs justify-start"
                              >
                                Security Template
                              </Button>
                            </div>
                          </div>
                        </details>
                      </CardContent>
                    </Card>
                  </div>
                )}
                
                {/* Enhanced JSON Display - Interactive Tree View */}
                <div className="space-y-6">
                  {/* Enhanced JSON Viewer with expand/collapse */}
                  <Card className="border-2 border-primary/20 bg-background">
                    <CardHeader className="bg-muted/50 p-4 border-l-4 border-primary/60">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <CardTitle className="flex items-center gap-2 text-foreground">
                            <Database className="w-5 h-5" />
                            Global Context Data
                            <Badge variant="secondary" className="ml-2 text-xs">Interactive</Badge>
                          </CardTitle>
                          <CardDescription className="text-muted-foreground mt-1">
                            Expand and collapse sections to explore the nested data structure
                          </CardDescription>
                        </div>
                        <div className="flex gap-2 ml-4">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              if (isExpanded) {
                                // Collapse all
                                window.dispatchEvent(new CustomEvent('json-collapse-all', {
                                  detail: { viewerId: 'global-context-main' }
                                }));
                                setIsExpanded(false);
                              } else {
                                // Expand all
                                window.dispatchEvent(new CustomEvent('json-expand-all', {
                                  detail: { viewerId: 'global-context-main' }
                                }));
                                setIsExpanded(true);
                              }
                            }}
                            className="flex items-center gap-1"
                          >
                            {isExpanded ? (
                              <>
                                <ChevronRight className="w-4 h-4" />
                                Collapse All
                              </>
                            ) : (
                              <>
                                <ChevronDown className="w-4 h-4" />
                                Expand All
                              </>
                            )}
                          </Button>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent className="p-4">
                      <EnhancedJSONViewer
                        data={globalContext}
                        defaultExpanded={true}
                        maxHeight="max-h-[60vh]"
                        viewerId="global-context-main"
                      />
                    </CardContent>
                  </Card>

                  {/* Raw JSON View - Collapsed by default */}
                  <details className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                    <summary className="cursor-pointer">
                      <div className="bg-gray-50 dark:bg-gray-800 p-3 border-l-4 border-gray-400 dark:border-gray-600">
                        <h3 className="text-gray-700 dark:text-gray-300 font-semibold flex items-center gap-2">
                          <FileText className="w-4 h-4" />
                          Raw JSON (Copy/Export)
                        </h3>
                      </div>
                    </summary>
                    <div className="p-4">
                      <RawJSONDisplay
                        jsonData={globalContext}
                        title=""
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
                  Global context has not been initialized yet. Add your own properties as needed.
                </p>
                <Button
                  variant="default"
                  className="mt-4"
                  onClick={() => {
                    // Start with empty object - user can add properties as needed
                    const initialData = {};
                    setGlobalContext(initialData);
                    setEditingData(initialData);
                    setRawJsonText('{\n  \n}'); // Empty JSON with space for editing
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
        
        <DialogFooter className="flex justify-end">
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