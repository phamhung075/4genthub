import React, { Suspense } from 'react';
import TaskSearch from "../../TaskSearch";

interface TaskSearchSectionProps {
  projectId: string;
  taskTreeId: string;
  onTaskSelect: (task: unknown) => void;
  onSubtaskSelect: (subtask: unknown, parentTask: unknown) => void;
}

export const TaskSearchSection: React.FC<TaskSearchSectionProps> = ({
  projectId,
  taskTreeId,
  onTaskSelect,
  onSubtaskSelect
}) => {
  return (
    <div className="w-full">
      <Suspense fallback={<div>Loading search...</div>}>
        <TaskSearch
          projectId={projectId}
          taskTreeId={taskTreeId}
          onTaskSelect={onTaskSelect}
          onSubtaskSelect={onSubtaskSelect}
        />
      </Suspense>
    </div>
  );
};
