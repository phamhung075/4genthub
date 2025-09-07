import React, { useEffect, useState } from "react";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import { Separator } from "./ui/separator";
import { Subtask, getSubtask } from "../api";
import ClickableAssignees from "./ClickableAssignees";
import { FileText, Info, ChevronDown, ChevronRight, Hash, Calendar, Tag, Layers, Copy, Check as CheckIcon } from "lucide-react";
import RawJSONDisplay from "./ui/RawJSONDisplay";
import { HolographicStatusBadge, HolographicPriorityBadge } from "./ui/holographic-badges";

interface SubtaskDetailsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  subtask: Subtask | null;
  parentTaskId: string;
  onClose: () => void;
  onAgentClick?: (agentName: string, subtask: Subtask) => void;
}

export const SubtaskDetailsDialog: React.FC<SubtaskDetailsDialogProps> = ({
  open,
  onOpenChange,
  subtask,
  parentTaskId,
  onClose,
  onAgentClick
}) => {
  const [fullSubtask, setFullSubtask] = useState<Subtask | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'details' | 'json'>('details');
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['info', 'progress']));
  const [jsonCopied, setJsonCopied] = useState(false);

  // Set initial subtask when it changes
  useEffect(() => {
    if (subtask && subtask.id) {
      setFullSubtask(subtask);
    }
  }, [subtask]);

  // Fetch full subtask when dialog opens
  useEffect(() => {
    const taskId = subtask?.id || fullSubtask?.id;
    if (open && taskId && parentTaskId) {
      fetchFullSubtask(parentTaskId, taskId);
    }
  }, [open, subtask?.id, fullSubtask?.id, parentTaskId]);

  const fetchFullSubtask = async (parentId: string, subtaskId: string) => {
    setLoading(true);
    try {
      const data = await getSubtask(parentId, subtaskId);
      setFullSubtask(data);
    } catch (error) {
      console.error('[SubtaskDetailsDialog] Failed to fetch subtask:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleSection = (section: string) => {
    setExpandedSections(prev => {
      const newSet = new Set(prev);
      if (newSet.has(section)) {
        newSet.delete(section);
      } else {
        newSet.add(section);
      }
      return newSet;
    });
  };

  const copyJson = () => {
    if (fullSubtask) {
      navigator.clipboard.writeText(JSON.stringify(fullSubtask, null, 2));
      setJsonCopied(true);
      setTimeout(() => setJsonCopied(false), 2000);
    }
  };

  const handleCloseDialog = () => {
    setActiveTab('details');
    onClose();
  };

  if (!fullSubtask) {
    return null;
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-hidden flex flex-col">
        <DialogHeader className="flex-shrink-0">
          <DialogTitle className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <FileText className="w-5 h-5 text-blue-500" />
              <span className="text-lg font-semibold">Subtask Details</span>
              {loading && <Badge variant="secondary">Loading...</Badge>}
            </div>
            <div className="flex gap-2">
              <Button
                variant={activeTab === 'details' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setActiveTab('details')}
              >
                Details
              </Button>
              <Button
                variant={activeTab === 'json' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setActiveTab('json')}
              >
                JSON
              </Button>
            </div>
          </DialogTitle>
        </DialogHeader>

        <Separator className="my-2" />

        <div className="flex-1 overflow-y-auto px-1">
          {activeTab === 'details' ? (
            <div className="space-y-4">
              {/* Basic Information */}
              <div>
                <button
                  onClick={() => toggleSection('info')}
                  className="w-full flex items-center gap-2 p-2 hover:bg-gray-50 dark:hover:bg-gray-800 rounded transition-colors"
                >
                  {expandedSections.has('info') ? (
                    <ChevronDown className="w-4 h-4" />
                  ) : (
                    <ChevronRight className="w-4 h-4" />
                  )}
                  <Info className="w-4 h-4 text-blue-500" />
                  <span className="font-medium">Basic Information</span>
                </button>
                {expandedSections.has('info') && (
                  <div className="pl-8 space-y-3 mt-2">
                    <div className="flex items-center gap-2">
                      <Hash className="w-4 h-4 text-gray-400" />
                      <span className="text-sm text-gray-600 dark:text-gray-400">ID:</span>
                      <code className="text-xs bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">
                        {fullSubtask.id}
                      </code>
                    </div>
                    <div>
                      <span className="text-sm font-medium">Title:</span>
                      <p className="text-sm mt-1">{fullSubtask.title}</p>
                    </div>
                    <div>
                      <span className="text-sm font-medium">Description:</span>
                      <p className="text-sm mt-1 text-gray-600 dark:text-gray-400">
                        {fullSubtask.description || 'No description provided'}
                      </p>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Status:</span>
                        <HolographicStatusBadge status={fullSubtask.status as any} size="xs" />
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Priority:</span>
                        <HolographicPriorityBadge priority={fullSubtask.priority as any} size="xs" />
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Progress Information */}
              <div>
                <button
                  onClick={() => toggleSection('progress')}
                  className="w-full flex items-center gap-2 p-2 hover:bg-gray-50 dark:hover:bg-gray-800 rounded transition-colors"
                >
                  {expandedSections.has('progress') ? (
                    <ChevronDown className="w-4 h-4" />
                  ) : (
                    <ChevronRight className="w-4 h-4" />
                  )}
                  <Layers className="w-4 h-4 text-green-500" />
                  <span className="font-medium">Progress</span>
                </button>
                {expandedSections.has('progress') && (
                  <div className="pl-8 space-y-3 mt-2">
                    {fullSubtask.progress_percentage !== undefined && (
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm text-gray-600 dark:text-gray-400">Completion:</span>
                          <span className="text-sm font-medium">{fullSubtask.progress_percentage}%</span>
                        </div>
                        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                          <div 
                            className="h-2 rounded-full transition-all duration-300 relative overflow-hidden group"
                            style={{ width: `${fullSubtask.progress_percentage}%` }}
                          >
                            <div className="absolute inset-0 bg-gradient-to-r from-blue-400 to-blue-600" />
                            <div 
                              className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent"
                              style={{
                                backgroundSize: '200% 100%',
                                animation: 'shimmer-progress 2s infinite linear'
                              }}
                            />
                          </div>
                        </div>
                      </div>
                    )}
                    {fullSubtask.progress_notes && (
                      <div>
                        <span className="text-sm font-medium">Progress Notes:</span>
                        <p className="text-sm mt-1 text-gray-600 dark:text-gray-400">
                          {fullSubtask.progress_notes}
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Assignees */}
              {fullSubtask.assignees && fullSubtask.assignees.length > 0 && (
                <div>
                  <button
                    onClick={() => toggleSection('assignees')}
                    className="w-full flex items-center gap-2 p-2 hover:bg-gray-50 dark:hover:bg-gray-800 rounded transition-colors"
                  >
                    {expandedSections.has('assignees') ? (
                      <ChevronDown className="w-4 h-4" />
                    ) : (
                      <ChevronRight className="w-4 h-4" />
                    )}
                    <Tag className="w-4 h-4 text-purple-500" />
                    <span className="font-medium">Assignees</span>
                    <Badge variant="secondary" className="text-xs ml-2">
                      {fullSubtask.assignees.length}
                    </Badge>
                  </button>
                  {expandedSections.has('assignees') && (
                    <div className="pl-8 mt-2">
                      <ClickableAssignees
                        assignees={fullSubtask.assignees}
                        task={fullSubtask}
                        onAgentClick={(agent) => onAgentClick?.(agent, fullSubtask)}
                      />
                    </div>
                  )}
                </div>
              )}

              {/* Timestamps */}
              <div>
                <button
                  onClick={() => toggleSection('timestamps')}
                  className="w-full flex items-center gap-2 p-2 hover:bg-gray-50 dark:hover:bg-gray-800 rounded transition-colors"
                >
                  {expandedSections.has('timestamps') ? (
                    <ChevronDown className="w-4 h-4" />
                  ) : (
                    <ChevronRight className="w-4 h-4" />
                  )}
                  <Calendar className="w-4 h-4 text-orange-500" />
                  <span className="font-medium">Timestamps</span>
                </button>
                {expandedSections.has('timestamps') && (
                  <div className="pl-8 space-y-2 mt-2">
                    {fullSubtask.created_at && (
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Created:</span>
                        <span className="text-sm">{new Date(fullSubtask.created_at).toLocaleString()}</span>
                      </div>
                    )}
                    {fullSubtask.updated_at && (
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Updated:</span>
                        <span className="text-sm">{new Date(fullSubtask.updated_at).toLocaleString()}</span>
                      </div>
                    )}
                    {fullSubtask.completed_at && (
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Completed:</span>
                        <span className="text-sm">{new Date(fullSubtask.completed_at).toLocaleString()}</span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-medium">View Complete Raw Subtask Data (JSON)</h3>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={copyJson}
                  className="flex items-center gap-2"
                >
                  {jsonCopied ? (
                    <>
                      <CheckIcon className="w-4 h-4 text-green-500" />
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
              <RawJSONDisplay 
                jsonData={fullSubtask}
                title={`Subtask: ${fullSubtask.title}`}
                fileName={`subtask_${fullSubtask.id.slice(0, 8)}.json`}
              />
            </div>
          )}
        </div>

        <Separator className="my-2" />

        <DialogFooter className="flex-shrink-0">
          <Button variant="outline" onClick={handleCloseDialog}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default SubtaskDetailsDialog;