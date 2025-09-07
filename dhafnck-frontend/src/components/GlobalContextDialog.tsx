import { Check as CheckIcon, ChevronDown, ChevronRight, Edit, Folder, GitBranch, Globe, Info, Save, X } from "lucide-react";
import React, { useEffect, useState } from "react";
import { getGlobalContext, updateGlobalContext } from "../api";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import RawJSONDisplay from "./ui/RawJSONDisplay";

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
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    settings: true,
    patterns: true,
    capabilities: true,
    metadata: true,
    rawJson: false,  // Raw JSON collapsed by default
    projectJson: false,
    branchJson: false,
    taskJson: false
  });
  
  // Store the entire nested data structure for editing
  const [editingData, setEditingData] = useState<any>(null);

  // Fetch global context when dialog opens
  useEffect(() => {
    if (open) {
      fetchGlobalContext();
    } else {
      // Reset state when dialog closes
      setEditMode(false);
      setGlobalContext(null);
      setEditingData(null);
      setExpandedSections({
        settings: true,
        patterns: true,
        capabilities: true,
        metadata: true,
        rawJson: false,
        projectJson: false,
        branchJson: false,
        taskJson: false
      });
    }
  }, [open]);

  const fetchGlobalContext = async () => {
    setLoading(true);
    try {
      const response = await getGlobalContext();
      console.log('Fetched global context response:', response);
      
      // The response has the structure we saw: data nested under global_settings
      // Extract the actual context data from the nested structure
      let contextData = {};
      
      if (response?.global_settings) {
        // Direct global_settings at root level
        contextData = response.global_settings;
      } else if (response?.data?.global_settings) {
        // Nested under data
        contextData = response.data.global_settings;
      } else if (response?.context?.global_settings) {
        // Nested under context
        contextData = response.context.global_settings;
      } else if (response) {
        // Fallback to entire response
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
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      // Use the edited nested data directly
      const dataToSave = {
        ...editingData,
        last_updated: new Date().toISOString()
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
    // Reset to original data
    if (globalContext) {
      setEditingData(JSON.parse(JSON.stringify(globalContext))); // Deep copy
    }
    setEditMode(false);
  };


  // Toggle section expansion
  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  // Update nested field value
  const updateNestedField = (path: string[], value: any) => {
    if (!editingData) return;
    
    const newData = { ...editingData };
    let current = newData;
    
    // Navigate to the parent of the field to update
    for (let i = 0; i < path.length - 1; i++) {
      if (!current[path[i]]) {
        current[path[i]] = {};
      }
      current = current[path[i]];
    }
    
    // Update the field
    const lastKey = path[path.length - 1];
    if (value === '' || value === null || value === undefined) {
      delete current[lastKey];
    } else {
      current[lastKey] = value;
    }
    
    setEditingData(newData);
  };

  // Categorize fields by context level
  const categorizeFieldsByLevel = (data: any) => {
    if (!data) return { global: {}, project: {}, branch: {}, task: {} };
    
    // Define which fields belong to which level
    const globalFields = [
      'user_preferences', 'ai_agent_settings', 'security_settings', 
      'dashboard_settings', 'global_preferences', 'organization_standards',
      'compliance_requirements', 'shared_resources', 'reusable_patterns',
      'autonomous_rules', 'security_policies', 'coding_standards',
      'workflow_templates', 'delegation_rules', 'global_settings'
    ];
    
    const projectFields = [
      'project_info', 'project_settings', 'technical_specifications',
      'team_preferences', 'technology_stack', 'project_workflow',
      'local_standards', 'project_preferences'
    ];
    
    const branchFields = [
      'branch_info', 'branch_workflow', 'feature_flags',
      'discovered_patterns', 'branch_decisions', 'branch_settings'
    ];
    
    const taskFields = [
      'task_data', 'execution_context', 'test_results',
      'blockers', 'implementation_notes', 'task_settings'
    ];
    
    const categorized = {
      global: {},
      project: {},
      branch: {},
      task: {},
      other: {}
    };
    
    // Categorize each field
    Object.entries(data).forEach(([key, value]) => {
      if (globalFields.includes(key)) {
        categorized.global[key] = value;
      } else if (projectFields.includes(key)) {
        categorized.project[key] = value;
      } else if (branchFields.includes(key)) {
        categorized.branch[key] = value;
      } else if (taskFields.includes(key)) {
        categorized.task[key] = value;
      } else if (!['id', 'user_id', 'created_at', 'updated_at', 'last_updated', 'version'].includes(key)) {
        // Don't show metadata fields in categorized view
        categorized.other[key] = value;
      }
    });
    
    return categorized;
  };

  // Get level-based styling
  const getLevelStyling = (depth: number) => {
    const styles = [
      { // Level 0 - Root fields
        bg: 'bg-blue-50 dark:bg-blue-900/10',
        border: 'border-l-4 border-blue-500',
        text: 'text-blue-900 dark:text-blue-100',
        keySize: 'text-base font-semibold',
        padding: 'pl-3',
      },
      { // Level 1 - First nested
        bg: 'bg-green-50 dark:bg-green-900/10',
        border: 'border-l-4 border-green-500',
        text: 'text-green-900 dark:text-green-100',
        keySize: 'text-sm font-medium',
        padding: 'pl-6',
      },
      { // Level 2 - Second nested
        bg: 'bg-purple-50 dark:bg-purple-900/10',
        border: 'border-l-4 border-purple-500',
        text: 'text-purple-900 dark:text-purple-100',
        keySize: 'text-sm',
        padding: 'pl-9',
      },
      { // Level 3+ - Deep nested
        bg: 'bg-orange-50 dark:bg-orange-900/10',
        border: 'border-l-4 border-orange-500',
        text: 'text-orange-900 dark:text-orange-100',
        keySize: 'text-xs',
        padding: 'pl-12',
      }
    ];
    
    return styles[Math.min(depth, styles.length - 1)];
  };

  // Render nested object/array as editable fields with level-based styling
  const renderNestedData = (data: any, path: string[] = [], depth: number = 0) => {
    if (!data) return null;
    
    const levelStyle = getLevelStyling(depth);
    
    if (typeof data !== 'object' || data === null) {
      // Render primitive value
      if (editMode) {
        return (
          <input
            type="text"
            value={String(data)}
            onChange={(e) => updateNestedField(path, e.target.value)}
            className="ml-2 px-2 py-1 text-sm border rounded dark:bg-gray-700 dark:border-gray-600"
          />
        );
      }
      return <span className="ml-2 text-gray-700 dark:text-gray-300">{String(data)}</span>;
    }
    
    if (Array.isArray(data)) {
      // Render array
      return (
        <div className="space-y-1">
          {data.map((item, index) => (
            <div key={index} className={`${levelStyle.bg} ${levelStyle.border} ${levelStyle.padding} py-1 my-1 rounded-r`}>
              <div className="flex items-center gap-2">
                <span className={`${levelStyle.text} ${levelStyle.keySize}`}>[{index}]</span>
                {renderNestedData(item, [...path, String(index)], depth + 1)}
              </div>
            </div>
          ))}
          {editMode && (
            <button
              onClick={() => updateNestedField([...path, String(data.length)], '')}
              className="text-sm text-blue-600 dark:text-blue-400 hover:underline mt-1 ml-4"
            >
              + Add item
            </button>
          )}
        </div>
      );
    }
    
    // Render object
    return (
      <div className="space-y-2">
        {Object.entries(data).map(([key, value]) => {
          const isNested = typeof value === 'object' && value !== null;
          
          return (
            <div key={key} className={`${levelStyle.bg} ${levelStyle.border} ${levelStyle.padding} py-2 rounded-r`}>
              {isNested ? (
                <div>
                  <div className={`${levelStyle.text} ${levelStyle.keySize} mb-2`}>
                    {key}:
                  </div>
                  <div className="ml-4">
                    {renderNestedData(value, [...path, key], depth + 1)}
                  </div>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <span className={`${levelStyle.text} ${levelStyle.keySize} min-w-[150px]`}>
                    {key}:
                  </span>
                  {editMode ? (
                    <input
                      type="text"
                      value={String(value || '')}
                      onChange={(e) => updateNestedField([...path, key], e.target.value)}
                      className="flex-1 px-2 py-1 text-sm border rounded dark:bg-gray-700 dark:border-gray-600"
                    />
                  ) : (
                    <span className="text-gray-700 dark:text-gray-300">{String(value || '')}</span>
                  )}
                </div>
              )}
            </div>
          );
        })}
        {editMode && (
          <button
            onClick={() => {
              const newKey = prompt('Enter new field name:');
              if (newKey && !data[newKey]) {
                updateNestedField([...path, newKey], '');
              }
            }}
            className="text-sm text-blue-600 dark:text-blue-400 hover:underline mt-2 ml-4"
          >
            + Add field
          </button>
        )}
      </div>
    );
  };

  // Render data organized by context levels
  const renderDataByLevels = (data: any) => {
    const categorized = categorizeFieldsByLevel(data);
    
    const levelConfig = [
      { 
        key: 'global', 
        title: 'Global Context', 
        icon: Globe,
        bgColor: 'bg-blue-50 dark:bg-blue-900/20',
        borderColor: 'border-blue-200 dark:border-blue-800',
        iconColor: 'text-blue-600 dark:text-blue-400'
      },
      { 
        key: 'project', 
        title: 'Project Context', 
        icon: Folder,
        bgColor: 'bg-green-50 dark:bg-green-900/20',
        borderColor: 'border-green-200 dark:border-green-800',
        iconColor: 'text-green-600 dark:text-green-400'
      },
      { 
        key: 'branch', 
        title: 'Branch Context', 
        icon: GitBranch,
        bgColor: 'bg-purple-50 dark:bg-purple-900/20',
        borderColor: 'border-purple-200 dark:border-purple-800',
        iconColor: 'text-purple-600 dark:text-purple-400'
      },
      { 
        key: 'task', 
        title: 'Task Context', 
        icon: CheckIcon,
        bgColor: 'bg-orange-50 dark:bg-orange-900/20',
        borderColor: 'border-orange-200 dark:border-orange-800',
        iconColor: 'text-orange-600 dark:text-orange-400'
      }
    ];
    
    return (
      <div className="space-y-4">
        {levelConfig.map(({ key, title, icon: Icon, bgColor, borderColor, iconColor }) => {
          const levelData = categorized[key];
          const hasData = Object.keys(levelData).length > 0;
          
          if (!hasData && !editMode) return null;
          
          return (
            <div key={key} className={`${bgColor} ${borderColor} border rounded-lg p-4`}>
              <div 
                className="flex items-center gap-2 mb-3 cursor-pointer"
                onClick={() => toggleSection(key)}
              >
                {expandedSections[key] ? 
                  <ChevronDown className="w-4 h-4 text-gray-500" /> : 
                  <ChevronRight className="w-4 h-4 text-gray-500" />
                }
                <Icon className={`w-5 h-5 ${iconColor}`} />
                <h4 className="font-semibold text-gray-900 dark:text-gray-100">
                  {title}
                  {hasData && (
                    <span className="ml-2 text-sm text-gray-500 dark:text-gray-400">
                      ({Object.keys(levelData).length} fields)
                    </span>
                  )}
                </h4>
              </div>
              
              {expandedSections[key] && (
                <div className="ml-6">
                  {hasData ? (
                    renderNestedData(levelData, [key])
                  ) : (
                    <p className="text-sm text-gray-500 dark:text-gray-400 italic">
                      No {key} level data available
                    </p>
                  )}
                </div>
              )}
            </div>
          );
        })}
        
        {/* Other uncategorized fields */}
        {Object.keys(categorized.other || {}).length > 0 && (
          <div className="bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-2">
              <Info className="w-5 h-5 text-gray-500" />
              Other Fields
            </h4>
            <div className="ml-6">
              {renderNestedData(categorized.other, ['other'])}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-[90vw] h-[90vh] max-w-[90vw] max-h-[90vh] overflow-hidden flex flex-col bg-white dark:bg-gray-900 rounded-lg shadow-xl">
        <DialogHeader>
          <DialogTitle className="text-xl text-left flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Globe className="w-5 h-5" />
              Global Context Management
            </div>
            <div className="flex gap-2">
              {!editMode && globalContext && (
                <Button
                  variant="default"
                  size="sm"
                  onClick={() => setEditMode(true)}
                >
                  <Edit className="w-4 h-4 mr-2" />
                  Edit
                </Button>
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
        
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="text-center py-8">
              <div className="inline-block w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
              <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Loading global context...</p>
            </div>
          ) : globalContext ? (
            <div className="space-y-4">
              {/* Render all fields in a single nested hierarchical view */}
              {editMode ? (
                <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-3 mb-4">
                  <h3 className="font-semibold text-sm mb-2 dark:text-gray-200">Edit Mode</h3>
                  <div className="text-xs text-gray-600 dark:text-gray-400">
                    <p>Click on any value to edit it. Add new fields using the "+ Add field" buttons.</p>
                  </div>
                </div>
              ) : null}
              
              {/* Main nested data display with level-based visual distinction */}
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <Globe className="w-5 h-5" />
                  Global Context Data
                  <span className="text-xs text-gray-500 dark:text-gray-400 ml-2">
                    (Color-coded by nesting level)
                  </span>
                </h3>
                <div className="space-y-2">
                  {editMode ? renderNestedData(editingData) : renderNestedData(globalContext)}
                </div>
              </div>
              
              {/* Raw JSON Displays for different context levels */}
              <div className="space-y-6 mt-6">
                {(() => {
                  // Categorize data once to avoid multiple calls
                  const currentData = editMode ? editingData : globalContext;
                  const categorized = currentData ? categorizeFieldsByLevel(currentData) : null;
                  
                  return (
                    <>
                      {/* Global Context JSON */}
                      <div>
                        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                          <button
                            onClick={() => toggleSection('rawJson')}
                            className="flex items-center gap-2 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                          >
                            {expandedSections.rawJson ? 
                              <ChevronDown className="w-4 h-4" /> : 
                              <ChevronRight className="w-4 h-4" />
                            }
                            <Globe className="w-5 h-5" />
                            Global Context Raw Data
                          </button>
                        </h3>
                        {expandedSections.rawJson && currentData && (
                          <RawJSONDisplay 
                            jsonData={currentData}
                            title="Global Context Management"
                            fileName="global_context.json"                            
                          />
                        )}
                      </div>

                      {/* Project Context JSON */}
                      {categorized?.project && Object.keys(categorized.project).length > 0 && (
                        <div>
                          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                            <button
                              onClick={() => toggleSection('projectJson')}
                              className="flex items-center gap-2 hover:text-green-600 dark:hover:text-green-400 transition-colors"
                            >
                              {expandedSections.projectJson ? 
                                <ChevronDown className="w-4 h-4" /> : 
                                <ChevronRight className="w-4 h-4" />
                              }
                              <Folder className="w-5 h-5" />
                              Project Context Raw Data
                            </button>
                          </h3>
                          {expandedSections.projectJson && (
                            <RawJSONDisplay 
                              jsonData={categorized.project}
                              title="Project Context"
                              fileName="project_context.json"
                            />
                          )}
                        </div>
                      )}

                      {/* Branch Context JSON */}
                      {categorized?.branch && Object.keys(categorized.branch).length > 0 && (
                        <div>
                          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                            <button
                              onClick={() => toggleSection('branchJson')}
                              className="flex items-center gap-2 hover:text-purple-600 dark:hover:text-purple-400 transition-colors"
                            >
                              {expandedSections.branchJson ? 
                                <ChevronDown className="w-4 h-4" /> : 
                                <ChevronRight className="w-4 h-4" />
                              }
                              <GitBranch className="w-5 h-5" />
                              Branch Context Raw Data
                            </button>
                          </h3>
                          {expandedSections.branchJson && (
                            <RawJSONDisplay 
                              jsonData={categorized.branch}
                              title="Branch Context"
                              fileName="branch_context.json"
                            />
                          )}
                        </div>
                      )}

                      {/* Task Context JSON */}
                      {categorized?.task && Object.keys(categorized.task).length > 0 && (
                        <div>
                          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                            <button
                              onClick={() => toggleSection('taskJson')}
                              className="flex items-center gap-2 hover:text-orange-600 dark:hover:text-orange-400 transition-colors"
                            >
                              {expandedSections.taskJson ? 
                                <ChevronDown className="w-4 h-4" /> : 
                                <ChevronRight className="w-4 h-4" />
                              }
                              <CheckIcon className="w-5 h-5" />
                              Task Context Raw Data
                            </button>
                          </h3>
                          {expandedSections.taskJson && (
                            <RawJSONDisplay 
                              jsonData={categorized.task}
                              title="Task Context"
                              fileName="task_context.json"
                            />
                          )}
                        </div>
                      )}
                    </>
                  );
                })()}
              </div>
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
                  // Initialize with empty structure
                  const initialData = {
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
                  setGlobalContext(initialData);
                  setEditingData(initialData);
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