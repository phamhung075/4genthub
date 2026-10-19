import { Eye, Trash2 } from "lucide-react";
import React from "react";
import { cn } from "../../../lib/utils";
import { ShimmerBadge } from "../../ui/shimmer-badge";
import { ShimmerButton } from "../../ui/shimmer-button";
import { useBranchAnimation } from "../../../hooks/useBranchAnimation";
import type { BranchLike, Project } from "../../../types";

interface BranchItemProps {
  branch: BranchLike;
  projectId: string;
  selected: string | null;
  taskCount: number;
  isAnimatingCount: 'up' | 'down' | null;
  onSelect: (projectId: string, branchId: string) => void;
  onShowDetails?: (project: Project, branch: BranchLike) => void;
  onDelete: (data: { project: Project; branch: BranchLike }) => void;
  project: Project;
}

export const BranchItem: React.FC<BranchItemProps> = ({
  branch,
  projectId,
  selected,
  taskCount,
  isAnimatingCount,
  onSelect,
  onShowDetails,
  onDelete,
  project,
}) => {
  // Use animation hook for this branch
  const {
    isVisible,
    animationClass,
    desktopElementRef,
  } = useBranchAnimation(branch, false);

  const isSelected = selected === `${projectId}:${branch.id}`;

  // Don't render if marked as deleted
  if (!isVisible) {
    return null;
  }

  return (
    <li key={branch.id}>
      <div
        ref={desktopElementRef}
        data-branch-id={branch.id}
        className={cn(
          "group relative flex items-center gap-1",
          animationClass
        )}
      >
        <span className="text-muted-foreground">—</span>
        <ShimmerButton
          size="sm"
          variant={isSelected ? "default" : "ghost"}
          className={cn(
            "flex-1 min-w-0 justify-start text-xs text-left",
            isSelected && "bg-blue-50 dark:bg-blue-900/20 border-2 border-blue-300 dark:border-blue-700"
          )}
          onClick={() => {
            onSelect(projectId, branch.id);
          }}
        >
          <span className="truncate text-left flex-1">{branch.git_branch_name || branch.name}</span>
          <div className="flex items-center gap-1">
            <ShimmerBadge
              variant="secondary"
              className={cn(
                "text-xs",
                isAnimatingCount === 'up' && "count-change-up",
                isAnimatingCount === 'down' && "count-change-down",
                isAnimatingCount && "count-pulse"
              )}
            >
              {taskCount}
            </ShimmerBadge>
          </div>
        </ShimmerButton>
        {/* Same rule as the project row: visible without hover, faded only where a pointer exists. */}
        <div className="flex gap-1 transition-opacity ml-2 shrink-0 opacity-100 [@media(hover:hover)]:opacity-0 [@media(hover:hover)]:group-hover:opacity-100 [@media(hover:hover)]:group-focus-within:opacity-100">
          <ShimmerButton
            size="icon"
            variant="ghost"
            className="h-10 w-10"
            onClick={() => onShowDetails && onShowDetails(project, branch)}
            aria-label="View Branch Details"
            title="View Branch Details"
          >
            <Eye className="w-4 h-4" />
          </ShimmerButton>
          {(branch.git_branch_name || branch.name) !== 'main' && (
            <ShimmerButton
              size="icon"
              variant="ghost"
              className="h-10 w-10"
              onClick={() => onDelete({ project, branch })}
              aria-label="Delete Branch"
            >
              <Trash2 className="w-4 h-4 text-destructive" />
            </ShimmerButton>
          )}
        </div>
      </div>
    </li>
  );
};
