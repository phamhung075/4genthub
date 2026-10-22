import { Check as CheckIcon, ChevronDown, ChevronRight, Code, Copy, Database, FileCode, FileText, GitBranch, Info, Layers, Settings, Shield, Users, Wifi, WifiOff } from "lucide-react";
import React, { useEffect, useState } from "react";
import { getBranchContext } from "../api";
import type { Branch, BranchContextData, BranchSummary, ContextMetadata, Project } from "../types";
import { useBranchWebSocket } from "../hooks/useWebSocketV2";
import { useAuth } from "../contexts/AuthContext";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import { EnhancedJSONViewer } from "./ui/EnhancedJSONViewer";
import RawJSONDisplay from "./ui/RawJSONDisplay";
import { Separator } from "./ui/separator";
import logger from "../utils/logger";

/**
 * Resolved branch context: `BranchContextData` plus the sections this dialog renders. Custom
 * fields ride along through its index signature and stay `unknown` until they are rendered.
 */
type BranchContextView = BranchContextData & {
  branch_standards?: Record<string, unknown>;
  project_context?: Record<string, unknown>;
  branch_data?: Record<string, unknown>;
  agent_assignments?: Record<string, unknown> | unknown[];
  metadata?: ContextMetadata & { created_at?: string; updated_at?: string };
};

interface BranchDetailsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  project: Project | null;
  /** Either the bulk-list summary or the raw branch record nested in a project. */
  branch: Branch | BranchSummary | null;
  onClose: () => void;
}

export const BranchDetailsDialog: React.FC<BranchDetailsDialogProps> = ({
  open,
  onOpenChange,
  project,
  branch,
  onClose
}) => {
  const { user, tokens } = useAuth();
  const [branchContext, setBranchContext] = useState<BranchContextView | null>(null);
  const [contextLoading, setContextLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'details' | 'context'>('details');
  const [jsonCopied, setJsonCopied] = useState(false);

  // The branch record is typed, but the endpoint decorates it with fields the domain type does
  // not model; this read-only view keeps those renderable without weakening the prop.
  const branchFields = (branch ?? {}) as Record<string, unknown>;

  // Initialize WebSocket connection for real-time branch updates
  const { isConnected } = useBranchWebSocket(user?.id || '', tokens?.access_token || '', branch?.id);

  // Fetch branch context when dialog opens
  useEffect(() => {
    if (open && branch?.id) {
      setContextLoading(true);

      // Fetch branch context
      getBranchContext(branch.id)
        .then((context: unknown) => {
          logger.debug('Raw branch context response:', context);

          if (!context) {
            logger.debug('No context data received');
            setBranchContext(null);
            return;
          }

          // `getBranchContext` returns untyped JSON; this is the boundary where the endpoint
          // contract - `data.resolved_context` (or a plain `resolved_context`) - is asserted.
          const response = context as Record<string, unknown>;
          const data = response.data;
          const resolvedContext =
            data !== null && typeof data === 'object' && 'resolved_context' in data
              ? data.resolved_context
              : response.resolved_context;

          // Keep the entire response structure to preserve custom fields such as
          // dependencies_to_install or risk_mitigation that resolved_context may not carry.
          const extraFields = Object.fromEntries(
            Object.entries(response).filter(
              ([key]) => !['data', 'resolved_context', 'status', 'success'].includes(key)
            )
          );

          const fullContext = {
            ...(resolvedContext as Record<string, unknown>),
            ...extraFields,
            // Also preserve the original response structure for debugging
            _originalResponse: context
          } as BranchContextView;

          logger.debug('Processed full context with all nested data:', fullContext);
          setBranchContext(fullContext);
        })
        .catch(error => {
          logger.error('Error fetching branch context:', error);
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

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-[90vw] max-w-6xl h-[85vh] mx-auto overflow-hidden bg-white dark:bg-gray-900 rounded-lg shadow-xl flex flex-col">
        <DialogHeader className="pb-0">
          <div className="flex items-center justify-between">
            <DialogTitle className="text-xl text-left flex items-center gap-2">
              <GitBranch className="w-5 h-5" />
              {branch?.name || 'Branch Details'}
            </DialogTitle>
            <div className="flex items-center gap-2">
              {/* WebSocket Connection Status */}
              <div className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs ${
                isConnected
                  ? 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400'
                  : 'bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-400'
              }`}>
                {isConnected ? (
                  <>
                    <Wifi className="w-3 h-3" />
                    <span>Live</span>
                  </>
                ) : (
                  <>
                    <WifiOff className="w-3 h-3" />
                    <span>Offline</span>
                  </>
                )}
              </div>
            </div>
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
            {!contextLoading && branchContext && Object.keys(branchContext).length > 0 && (
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
                    <span className="text-base-secondary">Name:</span>
                    <span className="ml-2 font-medium">{branch?.name}</span>
                  </div>
                  <div>
                    <span className="text-base-secondary">ID:</span>
                    <span className="ml-2 font-mono text-xs">{branch?.id}</span>
                  </div>
                  <div>
                    <span className="text-base-secondary">Description:</span>
                    <span className="ml-2">{branchFields.description ? String(branchFields.description) : "No description"}</span>
                  </div>
                  <div>
                    <span className="text-base-secondary">Project:</span>
                    <span className="ml-2">{project?.name}</span>
                  </div>
                  <div>
                    <span className="text-base-secondary">Project ID:</span>
                    <span className="ml-2 font-mono text-xs">{project?.id}</span>
                  </div>
                </div>
              </div>

              <Separator />

              {/* Branch Status */}
              {branch && Boolean(branchFields.status) && (
                <>
                  <div className="bg-surface-hover p-4 rounded-lg">
                    <h3 className="text-lg font-semibold mb-3 text-blue-700">Branch Status</h3>
                    <div className="bg-surface p-3 rounded border border-surface-border">
                      <pre className="text-xs overflow-x-auto whitespace-pre-wrap">
                        {typeof branchFields.status === 'object'
                          ? JSON.stringify(branchFields.status, null, 2)
                          : String(branchFields.status)}
                      </pre>
                    </div>
                  </div>
                  <Separator />
                </>
              )}

              {/* Task Statistics */}
              {branch && (Boolean(branchFields.task_statistics) || branchFields.total_tasks !== undefined) && (
                <>
                  <div className="bg-surface-hover p-4 rounded-lg">
                    <h3 className="text-lg font-semibold mb-3 text-green-700">Task Statistics</h3>
                    <div className="bg-surface p-3 rounded border border-surface-border">
                      {branchFields.total_tasks !== undefined && (
                        <div className="mb-2">
                          <span className="font-medium">Total Tasks:</span> {String(branchFields.total_tasks)}
                        </div>
                      )}
                      {Boolean(branchFields.task_statistics) && (
                        <pre className="text-xs overflow-x-auto whitespace-pre-wrap">
                          {typeof branchFields.task_statistics === 'object'
                            ? JSON.stringify(branchFields.task_statistics, null, 2)
                            : String(branchFields.task_statistics)}
                        </pre>
                      )}
                    </div>
                  </div>
                  <Separator />
                </>
              )}

              {/* Assigned Agents */}
              {branch && Boolean(branchFields.assigned_agents) && (
                <>
                  <div className="bg-surface-hover p-4 rounded-lg">
                    <h3 className="text-lg font-semibold mb-3 text-purple-700">Assigned Agents</h3>
                    <div className="bg-surface p-3 rounded border border-surface-border">
                      <pre className="text-xs overflow-x-auto whitespace-pre-wrap">
                        {typeof branchFields.assigned_agents === 'object'
                          ? JSON.stringify(branchFields.assigned_agents, null, 2)
                          : String(branchFields.assigned_agents)}
                      </pre>
                    </div>
                  </div>
                  <Separator />
                </>
              )}

              {/* Branch Metadata */}
              {branch && Boolean(branchFields.metadata) && (
                <>
                  <div className="bg-surface-hover p-4 rounded-lg">
                    <h3 className="text-lg font-semibold mb-3 text-orange-700">Branch Metadata</h3>
                    <div className="bg-surface p-3 rounded border border-surface-border">
                      <pre className="text-xs overflow-x-auto whitespace-pre-wrap">
                        {typeof branchFields.metadata === 'object'
                          ? JSON.stringify(branchFields.metadata, null, 2)
                          : String(branchFields.metadata)}
                      </pre>
                    </div>
                  </div>
                  <Separator />
                </>
              )}

              {/* Additional Fields - Display any other fields */}
              {branch && (
                <>
                  {Object.entries(branchFields).filter(([key]) =>
                    !['id', 'name', 'description', 'status', 'task_statistics', 'total_tasks', 'assigned_agents', 'metadata'].includes(key)
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
                      Branch Context Data
                    </h3>
                    <p className="text-sm text-blue-600 dark:text-blue-400 mt-1">
                      Complete hierarchical context for this branch including inherited data
                    </p>
                  </div>

                  {/* Organized Context Sections */}
                  <div className="space-y-4">
                    {/* Branch Settings & Configuration */}
                    {(branchContext.branch_settings || branchContext.branch_standards || branchContext.branch_workflow) && (
                      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950/30 dark:to-indigo-950/30 p-3 border-l-4 border-blue-400 dark:border-blue-600">
                          <h3 className="text-gray-700 dark:text-gray-300 font-semibold flex items-center gap-2">
                            <Settings className="w-4 h-4" />
                            Branch Configuration
                          </h3>
                        </div>
                        <div className="p-4 space-y-3">
                          {branchContext.branch_settings && (
                            <details className="group">
                              <summary className="cursor-pointer font-medium text-sm text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 flex items-center gap-2">
                                <ChevronRight className="w-4 h-4 transition-transform group-open:rotate-90" />
                                Settings
                              </summary>
                              <div className="mt-2 ml-6">
                                <EnhancedJSONViewer data={branchContext.branch_settings} defaultExpanded={false} />
                              </div>
                            </details>
                          )}
                          {branchContext.branch_standards && (
                            <details className="group">
                              <summary className="cursor-pointer font-medium text-sm text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 flex items-center gap-2">
                                <ChevronRight className="w-4 h-4 transition-transform group-open:rotate-90" />
                                <Shield className="w-4 h-4" />
                                Standards & Policies
                              </summary>
                              <div className="mt-2 ml-6">
                                <EnhancedJSONViewer data={branchContext.branch_standards} defaultExpanded={false} />
                              </div>
                            </details>
                          )}
                          {branchContext.branch_workflow && (
                            <details className="group">
                              <summary className="cursor-pointer font-medium text-sm text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 flex items-center gap-2">
                                <ChevronRight className="w-4 h-4 transition-transform group-open:rotate-90" />
                                <FileCode className="w-4 h-4" />
                                Workflow
                              </summary>
                              <div className="mt-2 ml-6">
                                <EnhancedJSONViewer data={branchContext.branch_workflow} defaultExpanded={false} />
                              </div>
                            </details>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Project Context (Inherited) */}
                    {branchContext.project_context && (
                      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                        <div className="bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-950/30 dark:to-emerald-950/30 p-3 border-l-4 border-green-400 dark:border-green-600">
                          <h3 className="text-gray-700 dark:text-gray-300 font-semibold flex items-center gap-2">
                            <Database className="w-4 h-4" />
                            Project Context (Inherited)
                          </h3>
                        </div>
                        <div className="p-4">
                          <EnhancedJSONViewer data={branchContext.project_context} defaultExpanded={false} maxHeight="max-h-64" />
                        </div>
                      </div>
                    )}

                    {/* Branch Data */}
                    {branchContext.branch_data && (
                      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                        <div className="bg-gradient-to-r from-purple-50 to-violet-50 dark:from-purple-950/30 dark:to-violet-950/30 p-3 border-l-4 border-purple-400 dark:border-purple-600">
                          <h3 className="text-gray-700 dark:text-gray-300 font-semibold flex items-center gap-2">
                            <GitBranch className="w-4 h-4" />
                            Branch Data
                          </h3>
                        </div>
                        <div className="p-4">
                          <EnhancedJSONViewer data={branchContext.branch_data} defaultExpanded={false} />
                        </div>
                      </div>
                    )}

                    {/* Agent Assignments */}
                    {branchContext.agent_assignments && (
                      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                        <div className="bg-gradient-to-r from-orange-50 to-amber-50 dark:from-orange-950/30 dark:to-amber-950/30 p-3 border-l-4 border-orange-400 dark:border-orange-600">
                          <h3 className="text-gray-700 dark:text-gray-300 font-semibold flex items-center gap-2">
                            <Users className="w-4 h-4" />
                            Agent Assignments
                          </h3>
                        </div>
                        <div className="p-4">
                          <EnhancedJSONViewer data={branchContext.agent_assignments} defaultExpanded={true} maxHeight="max-h-48" />
                        </div>
                      </div>
                    )}

                    {/* Metadata */}
                    {branchContext.metadata && (
                      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                        <div className="bg-gradient-to-r from-indigo-50 to-blue-50 dark:from-indigo-950/30 dark:to-blue-950/30 p-3 border-l-4 border-indigo-400 dark:border-indigo-600">
                          <h3 className="text-gray-700 dark:text-gray-300 font-semibold flex items-center gap-2">
                            <Info className="w-4 h-4" />
                            Metadata
                          </h3>
                        </div>
                        <div className="p-4">
                          {branchContext.metadata.created_at && (
                            <div className="mb-2 text-sm">
                              <span className="text-gray-500 dark:text-gray-400">Created:</span>
                              <span className="ml-2 text-gray-700 dark:text-gray-300">
                                {new Date(branchContext.metadata.created_at).toLocaleString()}
                              </span>
                            </div>
                          )}
                          {branchContext.metadata.updated_at && (
                            <div className="mb-3 text-sm">
                              <span className="text-gray-500 dark:text-gray-400">Updated:</span>
                              <span className="ml-2 text-gray-700 dark:text-gray-300">
                                {new Date(branchContext.metadata.updated_at).toLocaleString()}
                              </span>
                            </div>
                          )}
                          <details className="group">
                            <summary className="cursor-pointer font-medium text-sm text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 flex items-center gap-2">
                              <ChevronRight className="w-4 h-4 transition-transform group-open:rotate-90" />
                              View All Metadata
                            </summary>
                            <div className="mt-2">
                              <EnhancedJSONViewer data={branchContext.metadata} defaultExpanded={true} maxHeight="max-h-60" />
                            </div>
                          </details>
                        </div>
                      </div>
                    )}

                    {/* Custom Fields / Additional Data */}
                    {(() => {
                      const knownFields = ['branch_settings', 'branch_standards', 'branch_workflow', 'project_context', 'branch_data', 'agent_assignments', 'metadata', '_originalResponse', '_inheritance'];
                      const customFields = Object.entries(branchContext).filter(([key]) => !knownFields.includes(key) && !key.startsWith('_'));

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
                          jsonData={branchContext}
                          title="Branch Context Data"
                          fileName="branch_context.json"
                        />
                      </div>
                    </details>
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
            {activeTab === 'context' && branchContext && (
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
