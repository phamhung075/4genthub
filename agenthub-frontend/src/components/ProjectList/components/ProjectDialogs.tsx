import React from "react";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "../../ui/dialog";
import { Input } from "../../ui/input";
import { ShimmerButton } from "../../ui/shimmer-button";
import type { ProjectDialogsProps } from "../../../types/componentTypes";

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
            {showDelete && showDelete.git_branchs && Object.keys(showDelete.git_branchs as Record<string, any>).length > 1 && (
              <p className="text-sm text-amber-600 dark:text-amber-400">
                ⚠️ This project has {Object.keys(showDelete.git_branchs as Record<string, any>).length} branches. You must delete all branches except "main" before deleting the project.
              </p>
            )}
            {showDelete && showDelete.git_branchs && (() => {
              const branches = showDelete.git_branchs as Record<string, any>;
              const totalTasks = Object.values(branches).reduce((sum, branch) => sum + ((branch as any).task_count || 0), 0);
              return totalTasks > 0 ? (
                <p className="text-sm text-amber-600 dark:text-amber-400">
                  ⚠️ This project contains {totalTasks} task{totalTasks === 1 ? '' : 's'}. All tasks must be deleted first.
                </p>
              ) : null;
            })()}
            <p className="text-sm text-muted-foreground">This action cannot be undone.</p>
          </div>
          <DialogFooter className="mt-3">
            <ShimmerButton variant="secondary" onClick={onCloseDelete} size="sm">Cancel</ShimmerButton>
            <ShimmerButton
              variant={
                (showDelete && showDelete.git_branchs && Object.keys(showDelete.git_branchs as Record<string, any>).length > 1) ||
                (showDelete && showDelete.git_branchs && Object.values(showDelete.git_branchs as Record<string, any>).reduce((sum, branch) => sum + ((branch as any).task_count || 0), 0) > 0)
                  ? "secondary"
                  : "destructive"
              }
              onClick={onDeleteProject}
              size="sm"
              disabled={
                saving ||
                Boolean(showDelete && showDelete.git_branchs && Object.keys(showDelete.git_branchs as Record<string, any>).length > 1) ||
                Boolean(showDelete && showDelete.git_branchs && Object.values(showDelete.git_branchs as Record<string, any>).reduce((sum, branch) => sum + ((branch as any).task_count || 0), 0) > 0)
              }
              title={
                (showDelete && showDelete.git_branchs && Object.keys(showDelete.git_branchs as Record<string, any>).length > 1)
                  ? "Delete all branches except 'main' first"
                  : (showDelete && showDelete.git_branchs && Object.values(showDelete.git_branchs as Record<string, any>).reduce((sum, branch) => sum + ((branch as any).total_tasks || 0), 0) > 0)
                    ? "Delete all tasks first"
                    : undefined
              }
              className={
                (showDelete && showDelete.git_branchs && Object.keys(showDelete.git_branchs as Record<string, any>).length > 1) ||
                (showDelete && showDelete.git_branchs && Object.values(showDelete.git_branchs as Record<string, any>).reduce((sum, branch) => sum + ((branch as any).task_count || 0), 0) > 0)
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
            <p className="text-sm">Are you sure you want to delete the branch <strong>{showDeleteBranch?.branch.git_branch_name || showDeleteBranch?.branch.name}</strong> from project <strong>{showDeleteBranch?.project.name}</strong>?</p>
            {showDeleteBranch && (showDeleteBranch.branch.task_count || 0) > 0 && (
              <p className="text-sm text-destructive">
                Warning: This branch contains {showDeleteBranch.branch.task_count || 0} task(s) that will also be deleted.
              </p>
            )}
            <p className="text-sm text-muted-foreground">This action cannot be undone.</p>
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