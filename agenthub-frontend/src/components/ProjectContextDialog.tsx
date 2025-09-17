import React, { useEffect, useState } from "react";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import { Textarea } from "./ui/textarea";
import { FolderOpen, Save, Edit, X, Copy, Check as CheckIcon, Settings, Code, Users, Workflow, FileText, Cog, Wrench, Globe, Layers } from "lucide-react";
import { getProjectContext, updateProjectContext, getGlobalContext } from "../api";

interface ProjectContextDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onClose: () => void;
  projectId: string;
}

// Parse markdown for Project Settings (key: value format)
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

// Parse markdown for Technology Stack (structured format)
const parseTechStackMarkdown = (content: string): Record<string, any> => {
  const result: Record<string, any> = {};
  const lines = content.split('\n');
  let currentSection = '';
  let currentItems: string[] = [];

  lines.forEach((line) => {
    if (line.trim().endsWith(':') && !line.includes(' - ')) {
      if (currentSection && currentItems.length > 0) {
        result[currentSection] = currentItems;
      }
      
      currentSection = line.trim().slice(0, -1);
      currentItems = [];
    } else if (currentSection && line.trim().startsWith('- ')) {
      currentItems.push(line.trim().substring(2));
    }
  });

  if (currentSection && currentItems.length > 0) {
    result[currentSection] = currentItems;
  }

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

const techStackToMarkdown = (data: Record<string, any>): string => {
  if (!data || Object.keys(data).length === 0) {
    return '';
  }
  
  return Object.entries(data).map(([category, items]) => {
    if (Array.isArray(items)) {
      const itemList = items.map(item => `- ${item}`).join('\n');
      return `${category}:\n${itemList}`;
    }
    return `${category}: ${items}`;
  }).join('\n\n');
};

export const ProjectContextDialog: React.FC<ProjectContextDialogProps> = ({
  open,
  onOpenChange,
  onClose,
  projectId
}) => {
  const [projectContext, setProjectContext] = useState<any>(null);
  const [globalContext, setGlobalContext] = useState<any>(null);
  const [showInheritance, setShowInheritance] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [jsonCopied, setJsonCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<'project_info' | 'team_preferences' | 'technology_stack' | 'project_workflow' | 'local_standards' | 'project_settings' | 'technical_specifications' | 'inheritance'>('project_info');
  
  // Separate markdown content for each section
  const [projectInfoMarkdown, setProjectInfoMarkdown] = useState('');
  const [teamPreferencesMarkdown, setTeamPreferencesMarkdown] = useState('');
  const [technologyStackMarkdown, setTechnologyStackMarkdown] = useState('');
  const [projectWorkflowMarkdown, setProjectWorkflowMarkdown] = useState('');
  const [localStandardsMarkdown, setLocalStandardsMarkdown] = useState('');
  const [projectSettingsMarkdown, setProjectSettingsMarkdown] = useState('');
  const [technicalSpecificationsMarkdown, setTechnicalSpecificationsMarkdown] = useState('');

  // Fetch project context when dialog opens
  useEffect(() => {
    if (open && projectId) {
      fetchProjectContext();
      fetchGlobalContext();
    } else {
      setEditMode(false);
      setProjectContext(null);
      setGlobalContext(null);
      setActiveTab('project_info');
    }
  }, [open, projectId]);

  const fetchGlobalContext = async () => {
    try {
      const context = await getGlobalContext();
      if (context) {
        setGlobalContext(context.data || context);
      }
    } catch (error) {
      console.error('Error fetching global context:', error);
    }
  };

  const fetchProjectContext = async () => {
    setLoading(true);
    try {
      const context = await getProjectContext(projectId);
      console.log('Fetched project context:', context);
      
      if (context) {
        setProjectContext(context);
        
        // Handle the actual API response structure
        const contextData = context.data || context;
        
        // Extract project-specific fields
        const projectInfo = contextData.project_info || {};
        const teamPreferences = contextData.team_preferences || {};
        const technologyStack = contextData.technology_stack || {};
        const projectWorkflow = contextData.project_workflow || {};
        const localStandards = contextData.local_standards || {};
        const projectSettings = contextData.project_settings || {};
        const technicalSpecifications = contextData.technical_specifications || {};
        
        // Convert each section to markdown format
        setProjectInfoMarkdown(keyValueToMarkdown(projectInfo));
        setTeamPreferencesMarkdown(keyValueToMarkdown(teamPreferences));
        setTechnologyStackMarkdown(techStackToMarkdown(technologyStack));
        setProjectWorkflowMarkdown(keyValueToMarkdown(projectWorkflow));
        setLocalStandardsMarkdown(keyValueToMarkdown(localStandards));
        setProjectSettingsMarkdown(keyValueToMarkdown(projectSettings));
        setTechnicalSpecificationsMarkdown(keyValueToMarkdown(technicalSpecifications));
      }
    } catch (error) {
      console.error('Error fetching project context:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      // Parse markdown content from each section
      const projectInfo = parseKeyValueMarkdown(projectInfoMarkdown);
      const teamPreferences = parseKeyValueMarkdown(teamPreferencesMarkdown);
      const technologyStack = parseTechStackMarkdown(technologyStackMarkdown);
      const projectWorkflow = parseKeyValueMarkdown(projectWorkflowMarkdown);
      const localStandards = parseKeyValueMarkdown(localStandardsMarkdown);
      const projectSettings = parseKeyValueMarkdown(projectSettingsMarkdown);
      const technicalSpecifications = parseKeyValueMarkdown(technicalSpecificationsMarkdown);
      
      // Prepare the data to save
      const dataToSave = {
        project_info: projectInfo,
        team_preferences: teamPreferences,
        technology_stack: technologyStack,
        project_workflow: projectWorkflow,
        local_standards: localStandards,
        project_settings: projectSettings,
        technical_specifications: technicalSpecifications
      };

      // Call the update API
      await updateProjectContext(projectId, dataToSave);
      
      // Refresh the context
      await fetchProjectContext();
      
      // Exit edit mode
      setEditMode(false);
    } catch (error) {
      console.error('Error saving project context:', error);
      alert('Failed to save project context. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    if (projectContext) {
      const contextData = projectContext.data || projectContext;
      
      setProjectInfoMarkdown(keyValueToMarkdown(contextData.project_info || {}));
      setTeamPreferencesMarkdown(keyValueToMarkdown(contextData.team_preferences || {}));
      setTechnologyStackMarkdown(techStackToMarkdown(contextData.technology_stack || {}));
      setProjectWorkflowMarkdown(keyValueToMarkdown(contextData.project_workflow || {}));
      setLocalStandardsMarkdown(keyValueToMarkdown(contextData.local_standards || {}));
      setProjectSettingsMarkdown(keyValueToMarkdown(contextData.project_settings || {}));
      setTechnicalSpecificationsMarkdown(keyValueToMarkdown(contextData.technical_specifications || {}));
    }
    setEditMode(false);
  };

  const copyJsonToClipboard = () => {
    if (projectContext) {
      const jsonString = JSON.stringify(projectContext, null, 2);
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
      case 'project_info': return projectInfoMarkdown;
      case 'team_preferences': return teamPreferencesMarkdown;
      case 'technology_stack': return technologyStackMarkdown;
      case 'project_workflow': return projectWorkflowMarkdown;
      case 'local_standards': return localStandardsMarkdown;
      case 'project_settings': return projectSettingsMarkdown;
      case 'technical_specifications': return technicalSpecificationsMarkdown;
      case 'inheritance': return ''; // Inheritance tab doesn't have markdown
      default: return '';
    }
  };

  // Set the appropriate markdown content based on active tab
  const setCurrentMarkdown = (value: string) => {
    switch (activeTab) {
      case 'project_info': setProjectInfoMarkdown(value); break;
      case 'team_preferences': setTeamPreferencesMarkdown(value); break;
      case 'technology_stack': setTechnologyStackMarkdown(value); break;
      case 'project_workflow': setProjectWorkflowMarkdown(value); break;
      case 'local_standards': setLocalStandardsMarkdown(value); break;
      case 'project_settings': setProjectSettingsMarkdown(value); break;
      case 'technical_specifications': setTechnicalSpecificationsMarkdown(value); break;
      case 'inheritance': break; // Inheritance tab is read-only
    }
  };

  // Get placeholder text based on active tab
  const getPlaceholder = () => {
    switch (activeTab) {
      case 'project_info':
        return 'Add project information:\nname: My Project\ndescription: Project description\nversion: 1.0.0';
      case 'team_preferences':
        return 'Add team preferences:\ncode_review_required: true\npreferred_branch_naming: feature/ticket-description\nmeeting_schedule: Daily at 9 AM';
      case 'technology_stack':
        return 'Add technology stack:\nFrontend:\n- React\n- TypeScript\n- Tailwind CSS\n\nBackend:\n- Node.js\n- Express\n- PostgreSQL';
      case 'project_workflow':
        return 'Add project workflow:\nphases: Planning, Development, Testing, Deployment\ntesting_strategy: Unit tests, Integration tests, E2E tests\ndeployment_process: CI/CD pipeline';
      case 'local_standards':
        return 'Add local standards:\nnaming_convention: camelCase\nfile_structure: Domain-driven design\ncode_style: Prettier + ESLint';
      case 'project_settings':
        return 'Add project settings:\nenvironment: development\ndebug_mode: true\napi_base_url: http://localhost:3000';
      case 'technical_specifications':
        return 'Add technical specifications:\narchitecture: Microservices\napi_version: v2\nsecurity: JWT authentication\nperformance_targets: 99.9% uptime';
      default:
        return '';
    }
  };

  const getTabIcon = (tab: string) => {
    switch (tab) {
      case 'project_info': return <FileText className="w-4 h-4" />;
      case 'team_preferences': return <Users className="w-4 h-4" />;
      case 'technology_stack': return <Code className="w-4 h-4" />;
      case 'project_workflow': return <Workflow className="w-4 h-4" />;
      case 'local_standards': return <Settings className="w-4 h-4" />;
      case 'project_settings': return <Cog className="w-4 h-4" />;
      case 'technical_specifications': return <Wrench className="w-4 h-4" />;
      case 'inheritance': return <Layers className="w-4 h-4" />;
      default: return <Settings className="w-4 h-4" />;
    }
  };

  const getTabLabel = (tab: string) => {
    switch (tab) {
      case 'project_info': return 'Project Info';
      case 'team_preferences': return 'Team Preferences';
      case 'technology_stack': return 'Technology Stack';
      case 'project_workflow': return 'Project Workflow';
      case 'local_standards': return 'Local Standards';
      case 'project_settings': return 'Project Settings';
      case 'technical_specifications': return 'Technical Specs';
      case 'inheritance': return 'Inheritance';
      default: return 'Settings';
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="text-xl text-left flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FolderOpen className="w-5 h-5" />
              Project Context Management
            </div>
            <div className="flex gap-2">
              {!editMode && projectContext && (
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
          {(['project_info', 'team_preferences', 'technology_stack', 'project_workflow', 'local_standards', 'project_settings', 'technical_specifications', 'inheritance'] as const).map((tab) => (
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
              <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Loading project context...</p>
            </div>
          ) : projectContext ? (
            <div className="h-full flex flex-col p-4">
              {editMode ? (
                // Edit Mode - Markdown Editor for active tab
                <>
                  <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3 mb-4">
                    <h3 className="font-semibold text-sm mb-2 dark:text-gray-200">
                      {getTabLabel(activeTab)} Format
                    </h3>
                    <div className="text-xs text-gray-600 dark:text-gray-400">
                      {activeTab === 'technology_stack' ? (
                        <p>Use <code className="bg-white dark:bg-gray-700 px-1 rounded">Category:</code> followed by <code className="bg-white dark:bg-gray-700 px-1 rounded">- item</code> format.</p>
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
                      {/* Global Context Section */}
                      <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 border border-blue-200 dark:border-blue-800">
                        <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                          <Globe className="w-5 h-5" />
                          Global Context (Inherited)
                        </h3>
                        {globalContext ? (
                          <div className="space-y-2">
                            {globalContext.organization_standards && (
                              <div className="text-sm">
                                <span className="font-medium">Organization Standards:</span>
                                <pre className="mt-1 text-xs bg-white dark:bg-gray-800 p-2 rounded overflow-x-auto">
                                  {JSON.stringify(globalContext.organization_standards, null, 2)}
                                </pre>
                              </div>
                            )}
                            {globalContext.compliance_requirements && (
                              <div className="text-sm">
                                <span className="font-medium">Compliance Requirements:</span>
                                <pre className="mt-1 text-xs bg-white dark:bg-gray-800 p-2 rounded overflow-x-auto">
                                  {JSON.stringify(globalContext.compliance_requirements, null, 2)}
                                </pre>
                              </div>
                            )}
                            {globalContext.shared_resources && (
                              <div className="text-sm">
                                <span className="font-medium">Shared Resources:</span>
                                <pre className="mt-1 text-xs bg-white dark:bg-gray-800 p-2 rounded overflow-x-auto">
                                  {JSON.stringify(globalContext.shared_resources, null, 2)}
                                </pre>
                              </div>
                            )}
                            {globalContext.reusable_patterns && (
                              <div className="text-sm">
                                <span className="font-medium">Reusable Patterns:</span>
                                <pre className="mt-1 text-xs bg-white dark:bg-gray-800 p-2 rounded overflow-x-auto">
                                  {JSON.stringify(globalContext.reusable_patterns, null, 2)}
                                </pre>
                              </div>
                            )}
                            {globalContext.global_preferences && (
                              <div className="text-sm">
                                <span className="font-medium">Global Preferences:</span>
                                <pre className="mt-1 text-xs bg-white dark:bg-gray-800 p-2 rounded overflow-x-auto">
                                  {JSON.stringify(globalContext.global_preferences, null, 2)}
                                </pre>
                              </div>
                            )}
                            {!globalContext.organization_standards && 
                             !globalContext.compliance_requirements && 
                             !globalContext.shared_resources && 
                             !globalContext.reusable_patterns && 
                             !globalContext.global_preferences && (
                              <p className="text-sm text-gray-500 dark:text-gray-400 italic">
                                No global context fields defined.
                              </p>
                            )}
                          </div>
                        ) : (
                          <p className="text-sm text-gray-500 dark:text-gray-400 italic">
                            No global context available.
                          </p>
                        )}
                      </div>

                      {/* Arrow indicator */}
                      <div className="flex justify-center">
                        <div className="text-gray-400 dark:text-gray-600">
                          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                          </svg>
                        </div>
                      </div>

                      {/* Project Context Section */}
                      <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4 border border-green-200 dark:border-green-800">
                        <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                          <FolderOpen className="w-5 h-5" />
                          Project Context (Current Level)
                        </h3>
                        {projectContext ? (
                          <div className="space-y-2">
                            <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                              This is the current context level. Fields defined here override inherited values from global context.
                            </p>
                            <div className="grid grid-cols-2 gap-3">
                              <div className="text-sm">
                                <span className="font-medium">Has Project Info:</span>
                                <span className="ml-2">{projectContext.data?.project_info ? '✓' : '✗'}</span>
                              </div>
                              <div className="text-sm">
                                <span className="font-medium">Has Team Preferences:</span>
                                <span className="ml-2">{projectContext.data?.team_preferences ? '✓' : '✗'}</span>
                              </div>
                              <div className="text-sm">
                                <span className="font-medium">Has Technology Stack:</span>
                                <span className="ml-2">{projectContext.data?.technology_stack ? '✓' : '✗'}</span>
                              </div>
                              <div className="text-sm">
                                <span className="font-medium">Has Project Workflow:</span>
                                <span className="ml-2">{projectContext.data?.project_workflow ? '✓' : '✗'}</span>
                              </div>
                              <div className="text-sm">
                                <span className="font-medium">Has Local Standards:</span>
                                <span className="ml-2">{projectContext.data?.local_standards ? '✓' : '✗'}</span>
                              </div>
                              <div className="text-sm">
                                <span className="font-medium">Has Project Settings:</span>
                                <span className="ml-2">{projectContext.data?.project_settings ? '✓' : '✗'}</span>
                              </div>
                            </div>
                          </div>
                        ) : (
                          <p className="text-sm text-gray-500 dark:text-gray-400 italic">
                            No project context available.
                          </p>
                        )}
                      </div>

                      {/* Information about inheritance */}
                      <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                        <h4 className="font-medium text-sm mb-2 flex items-center gap-2">
                          <Layers className="w-4 h-4" />
                          How Inheritance Works
                        </h4>
                        <ul className="text-xs text-gray-600 dark:text-gray-400 space-y-1">
                          <li>• Project context inherits from Global context</li>
                          <li>• Branch contexts will inherit from this Project context</li>
                          <li>• Task contexts will inherit from their Branch context</li>
                          <li>• Lower levels can override inherited values</li>
                          <li>• Use the delegation system to push values up the hierarchy</li>
                        </ul>
                      </div>
                    </div>
                  ) : (
                    // Regular tab content
                    <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-6">
                      <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                        {getTabIcon(activeTab)}
                        {getTabLabel(activeTab)}
                      </h3>
                      {getCurrentMarkdown() ? (
                        <pre className="whitespace-pre-wrap font-mono text-sm text-gray-800 dark:text-gray-200">
                          {getCurrentMarkdown()}
                        </pre>
                      ) : (
                        <p className="text-sm text-gray-500 dark:text-gray-400 italic">
                          No {getTabLabel(activeTab).toLowerCase()} defined yet.
                        </p>
                      )}
                    </div>
                  )}
                  
                  {/* Show raw JSON at the bottom in view mode */}
                  <details className="cursor-pointer">
                    <summary className="font-semibold text-sm text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100">
                      View Complete JSON Context
                    </summary>
                    <div className="mt-3 bg-gray-100 dark:bg-gray-800 p-3 rounded">
                      <pre className="text-xs overflow-x-auto whitespace-pre-wrap text-gray-800 dark:text-gray-200">
                        {JSON.stringify(projectContext, null, 2)}
                      </pre>
                    </div>
                  </details>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-8 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <FolderOpen className="w-12 h-12 text-gray-400 dark:text-gray-500 mx-auto mb-3" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">No Project Context Available</h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                Project context has not been initialized yet.
              </p>
              <Button 
                variant="default" 
                className="mt-4"
                onClick={() => {
                  // Initialize with empty values
                  setProjectInfoMarkdown('');
                  setTeamPreferencesMarkdown('');
                  setTechnologyStackMarkdown('');
                  setProjectWorkflowMarkdown('');
                  setLocalStandardsMarkdown('');
                  setProjectSettingsMarkdown('');
                  setTechnicalSpecificationsMarkdown('');
                  setProjectContext({ 
                    data: {
                      project_info: {},
                      team_preferences: {},
                      technology_stack: {},
                      project_workflow: {},
                      local_standards: {},
                      project_settings: {},
                      technical_specifications: {}
                    }
                  });
                  setEditMode(true);
                }}
              >
                <Edit className="w-4 h-4 mr-2" />
                Initialize Project Context
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

export default ProjectContextDialog;