import { ChevronDown, ChevronRight, Eye, Folder, GitBranchPlus, Pencil, Trash2 } from "lucide-react";
import React from "react";
import { Project } from "../../../api";
import { cn } from "../../../lib/utils";
import { ShimmerBadge } from "../../ui/shimmer-badge";
import { ShimmerButton } from "../../ui/shimmer-button";
import { useProjectAnimation } from "../../../hooks/useProjectAnimation";

interface ProjectItemProps {
  project: Project;
  isOpen: boolean;
  onToggle: (projectId: string) => void;
  onShowDetails?: (project: Project) => void;
  onCreateBranch: (project: Project) => void;
  onEdit: (project: Project) => void;
  onDelete: (project: Project) => void;
}

export const ProjectItem: React.FC<ProjectItemProps> = ({
  project,
  isOpen,
  onToggle,
  onShowDetails,
  onCreateBranch,
  onEdit,
  onDelete,
}) => {
  // Use animation hook for this project
  const {
    isVisible,
    animationClass,
    desktopElementRef,
  } = useProjectAnimation(project, false); // Projects are desktop-only for now

  // Don't render if marked as deleted
  if (!isVisible) {
    return null;
  }

  // Calculate total tasks across all branches
  const branches = project.git_branchs as Record<string, any>;
  const branchCount = branches ? Object.keys(branches).length : 0;
  const totalTasks = branches
    ? Object.values(branches).reduce((sum, branch) => sum + ((branch as any).task_count || 0), 0)
    : 0;

  return (
    <div
      ref={desktopElementRef}
      data-project-id={project.id}
      className={cn(
        "group relative flex items-center justify-between p-2 rounded-md hover:bg-background-hover transition-colors cursor-pointer",
        animationClass
      )}
    >
      <div className="flex items-center gap-2 flex-1 min-w-0" onClick={() => onToggle(project.id)}>
        {isOpen ? <ChevronDown className="w-4 h-4 shrink-0" /> : <ChevronRight className="w-4 h-4 shrink-0" />}
        <Folder className="w-4 h-4 shrink-0" />
        <span className="font-semibold text-sm truncate text-left" title={project.name}>
          {project.name}
        </span>
        <div className="flex gap-1 ml-2 shrink-0">
          {branchCount > 0 && (
            <ShimmerBadge variant={isOpen ? "secondary" : "outline"} className="text-xs">
              {branchCount} {branchCount === 1 ? 'branch' : 'branches'}
            </ShimmerBadge>
          )}
          {totalTasks > 0 && (
            <ShimmerBadge variant="default" className="text-xs">
              {totalTasks} {totalTasks === 1 ? 'task' : 'tasks'}
            </ShimmerBadge>
          )}
        </div>
      </div>
      {/* Reachable without a mouse: a touch device has no hover, so the actions are visible by
          default and only fade until hover on a device that HAS hover (pointer or keyboard). */}
      <div className="flex gap-1 transition-opacity ml-2 shrink-0 opacity-100 [@media(hover:hover)]:opacity-0 [@media(hover:hover)]:group-hover:opacity-100 [@media(hover:hover)]:group-focus-within:opacity-100">
        {onShowDetails && (
          <ShimmerButton
            size="icon"
            variant="ghost"
            className="h-10 w-10"
            aria-label="View Project Details"
            title="View Project Details"
            onClick={() => onShowDetails(project)}
          >
            <Eye className="h-4 w-4" />
          </ShimmerButton>
        )}
        <ShimmerButton
          size="icon"
          variant="ghost"
          className="h-10 w-10"
          aria-label="Create Branch"
          onClick={() => onCreateBranch(project)}
        >
          <GitBranchPlus className="h-4 w-4" />
        </ShimmerButton>
        <ShimmerButton
          size="icon"
          variant="ghost"
          className="h-10 w-10"
          aria-label="Edit"
          onClick={() => onEdit(project)}
        >
          <Pencil className="h-4 w-4" />
        </ShimmerButton>
        <ShimmerButton
          size="icon"
          variant="ghost"
          className="h-10 w-10"
          aria-label="Delete"
          onClick={() => onDelete(project)}
        >
          <Trash2 className="h-4 w-4 text-destructive" />
        </ShimmerButton>
      </div>
    </div>
  );
};
