import React from "react";
import { Project } from "../../../api";
import { BranchSummary } from "../../../types";
import type { ProjectListContentProps } from "../../../types/componentTypes";
import { BranchItem } from "./BranchItem";
import { ProjectItem } from "./ProjectItem";

export const ProjectListContent: React.FC<ProjectListContentProps> = ({
  projects,
  branchSummaries,
  taskCounts,
  openProjects,
  selected,
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
            <ProjectItem
              project={project}
              isOpen={openProjects[project.id]}
              onToggle={onToggleProject}
              onShowDetails={onShowProjectDetails}
              onCreateBranch={onCreateBranch}
              onEdit={onEditProject}
              onDelete={onDeleteProject}
            />
            <ul className="flex flex-col gap-1 ml-8 mt-1" style={{ display: openProjects[project.id] ? 'flex' : 'none' }}>
              {branchSummaries[project.id] ? (
                // Use optimized branch summaries if available
                branchSummaries[project.id].map((branch) => (
                  <BranchItem
                    key={branch.id}
                    branch={branch}
                    projectId={project.id}
                    selected={selected}
                    taskCount={taskCounts[branch.id] ?? 0}
                    isAnimatingCount={animatingCounts.get(branch.id) || null}
                    onSelect={onSelectBranch}
                    onShowDetails={onShowBranchDetails}
                    onDelete={onDeleteBranch}
                    project={project}
                  />
                ))
              ) : project.git_branchs ? (
                // Fallback to original branch data if optimized not loaded
                Object.values(project.git_branchs as Record<string, any>).map((tree: any) => (
                  <BranchItem
                    key={tree.id}
                    branch={tree}
                    projectId={project.id}
                    selected={selected}
                    taskCount={tree.task_count !== undefined ? tree.task_count : (taskCounts[tree.id as string] ?? 0)}
                    isAnimatingCount={animatingCounts.get(tree.id) || null}
                    onSelect={onSelectBranch}
                    onShowDetails={onShowBranchDetails}
                    onDelete={onDeleteBranch}
                    project={project}
                  />
                ))
              ) : null}
            </ul>
          </li>
        ))}
      </ul>
    </>
  );
};