import { ChevronDown, ChevronRight, Eye, Folder, GitBranchPlus, Pencil, Trash2 } from "lucide-react";
import React from "react";
import { Project } from "../../../api";
import { cn } from "../../../lib/utils";
import { BranchSummary } from "../../../types";
import { ShimmerBadge } from "../../ui/shimmer-badge";
import { ShimmerButton } from "../../ui/shimmer-button";
import type { ProjectListContentProps } from "../../../types/componentTypes";

export const ProjectListContent: React.FC<ProjectListContentProps> = ({
  projects,
  branchSummaries,
  taskCounts,
  openProjects,
  selected,
  newBranches,
  fadingOutBranches,
  deletingBranches,
  animatingCounts,
  onToggleProject,
  onSelectBranch,
  onShowProjectDetails,
  onShowBranchDetails,
  onCreateBranch,
  onEditProject,
  onDeleteProject,
  onDeleteBranch,
}) => {
  if (projects.length === 0) {
    return <div className="text-xs text-muted-foreground">No projects found.</div>;
  }

  return (
    <>
      {/* CSS for count change animation */}
      <style>{`
        @keyframes countPulse {
          0%, 100% {
            transform: scale(1);
            box-shadow: 0 0 0 0 rgba(59, 130, 246, 0);
          }
          25% {
            transform: scale(1.2);
            box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.3);
          }
          50% {
            transform: scale(1.1);
            box-shadow: 0 0 0 8px rgba(59, 130, 246, 0);
          }
        }

        .count-pulse {
          animation: countPulse 0.6s ease-in-out;
        }

        .count-change-up {
          animation: countPulse 0.6s ease-in-out;
          background: linear-gradient(135deg, #10b981 0%, #34d399 100%) !important;
        }

        .count-change-down {
          animation: countPulse 0.6s ease-in-out;
          background: linear-gradient(135deg, #ef4444 0%, #f87171 100%) !important;
        }
      `}</style>

      <ul className="flex flex-col gap-1">
        {projects.map((project) => (
          <li key={project.id}>
            <div className="group relative flex items-center justify-between p-2 rounded-md hover:bg-background-hover transition-colors cursor-pointer">
              <div className="flex items-center gap-2 flex-1" onClick={() => onToggleProject(project.id)}>
                {openProjects[project.id] ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                <Folder className="w-4 h-4" />
                <span className="font-semibold text-sm truncate text-left" title={project.name}>{project.name}</span>
                <div className="flex gap-1 ml-2">
                  {project.git_branchs && Object.keys(project.git_branchs as Record<string, any>).length > 0 && (
                    <ShimmerBadge variant={openProjects[project.id] ? "secondary" : "outline"} className="text-xs">
                      {Object.keys(project.git_branchs as Record<string, any>).length} {Object.keys(project.git_branchs as Record<string, any>).length === 1 ? 'branch' : 'branches'}
                    </ShimmerBadge>
                  )}
                  {(() => {
                    const branches = project.git_branchs as Record<string, any>;
                    const totalTasks = branches ?
                      Object.values(branches).reduce((sum, branch) => sum + ((branch as any).task_count || 0), 0) : 0;
                    return totalTasks > 0 ? (
                      <ShimmerBadge variant="default" className="text-xs">
                        {totalTasks} {totalTasks === 1 ? 'task' : 'tasks'}
                      </ShimmerBadge>
                    ) : null;
                  })()}
                </div>
              </div>
              <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity ml-2 shrink-0">
                <ShimmerButton
                  size="icon"
                  variant="ghost"
                  className="h-7 w-7"
                  aria-label="View Project Details"
                  title="View Project Details"
                  onClick={() => onShowProjectDetails && onShowProjectDetails(project)}
                >
                  <Eye className="w-3 h-3" />
                </ShimmerButton>
                <ShimmerButton size="icon" variant="ghost" className="h-7 w-7" aria-label="Create Branch" onClick={() => onCreateBranch(project)}>
                  <GitBranchPlus className="w-3 h-3" />
                </ShimmerButton>
                <ShimmerButton size="icon" variant="ghost" className="h-7 w-7" aria-label="Edit" onClick={() => onEditProject(project)}>
                  <Pencil className="w-3 h-3" />
                </ShimmerButton>
                <ShimmerButton size="icon" variant="ghost" className="h-7 w-7" aria-label="Delete" onClick={() => onDeleteProject(project)}>
                  <Trash2 className="w-3 h-3 text-destructive" />
                </ShimmerButton>
              </div>
            </div>
            <ul className="flex flex-col gap-1 ml-8 mt-1" style={{ display: openProjects[project.id] ? 'flex' : 'none' }}>
              {branchSummaries[project.id] ? (
                // Use optimized branch summaries if available
                branchSummaries[project.id].map((branch) => (
                  <li key={branch.id}>
                    <div className={cn(
                      "group relative flex items-center gap-1 transition-all duration-300 ease-in-out",
                      // Fade-in animation for new branches
                      newBranches.has(branch.id) && "opacity-0 -translate-x-2.5",
                      !newBranches.has(branch.id) && "opacity-100 translate-x-0",
                      // Fade-out animation for deleting branches
                      fadingOutBranches.has(branch.id) && "opacity-0 -translate-x-2.5 pointer-events-none",
                      // Loading state for deletion process
                      deletingBranches.has(branch.id) && !fadingOutBranches.has(branch.id) && "opacity-50 pointer-events-none"
                    )}>
                      <span className="text-muted-foreground">—</span>
                      <ShimmerButton
                        size="sm"
                        variant={selected === `${project.id}:${branch.id}` ? "default" : "ghost"}
                        className={cn(
                          "flex-1 justify-start text-xs text-left",
                          selected === `${project.id}:${branch.id}` && "bg-blue-50 dark:bg-blue-900/20 border-2 border-blue-300 dark:border-blue-700"
                        )}
                        onClick={() => {
                          onSelectBranch && onSelectBranch(project.id, branch.id);
                        }}
                      >
                        <span className="truncate text-left flex-1">{branch.git_branch_name || branch.name}</span>
                        <div className="flex items-center gap-1">
                          <ShimmerBadge
                            variant="secondary"
                            className={cn(
                              "text-xs",
                              animatingCounts.get(branch.id) === 'up' && "count-change-up",
                              animatingCounts.get(branch.id) === 'down' && "count-change-down",
                              animatingCounts.has(branch.id) && "count-pulse"
                            )}
                          >
                            {taskCounts[branch.id] ?? 0}
                          </ShimmerBadge>
                        </div>
                      </ShimmerButton>
                      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity ml-2 shrink-0">
                        <ShimmerButton
                          size="icon"
                          variant="ghost"
                          className="h-6 w-6"
                          onClick={() => onShowBranchDetails && onShowBranchDetails(project, branch)}
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
                            onClick={() => onDeleteBranch({ project, branch })}
                            disabled={deletingBranches.has(branch.id)}
                            aria-label={deletingBranches.has(branch.id) ? "Deleting Branch..." : "Delete Branch"}
                          >
                            {deletingBranches.has(branch.id) ? (
                              <div className="animate-spin h-3 w-3 border-2 border-destructive border-t-transparent rounded-full" />
                            ) : (
                              <Trash2 className="w-3 h-3 text-destructive" />
                            )}
                          </ShimmerButton>
                        )}
                      </div>
                    </div>
                  </li>
                ))
              ) : project.git_branchs ? (
                // Fallback to original branch data if optimized not loaded
                Object.values(project.git_branchs as Record<string, any>).map((tree: any) => (
                  <li key={tree.id}>
                    <div className={cn(
                      "group relative flex items-center gap-1 transition-all duration-300 ease-in-out",
                      // Fade-in animation for new branches
                      newBranches.has(tree.id) && "opacity-0 -translate-x-2.5",
                      !newBranches.has(tree.id) && "opacity-100 translate-x-0",
                      // Fade-out animation for deleting branches
                      fadingOutBranches.has(tree.id) && "opacity-0 -translate-x-2.5 pointer-events-none",
                      // Loading state for deletion process
                      deletingBranches.has(tree.id) && !fadingOutBranches.has(tree.id) && "opacity-50 pointer-events-none"
                    )}>
                      <span className="text-muted-foreground">—</span>
                      <ShimmerButton
                        size="sm"
                        variant={selected === `${project.id}:${tree.id}` ? "secondary" : "ghost"}
                        className="flex-1 justify-start text-xs text-left"
                        onClick={() => {
                          onSelectBranch && onSelectBranch(project.id, tree.id);
                        }}
                      >
                        <span className="truncate text-left flex-1">{tree.git_branch_name || tree.name}</span>
                        <ShimmerBadge
                          variant="secondary"
                          className={cn(
                            "text-xs ml-2",
                            animatingCounts.get(tree.id) === 'up' && "count-change-up",
                            animatingCounts.get(tree.id) === 'down' && "count-change-down",
                            animatingCounts.has(tree.id) && "count-pulse"
                          )}
                        >
                          {tree.task_count !== undefined ? tree.task_count : (taskCounts[tree.id as string] ?? 0)}
                        </ShimmerBadge>
                      </ShimmerButton>
                      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity ml-2 shrink-0">
                        <ShimmerButton
                          size="icon"
                          variant="ghost"
                          className="h-6 w-6"
                          onClick={() => onShowBranchDetails && onShowBranchDetails(project, tree)}
                          aria-label="View Branch Details"
                          title="View Branch Details"
                        >
                          <Eye className="w-3 h-3" />
                        </ShimmerButton>
                        {(tree.git_branch_name || tree.name) !== 'main' && (
                          <ShimmerButton
                            size="icon"
                            variant="ghost"
                            className="h-6 w-6"
                            onClick={() => onDeleteBranch({ project, branch: tree })}
                            disabled={deletingBranches.has(tree.id)}
                            aria-label={deletingBranches.has(tree.id) ? "Deleting Branch..." : "Delete Branch"}
                          >
                            {deletingBranches.has(tree.id) ? (
                              <div className="animate-spin h-3 w-3 border-2 border-destructive border-t-transparent rounded-full" />
                            ) : (
                              <Trash2 className="w-3 h-3 text-destructive" />
                            )}
                          </ShimmerButton>
                        )}
                      </div>
                    </div>
                  </li>
                ))
              ) : null}
            </ul>
          </li>
        ))}
      </ul>
    </>
  );
};