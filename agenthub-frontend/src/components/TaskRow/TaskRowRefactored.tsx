import React from 'react';
import { TaskRowProps } from '../../types/taskTypes';
import { useTaskAnimation } from './hooks/useTaskAnimation';
import { useTaskRowState } from './hooks/useTaskRowState';
import { TaskRowMobile } from './components/TaskRowMobile';
import { TaskRowDesktop } from './components/TaskRowDesktop';
import logger from '../../utils/logger';

const TaskRowRefactored: React.FC<TaskRowProps> = ({
  summary,
  isExpanded,
  isLoading,
  fullTask,
  isHighlighted,
  isHovered,
  projectId,
  taskTreeId,
  isMobile,
  onToggleExpansion,
  onOpenDialog,
  onHover
}) => {
  // Log component mount for debugging
  console.log('🎬 [TaskRowRefactored] Component mount:', {
    taskId: summary.id,
    taskTitle: summary.title,
    isMobile,
    timestamp: new Date().toISOString(),
    hasCreatedAt: !!summary.created_at,
    createdAt: summary.created_at
  });

  // Animation management
  const { mobileElementRef, desktopElementRef } = useTaskAnimation(summary, isMobile);

  // State management
  const { isVisible } = useTaskRowState();

  // Log render decision
  logger.debug('TaskRowRefactored rendering', {
    component: 'TaskRowRefactored',
    taskId: summary.id,
    isVisible,
    isMobile
  });

  // Don't render if not visible (after delete animation)
  if (!isVisible) {
    return null;
  }

  // Render mobile or desktop view based on device
  if (isMobile) {
    return (
      <TaskRowMobile
        summary={summary}
        fullTask={fullTask}
        isHighlighted={isHighlighted}
        isHovered={isHovered}
        isExpanded={isExpanded}
        isLoading={isLoading}
        projectId={projectId}
        taskTreeId={taskTreeId}
        onToggleExpansion={onToggleExpansion}
        onOpenDialog={onOpenDialog}
        onHover={onHover}
        elementRef={mobileElementRef}
      />
    );
  }

  return (
    <TaskRowDesktop
      summary={summary}
      fullTask={fullTask}
      isHighlighted={isHighlighted}
      isHovered={isHovered}
      isExpanded={isExpanded}
      isLoading={isLoading}
      projectId={projectId}
      taskTreeId={taskTreeId}
      onToggleExpansion={onToggleExpansion}
      onOpenDialog={onOpenDialog}
      onHover={onHover}
      elementRef={desktopElementRef}
    />
  );
};

export default TaskRowRefactored;