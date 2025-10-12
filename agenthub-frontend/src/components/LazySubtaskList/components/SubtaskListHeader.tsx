// SubtaskListHeader component - Header section with progress for LazySubtaskList
// Extracted from original LazySubtaskList.tsx during SOLID refactoring

import React from "react";
import { Plus } from "lucide-react";
import { Button } from "../../ui/button";
import { Badge } from "../../ui/badge";

interface ProgressSummary {
  total: number;
  completed: number;
  inProgress: number;
  percentage: number;
}

interface SubtaskListHeaderProps {
  progressSummary: ProgressSummary | null;
  onAddSubtask: () => void;
  isEmpty?: boolean;
}

/**
 * Header component for the subtask list
 * Shows title, progress summary, and add button
 */
export function SubtaskListHeader({
  progressSummary,
  onAddSubtask,
  isEmpty = false
}: SubtaskListHeaderProps) {

  // Empty state header
  if (isEmpty) {
    return (
      <div className="p-6 bg-gradient-to-r from-blue-50/30 to-transparent dark:from-blue-950/20 dark:to-transparent">
        <div className="flex items-center gap-2 mb-4">
          <div className="h-px flex-1 bg-gradient-to-r from-blue-300 to-transparent dark:from-blue-700"></div>
          <span className="text-xs font-medium text-blue-600 dark:text-blue-400 uppercase tracking-wider">
            Subtasks
          </span>
          <div className="h-px flex-1 bg-gradient-to-l from-blue-300 to-transparent dark:from-blue-700"></div>
        </div>

        <div className="text-center text-sm text-blue-600/70 dark:text-blue-400/70 py-4">
          <div className="mb-3">No subtasks found.</div>
          <Button
            variant="outline"
            size="sm"
            className="text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 border-blue-300 hover:bg-blue-50 dark:border-blue-700 dark:hover:bg-blue-950/50 relative z-20"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onAddSubtask();
            }}
          >
            <Plus className="w-3 h-3 mr-1" />
            Add Subtask
          </Button>
        </div>
      </div>
    );
  }

  // Header with data
  return (
    <div className="space-y-3">
      {/* Subtask Section Header */}
      <div className="flex items-center gap-2 mb-2">
        <div className="h-px flex-1 bg-gradient-to-r from-blue-300 to-transparent dark:from-blue-700"></div>
        <span className="text-xs font-medium text-blue-600 dark:text-blue-400 uppercase tracking-wider">
          Subtasks
        </span>
        <div className="h-px flex-1 bg-gradient-to-l from-blue-300 to-transparent dark:from-blue-700"></div>
      </div>

      {/* Progress Summary */}
      {progressSummary && (
        <div className="flex items-center gap-4 p-3 bg-white/70 dark:bg-gray-800/70 rounded-lg border border-blue-200 dark:border-blue-800">
          <div className="text-sm">
            <strong className="text-blue-700 dark:text-blue-300">Progress:</strong>{" "}
            {progressSummary.completed}/{progressSummary.total} completed ({progressSummary.percentage}%)
          </div>

          {progressSummary.inProgress > 0 && (
            <Badge variant="secondary" className="text-xs">
              {progressSummary.inProgress} in progress
            </Badge>
          )}

          <div className="flex-1">
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div
                className="h-2 rounded-full transition-all duration-300 relative overflow-hidden group"
                style={{ width: `${progressSummary.percentage}%` }}
              >
                {/* Background gradient - lighter blue for subtasks */}
                <div className="absolute inset-0 bg-gradient-to-r from-blue-300 to-blue-500" />

                {/* Animated shimmer overlay */}
                <div
                  className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent"
                  style={{
                    backgroundSize: '200% 100%',
                    animation: 'shimmer-progress 2s infinite linear'
                  }}
                />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default SubtaskListHeader;