import { AlertCircle, Bot, Check as CheckIcon, ChevronDown, ChevronRight, Code, Copy, Database, Edit, FileText, GitBranch, Globe, Info, LayoutDashboard, Package, Save, Settings, Shield, Tag, X } from "lucide-react";
import React, { useEffect, useState } from "react";
import { getGlobalContext, updateGlobalContext } from "../api";
import {
  categorizeField,
  ContextFieldMetadata,
  GLOBAL_CONTEXT_FIELD_METADATA,
  GlobalContext
} from "../types/context.types";
import logger from "../utils/logger";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "./ui/accordion";
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
  const [jsonCopied, setJsonCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<'view' | 'edit'>('view');

  // Store the entire nested data structure for editing
  const [editingData, setEditingData] = useState<GlobalContext | null>(null);

  // Raw JSON editing state
  const [rawJsonText, setRawJsonText] = useState<string>('');
  const [jsonValidationError, setJsonValidationError] = useState<string>('');

  // Accordion state for controlling which sections are expanded
  const [expandedSections, setExpandedSections] = useState<string[]>(['claude_md_rules']);

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
      logger.debug('Fetched global context response:', response);
      
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
      
      logger.debug('Extracted context data:', contextData);
      
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

      logger.debug('Final context data:', finalContextData);
    } catch (error) {
      logger.error('Error fetching global context:', error);
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

  // Update nested field value for edit mode (legacy - not used in raw JSON mode)
  const updateNestedField = (path: string[], value: any) => {
    if (!editingData) return;

    const newData = { ...editingData };
    let current: any = newData;

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

  // Get icon component for field metadata
  const getIconComponent = (iconName: string) => {
    const iconMap: Record<string, any> = {
      FileText,
      Settings,
      Bot,
      Shield,
      GitBranch,
      Code,
      LayoutDashboard,
      Package,
      Tag,
      Info,
      Database
    };
    return iconMap[iconName] || Tag;
  };

  // Render a context section with proper styling and metadata
  const renderContextSection = (key: string, value: any, metadata: ContextFieldMetadata) => {
    const IconComponent = getIconComponent(metadata.icon || 'Package');
    const colorClasses = {
      blue: 'bg-blue-50 dark:bg-blue-900 border-blue-200 dark:border-blue-700 text-blue-700 dark:text-blue-300',
      green: 'bg-green-50 dark:bg-green-900 border-green-200 dark:border-green-700 text-green-700 dark:text-green-300',
      purple: 'bg-purple-50 dark:bg-purple-900 border-purple-200 dark:border-purple-700 text-purple-700 dark:text-purple-300',
      red: 'bg-red-50 dark:bg-red-900 border-red-200 dark:border-red-700 text-red-700 dark:text-red-300',
      orange: 'bg-orange-50 dark:bg-orange-900 border-orange-200 dark:border-orange-700 text-orange-700 dark:text-orange-300',
      indigo: 'bg-indigo-50 dark:bg-indigo-900 border-indigo-200 dark:border-indigo-700 text-indigo-700 dark:text-indigo-300',
      cyan: 'bg-cyan-50 dark:bg-cyan-900 border-cyan-200 dark:border-cyan-700 text-cyan-700 dark:text-cyan-300',
      gray: 'bg-gray-50 dark:bg-gray-900 border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300'
    };

    const colorClass = colorClasses[metadata.color as keyof typeof colorClasses] || colorClasses.gray;

    return (
      <Card key={key} className="overflow-hidden">
        <CardHeader className={`${colorClass} p-3 border-l-4`}>
          <CardTitle className="flex items-center gap-2 text-sm">
            <IconComponent className="w-4 h-4" />
            {metadata.label}
          </CardTitle>
          {metadata.description && (
            <CardDescription className="text-xs">
              {metadata.description}
            </CardDescription>
          )}
        </CardHeader>
        <CardContent className="p-4">
          <EnhancedJSONViewer
            data={value}
            defaultExpanded={metadata.defaultExpanded || false}
            maxHeight="max-h-64"
          />
        </CardContent>
      </Card>
    );
  };

  // Get organized sections from context data
  const getOrganizedSections = (context: GlobalContext) => {
    const sections: Array<{ key: string; value: any; metadata: ContextFieldMetadata }> = [];
    const processedKeys = new Set<string>();

    // First, add known fields with metadata
    GLOBAL_CONTEXT_FIELD_METADATA.forEach(metadata => {
      if (context[metadata.key] && !processedKeys.has(metadata.key)) {
        sections.push({
          key: metadata.key,
          value: context[metadata.key],
          metadata
        });
        processedKeys.add(metadata.key);
      }
    });

    // Then, add unknown fields
    const knownMetadataKeys = ['version', 'last_updated', 'created_at', 'updated_at', 'user_id', 'id'];
    Object.entries(context).forEach(([key, value]) => {
      if (!processedKeys.has(key) && !knownMetadataKeys.includes(key) && !key.startsWith('_')) {
        const metadata = categorizeField(key, value);
        sections.push({ key, value, metadata });
        processedKeys.add(key);
      }
    });

    return sections;
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
                
                {/* Modern Accordion-Based Context Sections */}
                <div className="space-y-6">
                  {/* Priority Section: CLAUDE.md Rules - Always show first and expanded */}
                  {globalContext.claude_md_rules && (
                    <Card className="border-2 border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-gray-800">
                      <CardHeader className="bg-blue-50 dark:bg-gray-800 p-4 border-l-4 border-blue-400 dark:border-blue-600">
                        <CardTitle className="flex items-center gap-2 text-blue-700 dark:text-blue-300">
                          <FileText className="w-5 h-5" />
                          CLAUDE.md Rules
                          <Badge variant="secondary" className="ml-2 text-xs">Priority</Badge>
                        </CardTitle>
                        <CardDescription className="text-blue-600 dark:text-blue-400">
                          Core AI agent rules and guidelines from CLAUDE.md
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="p-4">
                        <div className="space-y-3">
                          {Object.entries(globalContext.claude_md_rules).map(([ruleKey, ruleValue]) => (
                            <div key={ruleKey} className="bg-white dark:bg-gray-900 rounded-lg border border-blue-200 dark:border-blue-700 p-3">
                              <h4 className="font-medium text-sm text-blue-700 dark:text-blue-300 mb-1">
                                {ruleKey.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                              </h4>
                              <p className="text-sm text-gray-700 dark:text-gray-300">
                                {String(ruleValue)}
                              </p>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {/* Regular Context Sections using Accordion */}
                  <Accordion
                    type="multiple"
                    value={expandedSections}
                    onValueChange={setExpandedSections}
                    className="space-y-4"
                  >
                    {getOrganizedSections(globalContext).map(({ key, value, metadata }) => {
                      // Skip claude_md_rules as it's handled separately above
                      if (key === 'claude_md_rules') return null;

                      return (
                        <AccordionItem key={key} value={key} className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden bg-white dark:bg-gray-800">
                          <AccordionTrigger className="hover:no-underline px-4 py-3 bg-gray-50 dark:bg-gray-800">
                            <div className="flex items-center gap-3 text-left">
                              {React.createElement(getIconComponent(metadata.icon || 'Package'), { className: 'w-4 h-4' })}
                              <div>
                                <div className="font-medium text-sm">{metadata.label}</div>
                                {metadata.description && (
                                  <div className="text-xs text-gray-500 dark:text-gray-400">
                                    {metadata.description}
                                  </div>
                                )}
                              </div>
                              <div className="ml-auto flex items-center gap-2">
                                <Badge variant={metadata.category === 'core' ? 'default' : 'secondary'} className="text-xs">
                                  {metadata.category}
                                </Badge>
                              </div>
                            </div>
                          </AccordionTrigger>
                          <AccordionContent className="px-4 pb-4">
                            <EnhancedJSONViewer
                              data={value}
                              defaultExpanded={metadata.defaultExpanded || false}
                              maxHeight="max-h-64"
                            />
                          </AccordionContent>
                        </AccordionItem>
                      );
                    })}
                  </Accordion>

                  {/* Metadata */}
                  {(globalContext.version || globalContext.last_updated) && (
                    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                      <div className="bg-gray-50 dark:bg-gray-800 p-3 border-l-4 border-gray-400 dark:border-gray-600">
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
                      <div className="bg-gray-50 dark:bg-gray-800 p-3 border-l-4 border-gray-400 dark:border-gray-600">
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
                    // Expand all accordion sections
                    const allSectionKeys = getOrganizedSections(globalContext)
                      .map(section => section.key)
                      .filter(key => key !== 'claude_md_rules');
                    setExpandedSections(allSectionKeys);

                    // Also expand all JSON viewers
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
                    // Collapse all accordion sections
                    setExpandedSections([]);

                    // Also collapse all JSON viewers
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
                        logger.error('Failed to copy JSON:', err);
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