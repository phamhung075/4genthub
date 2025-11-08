import { useState } from "react";
import { Project } from "../../../api";
import type {
  ProjectDialogType,
  UseProjectDialogsReturn
} from "../../../types/hookTypes";
import type { ProjectFormData, DeleteBranchDialogState } from "../../../types/componentTypes";

export const useProjectDialogs = (): UseProjectDialogsReturn => {
  const [showCreate, setShowCreate] = useState(false);
  const [showEdit, setShowEdit] = useState<Project | null>(null);
  const [showDelete, setShowDelete] = useState<Project | null>(null);
  const [showCreateBranch, setShowCreateBranch] = useState<Project | null>(null);
  const [showDeleteBranch, setShowDeleteBranch] = useState<DeleteBranchDialogState | null>(null);
  const [form, setForm] = useState<ProjectFormData>({ name: "", description: "" });
  const [saving, setSaving] = useState(false);

  const openCreateDialog = () => {
    setForm({ name: "", description: "" });
    setShowCreate(true);
  };

  const openEditDialog = (project: Project) => {
    setForm({ name: project.name, description: project.description || "" });
    setShowEdit(project);
  };

  const openDeleteDialog = (project: Project) => {
    setShowDelete(project);
  };

  const openCreateBranchDialog = (project: Project) => {
    setForm({ name: "", description: "" });
    setShowCreateBranch(project);
  };

  const openDeleteBranchDialog = (dialogState: DeleteBranchDialogState) => {
    setShowDeleteBranch(dialogState);
  };

  const closeDialog = (type: ProjectDialogType) => {
    switch (type) {
      case 'create':
        setShowCreate(false);
        break;
      case 'edit':
        setShowEdit(null);
        break;
      case 'delete':
        setShowDelete(null);
        break;
      case 'createBranch':
        setShowCreateBranch(null);
        break;
      case 'deleteBranch':
        setShowDeleteBranch(null);
        break;
    }
    setForm({ name: "", description: "" });
  };

  const updateForm = (updates: Partial<ProjectFormData>) => {
    setForm(prev => ({ ...prev, ...updates }));
  };

  return {
    showCreate,
    showEdit,
    showDelete,
    showCreateBranch,
    showDeleteBranch,
    form,
    saving,
    setSaving,
    openCreateDialog,
    openEditDialog,
    openDeleteDialog,
    openCreateBranchDialog,
    openDeleteBranchDialog,
    closeDialog,
    updateForm,
    setForm,
  };
};