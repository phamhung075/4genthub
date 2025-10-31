import { useState, useCallback, useEffect, useRef } from 'react';
import { animationFactory, AnimationType } from '../services/AnimationFactory';
import { Branch } from '../types/api.types';
import logger from '../utils/logger';
import { branchDeletionTracker } from '../services/branchDeletionTracker';

// Animation CSS classes are defined in: src/styles/task-animations.css
// They are applied globally via AnimationFactory

// Animation state types matching task/subtask/project implementation
type BranchAnimationState = 'none' | 'creating' | 'deleting' | 'updating';

export function useBranchAnimation(
  branch: Branch,
  isMobile: boolean = false
) {
  const [animationState, setAnimationState] = useState<BranchAnimationState>('none');
  const [isVisible, setIsVisible] = useState(true);
  const mobileElementRef = useRef<HTMLDivElement>(null);
  const desktopElementRef = useRef<HTMLDivElement>(null);

  // Track previous values to detect updates
  const prevNameRef = useRef<string>(branch.git_branch_name);
  const prevStatusRef = useRef<string | undefined>(branch.status);
  const prevDescriptionRef = useRef<string | undefined>(branch.description);
  const hasMountedRef = useRef(false);

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

      animationFactory.registerElement(branch.id, currentElement, {
        onAnimationStart: (type: AnimationType) => {
          logger.debug('🎬 Animation started', { branchId: branch.id, type }, 'useBranchAnimation.ts');
        },
        onAnimationEnd: (type: AnimationType) => {
          logger.debug('🎬 Animation completed', { branchId: branch.id, type }, 'useBranchAnimation.ts');
        }
      });

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
    // ALWAYS try to animate on first mount - the component only mounts when a branch is added
    logger.debug('🎬 [useBranchAnimation] Mount-time check', {
      branchId: branch.id,
      hasCreatedAt: !!branch.created_at,
      createdAt: branch.created_at
    }, 'useBranchAnimation.ts');

    // Small delay to ensure DOM is ready, then trigger animation
    setTimeout(() => {
      logger.debug('🎬 Mount-time animation triggered', { branchId: branch.id }, 'useBranchAnimation.ts');
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
    const nameChanged = prevNameRef.current !== branch.git_branch_name;
    const statusChanged = prevStatusRef.current !== branch.status;
    const descriptionChanged = prevDescriptionRef.current !== branch.description;

    if (nameChanged || statusChanged || descriptionChanged) {
      logger.debug('🎬 [useBranchAnimation] Branch update detected', {
        branchId: branch.id,
        nameChanged,
        statusChanged,
        descriptionChanged,
        oldName: prevNameRef.current,
        newName: branch.git_branch_name
      }, 'useBranchAnimation.ts');

      // Trigger update animation
      playUpdateAnimation('websocket');

      // Update refs for next comparison
      prevNameRef.current = branch.git_branch_name;
      prevStatusRef.current = branch.status;
      prevDescriptionRef.current = branch.description;
    }
  }, [branch.git_branch_name, branch.status, branch.description, playUpdateAnimation]); // Run when any field changes

  // Detect when branch is marked for deletion and trigger delete animation
  useEffect(() => {
    const checkInterval = setInterval(() => {
      if (branchDeletionTracker.isMarkedForDeletion(branch.id)) {
        logger.debug('🗑️ [useBranchAnimation] Branch marked for deletion, triggering animation', { branchId: branch.id }, 'useBranchAnimation.ts');
        playDeleteAnimation('websocket');
        // Stop checking once we've triggered the animation
        clearInterval(checkInterval);
      }
    }, 50); // Check every 50ms

    // Cleanup interval on unmount
    return () => clearInterval(checkInterval);
  }, [branch.id, playDeleteAnimation]);

  // Helper function to get fallback animation class - matches task/subtask/project implementation
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
