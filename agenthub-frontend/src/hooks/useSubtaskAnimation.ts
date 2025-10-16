// useSubtaskAnimation - Hook for managing subtask row animations
// Follows SOLID principles - Single responsibility for animation logic

import { useState, useCallback, useEffect, useRef } from 'react';
import { animationFactory, AnimationType } from '../services/AnimationFactory';
import logger from '../utils/logger';
import { taskDeletionTracker } from '../services/taskDeletionTracker';
import type { SubtaskAnimationState, AnimationCallbacks } from '../types/animationTypes';

interface UseSubtaskAnimationProps {
  subtaskId: string;
  onRegisterCallbacks?: (subtaskId: string, callbacks: AnimationCallbacks) => void;
  onUnregisterCallbacks?: (subtaskId: string) => void;
}

export function useSubtaskAnimation({
  subtaskId,
  onRegisterCallbacks,
  onUnregisterCallbacks
}: UseSubtaskAnimationProps) {
  const [animationState, setAnimationState] = useState<SubtaskAnimationState>('none');
  const [isVisible, setIsVisible] = useState(true);
  const elementRef = useRef<HTMLTableRowElement>(null);

  // Animation handlers that delegate to AnimationFactory
  const playCreateAnimation = useCallback((source: 'websocket' | 'mount' = 'mount') => {
    logger.debug('🎬 [useSubtaskAnimation] playCreateAnimation called', {
      subtaskId,
      source
    }, 'useSubtaskAnimation.ts');

    const success = animationFactory.animate(subtaskId, 'create', source);

    logger.debug('Subtask animation delegated to factory', {
      component: 'useSubtaskAnimation',
      subtaskId,
      source,
      success
    }, 'useSubtaskAnimation.ts');

    // Fallback to local state if factory fails
    if (!success) {
      setAnimationState('creating');
      setTimeout(() => setAnimationState('none'), 800);
    }

    return success;
  }, [subtaskId]);

  const playDeleteAnimation = useCallback((source: 'websocket' | 'mount' = 'mount') => {
    logger.debug('🎬 SubtaskRow starting delete animation for:', subtaskId);

    const success = animationFactory.animate(subtaskId, 'delete', source);

    // Fallback to local state if factory fails
    if (!success) {
      setAnimationState('deleting');
    }

    setTimeout(() => {
      logger.debug('🎬 SubtaskRow delete animation complete, hiding:', subtaskId);
      setIsVisible(false);
    }, 800);

    return success;
  }, [subtaskId]);

  const playUpdateAnimation = useCallback((source: 'websocket' | 'mount' = 'mount') => {
    const success = animationFactory.animate(subtaskId, 'update', source);

    // Fallback to local state if factory fails
    if (!success) {
      setAnimationState('updating');
      setTimeout(() => setAnimationState('none'), 5000);
    }

    return success;
  }, [subtaskId]);

  // Register element with AnimationFactory on mount
  useEffect(() => {
    const currentElement = elementRef.current;

    if (currentElement) {
      logger.debug('🎬 [useSubtaskAnimation] Registering element', {
        subtaskId,
        element: currentElement.tagName
      }, 'useSubtaskAnimation.ts');

      animationFactory.registerElement(subtaskId, currentElement, {
        onAnimationStart: (type: AnimationType) => {
          logger.debug('🎬 Subtask animation started', { subtaskId, type }, 'useSubtaskAnimation.ts');
        },
        onAnimationEnd: (type: AnimationType) => {
          logger.debug('🎬 Subtask animation completed', { subtaskId, type }, 'useSubtaskAnimation.ts');
        }
      });

      logger.debug('Subtask element registered with AnimationFactory', {
        component: 'useSubtaskAnimation',
        subtaskId
      });
    }

    // Cleanup on unmount
    return () => {
      logger.debug('🎬 [useSubtaskAnimation] Unregistering', { subtaskId }, 'useSubtaskAnimation.ts');
      animationFactory.unregisterElement(subtaskId);
      logger.debug('Subtask element unregistered from AnimationFactory', {
        component: 'useSubtaskAnimation',
        subtaskId
      });
    };
  }, [subtaskId]);

  // Register animation callbacks with parent
  useEffect(() => {
    if (onRegisterCallbacks) {
      logger.debug('📝 SubtaskRow registering callbacks for subtask:', subtaskId);
      onRegisterCallbacks(subtaskId, {
        playCreateAnimation,
        playDeleteAnimation,
        playUpdateAnimation
      });
    } else {
      logger.warn('⚠️ SubtaskRow: No onRegisterCallbacks provided for subtask:', subtaskId);
    }

    return () => {
      if (onUnregisterCallbacks) {
        logger.debug('🧹 SubtaskRow unregistering callbacks for subtask:', subtaskId);
        onUnregisterCallbacks(subtaskId);
      }
    };
  }, [subtaskId, playCreateAnimation, playDeleteAnimation, playUpdateAnimation, onRegisterCallbacks, onUnregisterCallbacks]);

  // Detect when subtask is marked for deletion and trigger delete animation
  useEffect(() => {
    const checkInterval = setInterval(() => {
      if (taskDeletionTracker.isMarkedForDeletion(subtaskId)) {
        logger.debug('🗑️ [useSubtaskAnimation] Subtask marked for deletion, triggering animation', { subtaskId }, 'useSubtaskAnimation.ts');
        playDeleteAnimation('websocket');
        // Stop checking once we've triggered the animation
        clearInterval(checkInterval);
      }
    }, 50); // Check every 50ms

    // Cleanup interval on unmount
    return () => clearInterval(checkInterval);
  }, [subtaskId, playDeleteAnimation]);

  const getAnimationClass = (): string => {
    switch (animationState) {
      case 'creating':
        return 'subtaskRowCreateAnimation';
      case 'deleting':
        return 'subtaskRowDeleteAnimation';
      case 'updating':
        return 'subtaskRowUpdateAnimation';
      default:
        return '';
    }
  };

  return {
    animationState,
    isVisible,
    animationClass: getAnimationClass(),
    elementRef
  };
}
