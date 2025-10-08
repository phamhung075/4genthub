import { Eye, Trash2 } from "lucide-react";
import React, { useEffect, useRef } from "react";
import { cn } from "../../../lib/utils";
import { ShimmerBadge } from "../../ui/shimmer-badge";
import { ShimmerButton } from "../../ui/shimmer-button";
import { animationFactory, AnimationType } from "../../../services/AnimationFactory";
import type { BranchSummary } from "../../../types";

interface BranchItemProps {
  branch: BranchSummary;
  projectId: string;
  selected: string | null;
  isNew: boolean;
  isFadingOut: boolean;
  isDeleting: boolean;
  taskCount: number;
  isAnimatingCount: 'up' | 'down' | null;
  onSelect: (projectId: string, branchId: string) => void;
  onShowDetails?: (project: any, branch: any) => void;
  onDelete: (data: { project: any; branch: any }) => void;
  project: any;
}

export const BranchItem: React.FC<BranchItemProps> = ({
  branch,
  projectId,
  selected,
  isNew,
  isFadingOut,
  isDeleting,
  taskCount,
  isAnimatingCount,
  onSelect,
  onShowDetails,
  onDelete,
  project,
}) => {
  const elementRef = useRef<HTMLDivElement>(null);

  // Register element with AnimationFactory on mount
  useEffect(() => {
    if (elementRef.current) {
      animationFactory.registerElement(branch.id, elementRef.current, {
        onAnimationStart: (type) => {
          console.log(`🎬 Branch animation started: ${type} for ${branch.id}`);
        },
        onAnimationEnd: (type) => {
          console.log(`🎬 Branch animation complete: ${type} for ${branch.id}`);
        }
      });

      console.log(`✅ Registered branch element with AnimationFactory: ${branch.id}`);
    }

    return () => {
      animationFactory.unregisterElement(branch.id);
      console.log(`🗑️ Unregistered branch element from AnimationFactory: ${branch.id}`);
    };
  }, [branch.id]);

  const isSelected = selected === `${projectId}:${branch.id}`;

  return (
    <li key={branch.id}>
      <div
        ref={elementRef}
        data-branch-id={branch.id}
        className={cn(
          "group relative flex items-center gap-1 transition-all duration-300 ease-in-out",
          // Fade-in animation for new branches
          isNew && "opacity-0 -translate-x-2.5",
          !isNew && "opacity-100 translate-x-0",
          // Fade-out animation for deleting branches
          isFadingOut && "opacity-0 -translate-x-2.5 pointer-events-none",
          // Loading state for deletion process
          isDeleting && !isFadingOut && "opacity-50 pointer-events-none"
        )}
      >
        <span className="text-muted-foreground">—</span>
        <ShimmerButton
          size="sm"
          variant={isSelected ? "default" : "ghost"}
          className={cn(
            "flex-1 justify-start text-xs text-left",
            isSelected && "bg-blue-50 dark:bg-blue-900/20 border-2 border-blue-300 dark:border-blue-700"
          )}
          onClick={() => {
            onSelect && onSelect(projectId, branch.id);
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
        <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity ml-2 shrink-0">
          <ShimmerButton
            size="icon"
            variant="ghost"
            className="h-6 w-6"
            onClick={() => onShowDetails && onShowDetails(project, branch)}
            aria-label="View Branch Details"
            title="View Branch Details"
          >
            <Eye className="w-3 h-3" />
          </ShimmerButton>
          {(branch.git_branch_name || branch.name) !== 'main' && (
            <ShimmerButton
              size="icon"
              variant="ghost"
              className="h-6 w-6"
              onClick={() => onDelete({ project, branch })}
              disabled={isDeleting}
              aria-label={isDeleting ? "Deleting Branch..." : "Delete Branch"}
            >
              {isDeleting ? (
                <div className="animate-spin h-3 w-3 border-2 border-destructive border-t-transparent rounded-full" />
              ) : (
                <Trash2 className="w-3 h-3 text-destructive" />
              )}
            </ShimmerButton>
          )}
        </div>
      </div>
    </li>
  );
};
