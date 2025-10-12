import React, { Suspense } from 'react';
import TaskSearch from "../../TaskSearch";

interface TaskSearchSectionProps {
  projectId: string;
  taskTreeId: string;
  onTaskSelect: (task: any) => void;
  onSubtaskSelect: (subtask: any, parentTask: any) => void;
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