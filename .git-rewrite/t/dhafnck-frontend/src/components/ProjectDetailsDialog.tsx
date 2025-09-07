import React, { useEffect, useState } from "react";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import { Separator } from "./ui/separator";
import { getProjectContext, Project } from "../api";
import { FileText, Info, ChevronDown, ChevronRight, Hash, Calendar, Tag, Layers, Copy, Check as CheckIcon, Folder, Users } from "lucide-react";

interface ProjectDetailsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  project: Project | null;
  onClose: () => void;
}

export const ProjectDetailsDialog: React.FC<ProjectDetailsDialogProps> = ({
  open,
  onOpenChange,
  project,
  onClose
}) => {
  const [projectContext, setProjectContext] = useState<any>(null);
  const [contextLoading, setContextLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'details' | 'context'>('details');
  const [contextTab, setContextTab] = useState<'info' | 'technical' | 'patterns' | 'workflows'>('info');
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['data', 'resolved_context', 'project_data', 'metadata']));
  const [jsonCopied, setJsonCopied] = useState(false);

  // Fetch project context when dialog opens
  useEffect(() => {
    if (open && project?.id) {
      setContextLoading(true);
      
      // Fetch project context
      getProjectContext(project.id)
        .then(context => {
          console.log('Raw project context response:', context);
          
          // Extract the actual context data from the response
          if (context) {
            if (context.data && context.data.resolved_context) {
              // New format: data.resolved_context contains the actual context
              console.log('Using resolved_context from data:', context.data.resolved_context);
              setProjectContext(context.data.resolved_context);
            } else if (context.resolved_context) {
              // Alternative format: resolved_context at root level
              console.log('Using resolved_context from root:', context.resolved_context);
              setProjectContext(context.resolved_context);
            } else if (context.data) {
              // Fallback: use data object if it exists
              console.log('Using data object:', context.data);
              setProjectContext(context.data);
            } else {
              // Last resort: use the whole response
              console.log('Using full response:', context);
              setProjectContext(context);
            }
          } else {
            console.log('No context data received');
            setProjectContext(null);
          }
        })
        .catch(error => {
          console.error('Error fetching project context:', error);
          setProjectContext(null);
        })
        .finally(() => {
          setContextLoading(false);
        });
    } else if (!open) {
      // Clear data when dialog closes
      setProjectContext(null);
      setActiveTab('details');
    }
  }, [open, project?.id]);

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

  // Format nested objects to readable markdown-like text
  const formatNestedObject = (data: any, indent: number = 0): string => {
    if (!data || typeof data !== 'object') {
      return String(data);
    }
    
    const spaces = '  '.repeat(indent);
    let result: string[] = [];
    
    Object.entries(data).forEach(([key, value]) => {
      if (typeof value === 'object' && value !== null) {
        if (Array.isArray(value)) {
          result.push(`${spaces}${key}: ${value.join(', ')}`);
        } else {
          result.push(`${spaces}${key}:`);
          result.push(formatNestedObject(value, indent + 1));
        }
      } else {
        result.push(`${spaces}${key}: ${value}`);
      }
    });
    
    return result.join('\n');
  };

  // Render nested JSON beautifully (same as TaskDetailsDialog)
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
                } else if (key.includes('agent')) {
                  keyIcon = <Users className="inline w-3 h-3 mr-1" />;
                  keyColor = 'text-orange-600';
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

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-xl text-left flex items-center gap-2">
            <Folder className="w-5 h-5" />
            {project?.name || 'Project Details'}
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
              {!contextLoading && projectContext && Object.keys(projectContext).length > 0 && (
                <Badge variant="secondary" className="text-xs">Available</Badge>
              )}
            </button>
          </div>
        </DialogHeader>
        
        <div className="mt-4">
          {/* Details Tab Content */}
          {activeTab === 'details' && (
            <div className="space-y-4">
              {/* Basic Information */}
              <div className="bg-gray-50 p-4 rounded-lg">
                <h3 className="text-lg font-semibold mb-3">Basic Information</h3>
                <div className="space-y-2 text-sm">
                  <div>
                    <span className="text-muted-foreground">Name:</span>
                    <span className="ml-2 font-medium">{project?.name}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">ID:</span>
                    <span className="ml-2 font-mono text-xs">{project?.id}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Description:</span>
                    <span className="ml-2">{project?.description || "No description"}</span>
                  </div>
                  {(project as any)?.created_at && (
                    <div>
                      <span className="text-muted-foreground">Created:</span>
                      <span className="ml-2">
                        {new Date((project as any).created_at).toLocaleString()}
                      </span>
                    </div>
                  )}
                  {(project as any)?.updated_at && (
                    <div>
                      <span className="text-muted-foreground">Updated:</span>
                      <span className="ml-2">
                        {new Date((project as any).updated_at).toLocaleString()}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              <Separator />

              {/* Git Branches */}
              {project?.git_branchs && Object.keys(project.git_branchs).length > 0 && (
                <>
                  <div className="bg-blue-50 p-4 rounded-lg">
                    <h3 className="text-lg font-semibold mb-3 text-blue-700">
                      Git Branches ({Object.keys(project.git_branchs).length})
                    </h3>
                    <div className="bg-white p-3 rounded border border-blue-200">
                      <div className="space-y-2">
                        {Object.entries(project.git_branchs).map(([key, branch]: [string, any]) => (
                          <div key={key} className="flex items-center justify-between p-2 hover:bg-gray-50 rounded">
                            <div className="flex items-center gap-2">
                              <div className="w-2 h-2 rounded-full bg-blue-400"></div>
                              <span className="font-medium">{branch.name}</span>
                              {branch.task_count !== undefined && (
                                <Badge variant="secondary" className="text-xs">
                                  {branch.task_count} tasks
                                </Badge>
                              )}
                            </div>
                            <span className="text-xs text-gray-500 font-mono">{branch.id}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                  <Separator />
                </>
              )}

              {/* Project Status */}
              {project && (project as any)['status'] && (
                <>
                  <div className="bg-green-50 p-4 rounded-lg">
                    <h3 className="text-lg font-semibold mb-3 text-green-700">Project Status</h3>
                    <div className="bg-white p-3 rounded border border-green-200">
                      <pre className="text-xs overflow-x-auto whitespace-pre-wrap">
                        {typeof (project as any)['status'] === 'object' 
                          ? JSON.stringify((project as any)['status'], null, 2)
                          : (project as any)['status']}
                      </pre>
                    </div>
                  </div>
                  <Separator />
                </>
              )}

              {/* Project Metadata */}
              {project && (project as any)['metadata'] && (
                <>
                  <div className="bg-orange-50 p-4 rounded-lg">
                    <h3 className="text-lg font-semibold mb-3 text-orange-700">Project Metadata</h3>
                    <div className="bg-white p-3 rounded border border-orange-200">
                      <pre className="text-xs overflow-x-auto whitespace-pre-wrap">
                        {typeof (project as any)['metadata'] === 'object' 
                          ? JSON.stringify((project as any)['metadata'], null, 2)
                          : (project as any)['metadata']}
                      </pre>
                    </div>
                  </div>
                  <Separator />
                </>
              )}

              {/* Additional Fields - Display any other fields */}
              {project && (
                <>
                  {Object.entries(project).filter(([key]) => 
                    !['id', 'name', 'description', 'git_branchs', 'status', 'metadata'].includes(key)
                  ).map(([key, value]) => {
                    if (value === null || value === undefined) return null;
                    
                    return (
                      <React.Fragment key={key}>
                        <div className="bg-gray-50 p-4 rounded-lg">
                          <h3 className="text-lg font-semibold mb-3 capitalize">{key.replace(/_/g, ' ')}</h3>
                          <div className="bg-white p-3 rounded border border-gray-200">
                            {typeof value === 'object' ? (
                              <pre className="text-xs overflow-x-auto whitespace-pre-wrap">
                                {JSON.stringify(value, null, 2)}
                              </pre>
                            ) : (
                              <span className="text-sm">{String(value)}</span>
                            )}
                          </div>
                        </div>
                        <Separator />
                      </React.Fragment>
                    );
                  })}
                </>
              )}

              {/* Raw Data */}
              <details className="cursor-pointer">
                <summary className="font-semibold text-sm text-gray-700 hover:text-gray-900">
                  View Complete Raw Project Data (JSON)
                </summary>
                <div className="mt-3 bg-gray-100 p-3 rounded">
                  <pre className="text-xs overflow-x-auto whitespace-pre-wrap">
                    {JSON.stringify(project, null, 2)}
                  </pre>
                </div>
              </details>
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
              ) : projectContext ? (
                <>
                  {/* Context Actions */}
                  <div className="flex justify-end gap-2">
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

                  {/* Context Sub-tabs */}
                  <div className="flex gap-2 border-b pb-2">
                    <Button
                      variant={contextTab === 'info' ? 'default' : 'ghost'}
                      size="sm"
                      onClick={() => setContextTab('info')}
                      className="flex items-center gap-2"
                    >
                      <Info className="w-4 h-4" />
                      Project Info
                    </Button>
                    <Button
                      variant={contextTab === 'technical' ? 'default' : 'ghost'}
                      size="sm"
                      onClick={() => setContextTab('technical')}
                      className="flex items-center gap-2"
                    >
                      <Layers className="w-4 h-4" />
                      Technical Specs
                    </Button>
                    <Button
                      variant={contextTab === 'patterns' ? 'default' : 'ghost'}
                      size="sm"
                      onClick={() => setContextTab('patterns')}
                      className="flex items-center gap-2"
                    >
                      <FileText className="w-4 h-4" />
                      Patterns
                    </Button>
                    <Button
                      variant={contextTab === 'workflows' ? 'default' : 'ghost'}
                      size="sm"
                      onClick={() => setContextTab('workflows')}
                      className="flex items-center gap-2"
                    >
                      <Users className="w-4 h-4" />
                      Workflows
                    </Button>
                  </div>
                  
                  {/* Context Content based on sub-tab */}
                  <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-6">
                    {contextTab === 'info' && (
                      <div>
                        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                          <Info className="w-5 h-5" /> Project Information
                        </h3>
                        {projectContext.project_info || projectContext.project_settings ? (
                          <pre className="whitespace-pre-wrap font-mono text-sm text-gray-800 dark:text-gray-200">
                            {formatNestedObject(projectContext.project_info || projectContext.project_settings || {})}
                          </pre>
                        ) : (
                          <p className="text-sm text-gray-500 dark:text-gray-400 italic">
                            No project information defined yet.
                          </p>
                        )}
                      </div>
                    )}

                    {contextTab === 'technical' && (
                      <div>
                        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                          <Layers className="w-5 h-5" /> Technical Specifications
                        </h3>
                        {projectContext.technical_specifications || projectContext.technology_stack ? (
                          <pre className="whitespace-pre-wrap font-mono text-sm text-gray-800 dark:text-gray-200">
                            {formatNestedObject(projectContext.technical_specifications || projectContext.technology_stack || {})}
                          </pre>
                        ) : (
                          <p className="text-sm text-gray-500 dark:text-gray-400 italic">
                            No technical specifications defined yet.
                          </p>
                        )}
                      </div>
                    )}

                    {contextTab === 'patterns' && (
                      <div>
                        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                          <FileText className="w-5 h-5" /> Project Patterns
                        </h3>
                        {projectContext.project_patterns ? (
                          <pre className="whitespace-pre-wrap font-mono text-sm text-gray-800 dark:text-gray-200">
                            {formatNestedObject(projectContext.project_patterns || {})}
                          </pre>
                        ) : (
                          <p className="text-sm text-gray-500 dark:text-gray-400 italic">
                            No project patterns defined yet.
                          </p>
                        )}
                      </div>
                    )}

                    {contextTab === 'workflows' && (
                      <div>
                        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                          <Users className="w-5 h-5" /> Development Workflows
                        </h3>
                        {projectContext.development_workflows || projectContext.project_workflow ? (
                          <pre className="whitespace-pre-wrap font-mono text-sm text-gray-800 dark:text-gray-200">
                            {formatNestedObject(projectContext.development_workflows || projectContext.project_workflow || {})}
                          </pre>
                        ) : (
                          <p className="text-sm text-gray-500 dark:text-gray-400 italic">
                            No development workflows defined yet.
                          </p>
                        )}
                      </div>
                    )}
                    
                    {/* Show raw JSON at the bottom */}
                    <details className="cursor-pointer mt-6">
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
                </>
              ) : (
                <div className="text-center py-8 bg-gray-50 dark:bg-gray-800 rounded-lg">
                  <Folder className="w-12 h-12 text-gray-400 dark:text-gray-500 mx-auto mb-3" />
                  <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">No Project Context Available</h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                    Project context has not been initialized yet.
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

export default ProjectDetailsDialog;