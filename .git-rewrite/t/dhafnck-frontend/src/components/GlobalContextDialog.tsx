import React, { useEffect, useState } from "react";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import { Textarea } from "./ui/textarea";
import { Globe, Save, Edit, X, Copy, Check as CheckIcon, Settings, Layers, Zap, Info } from "lucide-react";
import { getGlobalContext, updateGlobalContext } from "../api";

interface GlobalContextDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onClose: () => void;
}

// Parse markdown for Organization Settings and Metadata (key: value format)
const parseKeyValueMarkdown = (content: string): Record<string, string> => {
  const result: Record<string, string> = {};
  const lines = content.split('\n');
  let currentKey = '';
  let currentValue: string[] = [];

  lines.forEach((line) => {
    // Check if line contains a key-value separator
    if (line.includes(':') && !currentKey) {
      // Save previous key-value if exists
      if (currentKey && currentValue.length > 0) {
        result[currentKey] = currentValue.join('\n').trim();
      }
      
      // Parse new key-value
      const [key, ...valueParts] = line.split(':');
      currentKey = key.trim();
      const value = valueParts.join(':').trim();
      
      if (value) {
        // Single line value
        result[currentKey] = value;
        currentKey = '';
        currentValue = [];
      } else {
        // Multi-line value starts on next line
        currentValue = [];
      }
    } else if (currentKey) {
      // Continuation of multi-line value
      if (line.trim()) {
        currentValue.push(line);
      } else if (currentValue.length > 0) {
        // Empty line ends multi-line value
        result[currentKey] = currentValue.join('\n').trim();
        currentKey = '';
        currentValue = [];
      }
    }
  });

  // Save last key-value if exists
  if (currentKey && currentValue.length > 0) {
    result[currentKey] = currentValue.join('\n').trim();
  }

  return result;
};

// Parse markdown for Global Patterns (pattern_name: followed by description)
const parsePatternsMarkdown = (content: string): Record<string, string> => {
  const result: Record<string, string> = {};
  const lines = content.split('\n');
  let currentPattern = '';
  let currentDescription: string[] = [];

  lines.forEach((line) => {
    // Check if line is a pattern name (ends with :)
    if (line.trim().endsWith(':') && !line.includes(' ')) {
      // Save previous pattern if exists
      if (currentPattern && currentDescription.length > 0) {
        result[currentPattern] = currentDescription.join('\n').trim();
      }
      
      // Start new pattern
      currentPattern = line.trim().slice(0, -1); // Remove the colon
      currentDescription = [];
    } else if (currentPattern && line.trim()) {
      // Add to current pattern description
      currentDescription.push(line);
    } else if (!line.trim() && currentPattern && currentDescription.length > 0) {
      // Empty line may signal end of pattern
      result[currentPattern] = currentDescription.join('\n').trim();
      currentPattern = '';
      currentDescription = [];
    }
  });

  // Save last pattern if exists
  if (currentPattern && currentDescription.length > 0) {
    result[currentPattern] = currentDescription.join('\n').trim();
  }

  return result;
};

// Parse markdown for Shared Capabilities (bullet points)
const parseCapabilitiesMarkdown = (content: string): string[] => {
  const result: string[] = [];
  const lines = content.split('\n');

  lines.forEach((line) => {
    const trimmed = line.trim();
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ') || trimmed.startsWith('• ')) {
      result.push(trimmed.substring(2).trim());
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
    // Handle nested objects and arrays
    if (typeof value === 'object' && value !== null) {
      if (Array.isArray(value)) {
        return `${key}: ${value.join(', ')}`;
      } else {
        // For objects, show as JSON string or formatted text
        return `${key}: ${JSON.stringify(value, null, 2)}`;
      }
    }
    return `${key}: ${value}`;
  }).join('\n');
};

const patternsToMarkdown = (data: Record<string, any>): string => {
  if (!data || Object.keys(data).length === 0) {
    return '';
  }
  
  return Object.entries(data).map(([key, value]) => {
    // Handle nested objects properly
    if (typeof value === 'object' && value !== null) {
      // Convert nested object to readable format
      const nestedContent = Object.entries(value).map(([nestedKey, nestedValue]) => {
        if (typeof nestedValue === 'object' && nestedValue !== null) {
          // Handle deeply nested objects/arrays
          if (Array.isArray(nestedValue)) {
            return `  ${nestedKey}: ${nestedValue.join(', ')}`;
          } else {
            // For deeply nested objects, show each property
            const deepContent = Object.entries(nestedValue).map(([k, v]) => 
              `    ${k}: ${v}`
            ).join('\n');
            return `  ${nestedKey}:\n${deepContent}`;
          }
        }
        return `  ${nestedKey}: ${nestedValue}`;
      }).join('\n');
      return `${key}:\n${nestedContent}`;
    }
    return `${key}:\n${value}`;
  }).join('\n\n');
};

const capabilitiesToMarkdown = (data: string[]): string => {
  if (!data || data.length === 0) {
    return '';
  }
  return data.map(item => `- ${item}`).join('\n');
};

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
  const [activeTab, setActiveTab] = useState<'settings' | 'patterns' | 'capabilities' | 'metadata'>('settings');
  
  // Separate markdown content for each section
  const [settingsMarkdown, setSettingsMarkdown] = useState('');
  const [patternsMarkdown, setPatternsMarkdown] = useState('');
  const [capabilitiesMarkdown, setCapabilitiesMarkdown] = useState('');
  const [metadataMarkdown, setMetadataMarkdown] = useState('');

  // Fetch global context when dialog opens
  useEffect(() => {
    if (open) {
      fetchGlobalContext();
    } else {
      // Reset state when dialog closes
      setEditMode(false);
      setGlobalContext(null);
      setActiveTab('settings');
    }
  }, [open]);

  const fetchGlobalContext = async () => {
    setLoading(true);
    try {
      const context = await getGlobalContext();
      console.log('Fetched global context:', context);
      
      if (context) {
        console.log('Processing context response:', context);
        setGlobalContext(context);
        
        // Handle the actual API response structure
        // Backend returns: context.data.resolved_context.global_settings
        // Map to frontend expected structure
        const contextData = context.data || context;
        const resolvedContext = contextData.resolved_context || {};
        const globalSettings = resolvedContext.global_settings || {};
        
        console.log('Resolved context:', resolvedContext);
        console.log('Global settings:', globalSettings);
        
        // Convert backend fields to frontend expected format
        const organizationSettings = {
          ...(globalSettings.autonomous_rules || {}),
          ...(globalSettings.security_policies || {}),
          ...(globalSettings.coding_standards || {})
        };
        
        const globalPatterns = globalSettings.workflow_templates || {};
        const sharedCapabilities = []; // This might need to be extracted from another field
        const metadata = {
          id: resolvedContext.id || '',
          lastUpdated: new Date().toISOString(),
          ...globalSettings.delegation_rules || {}
        };
        
        console.log('Mapped data:', { organizationSettings, globalPatterns, sharedCapabilities, metadata });
        
        // Convert each section to markdown format
        setSettingsMarkdown(keyValueToMarkdown(organizationSettings));
        setPatternsMarkdown(patternsToMarkdown(globalPatterns));
        setCapabilitiesMarkdown(capabilitiesToMarkdown(sharedCapabilities));
        setMetadataMarkdown(keyValueToMarkdown(metadata));
      } else {
        console.log('No context received, showing empty state');
      }
    } catch (error) {
      console.error('Error fetching global context:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      // Parse markdown content from each section
      const organizationSettings = parseKeyValueMarkdown(settingsMarkdown);
      const globalPatterns = parsePatternsMarkdown(patternsMarkdown);
      const sharedCapabilities = parseCapabilitiesMarkdown(capabilitiesMarkdown);
      const metadata = parseKeyValueMarkdown(metadataMarkdown);
      
      // Prepare the data to save
      const dataToSave = {
        organizationSettings,
        globalPatterns,
        sharedCapabilities,
        metadata: {
          ...metadata,
          lastUpdated: new Date().toISOString(),
          updatedBy: 'user' // In a real app, this would be the actual user
        }
      };

      // Call the update API
      await updateGlobalContext(dataToSave);
      
      // Refresh the context
      await fetchGlobalContext();
      
      // Exit edit mode
      setEditMode(false);
    } catch (error) {
      console.error('Error saving global context:', error);
      alert('Failed to save global context. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    // Reset to original data using the same mapping as fetchGlobalContext
    if (globalContext) {
      const contextData = globalContext.data || globalContext;
      const resolvedContext = contextData.resolved_context || {};
      const globalSettings = resolvedContext.global_settings || {};
      
      // Convert backend fields to frontend expected format
      const organizationSettings = {
        ...(globalSettings.autonomous_rules || {}),
        ...(globalSettings.security_policies || {}),
        ...(globalSettings.coding_standards || {})
      };
      
      const globalPatterns = globalSettings.workflow_templates || {};
      const sharedCapabilities = [];
      const metadata = {
        id: resolvedContext.id || '',
        lastUpdated: new Date().toISOString(),
        ...globalSettings.delegation_rules || {}
      };
      
      setSettingsMarkdown(keyValueToMarkdown(organizationSettings));
      setPatternsMarkdown(patternsToMarkdown(globalPatterns));
      setCapabilitiesMarkdown(capabilitiesToMarkdown(sharedCapabilities));
      setMetadataMarkdown(keyValueToMarkdown(metadata));
    }
    setEditMode(false);
  };

  const copyJsonToClipboard = () => {
    if (globalContext) {
      const jsonString = JSON.stringify(globalContext, null, 2);
      navigator.clipboard.writeText(jsonString).then(() => {
        setJsonCopied(true);
        setTimeout(() => setJsonCopied(false), 2000);
      }).catch(err => {
        console.error('Failed to copy JSON:', err);
      });
    }
  };

  // Get the appropriate markdown content based on active tab
  const getCurrentMarkdown = () => {
    switch (activeTab) {
      case 'settings': return settingsMarkdown;
      case 'patterns': return patternsMarkdown;
      case 'capabilities': return capabilitiesMarkdown;
      case 'metadata': return metadataMarkdown;
      default: return '';
    }
  };

  // Set the appropriate markdown content based on active tab
  const setCurrentMarkdown = (value: string) => {
    switch (activeTab) {
      case 'settings': setSettingsMarkdown(value); break;
      case 'patterns': setPatternsMarkdown(value); break;
      case 'capabilities': setCapabilitiesMarkdown(value); break;
      case 'metadata': setMetadataMarkdown(value); break;
    }
  };

  // Get placeholder text based on active tab
  const getPlaceholder = () => {
    switch (activeTab) {
      case 'settings':
        return 'Add organization settings in format:\nkey: value\napi_url: https://api.example.com\nmax_retries: 3';
      case 'patterns':
        return 'Add global patterns in format:\npattern_name:\nDescription or code for the pattern\n\nanother_pattern:\nIts description';
      case 'capabilities':
        return 'Add shared capabilities as bullet points:\n- Authentication system\n- Real-time notifications\n- Data export functionality';
      case 'metadata':
        return 'Add metadata in format:\nkey: value\nversion: 1.0.0\nauthor: Team Name';
      default:
        return '';
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="text-xl text-left flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Globe className="w-5 h-5" />
              Global Context Management
            </div>
            <div className="flex gap-2">
              {!editMode && globalContext && (
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
        <div className="flex gap-2 border-b pb-2">
          <Button
            variant={activeTab === 'settings' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setActiveTab('settings')}
            className="flex items-center gap-2"
          >
            <Settings className="w-4 h-4" />
            Organization Settings
          </Button>
          <Button
            variant={activeTab === 'patterns' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setActiveTab('patterns')}
            className="flex items-center gap-2"
          >
            <Layers className="w-4 h-4" />
            Global Patterns
          </Button>
          <Button
            variant={activeTab === 'capabilities' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setActiveTab('capabilities')}
            className="flex items-center gap-2"
          >
            <Zap className="w-4 h-4" />
            Shared Capabilities
          </Button>
          <Button
            variant={activeTab === 'metadata' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setActiveTab('metadata')}
            className="flex items-center gap-2"
          >
            <Info className="w-4 h-4" />
            Metadata
          </Button>
        </div>
        
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="text-center py-8">
              <div className="inline-block w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
              <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Loading global context...</p>
            </div>
          ) : globalContext ? (
            <div className="h-full flex flex-col p-4">
              {editMode ? (
                // Edit Mode - Markdown Editor for active tab
                <>
                  <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3 mb-4">
                    <h3 className="font-semibold text-sm mb-2 dark:text-gray-200">
                      {activeTab === 'settings' && 'Organization Settings Format'}
                      {activeTab === 'patterns' && 'Global Patterns Format'}
                      {activeTab === 'capabilities' && 'Shared Capabilities Format'}
                      {activeTab === 'metadata' && 'Metadata Format'}
                    </h3>
                    <div className="text-xs text-gray-600 dark:text-gray-400">
                      {activeTab === 'settings' && (
                        <p>Use <code className="bg-white dark:bg-gray-700 px-1 rounded">key: value</code> format. Each setting on a new line.</p>
                      )}
                      {activeTab === 'patterns' && (
                        <p>Use <code className="bg-white dark:bg-gray-700 px-1 rounded">pattern_name:</code> followed by description/code on next lines.</p>
                      )}
                      {activeTab === 'capabilities' && (
                        <p>Use bullet points <code className="bg-white dark:bg-gray-700 px-1 rounded">- capability</code> for each item.</p>
                      )}
                      {activeTab === 'metadata' && (
                        <p>Use <code className="bg-white dark:bg-gray-700 px-1 rounded">key: value</code> format. Auto-generated fields will be preserved.</p>
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
                // View Mode - Display current tab content
                <div className="space-y-4">
                  <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-6">
                    <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                      {activeTab === 'settings' && <><Settings className="w-5 h-5" /> Organization Settings</>}
                      {activeTab === 'patterns' && <><Layers className="w-5 h-5" /> Global Patterns</>}
                      {activeTab === 'capabilities' && <><Zap className="w-5 h-5" /> Shared Capabilities</>}
                      {activeTab === 'metadata' && <><Info className="w-5 h-5" /> Metadata</>}
                    </h3>
                    {getCurrentMarkdown() ? (
                      <pre className="whitespace-pre-wrap font-mono text-sm text-gray-800 dark:text-gray-200">
                        {getCurrentMarkdown()}
                      </pre>
                    ) : (
                      <p className="text-sm text-gray-500 dark:text-gray-400 italic">
                        No {activeTab === 'settings' && 'settings'}
                        {activeTab === 'patterns' && 'patterns'}
                        {activeTab === 'capabilities' && 'capabilities'}
                        {activeTab === 'metadata' && 'metadata'} defined yet.
                      </p>
                    )}
                  </div>
                  
                  {/* Show raw JSON at the bottom in view mode */}
                  <details className="cursor-pointer">
                    <summary className="font-semibold text-sm text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100">
                      View Complete JSON Context
                    </summary>
                    <div className="mt-3 bg-gray-100 dark:bg-gray-800 p-3 rounded">
                      <pre className="text-xs overflow-x-auto whitespace-pre-wrap text-gray-800 dark:text-gray-200">
                        {JSON.stringify(globalContext, null, 2)}
                      </pre>
                    </div>
                  </details>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-8 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <Globe className="w-12 h-12 text-gray-400 dark:text-gray-500 mx-auto mb-3" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">No Global Context Available</h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                Global context has not been initialized yet.
              </p>
              <Button 
                variant="default" 
                className="mt-4"
                onClick={() => {
                  // Initialize with empty values and the expected backend structure
                  setSettingsMarkdown('');
                  setPatternsMarkdown('');
                  setCapabilitiesMarkdown('');
                  setMetadataMarkdown('');
                  setGlobalContext({ 
                    data: {
                      resolved_context: {
                        id: "7fa54328-bfb4-523c-ab6f-465e05e1bba5",
                        global_settings: {
                          autonomous_rules: {},
                          security_policies: {},
                          coding_standards: {},
                          workflow_templates: {},
                          delegation_rules: {}
                        }
                      }
                    }
                  });
                  setEditMode(true);
                }}
              >
                <Edit className="w-4 h-4 mr-2" />
                Initialize Global Context
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

export default GlobalContextDialog;