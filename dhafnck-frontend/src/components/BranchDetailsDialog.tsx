import { Calendar, Check as CheckIcon, ChevronDown, ChevronRight, Copy, FileText, GitBranch, Hash, Info, Layers, Tag, Users } from "lucide-react";
import React, { useEffect, useState } from "react";
import { getBranchContext, Project } from "../api";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import RawJSONDisplay from "./ui/RawJSONDisplay";
import { Separator } from "./ui/separator";

interface BranchDetailsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  project: Project | null;
  branch: any | null;
  onClose: () => void;
}

export const BranchDetailsDialog: React.FC<BranchDetailsDialogProps> = ({
  open,
  onOpenChange,
  project,
  branch,
  onClose
}) => {
  const [branchContext, setBranchContext] = useState<any>(null);
  const [contextLoading, setContextLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'details' | 'context'>('details');
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['data', 'resolved_context', 'branch_data', 'metadata']));
  const [jsonCopied, setJsonCopied] = useState(false);

  // Fetch branch context when dialog opens
  useEffect(() => {
    if (open && branch?.id) {
      setContextLoading(true);
      
      // Fetch branch context
      getBranchContext(branch.id)
        .then(context => {
          console.log('Raw branch context response:', context);
          
          // Store the full response to ensure we capture ALL data including custom fields
          if (context) {
            // Keep the entire response structure to preserve all nested data
            // This ensures custom fields like dependencies_to_install, risk_mitigation, etc. are preserved
            const fullContext = {
              // First priority: resolved_context which contains the actual merged data
              ...(context.data?.resolved_context || context.resolved_context || {}),
              
              // Add any additional fields from the response that might not be in resolved_context
              // This ensures we don't lose any custom data sent by the backend
              ...Object.keys(context).reduce((acc: any, key) => {
                if (key !== 'data' && key !== 'resolved_context' && key !== 'status' && key !== 'success') {
                  acc[key] = context[key];
                }
                return acc;
              }, {} as any),
              
              // Also preserve the original response structure for debugging
              _originalResponse: context
            };
            
            console.log('Processed full context with all nested data:', fullContext);
            setBranchContext(fullContext);
          } else {
            console.log('No context data received');
            setBranchContext(null);
          }
        })
        .catch(error => {
          console.error('Error fetching branch context:', error);
          setBranchContext(null);
        })
        .finally(() => {
          setContextLoading(false);
        });
    } else if (!open) {
      // Clear data when dialog closes
      setBranchContext(null);
      setActiveTab('details');
    }
  }, [open, branch?.id]);

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
    if (branchContext) {
      const jsonString = JSON.stringify(branchContext, null, 2);
      navigator.clipboard.writeText(jsonString).then(() => {
        setJsonCopied(true);
        setTimeout(() => setJsonCopied(false), 2000);
      }).catch(err => {
        console.error('Failed to copy JSON:', err);
      });
    }
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
                        ? 'p-3 bg-surface-hover rounded-lg border border-surface-border' 
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
      <DialogContent className="w-[90vw] h-[90vh] max-w-[90vw] max-h-[90vh] overflow-hidden bg-white dark:bg-gray-900 rounded-lg shadow-xl flex flex-col">
        <DialogHeader>
          <DialogTitle className="text-xl text-left flex items-center gap-2">
            <GitBranch className="w-5 h-5" />
            {branch?.name || 'Branch Details'}
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
              {!contextLoading && branchContext && Object.keys(branchContext).length > 0 && (
                <Badge variant="secondary" className="text-xs">Available</Badge>
              )}
            </button>
          </div>
        </DialogHeader>
        
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
                    <span className="ml-2 font-medium">{branch?.name}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">ID:</span>
                    <span className="ml-2 font-mono text-xs">{branch?.id}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Description:</span>
                    <span className="ml-2">{branch?.description || "No description"}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Project:</span>
                    <span className="ml-2">{project?.name}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Project ID:</span>
                    <span className="ml-2 font-mono text-xs">{project?.id}</span>
                  </div>
                </div>
              </div>

              <Separator />

              {/* Branch Status */}
              {branch && branch['status'] && (
                <>
                  <div className="bg-surface-hover p-4 rounded-lg">
                    <h3 className="text-lg font-semibold mb-3 text-blue-700">Branch Status</h3>
                    <div className="bg-surface p-3 rounded border border-surface-border">
                      <pre className="text-xs overflow-x-auto whitespace-pre-wrap">
                        {typeof branch['status'] === 'object' 
                          ? JSON.stringify(branch['status'], null, 2)
                          : branch['status']}
                      </pre>
                    </div>
                  </div>
                  <Separator />
                </>
              )}

              {/* Task Statistics */}
              {branch && (branch['task_statistics'] || branch['task_count'] !== undefined) && (
                <>
                  <div className="bg-surface-hover p-4 rounded-lg">
                    <h3 className="text-lg font-semibold mb-3 text-green-700">Task Statistics</h3>
                    <div className="bg-surface p-3 rounded border border-surface-border">
                      {branch['task_count'] !== undefined && (
                        <div className="mb-2">
                          <span className="font-medium">Total Tasks:</span> {branch['task_count']}
                        </div>
                      )}
                      {branch['task_statistics'] && (
                        <pre className="text-xs overflow-x-auto whitespace-pre-wrap">
                          {typeof branch['task_statistics'] === 'object' 
                            ? JSON.stringify(branch['task_statistics'], null, 2)
                            : branch['task_statistics']}
                        </pre>
                      )}
                    </div>
                  </div>
                  <Separator />
                </>
              )}

              {/* Assigned Agents */}
              {branch && branch['assigned_agents'] && (
                <>
                  <div className="bg-surface-hover p-4 rounded-lg">
                    <h3 className="text-lg font-semibold mb-3 text-purple-700">Assigned Agents</h3>
                    <div className="bg-surface p-3 rounded border border-surface-border">
                      <pre className="text-xs overflow-x-auto whitespace-pre-wrap">
                        {typeof branch['assigned_agents'] === 'object' 
                          ? JSON.stringify(branch['assigned_agents'], null, 2)
                          : branch['assigned_agents']}
                      </pre>
                    </div>
                  </div>
                  <Separator />
                </>
              )}

              {/* Branch Metadata */}
              {branch && branch['metadata'] && (
                <>
                  <div className="bg-surface-hover p-4 rounded-lg">
                    <h3 className="text-lg font-semibold mb-3 text-orange-700">Branch Metadata</h3>
                    <div className="bg-surface p-3 rounded border border-surface-border">
                      <pre className="text-xs overflow-x-auto whitespace-pre-wrap">
                        {typeof branch['metadata'] === 'object' 
                          ? JSON.stringify(branch['metadata'], null, 2)
                          : branch['metadata']}
                      </pre>
                    </div>
                  </div>
                  <Separator />
                </>
              )}

              {/* Additional Fields - Display any other fields */}
              {branch && (
                <>
                  {Object.entries(branch).filter(([key]) => 
                    !['id', 'name', 'description', 'status', 'task_statistics', 'task_count', 'assigned_agents', 'metadata'].includes(key)
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
                  View Complete Raw Branch Data (JSON)
                </summary>
                <div className="mt-3">
                  <RawJSONDisplay 
                    jsonData={{ branch: branch, project: project }}
                    title="Branch Data"
                    fileName="branch.json"
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
              ) : branchContext ? (
                <>
                  {/* Context Header */}
                  <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950/20 dark:to-indigo-950/20 p-4 rounded-lg border border-blue-200 dark:border-blue-800">
                    <h3 className="text-lg font-semibold text-blue-700 dark:text-blue-300 flex items-center gap-2">
                      <Layers className="w-5 h-5" />
                      Branch Context - Complete Hierarchical View
                    </h3>
                    <p className="text-sm text-blue-600 dark:text-blue-400 mt-1">
                      Interactive nested view showing ALL context data including custom fields - click to expand/collapse sections
                    </p>
                  </div>
                  
                  {/* Key Implementation Details - Organized View */}
                  {branchContext.branch_settings?.branch_workflow?.authentication_implementation && (
                    <div className="bg-surface-hover p-4 rounded-lg border border-surface-border">
                      <h4 className="text-md font-semibold text-green-700 dark:text-green-300 mb-3">
                        🎯 Authentication Implementation Overview
                      </h4>
                      
                      {/* Timeline and Progress */}
                      <div className="grid grid-cols-2 gap-4 mb-3">
                        <div className="bg-surface p-2 rounded">
                          <span className="text-xs text-gray-500">Timeline</span>
                          <p className="font-medium">{branchContext.branch_settings.branch_workflow.authentication_implementation.timeline || 'TBD'}</p>
                        </div>
                        <div className="bg-surface p-2 rounded">
                          <span className="text-xs text-gray-500">Current Phase</span>
                          <p className="font-medium">{branchContext.branch_settings.branch_workflow.authentication_implementation.current_phase || 'Planning'}</p>
                        </div>
                      </div>
                      
                      {/* Dependencies Summary */}
                      {branchContext.branch_settings.branch_workflow.authentication_implementation.dependencies_to_install && (
                        <details className="mb-3">
                          <summary className="cursor-pointer text-sm font-medium text-green-600 hover:text-green-700">
                            📦 Dependencies ({Object.keys(branchContext.branch_settings.branch_workflow.authentication_implementation.dependencies_to_install).length} categories)
                          </summary>
                          <div className="mt-2 ml-4 text-sm">
                            {renderNestedJson(branchContext.branch_settings.branch_workflow.authentication_implementation.dependencies_to_install)}
                          </div>
                        </details>
                      )}
                      
                      {/* Implementation Phases Summary */}
                      {branchContext.branch_settings.branch_workflow.authentication_implementation.implementation_plan && (
                        <details className="mb-3">
                          <summary className="cursor-pointer text-sm font-medium text-green-600 hover:text-green-700">
                            📋 Implementation Phases ({branchContext.branch_settings.branch_workflow.authentication_implementation.phases} phases)
                          </summary>
                          <div className="mt-2 ml-4 text-sm max-h-60 overflow-y-auto">
                            {renderNestedJson(branchContext.branch_settings.branch_workflow.authentication_implementation.implementation_plan)}
                          </div>
                        </details>
                      )}
                      
                      {/* Risk Mitigation Summary */}
                      {branchContext.branch_settings.branch_workflow.authentication_implementation.risk_mitigation && (
                        <details className="mb-3">
                          <summary className="cursor-pointer text-sm font-medium text-green-600 hover:text-green-700">
                            ⚠️ Risk Mitigation Strategies
                          </summary>
                          <div className="mt-2 ml-4 text-sm">
                            {renderNestedJson(branchContext.branch_settings.branch_workflow.authentication_implementation.risk_mitigation)}
                          </div>
                        </details>
                      )}
                    </div>
                  )}
                  
                  {/* Branch Settings Section */}
                  {branchContext.branch_settings && (
                    <div className="bg-surface-hover p-4 rounded-lg border border-surface-border">
                      <h4 className="text-md font-semibold text-blue-700 dark:text-blue-300 mb-3">
                        ⚙️ Branch Settings & Standards
                      </h4>
                      
                      {/* Security Standards */}
                      {branchContext.branch_settings.branch_standards?.security && (
                        <details className="mb-3">
                          <summary className="cursor-pointer text-sm font-medium text-blue-600 hover:text-blue-700">
                            🔒 Security Standards
                          </summary>
                          <div className="mt-2 ml-4 text-sm bg-surface p-2 rounded">
                            {renderNestedJson(branchContext.branch_settings.branch_standards.security)}
                          </div>
                        </details>
                      )}
                      
                      {/* API Design Standards */}
                      {branchContext.branch_settings.branch_standards?.api_design && (
                        <details className="mb-3">
                          <summary className="cursor-pointer text-sm font-medium text-blue-600 hover:text-blue-700">
                            🔌 API Design Standards
                          </summary>
                          <div className="mt-2 ml-4 text-sm bg-surface p-2 rounded">
                            {renderNestedJson(branchContext.branch_settings.branch_standards.api_design)}
                          </div>
                        </details>
                      )}
                      
                      {/* Agent Assignments */}
                      {branchContext.branch_settings.agent_assignments && (
                        <details className="mb-3">
                          <summary className="cursor-pointer text-sm font-medium text-blue-600 hover:text-blue-700">
                            🤖 Agent Assignments ({Object.keys(branchContext.branch_settings.agent_assignments).length} agents)
                          </summary>
                          <div className="mt-2 ml-4 text-sm bg-surface p-2 rounded">
                            {renderNestedJson(branchContext.branch_settings.agent_assignments)}
                          </div>
                        </details>
                      )}
                    </div>
                  )}
                  
                  {/* Metadata Section */}
                  {branchContext.metadata && (
                    <div className="bg-surface-hover p-4 rounded-lg border border-surface-border">
                      <h4 className="text-md font-semibold text-purple-700 dark:text-purple-300 mb-3">
                        📊 Metadata & System Information
                      </h4>
                      
                      <div className="grid grid-cols-2 gap-4 mb-3">
                        {branchContext.metadata.created_at && (
                          <div className="bg-surface p-2 rounded">
                            <span className="text-xs text-gray-500">Created</span>
                            <p className="font-medium text-sm">{new Date(branchContext.metadata.created_at).toLocaleDateString()}</p>
                          </div>
                        )}
                        {branchContext.metadata.updated_at && (
                          <div className="bg-surface p-2 rounded">
                            <span className="text-xs text-gray-500">Last Updated</span>
                            <p className="font-medium text-sm">{new Date(branchContext.metadata.updated_at).toLocaleDateString()}</p>
                          </div>
                        )}
                      </div>
                      
                      {/* Other Metadata */}
                      <details>
                        <summary className="cursor-pointer text-sm font-medium text-purple-600 hover:text-purple-700">
                          View All Metadata
                        </summary>
                        <div className="mt-2 ml-4 text-sm bg-surface p-2 rounded max-h-40 overflow-y-auto">
                          {renderNestedJson(branchContext.metadata)}
                        </div>
                      </details>
                    </div>
                  )}
                  
                  {/* Inheritance Information */}
                  {branchContext._inheritance && (
                    <div className="bg-surface-hover p-4 rounded-lg border border-surface-border">
                      <h4 className="text-md font-semibold text-orange-700 dark:text-orange-300 mb-3">
                        🔗 Context Inheritance
                      </h4>
                      <div className="text-sm">
                        <p className="mb-2">
                          <span className="font-medium">Inheritance Chain:</span> {branchContext._inheritance.chain?.join(' → ') || 'N/A'}
                        </p>
                        <p className="mb-2">
                          <span className="font-medium">Inheritance Depth:</span> {branchContext._inheritance.inheritance_depth || 0}
                        </p>
                      </div>
                    </div>
                  )}
                  
                  {/* Debug Information - Collapsed by Default */}
                  <details className="bg-surface-hover p-4 rounded-lg border border-surface-border">
                    <summary className="cursor-pointer text-md font-medium text-white-600 hover:text-gray-700">
                      🐛 Debug: View Raw Context Data
                    </summary>
                    <div className="mt-3">
                      <p className="text-xs text-gray-500 mb-2">Complete context structure for debugging purposes</p>
                      <RawJSONDisplay 
                        jsonData={branchContext}
                        title="Branch Context"
                        fileName="branch_context.json"
                      />
                    </div>
                  </details>
                  
                  {/* Expand/Collapse All Controls */}
                  <div className="flex gap-2 justify-end mt-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        // Expand all sections including HTML details elements
                        const allPaths = new Set<string>();
                        const traverse = (obj: any, path: string = '') => {
                          if (obj && typeof obj === 'object') {
                            allPaths.add(path);
                            Object.keys(obj).forEach(key => {
                              const newPath = path ? `${path}.${key}` : key;
                              traverse(obj[key], newPath);
                            });
                          }
                        };
                        traverse(branchContext);
                        setExpandedSections(allPaths);
                        
                        // Also expand all HTML details elements
                        const detailsElements = document.querySelectorAll('details');
                        detailsElements.forEach(details => {
                          details.open = true;
                        });
                      }}
                    >
                      Expand All
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        // Collapse all sections
                        setExpandedSections(new Set(['data', 'resolved_context', 'branch_data', 'metadata']));
                        
                        // Also collapse all HTML details elements
                        const detailsElements = document.querySelectorAll('details');
                        detailsElements.forEach(details => {
                          details.open = false;
                        });
                      }}
                    >
                      Collapse All
                    </Button>
                  </div>
                </>
              ) : (
                <div className="text-center py-8 bg-surface-hover rounded-lg">
                  <FileText className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                  <h3 className="text-lg font-medium text-gray-900">No Context Available</h3>
                  <p className="text-sm text-gray-500 mt-2">
                    This branch doesn't have any context data yet.
                  </p>
                  <p className="text-xs text-gray-400 mt-4">
                    Context is created when branches are updated or when tasks are created within the branch.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
        <DialogFooter className="flex justify-between">
          <div className="flex gap-2">
            {((activeTab === 'context' && branchContext) || (activeTab === 'details' && branch)) && (
              <Button
                variant="outline"
                onClick={() => {
                  const dataToExport = activeTab === 'context' ? branchContext : branch;
                  if (dataToExport) {
                    const jsonString = JSON.stringify(dataToExport, null, 2);
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

export default BranchDetailsDialog;