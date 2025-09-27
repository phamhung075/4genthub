import React, { useEffect, useState } from "react";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import { Separator } from "./ui/separator";
import { getProjectContext, Project } from "../api";
import logger from "../utils/logger";
import { FileText, Info, ChevronDown, ChevronRight, Copy, Check as CheckIcon, Folder, Code, Settings, Shield, Database, GitBranch } from "lucide-react";
import { EnhancedJSONViewer } from "./ui/EnhancedJSONViewer";
import RawJSONDisplay from "./ui/RawJSONDisplay";

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
  const [jsonCopied, setJsonCopied] = useState(false);

  // Fetch project context when dialog opens
  useEffect(() => {
    if (open && project?.id) {
      setContextLoading(true);
      
      // Fetch project context
      getProjectContext(project.id)
        .then(context => {
          logger.debug('Raw project context response received', { context, component: 'ProjectDetailsDialog' });
          
          // Extract the actual context data from the response
          if (context) {
            if (context.data && context.data.resolved_context) {
              // New format: data.resolved_context contains the actual context
              logger.debug('Using resolved_context from data', { resolvedContext: context.data.resolved_context, component: 'ProjectDetailsDialog' });
              setProjectContext(context.data.resolved_context);
            } else if (context.resolved_context) {
              // Alternative format: resolved_context at root level
              logger.debug('Using resolved_context from root', { resolvedContext: context.resolved_context, component: 'ProjectDetailsDialog' });
              setProjectContext(context.resolved_context);
            } else if (context.data) {
              // Fallback: use data object if it exists
              logger.debug('Using data object as fallback', { data: context.data, component: 'ProjectDetailsDialog' });
              setProjectContext(context.data);
            } else {
              // Last resort: use the whole response
              logger.debug('Using full response as fallback', { context, component: 'ProjectDetailsDialog' });
              setProjectContext(context);
            }
          } else {
            logger.warn('No context data received from API', { projectId: project.id, component: 'ProjectDetailsDialog' });
            setProjectContext(null);
          }
        })
        .catch(error => {
          logger.error('Failed to fetch project context', { error, projectId: project?.id, component: 'ProjectDetailsDialog' });
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


  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-[90vw] max-w-6xl h-[85vh] mx-auto overflow-hidden bg-white dark:bg-gray-900 rounded-lg shadow-xl flex flex-col">
        <DialogHeader className="pb-0">
          <div className="flex items-center justify-between">
            <DialogTitle className="text-xl text-left flex items-center gap-2">
              <Folder className="w-5 h-5" />
              {project?.name || 'Project Details'}
            </DialogTitle>
          </div>
        </DialogHeader>
        
        {/* Tab Navigation */}
        <div className="flex gap-1 border-b px-6 -mt-2">
          <button
            onClick={() => setActiveTab('details')}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-[1px] ${
              activeTab === 'details' 
                ? 'text-blue-700 dark:text-blue-300 border-blue-400 dark:border-blue-500 bg-blue-50 dark:bg-blue-900/20' 
                : 'text-gray-500 border-transparent hover:text-gray-700'
            }`}
          >
            <Info className="w-4 h-4" />
            Details
          </button>
          
          <button
            onClick={() => setActiveTab('context')}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-[1px] ${
              activeTab === 'context' 
                ? 'text-blue-700 dark:text-blue-300 border-blue-400 dark:border-blue-500 bg-blue-50 dark:bg-blue-900/20' 
                : 'text-gray-500 border-transparent hover:text-gray-700'
            }`}
          >
            <FileText className="w-4 h-4" />
            Context
            {contextLoading && <span className="text-xs">(Loading...)</span>}
            {!contextLoading && projectContext && Object.keys(projectContext).length > 0 && (
              <Badge variant="secondary" className="text-xs ml-1">Available</Badge>
            )}
          </button>
        </div>
        
        <div className="flex-1 overflow-hidden flex flex-col">
          {/* Details Tab Content */}
          {activeTab === 'details' && (
            <div className="space-y-4 overflow-y-auto flex-1 p-4">
              {/* Basic Information */}
              <div className="bg-surface-hover p-4 rounded-lg">
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
                  <div className="bg-surface-hover p-4 rounded-lg">
                    <h3 className="text-lg font-semibold mb-3 text-blue-700">
                      Git Branches ({Object.keys(project.git_branchs).length})
                    </h3>
                    <div className="bg-surface p-3 rounded border border-surface-border">
                      <div className="space-y-2">
                        {Object.entries(project.git_branchs).map(([key, branch]: [string, any]) => (
                          <div key={key} className="flex items-center justify-between p-2 hover:bg-surface-hover rounded">
                            <div className="flex items-center gap-2">
                              <div className="w-2 h-2 rounded-full bg-primary"></div>
                              <span className="font-medium">{branch.name}</span>
                              {branch.total_tasks !== undefined && (
                                <Badge variant="secondary" className="text-xs">
                                  {branch.total_tasks} tasks
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
                  <div className="bg-surface-hover p-4 rounded-lg">
                    <h3 className="text-lg font-semibold mb-3 text-green-700">Project Status</h3>
                    <div className="bg-surface p-3 rounded border border-surface-border">
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
                  <div className="bg-surface-hover p-4 rounded-lg">
                    <h3 className="text-lg font-semibold mb-3 text-orange-700">Project Metadata</h3>
                    <div className="bg-surface p-3 rounded border border-surface-border">
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
                        <div className="bg-surface-hover p-4 rounded-lg">
                          <h3 className="text-lg font-semibold mb-3 capitalize">{key.replace(/_/g, ' ')}</h3>
                          <div className="bg-surface p-3 rounded border border-surface-border">
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
                <div className="mt-3">
                  <RawJSONDisplay 
                    jsonData={project}
                    title="Project Data"
                    fileName="project.json"
                  />
                </div>
              </details>
            </div>
          )}
          
          {/* Context Tab Content */}
          {activeTab === 'context' && (
            <div className="space-y-4 overflow-y-auto flex-1 p-4">
              {contextLoading ? (
                <div className="text-center py-8">
                  <div className="inline-block w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                  <p className="mt-2 text-sm text-gray-500">Loading context...</p>
                </div>
              ) : projectContext ? (
                <>
                  {/* Context Header */}
                  <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950/20 dark:to-indigo-950/20 p-4 rounded-lg border border-blue-200 dark:border-blue-800">
                    <h3 className="text-lg font-semibold text-blue-700 dark:text-blue-300 flex items-center gap-2">
                      <Database className="w-5 h-5" />
                      Project Context Data
                    </h3>
                    <p className="text-sm text-blue-600 dark:text-blue-400 mt-1">
                      Complete project context with configuration and settings
                    </p>
                  </div>
                  
                  {/* Organized Context Sections */}
                  <div className="space-y-4">
                    {/* Team Preferences */}
                    {projectContext.team_preferences && (
                      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                        <div className="bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-950/30 dark:to-emerald-950/30 p-3 border-l-4 border-green-400 dark:border-green-600">
                          <h3 className="text-gray-700 dark:text-gray-300 font-semibold flex items-center gap-2">
                            <Settings className="w-4 h-4" />
                            Team Preferences
                          </h3>
                        </div>
                        <div className="p-4">
                          <EnhancedJSONViewer data={projectContext.team_preferences} defaultExpanded={false} maxHeight="max-h-64" />
                        </div>
                      </div>
                    )}

                    {/* Technology Stack */}
                    {projectContext.technology_stack && (
                      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                        <div className="bg-gradient-to-r from-purple-50 to-violet-50 dark:from-purple-950/30 dark:to-violet-950/30 p-3 border-l-4 border-purple-400 dark:border-purple-600">
                          <h3 className="text-gray-700 dark:text-gray-300 font-semibold flex items-center gap-2">
                            <Code className="w-4 h-4" />
                            Technology Stack
                          </h3>
                        </div>
                        <div className="p-4">
                          <EnhancedJSONViewer data={projectContext.technology_stack} defaultExpanded={false} />
                        </div>
                      </div>
                    )}

                    {/* Project Workflow */}
                    {projectContext.project_workflow && (
                      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                        <div className="bg-gradient-to-r from-orange-50 to-amber-50 dark:from-orange-950/30 dark:to-amber-950/30 p-3 border-l-4 border-orange-400 dark:border-orange-600">
                          <h3 className="text-gray-700 dark:text-gray-300 font-semibold flex items-center gap-2">
                            <GitBranch className="w-4 h-4" />
                            Project Workflow
                          </h3>
                        </div>
                        <div className="p-4">
                          <EnhancedJSONViewer data={projectContext.project_workflow} defaultExpanded={false} />
                        </div>
                      </div>
                    )}

                    {/* Local Standards */}
                    {projectContext.local_standards && (
                      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                        <div className="bg-gradient-to-r from-indigo-50 to-blue-50 dark:from-indigo-950/30 dark:to-blue-950/30 p-3 border-l-4 border-indigo-400 dark:border-indigo-600">
                          <h3 className="text-gray-700 dark:text-gray-300 font-semibold flex items-center gap-2">
                            <Shield className="w-4 h-4" />
                            Local Standards
                          </h3>
                        </div>
                        <div className="p-4">
                          <EnhancedJSONViewer data={projectContext.local_standards} defaultExpanded={false} />
                        </div>
                      </div>
                    )}

                    {/* Metadata */}
                    {projectContext.metadata && (
                      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                        <div className="bg-gradient-to-r from-cyan-50 to-sky-50 dark:from-cyan-950/30 dark:to-sky-950/30 p-3 border-l-4 border-cyan-400 dark:border-cyan-600">
                          <h3 className="text-gray-700 dark:text-gray-300 font-semibold flex items-center gap-2">
                            <Info className="w-4 h-4" />
                            Metadata
                          </h3>
                        </div>
                        <div className="p-4">
                          {projectContext.metadata.created_at && (
                            <div className="mb-2 text-sm">
                              <span className="text-gray-500 dark:text-gray-400">Created:</span>
                              <span className="ml-2 text-gray-700 dark:text-gray-300">
                                {new Date(projectContext.metadata.created_at).toLocaleString()}
                              </span>
                            </div>
                          )}
                          {projectContext.metadata.updated_at && (
                            <div className="mb-3 text-sm">
                              <span className="text-gray-500 dark:text-gray-400">Updated:</span>
                              <span className="ml-2 text-gray-700 dark:text-gray-300">
                                {new Date(projectContext.metadata.updated_at).toLocaleString()}
                              </span>
                            </div>
                          )}
                          <details className="group">
                            <summary className="cursor-pointer font-medium text-sm text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 flex items-center gap-2">
                              <ChevronRight className="w-4 h-4 transition-transform group-open:rotate-90" />
                              View All Metadata
                            </summary>
                            <div className="mt-2">
                              <EnhancedJSONViewer data={projectContext.metadata} defaultExpanded={true} maxHeight="max-h-60" />
                            </div>
                          </details>
                        </div>
                      </div>
                    )}

                    {/* Custom Fields / Additional Data */}
                    {(() => {
                      const knownFields = ['team_preferences', 'technology_stack', 'project_workflow', 'local_standards', 'metadata', '_originalResponse', '_inheritance'];
                      const customFields = Object.entries(projectContext).filter(([key]) => !knownFields.includes(key) && !key.startsWith('_'));
                      
                      if (customFields.length > 0) {
                        return (
                          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                            <div className="bg-gradient-to-r from-gray-50 to-slate-50 dark:from-gray-950/30 dark:to-slate-950/30 p-3 border-l-4 border-gray-400 dark:border-gray-600">
                              <h3 className="text-gray-700 dark:text-gray-300 font-semibold flex items-center gap-2">
                                <Code className="w-4 h-4" />
                                Additional Context Data
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

                    {/* Raw JSON View - Always at the bottom */}
                    <details className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                      <summary className="cursor-pointer">
                        <div className="bg-gradient-to-r from-teal-50 to-cyan-50 dark:from-teal-950/30 dark:to-cyan-950/30 p-3 border-l-4 border-teal-400 dark:border-teal-600">
                          <h3 className="text-gray-700 dark:text-gray-300 font-semibold flex items-center gap-2">
                            <FileText className="w-4 h-4" />
                            Complete Raw Context
                          </h3>
                        </div>
                      </summary>
                      <div className="p-4">
                        <RawJSONDisplay 
                          jsonData={projectContext}
                          title="Project Context Data"
                          fileName="project_context.json"
                        />
                      </div>
                    </details>
                  </div>
                </>
              ) : (
                <div className="text-center py-8 bg-surface-hover rounded-lg">
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
        <DialogFooter className="flex justify-between">
          <div className="flex gap-2">
            {activeTab === 'context' && projectContext && (
              <>
                <Button
                  variant="outline"
                  onClick={() => {
                    // Expand all details elements
                    const detailsElements = document.querySelectorAll('details');
                    detailsElements.forEach(details => {
                      details.open = true;
                    });
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
                    // Collapse all details elements
                    const detailsElements = document.querySelectorAll('details');
                    detailsElements.forEach(details => {
                      details.open = false;
                    });
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
              </>
            )}
            {((activeTab === 'context' && projectContext) || (activeTab === 'details' && project)) && (
              <Button
                variant="outline"
                onClick={() => {
                  const dataToExport = activeTab === 'context' ? projectContext : project;
                  if (dataToExport) {
                    const jsonString = JSON.stringify(dataToExport, null, 2);
                    navigator.clipboard.writeText(jsonString).then(() => {
                      setJsonCopied(true);
                      setTimeout(() => setJsonCopied(false), 2000);
                    }).catch(err => {
                      logger.error('Failed to copy JSON to clipboard', { error: err, component: 'ProjectDetailsDialog' });
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
            )}
          </div>
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default ProjectDetailsDialog;