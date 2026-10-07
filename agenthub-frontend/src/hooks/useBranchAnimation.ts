import { useState, useCallback, useEffect, useRef } from 'react';
import { animationFactory, AnimationType } from '../services/AnimationFactory';
import { Branch, BranchSummary } from '../types/api.types';
import logger from '../utils/logger';

// Animation CSS classes are defined in: src/styles/task-animations.css
// They are applied globally via AnimationFactory

// Animation state types matching task/subtask/project implementation
type BranchAnimationState = 'none' | 'creating' | 'deleting' | 'updating';

export function useBranchAnimation(
  branch: Branch | BranchSummary,
  isMobile: boolean = false
) {
  const [animationState, setAnimationState] = useState<BranchAnimationState>('none');
  const [isVisible, setIsVisible] = useState(true);
  const mobileElementRef = useRef<HTMLDivElement>(null);
  const desktopElementRef = useRef<HTMLDivElement>(null);

  const playCreateAnimation = useCallback((source: 'websocket' | 'mount' = 'mount') => {
    logger.debug('🎬 [useBranchAnimation] playCreateAnimation called', {
      branchId: branch.id,
      source
    }, 'useBranchAnimation.ts');

    const success = animationFactory.animate(branch.id, 'create', source);

    logger.debug('Animation delegated to factory', {
      component: 'useBranchAnimation',
      branchId: branch.id,
      source,
      success
    }, 'useBranchAnimation.ts');

    // Fallback to local state if factory fails
    if (!success) {
      logger.debug('🎬 [useBranchAnimation] AnimationFactory failed, using CSS fallback', {
        branchId: branch.id,
        animationState: 'creating',
        cssClass: 'taskRowCreateAnimation'
      }, 'useBranchAnimation.ts');
      setAnimationState('creating');
      setTimeout(() => setAnimationState('none'), 800);
    }

    return success;
  }, [branch.id]);

  const playDeleteAnimation = useCallback((source: 'websocket' | 'mount' = 'mount') => {
    logger.debug('🎬 BranchItem starting delete animation for:', branch.id);

    const success = animationFactory.animate(branch.id, 'delete', source);

    // Fallback to local state if factory fails
    if (!success) {
      setAnimationState('deleting');
    }

    setTimeout(() => {
      logger.debug('🎬 BranchItem delete animation complete, hiding:', branch.id);
      setIsVisible(false);
    }, 800);

    return success;
  }, [branch.id]);

  const playUpdateAnimation = useCallback((source: 'websocket' | 'mount' = 'mount') => {
    const success = animationFactory.animate(branch.id, 'update', source);

    // Fallback to local state if factory fails
    if (!success) {
      setAnimationState('updating');
      setTimeout(() => setAnimationState('none'), 5000);
    }

    return success;
  }, [branch.id]);

  // Register element with AnimationFactory on mount
  useEffect(() => {
    const currentElement = isMobile ? mobileElementRef.current : desktopElementRef.current;

    if (currentElement) {
      logger.debug('🎬 [useBranchAnimation] Registering element', {
        branchId: branch.id,
        elementType: isMobile ? 'mobile' : 'desktop',
        element: currentElement.tagName
      }, 'useBranchAnimation.ts');

      // ✅ FIX 2025-11-22: Pass entityType 'branch' for correct CSS class selection
      animationFactory.registerElement(
        branch.id,
        currentElement,
        'branch', // Entity type for correct CSS classes (branchRowCreateAnimation, etc.)
        {
          onAnimationStart: (type: AnimationType) => {
            logger.debug('🎬 Animation started', { branchId: branch.id, type }, 'useBranchAnimation.ts');
          },
          onAnimationEnd: (type: AnimationType) => {
            logger.debug('🎬 Animation completed', { branchId: branch.id, type }, 'useBranchAnimation.ts');
          }
        }
      );

      logger.debug('Element registered with AnimationFactory', {
        component: 'useBranchAnimation',
        branchId: branch.id,
        isMobile
      });
    }

    // Cleanup on unmount
    return () => {
      logger.debug('🎬 [useBranchAnimation] Unregistering', { branchId: branch.id }, 'useBranchAnimation.ts');
      animationFactory.unregisterElement(branch.id);
      logger.debug('Element unregistered from AnimationFactory', {
        component: 'useBranchAnimation',
        branchId: branch.id
      });
    };
  }, [branch.id, isMobile]);

  // Mount-time animation check for newly created branches
  useEffect(() => {
    const createdAt = 'created_at' in branch ? branch.created_at : undefined;
    // KEPT SO THE EFFECT CAN CLEAR IT. This timer used to outlive the row: it fires
    // 50ms after mount, and on a remount that was long enough to land in the NEW row
    // and replay its create animation. The factory now dedupes that by element id,
    // but a pending timer should still not outlive the effect that started it.
    let timer: NodeJS.Timeout | undefined;

    // Only animate if branch was created recently (within last 2 seconds)
    // This prevents ALL branches from animating when the list re-renders
    if (createdAt) {
      const createdAtDate = new Date(createdAt);
      const now = new Date();
      const ageInMs = now.getTime() - createdAtDate.getTime();
      const isNewBranch = ageInMs < 2000; // Created within last 2 seconds

      if (isNewBranch) {
        // Small delay to ensure DOM is ready, then trigger animation
        timer = setTimeout(() => {
          playCreateAnimation('mount');
        }, 50);
      }
    }

    return () => {
      clearTimeout(timer);
    };
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

  // Helper function to get fallback animation class - matches task/subtask/project implementation
  // ✅ FIX 2025-11-22: Updated to use branch-specific CSS classes instead of task classes
  const getAnimationClass = (): string => {
    switch (animationState) {
      case 'creating':
        return 'branchRowCreateAnimation';
      case 'deleting':
        return 'branchRowDeleteAnimation';
      case 'updating':
        return 'branchRowUpdateAnimation';
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
