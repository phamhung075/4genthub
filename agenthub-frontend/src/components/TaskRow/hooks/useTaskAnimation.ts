import { useState, useCallback, useEffect, useRef } from 'react';
import { animationFactory, AnimationType } from '../../../services/AnimationFactory';
import { TaskSummary } from '../../../types/taskTypes';
import logger from '../../../utils/logger';
import { taskDeletionTracker } from '../../../services/taskDeletionTracker';

// Animation CSS classes are defined in: src/styles/task-animations.css
// They are applied globally via AnimationFactory

// Animation state types matching subtask implementation
type TaskAnimationState = 'none' | 'creating' | 'deleting' | 'updating';

export function useTaskAnimation(
  summary: TaskSummary,
  isMobile: boolean
) {
  const [animationState, setAnimationState] = useState<TaskAnimationState>('none');
  const [isVisible, setIsVisible] = useState(true);
  const mobileElementRef = useRef<HTMLDivElement>(null);
  const desktopElementRef = useRef<HTMLTableRowElement>(null);

  // Track previous values to detect updates
  const prevStatusRef = useRef<string>(summary.status);
  const prevTitleRef = useRef<string>(summary.title);
  const prevProgressRef = useRef<number | undefined>(summary.subtask_count);
  const hasMountedRef = useRef(false);

  const playCreateAnimation = useCallback((source: 'websocket' | 'mount' = 'mount') => {
    logger.debug('🎬 [useTaskAnimation] playCreateAnimation called', {
      taskId: summary.id,
      source
    }, 'useTaskAnimation.ts');

    const success = animationFactory.animate(summary.id, 'create', source);

    logger.debug('Animation delegated to factory', {
      component: 'useTaskAnimation',
      taskId: summary.id,
      source,
      success
    }, 'useTaskAnimation.ts');

    // Fallback to local state if factory fails
    if (!success) {
      logger.debug('🎬 [useTaskAnimation] AnimationFactory failed, using CSS fallback', {
        taskId: summary.id,
        animationState: 'creating',
        cssClass: 'taskRowCreateAnimation'
      }, 'useTaskAnimation.ts');
      setAnimationState('creating');
      setTimeout(() => setAnimationState('none'), 800);
    }

    return success;
  }, [summary.id]);

  const playDeleteAnimation = useCallback((source: 'websocket' | 'mount' = 'mount') => {
    logger.debug('🎬 TaskRow starting delete animation for:', summary.id);

    const success = animationFactory.animate(summary.id, 'delete', source);

    // Fallback to local state if factory fails
    if (!success) {
      setAnimationState('deleting');
    }

    setTimeout(() => {
      logger.debug('🎬 TaskRow delete animation complete, hiding:', summary.id);
      setIsVisible(false);
    }, 800);

    return success;
  }, [summary.id]);

  const playUpdateAnimation = useCallback((source: 'websocket' | 'mount' = 'mount') => {
    const success = animationFactory.animate(summary.id, 'update', source);

    // Fallback to local state if factory fails
    if (!success) {
      setAnimationState('updating');
      setTimeout(() => setAnimationState('none'), 5000);
    }

    return success;
  }, [summary.id]);

  // Register element with AnimationFactory on mount
  useEffect(() => {
    const currentElement = isMobile ? mobileElementRef.current : desktopElementRef.current;

    if (currentElement) {
      logger.debug('🎬 [useTaskAnimation] Registering element', {
        taskId: summary.id,
        elementType: isMobile ? 'mobile' : 'desktop',
        element: currentElement.tagName
      }, 'useTaskAnimation.ts');

      animationFactory.registerElement(summary.id, currentElement, {
        onAnimationStart: (type: AnimationType) => {
          logger.debug('🎬 Animation started', { taskId: summary.id, type }, 'useTaskAnimation.ts');
        },
        onAnimationEnd: (type: AnimationType) => {
          logger.debug('🎬 Animation completed', { taskId: summary.id, type }, 'useTaskAnimation.ts');
        }
      });

      logger.debug('Element registered with AnimationFactory', {
        component: 'useTaskAnimation',
        taskId: summary.id,
        isMobile
      });
    }

    // Cleanup on unmount
    return () => {
      logger.debug('🎬 [useTaskAnimation] Unregistering', { taskId: summary.id }, 'useTaskAnimation.ts');
      animationFactory.unregisterElement(summary.id);
      logger.debug('Element unregistered from AnimationFactory', {
        component: 'useTaskAnimation',
        taskId: summary.id
      });
    };
  }, [summary.id, isMobile]);

  // Mount-time animation check for newly created tasks
  useEffect(() => {
    // ALWAYS try to animate on first mount - the component only mounts when a task is added
    logger.debug('🎬 [useTaskAnimation] Mount-time check', {
      taskId: summary.id,
      hasCreatedAt: !!summary.created_at,
      createdAt: summary.created_at
    }, 'useTaskAnimation.ts');

    // Small delay to ensure DOM is ready, then trigger animation
    setTimeout(() => {
      logger.debug('🎬 Mount-time animation triggered', { taskId: summary.id }, 'useTaskAnimation.ts');
      playCreateAnimation('mount');
      hasMountedRef.current = true;
    }, 50);
  }, []); // Only run on mount

  // Detect ANY changes after mount and trigger update animation
  useEffect(() => {
    if (!hasMountedRef.current) {
      // Skip on first mount (create animation handles that)
      return;
    }

    // Check if ANY field changed
    const statusChanged = prevStatusRef.current !== summary.status;
    const titleChanged = prevTitleRef.current !== summary.title;
    const progressChanged = prevProgressRef.current !== summary.subtask_count;

    if (statusChanged || titleChanged || progressChanged) {
      logger.debug('🎬 [useTaskAnimation] Task update detected', {
        taskId: summary.id,
        statusChanged,
        titleChanged,
        progressChanged,
        oldStatus: prevStatusRef.current,
        newStatus: summary.status
      }, 'useTaskAnimation.ts');

      // Trigger update animation
      playUpdateAnimation('websocket');

      // Update refs for next comparison
      prevStatusRef.current = summary.status;
      prevTitleRef.current = summary.title;
      prevProgressRef.current = summary.subtask_count;
    }
  }, [summary.status, summary.title, summary.subtask_count, playUpdateAnimation]); // Run when any field changes

  // Detect when task is marked for deletion and trigger delete animation
  useEffect(() => {
    const checkInterval = setInterval(() => {
      if (taskDeletionTracker.isMarkedForDeletion(summary.id)) {
        logger.debug('🗑️ [useTaskAnimation] Task marked for deletion, triggering animation', { taskId: summary.id }, 'useTaskAnimation.ts');
        playDeleteAnimation('websocket');
        // Stop checking once we've triggered the animation
        clearInterval(checkInterval);
      }
    }, 50); // Check every 50ms

    // Cleanup interval on unmount
    return () => clearInterval(checkInterval);
  }, [summary.id, playDeleteAnimation]);

  // Helper function to get fallback animation class - matches subtask implementation
  // CSS classes are now global (defined in src/styles/task-animations.css)
  const getAnimationClass = (): string => {
    switch (animationState) {
      case 'creating':
        return 'taskRowCreateAnimation';
      case 'deleting':
        return 'taskRowDeleteAnimation';
      case 'updating':
        return 'taskRowUpdateAnimation';
      default:
        return '';
    }
  };

  return {
    animationState,
    isVisible,
    animationClass: getAnimationClass(),
    mobileElementRef,
    desktopElementRef,
    playCreateAnimation,
    playDeleteAnimation,
    playUpdateAnimation
  };
}