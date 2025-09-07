import React from "react";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import { Task } from "../api";
import { formatContextDisplay } from "../utils/contextHelpers";

interface TaskContextDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  task: Task | null;
  context: any | null;
  onClose: () => void;
  loading?: boolean;
}

export const TaskContextDialog: React.FC<TaskContextDialogProps> = ({
  open,
  onOpenChange,
  task,
  context,
  onClose,
  loading = false
}) => {
  // Format context data using helper functions
  const contextDisplay = formatContextDisplay(context?.data);
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[85vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="text-xl text-left">Task Context</DialogTitle>
        </DialogHeader>
        
        <div className="flex-1 overflow-y-auto space-y-4">
          {/* Task Information */}
          <div className="theme-context-section">
            <h4 className="font-medium text-sm mb-1">Task: {task?.title}</h4>
            <p className="text-xs text-base-secondary">ID: {task?.id}</p>
          </div>

          {/* Loading State */}
          {loading && (
            <div className="flex items-center justify-center py-8">
              <div className="text-sm text-base-secondary">Loading context...</div>
            </div>
          )}

          {/* Special Message State (No context available) */}
          {!loading && context && context.message && !context.error && (
            <div className="space-y-4">
              <div className="theme-alert theme-alert-warning">
                <h4 className="font-medium mb-2">{context.message}</h4>
                {context.info && (
                  <p className="text-sm mb-3">{context.info}</p>
                )}
                {context.suggestions && context.suggestions.length > 0 && (
                  <div className="mt-3">
                    <p className="text-sm font-medium mb-1">Suggestions:</p>
                    <ul className="list-disc list-inside text-sm space-y-1">
                      {context.suggestions.map((suggestion: string, index: number) => (
                        <li key={index}>{suggestion}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Error State */}
          {!loading && context && context.error && (
            <div className="theme-alert theme-alert-error">
              <h4 className="font-medium mb-2">{context.message}</h4>
              {context.details && (
                <p className="text-sm">{context.details}</p>
              )}
            </div>
          )}

          {/* Context Content */}
          {!loading && context && !context.error && !context.message && (
            <div className="space-y-4">
              {/* Context Summary */}
              {context.metadata && (
                <div>
                  <h4 className="font-semibold text-sm mb-3 text-base-primary">Context Metadata</h4>
                  <div className="theme-context-metadata">
                    <pre className="text-xs overflow-x-auto whitespace-pre-wrap text-base-primary">
                      {JSON.stringify(context.metadata, null, 2)}
                    </pre>
                  </div>
                </div>
              )}

              {/* Context Data */}
              {context.data && (
                <div>
                  <h4 className="font-semibold text-sm mb-3 text-base-primary">Context Data</h4>
                  <div className="theme-context-data">
                    <pre className="text-xs overflow-x-auto whitespace-pre-wrap text-base-primary">
                      {JSON.stringify(context.data, null, 2)}
                    </pre>
                  </div>
                </div>
              )}

              {/* Insights */}
              {context.insights && context.insights.length > 0 && (
                <div>
                  <h4 className="font-semibold text-sm mb-3 text-base-primary">Insights</h4>
                  <div className="theme-context-insights">
                    {context.insights.map((insight: any, index: number) => (
                      <div key={index} className="border-l-4 border-base pl-3">
                        <p className="text-sm font-medium text-base-primary">{insight.title || `Insight ${index + 1}`}</p>
                        <p className="text-xs text-base-secondary mt-1">{insight.content}</p>
                        {insight.timestamp && (
                          <p className="text-xs text-base-secondary mt-1">
                            {new Date(insight.timestamp).toLocaleString()}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Completion Summary - Enhanced Display */}
              {contextDisplay.completionSummary && (
                <div>
                  <h4 className="font-semibold text-sm mb-3 text-base-primary">
                    Completion Summary{contextDisplay.isLegacy ? ' (Legacy Format)' : ''}
                  </h4>
                  <div className={`${contextDisplay.isLegacy ? 'theme-alert theme-alert-warning' : 'theme-context-completion'}`}>
                    <p className="text-sm whitespace-pre-wrap text-base-primary">{contextDisplay.completionSummary}</p>
                    {contextDisplay.completionPercentage && (
                      <div className="mt-2 pt-2 border-t border-base">
                        <span className="text-xs text-base-secondary">Completion: </span>
                        <span className="text-xs font-medium text-base-primary">{contextDisplay.completionPercentage}%</span>
                      </div>
                    )}
                    {contextDisplay.isLegacy && (
                      <p className="text-xs text-base-secondary mt-2 italic">
                        Note: This is using the legacy completion_summary format
                      </p>
                    )}
                  </div>
                </div>
              )}

              {/* Task Status from Metadata */}
              {contextDisplay.taskStatus && (
                <div>
                  <h4 className="font-semibold text-sm mb-3 text-base-primary">Task Status</h4>
                  <div className="theme-context-metadata">
                    <span className="theme-badge theme-badge-primary">
                      {contextDisplay.taskStatus}
                    </span>
                  </div>
                </div>
              )}

              {/* Testing Notes from Next Steps */}
              {contextDisplay.testingNotes.length > 0 && (
                <div>
                  <h4 className="font-semibold text-sm mb-3 text-base-primary">Testing Notes & Next Steps</h4>
                  <div className="theme-context-insights">
                    {contextDisplay.testingNotes.map((step: string, index: number) => (
                      <div key={index} className="border-l-4 border-base pl-3">
                        <p className="text-sm text-base-primary">{step}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Progress History */}
              {context.progress && Array.isArray(context.progress) && context.progress.length > 0 && (
                <div>
                  <h4 className="font-semibold text-sm mb-3 text-base-primary">Progress History</h4>
                  <div className="theme-context-progress">
                    {context.progress.map((progress: any, index: number) => (
                      <div key={index} className="border-l-4 border-base pl-3">
                        <p className="text-sm text-base-primary">{progress.content}</p>
                        {progress.timestamp && (
                          <p className="text-xs text-base-secondary mt-1">
                            {new Date(progress.timestamp).toLocaleString()}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Raw Context */}
              <div>
                <h4 className="font-semibold text-sm mb-3 text-base-primary">Complete Context (Raw JSON)</h4>
                <div className="theme-context-raw">
                  <pre className="text-xs overflow-x-auto whitespace-pre-wrap max-h-96 text-base-primary">
                    {JSON.stringify(context, null, 2)}
                  </pre>
                </div>
              </div>
            </div>
          )}

          {/* No Context */}
          {!loading && !context && (
            <div className="flex items-center justify-center py-8">
              <div className="text-center">
                <p className="text-sm text-base-secondary mb-2">No context data available</p>
                <p className="text-xs text-base-secondary">Complete the task or update it to create context</p>
              </div>
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

export default TaskContextDialog;