// useSubtaskAnimation - Hook for managing subtask row animations
// Follows SOLID principles - Single responsibility for animation logic

import { useState, useCallback, useEffect } from 'react';
import logger from '../../../utils/logger';
import type { SubtaskAnimationState, AnimationCallbacks } from '../../../types/subtaskTypes';

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

  // Animation handlers
  const playCreateAnimation = useCallback(() => {
    setAnimationState('creating');
    setTimeout(() => setAnimationState('none'), 800);
  }, []);

  const playDeleteAnimation = useCallback(() => {
    logger.debug('🎬 SubtaskRow starting delete animation for:', subtaskId);
    setAnimationState('deleting');
    setTimeout(() => {
      logger.debug('🎬 SubtaskRow delete animation complete, hiding:', subtaskId);
      setIsVisible(false);
    }, 800);
  }, [subtaskId]);

  const playUpdateAnimation = useCallback(() => {
    setAnimationState('updating');
    setTimeout(() => setAnimationState('none'), 5000);
  }, []);

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

  const getAnimationClass = (): string => {
    switch (animationState) {
      case 'creating':
        return 'subtask-row-create-animation';
      case 'deleting':
        return 'subtask-row-delete-animation';
      case 'updating':
        return 'subtask-row-update-animation';
      default:
        return '';
    }
  };

  return {
    animationState,
    isVisible,
    animationClass: getAnimationClass()
  };
}