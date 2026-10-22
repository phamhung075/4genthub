import React from "react";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "../../ui/dialog";
import { Input } from "../../ui/input";
import { ShimmerButton } from "../../ui/shimmer-button";
import type { ProjectDialogsProps } from "../../../types/componentTypes";
import type { Branch } from "../../../types";

// The API decorates nested branch records with task counts that `Branch` does
// not model yet.
type BranchWithCounts = Branch & { task_count?: number; total_tasks?: number };

// `DeleteBranchDialogState.branch` is typed `unknown` in componentTypes; the
// dialog is only ever opened from the branch row that was clicked.
interface DeleteBranchTarget {
  name?: string;
  git_branch_name?: string;
  task_count?: number;
}

export const ProjectDialogs: React.FC<ProjectDialogsProps> = ({
  showCreate,
  showEdit,
  showDelete,
  showCreateBranch,
  showDeleteBranch,
  form,
  saving,
  onCloseCreate,
  onCloseEdit,
  onCloseDelete,
  onCloseCreateBranch,
  onCloseDeleteBranch,
  onFormChange,
  onCreateProject,
  onEditProject,
  onDeleteProject,
  onCreateBranch,
  onDeleteBranch,
}) => {
  const deleteBranches = showDelete?.git_branchs as Record<string, BranchWithCounts> | undefined;
  const deleteBranchCount = deleteBranches ? Object.keys(deleteBranches).length : 0;
  const deleteProjectTaskCount = deleteBranches
    ? Object.values(deleteBranches).reduce((sum, branch) => sum + (branch.task_count || 0), 0)
    : 0;
  const deleteProjectTotalTasks = deleteBranches
    ? Object.values(deleteBranches).reduce((sum, branch) => sum + (branch.total_tasks || 0), 0)
    : 0;

  const deleteBranch = showDeleteBranch?.branch as DeleteBranchTarget | undefined;
  const deleteBranchName = deleteBranch?.git_branch_name || deleteBranch?.name;
  const deleteBranchTaskCount = deleteBranch?.task_count || 0;

  return (
    <>
      {/* Create Project Dialog */}
      <Dialog open={showCreate} onOpenChange={(open) => !open && onCloseCreate()}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-base">New Project</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-2">
            <Input
              placeholder="Project name"
              value={form.name}
              onChange={(e) => onFormChange(e, 'name')}
              autoFocus
              className="h-8 text-sm"
            />
            <Input
              placeholder="Description (optional)"
              value={form.description}
              onChange={(e) => onFormChange(e, 'description')}
              className="h-8 text-sm"
            />
          </div>
          <DialogFooter className="mt-3">
            <ShimmerButton variant="secondary" onClick={onCloseCreate} size="sm">Cancel</ShimmerButton>
            <ShimmerButton variant="default" onClick={onCreateProject} disabled={!form.name.trim()} size="sm">
              Create
            </ShimmerButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Create Branch Dialog */}
      <Dialog open={!!showCreateBranch} onOpenChange={(v) => !v && onCloseCreateBranch()}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-base">New Branch in {showCreateBranch?.name}</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-2">
            <Input
              placeholder="Branch name"
              value={form.name}
              onChange={(e) => onFormChange(e, 'name')}
              autoFocus
              disabled={saving}
              className="h-8 text-sm"
            />
            <Input
              placeholder="Description (optional)"
              value={form.description}
              onChange={(e) => onFormChange(e, 'description')}
              disabled={saving}
              className="h-8 text-sm"
            />
          </div>
          <DialogFooter className="mt-3">
            <ShimmerButton variant="secondary" onClick={onCloseCreateBranch} disabled={saving} size="sm">Cancel</ShimmerButton>
            <ShimmerButton onClick={onCreateBranch} disabled={saving || !form.name.trim()} size="sm">
              {saving ? "Creating..." : "Create"}
            </ShimmerButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Project Dialog */}
      <Dialog open={!!showEdit} onOpenChange={(v: boolean) => { if (!v) onCloseEdit(); }}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-base">Edit Project</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-2">
            <Input
              placeholder="Project name"
              value={form.name}
              onChange={(e) => onFormChange(e, 'name')}
              autoFocus
              className="h-8 text-sm"
            />
            <Input
              placeholder="Description (optional)"
              value={form.description}
              onChange={(e) => onFormChange(e, 'description')}
              className="h-8 text-sm"
            />
          </div>
          <DialogFooter className="mt-3">
            <ShimmerButton variant="secondary" onClick={onCloseEdit} size="sm">Cancel</ShimmerButton>
            <ShimmerButton variant="default" onClick={onEditProject} disabled={!form.name.trim()} size="sm">
              Save
            </ShimmerButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Project Dialog */}
      <Dialog open={!!showDelete} onOpenChange={(v: boolean) => { if (!v) onCloseDelete(); }}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-base">Delete Project</DialogTitle>
          </DialogHeader>
          <div className="space-y-2">
            <p className="text-sm">Are you sure you want to delete the project <strong>{showDelete?.name}</strong>?</p>
            {deleteBranchCount > 1 && (
              <p className="text-sm text-amber-600 dark:text-amber-400">
                ⚠️ This project has {deleteBranchCount} branches. You must delete all branches except "main" before deleting the project.
              </p>
            )}
            {deleteProjectTaskCount > 0 && (
              <p className="text-sm text-amber-600 dark:text-amber-400">
                ⚠️ This project contains {deleteProjectTaskCount} task{deleteProjectTaskCount === 1 ? '' : 's'}. All tasks must be deleted first.
              </p>
            )}
            <p className="text-sm text-base-secondary">This action cannot be undone.</p>
          </div>
          <DialogFooter className="mt-3">
            <ShimmerButton variant="secondary" onClick={onCloseDelete} size="sm">Cancel</ShimmerButton>
            <ShimmerButton
              variant={
                deleteBranchCount > 1 || deleteProjectTaskCount > 0
                  ? "secondary"
                  : "destructive"
              }
              onClick={onDeleteProject}
              size="sm"
              disabled={
                saving ||
                deleteBranchCount > 1 ||
                deleteProjectTaskCount > 0
              }
              title={
                deleteBranchCount > 1
                  ? "Delete all branches except 'main' first"
                  : deleteProjectTotalTasks > 0
                    ? "Delete all tasks first"
                    : undefined
              }
              className={
                deleteBranchCount > 1 || deleteProjectTaskCount > 0
                  ? "opacity-50 cursor-not-allowed"
                  : ""
              }
            >
              {saving ? "Deleting..." : "Delete Project"}
            </ShimmerButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Branch Dialog */}
      <Dialog open={!!showDeleteBranch} onOpenChange={(v: boolean) => { if (!v) onCloseDeleteBranch(); }}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-base">Delete Branch</DialogTitle>
          </DialogHeader>
          <div className="space-y-2">
            <p className="text-sm">Are you sure you want to delete the branch <strong>{deleteBranchName}</strong> from project <strong>{showDeleteBranch?.project.name}</strong>?</p>
            {deleteBranchTaskCount > 0 && (
              <p className="text-sm text-error">
                Warning: This branch contains {deleteBranchTaskCount} task(s) that will also be deleted.
              </p>
            )}
            <p className="text-sm text-base-secondary">This action cannot be undone.</p>
          </div>
          <DialogFooter className="mt-3">
            <ShimmerButton variant="secondary" onClick={onCloseDeleteBranch} size="sm" disabled={saving}>
              Cancel
            </ShimmerButton>
            <ShimmerButton
              variant="destructive"
              onClick={onDeleteBranch}
              size="sm"
              disabled={saving}
            >
              {saving ? "Deleting..." : "Delete Branch"}
            </ShimmerButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};
