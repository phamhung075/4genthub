import { useState, useCallback, useEffect, useRef } from 'react';
import { animationFactory, AnimationType } from '../../../services/AnimationFactory';
import { TaskSummary } from '../../../types/taskTypes';
import logger from '../../../utils/logger';
import styles from '../TaskRow.module.css';

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

  const playCreateAnimation = useCallback((source: 'websocket' | 'mount' = 'mount') => {
    console.log('🎬 [useTaskAnimation] playCreateAnimation called:', {
      taskId: summary.id,
      source
    });

    const success = animationFactory.animate(summary.id, 'create', source);

    logger.debug('Animation delegated to factory', {
      component: 'useTaskAnimation',
      taskId: summary.id,
      source,
      success
    });

    // Fallback to local state if factory fails
    if (!success) {
      console.log('🎬 [useTaskAnimation] AnimationFactory failed, using CSS fallback:', {
        taskId: summary.id,
        animationState: 'creating',
        cssClass: styles.taskRowCreateAnimation
      });
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
      //console.log('🎬 [useTaskAnimation] Registering element:', {
      //  taskId: summary.id,
      //  elementType: isMobile ? 'mobile' : 'desktop',
      //  element: currentElement.tagName
      //});

      animationFactory.registerElement(summary.id, currentElement, {
        onAnimationStart: (type: AnimationType) => {
          console.log('🎬 Animation started:', { taskId: summary.id, type });
        },
        onAnimationEnd: (type: AnimationType) => {
          console.log('🎬 Animation completed:', { taskId: summary.id, type });
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
      //console.log('🎬 [useTaskAnimation] Unregistering:', summary.id);
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
    console.log('🎬 [useTaskAnimation] Mount-time check:', {
      taskId: summary.id,
      hasCreatedAt: !!summary.created_at,
      createdAt: summary.created_at
    });

    // Small delay to ensure DOM is ready, then trigger animation
    setTimeout(() => {
      console.log('🎬 Mount-time animation triggered:', summary.id);
      playCreateAnimation('mount');
    }, 50);
  }, []); // Only run on mount

  // Helper function to get fallback animation class - matches subtask implementation
  const getAnimationClass = (): string => {
    switch (animationState) {
      case 'creating':
        return styles.taskRowCreateAnimation;
      case 'deleting':
        return styles.taskRowDeleteAnimation;
      case 'updating':
        return styles.taskRowUpdateAnimation;
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