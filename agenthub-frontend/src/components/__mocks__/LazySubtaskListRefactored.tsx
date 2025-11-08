import { vi } from 'vitest';
import React from 'react';

// Mock implementation of LazySubtaskListRefactored component
// Used in tests to avoid rendering complex subtask management UI

interface LazySubtaskListProps {
  taskId: string;
  onSubtaskUpdate?: (subtask: any) => void;
  onSubtaskDelete?: (subtaskId: string) => void;
  onSubtaskCreate?: (subtask: any) => void;
  className?: string;
  readonly?: boolean;
  showHeader?: boolean;
}

export const LazySubtaskListRefactored: React.FC<LazySubtaskListProps> = ({
  taskId,
  className = "",
  readonly = false,
  showHeader = true
}) => {
  return (
    <div
      data-testid="lazy-subtask-list"
      className={className}
      data-task-id={taskId}
      data-readonly={readonly}
    >
      {showHeader && (
        <div data-testid="subtask-list-header">
          <h3>Subtasks for Task {taskId}</h3>
          {!readonly && (
            <button
              data-testid="add-subtask-button"
              onClick={() => onSubtaskCreate?.({ title: 'New Subtask' })}
            >
              Add Subtask
            </button>
          )}
        </div>
      )}
      <div data-testid="subtask-list-content">
        <p data-testid="mock-subtask">Mock subtask 1</p>
        <p data-testid="mock-subtask">Mock subtask 2</p>
      </div>
    </div>
  );
};

// Mock the module
vi.mock('../../components/LazySubtaskList/LazySubtaskListRefactored', () => ({
  LazySubtaskListRefactored: vi.fn((props: LazySubtaskListProps) => {
    const readonly = props.readonly || false;
    const showHeader = props.showHeader !== false;

    return (
      <div
        data-testid="lazy-subtask-list"
        className={props.className}
        data-task-id={props.taskId}
        data-readonly={readonly}
      >
        {showHeader && (
          <div data-testid="subtask-list-header">
            <h3>Subtasks for Task {props.taskId}</h3>
            {!readonly && (
              <button
                data-testid="add-subtask-button"
                onClick={() => props.onSubtaskCreate?.({ title: 'New Subtask' })}
              >
                Add Subtask
              </button>
            )}
          </div>
        )}
        <div data-testid="subtask-list-content">
          <p data-testid="mock-subtask">Mock subtask 1</p>
          <p data-testid="mock-subtask">Mock subtask 2</p>
        </div>
      </div>
    );
  })
}));

export default LazySubtaskListRefactored;
