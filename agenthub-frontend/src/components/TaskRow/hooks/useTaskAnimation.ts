import { useCallback, useEffect, useRef } from 'react';
import { animationFactory, AnimationType } from '../../../services/AnimationFactory';
import logger from '../../../utils/logger';
import { TaskSummary } from '../../../types/taskTypes';

export function useTaskAnimation(
  summary: TaskSummary,
  isMobile: boolean
) {
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

    return success;
  }, [summary.id]);

  // Register element with AnimationFactory on mount
  useEffect(() => {
    const currentElement = isMobile ? mobileElementRef.current : desktopElementRef.current;

    if (currentElement) {
      console.log('🎬 [useTaskAnimation] Registering element:', {
        taskId: summary.id,
        elementType: isMobile ? 'mobile' : 'desktop',
        element: currentElement.tagName
      });

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
      console.log('🎬 [useTaskAnimation] Unregistering:', summary.id);
      animationFactory.unregisterElement(summary.id);
      logger.debug('Element unregistered from AnimationFactory', {
        component: 'useTaskAnimation',
        taskId: summary.id
      });
    };
  }, [summary.id, isMobile]);

  // Mount-time animation check for newly created tasks
  useEffect(() => {
    if (summary.created_at) {
      const createdTime = new Date(summary.created_at).getTime();
      const now = Date.now();
      const timeSinceCreated = now - createdTime;
      const isNewlyCreated = timeSinceCreated < 10000; // 10 seconds

      console.log('🎬 [useTaskAnimation] Mount-time check:', {
        taskId: summary.id,
        createdAt: summary.created_at,
        timeSinceCreated,
        isNewlyCreated
      });

      if (isNewlyCreated) {
        // Small delay to ensure DOM is ready
        setTimeout(() => {
          console.log('🎬 Mount-time animation triggered:', summary.id);
          playCreateAnimation('mount');
        }, 100);
      }
    }
  }, []); // Only run on mount

  return {
    mobileElementRef,
    desktopElementRef,
    playCreateAnimation
  };
}