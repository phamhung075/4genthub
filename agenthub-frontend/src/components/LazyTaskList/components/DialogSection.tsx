import React, { lazy, Suspense } from 'react';
import { TaskSummary } from "../../../types/taskTypes";

// Lazy-loaded dialog components
const TaskDetailsDialog = lazy(() => import("../../TaskDetailsDialog"));
const TaskEditDialog = lazy(() => import("../../TaskEditDialog"));
const AgentAssignmentDialog = lazy(() => import("../../AgentAssignmentDialog"));
const AgentInfoDialog = lazy(() => import("../../AgentInfoDialog"));
const TaskContextDialog = lazy(() => import("../../TaskContextDialog"));
const DeleteConfirmDialog = lazy(() => import("../../DeleteConfirmDialog"));

interface DialogSectionProps {
  activeDialog: {
    type: 'details' | 'edit' | 'create' | 'assign' | 'context' | 'complete' | 'delete' | 'agent-response' | 'agent-info' | null;
    taskId?: string;
    data?: any;
  };
  fullTasks: Map<string, any>;
  taskSummaries: TaskSummary[];
  agents: any[];
  availableAgents: string[];
  saving: boolean;
  onCloseDialog: () => void;
  onOpenDialog: (type: string, taskId?: string, data?: any) => void;
  onUpdateTask: (taskId: string, updates: any) => Promise<void>;
  onCreateTask: (taskData: any) => Promise<void>;
  onDeleteTask: (taskId: string) => Promise<void>;
}

export const DialogSection: React.FC<DialogSectionProps> = ({
  activeDialog,
  fullTasks,
  taskSummaries,
  agents,
  availableAgents,
  saving,
  onCloseDialog,
  onOpenDialog,
  onUpdateTask,
  onCreateTask,
  onDeleteTask
}) => {
  return (
    <Suspense fallback={null}>
      {activeDialog.type === 'details' && activeDialog.taskId && (
        <TaskDetailsDialog
          open={true}
          onOpenChange={onCloseDialog}
          task={fullTasks.get(activeDialog.taskId) || null}
          onClose={onCloseDialog}
          onAgentClick={(_agentName, task) => {
            onCloseDialog();
            onOpenDialog('assign', task.id);
          }}
        />
      )}

      {activeDialog.type === 'edit' && activeDialog.taskId && (
        <TaskEditDialog
          open={true}
          onOpenChange={onCloseDialog}
          task={fullTasks.get(activeDialog.taskId) || null}
          onClose={onCloseDialog}
          onSave={(updates) => onUpdateTask(activeDialog.taskId!, updates)}
          saving={saving}
        />
      )}

      {activeDialog.type === 'create' && (
        <TaskEditDialog
          open={true}
          onOpenChange={onCloseDialog}
          task={null}
          onClose={onCloseDialog}
          onSave={onCreateTask}
          saving={saving}
        />
      )}

      {activeDialog.type === 'assign' && activeDialog.taskId && (
        <AgentAssignmentDialog
          open={true}
          onOpenChange={onCloseDialog}
          task={fullTasks.get(activeDialog.taskId) || null}
          onClose={onCloseDialog}
          onAssign={() => {}}
          agents={agents}
          availableAgents={availableAgents}
          saving={false}
        />
      )}

      {activeDialog.type === 'context' && activeDialog.taskId && (
        <TaskContextDialog
          open={true}
          onOpenChange={onCloseDialog}
          task={fullTasks.get(activeDialog.taskId) || null}
          context={null}
          onClose={onCloseDialog}
          loading={false}
        />
      )}

      {activeDialog.type === 'delete' && activeDialog.taskId && (
        <DeleteConfirmDialog
          open={true}
          onOpenChange={onCloseDialog}
          onConfirm={() => onDeleteTask(activeDialog.taskId!)}
          title="Delete Task"
          description="Are you sure you want to delete this task? This action cannot be undone."
          itemName={fullTasks.get(activeDialog.taskId)?.title || taskSummaries.find(t => t.id === activeDialog.taskId)?.title}
        />
      )}

      {activeDialog.type === 'agent-info' && activeDialog.data && (
        <AgentInfoDialog
          open={true}
          onOpenChange={onCloseDialog}
          agentName={activeDialog.data.agentName}
          taskTitle={activeDialog.data.taskTitle}
          onClose={onCloseDialog}
        />
      )}
    </Suspense>
  );
};