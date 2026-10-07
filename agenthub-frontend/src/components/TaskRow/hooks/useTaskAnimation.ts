import { useState, useCallback, useEffect, useRef } from 'react';
import { animationFactory, AnimationType } from '../../../services/AnimationFactory';
import { TaskSummary } from '../../../types/taskTypes';
import logger from '../../../utils/logger';

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

  // Tracks whether this row has mounted. A row created recently stays hidden (the
  // 'taskRowNew' class) until the WebSocket animation for it arrives; see the class
  // application below.
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

      // ✅ FIX 2025-11-22: Pass entityType 'task' for correct CSS class selection
      animationFactory.registerElement(
        summary.id,
        currentElement,
        'task', // Entity type for correct CSS classes (taskRowCreateAnimation, etc.)
        {
          onAnimationStart: (type: AnimationType) => {
            logger.debug('🎬 Animation started', { taskId: summary.id, type }, 'useTaskAnimation.ts');
          },
          onAnimationEnd: (type: AnimationType) => {
            logger.debug('🎬 Animation completed', { taskId: summary.id, type }, 'useTaskAnimation.ts');
          }
        }
      );

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

  // Mount-time animation - DISABLED
  // WebSocket notifications are the source of truth for animations (MCP trigger)
  // Both API route and MCP route send WebSocket 'created' events
  // WebSocketAnimationService handles all create animations
  useEffect(() => {
    hasMountedRef.current = true;
  }, []); // Only run on mount

  // NO prop-change update animation. The effect that used to sit here compared the
  // previous props and called playUpdateAnimation('websocket') - passing 'websocket'
  // for what is a RENDER, not a websocket event - and the real event is animated by
  // WebSocketAnimationService, so every update animated twice.

  // The deletion tracker's 50ms poll used to live here. Nothing ever marked one - the
  // trackers had no writer anywhere in the app - and the delete animation it guarded is
  // triggered from the delete site, where the cache removal is deferred 600ms so the row
  // is still registered when the animation fires. Removed with the trackers rather than
  // left in place looking live.

  // Helper function to get fallback animation class - matches subtask implementation
  // CSS classes are now global (defined in src/styles/task-animations.css)
  const getAnimationClass = (): string => {
    // Check if this is a newly created task (< 2 seconds old)
    // Apply 'taskRowNew' class to keep it hidden until WebSocket animation triggers
    if (summary.created_at && !hasMountedRef.current) {
      const createdAt = new Date(summary.created_at);
      const now = new Date();
      const ageInMs = now.getTime() - createdAt.getTime();
      const isNewTask = ageInMs < 2000; // Created within last 2 seconds

      if (isNewTask) {
        return 'taskRowNew'; // Start hidden, WebSocket animation will replace this
      }
    }

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
