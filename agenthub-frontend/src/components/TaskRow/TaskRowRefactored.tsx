import React from 'react';
import { TaskRowProps } from '../../types/taskTypes';
import logger from '../../utils/logger';
import { TaskRowDesktop } from './components/TaskRowDesktop';
import { TaskRowMobile } from './components/TaskRowMobile';
import { useTaskAnimation } from './hooks/useTaskAnimation';
import { useTaskRowState } from './hooks/useTaskRowState';

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
  logger.debug('🎬 [TaskRowRefactored] Component mount', {
    taskId: summary.id,
    taskTitle: summary.title,
    isMobile,
    timestamp: new Date().toISOString(),
    hasCreatedAt: !!summary.created_at,
    createdAt: summary.created_at
  }, 'TaskRowRefactored.tsx');

  // Animation management
  const {
    animationState,
    isVisible: isAnimationVisible,
    animationClass,
    mobileElementRef,
    desktopElementRef
  } = useTaskAnimation(summary, isMobile);

  // State management
  const { isVisible: isStateVisible } = useTaskRowState();

  // Combined visibility check
  const isVisible = isAnimationVisible && isStateVisible;

  // Log render decision
  logger.debug('TaskRowRefactored rendering', {
    component: 'TaskRowRefactored',
    taskId: summary.id,
    isVisible,
    animationState,
    animationClass,
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
        animationClass={animationClass}
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
      animationClass={animationClass}
    />
  );
};

export default TaskRowRefactored;