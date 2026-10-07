import { useState, useCallback, useEffect, useRef } from 'react';
import { animationFactory, AnimationType } from '../services/AnimationFactory';
import { Project } from '../types/api.types';
import logger from '../utils/logger';

// Animation CSS classes are defined in: src/styles/task-animations.css
// They are applied globally via AnimationFactory

// Animation state types matching task/subtask implementation
type ProjectAnimationState = 'none' | 'creating' | 'deleting' | 'updating';

export function useProjectAnimation(
  project: Project,
  isMobile: boolean
) {
  const [animationState, setAnimationState] = useState<ProjectAnimationState>('none');
  const [isVisible, setIsVisible] = useState(true);
  const mobileElementRef = useRef<HTMLDivElement>(null);
  const desktopElementRef = useRef<HTMLDivElement>(null);

  const playCreateAnimation = useCallback((source: 'websocket' | 'mount' = 'mount') => {
    logger.debug('🎬 [useProjectAnimation] playCreateAnimation called', {
      projectId: project.id,
      source
    }, 'useProjectAnimation.ts');

    const success = animationFactory.animate(project.id, 'create', source);

    logger.debug('Animation delegated to factory', {
      component: 'useProjectAnimation',
      projectId: project.id,
      source,
      success
    }, 'useProjectAnimation.ts');

    // Fallback to local state if factory fails
    if (!success) {
      logger.debug('🎬 [useProjectAnimation] AnimationFactory failed, using CSS fallback', {
        projectId: project.id,
        animationState: 'creating',
        cssClass: 'taskRowCreateAnimation'
      }, 'useProjectAnimation.ts');
      setAnimationState('creating');
      setTimeout(() => setAnimationState('none'), 800);
    }

    return success;
  }, [project.id]);

  const playDeleteAnimation = useCallback((source: 'websocket' | 'mount' = 'mount') => {
    logger.debug('🎬 ProjectCard starting delete animation for:', project.id);

    const success = animationFactory.animate(project.id, 'delete', source);

    // Fallback to local state if factory fails
    if (!success) {
      setAnimationState('deleting');
    }

    setTimeout(() => {
      logger.debug('🎬 ProjectCard delete animation complete, hiding:', project.id);
      setIsVisible(false);
    }, 800);

    return success;
  }, [project.id]);

  const playUpdateAnimation = useCallback((source: 'websocket' | 'mount' = 'mount') => {
    const success = animationFactory.animate(project.id, 'update', source);

    // Fallback to local state if factory fails
    if (!success) {
      setAnimationState('updating');
      setTimeout(() => setAnimationState('none'), 5000);
    }

    return success;
  }, [project.id]);

  // Register element with AnimationFactory on mount
  useEffect(() => {
    const currentElement = isMobile ? mobileElementRef.current : desktopElementRef.current;

    if (currentElement) {
      logger.debug('🎬 [useProjectAnimation] Registering element', {
        projectId: project.id,
        elementType: isMobile ? 'mobile' : 'desktop',
        element: currentElement.tagName
      }, 'useProjectAnimation.ts');

      // ✅ FIX 2025-11-22: Pass entityType 'project' for correct CSS class selection
      animationFactory.registerElement(
        project.id,
        currentElement,
        'project', // Entity type for correct CSS classes (projectRowCreateAnimation, etc.)
        {
          onAnimationStart: (type: AnimationType) => {
            logger.debug('🎬 Animation started', { projectId: project.id, type }, 'useProjectAnimation.ts');
          },
          onAnimationEnd: (type: AnimationType) => {
            logger.debug('🎬 Animation completed', { projectId: project.id, type }, 'useProjectAnimation.ts');
          }
        }
      );

      logger.debug('Element registered with AnimationFactory', {
        component: 'useProjectAnimation',
        projectId: project.id,
        isMobile
      });
    }

    // Cleanup on unmount
    return () => {
      logger.debug('🎬 [useProjectAnimation] Unregistering', { projectId: project.id }, 'useProjectAnimation.ts');
      animationFactory.unregisterElement(project.id);
      logger.debug('Element unregistered from AnimationFactory', {
        component: 'useProjectAnimation',
        projectId: project.id
      });
    };
  }, [project.id, isMobile]);

  // Mount-time animation check for newly created projects
  useEffect(() => {
    // KEPT SO THE EFFECT CAN CLEAR IT. This timer used to outlive the row: it fires
    // 50ms after mount, and on a remount that was long enough to land in the NEW row
    // and replay its create animation. The factory now dedupes that by element id,
    // but a pending timer should still not outlive the effect that started it.
    let timer: NodeJS.Timeout | undefined;

    // Only animate if project was created recently (within last 2 seconds)
    // This prevents ALL projects from animating when the list re-renders
    if (project.created_at) {
      const createdAt = new Date(project.created_at);
      const now = new Date();
      const ageInMs = now.getTime() - createdAt.getTime();
      const isNewProject = ageInMs < 2000; // Created within last 2 seconds

      if (isNewProject) {
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

  // Helper function to get fallback animation class - matches task/subtask implementation
  // ✅ FIX 2025-11-22: Updated to use project-specific CSS classes instead of task classes
  const getAnimationClass = (): string => {
    switch (animationState) {
      case 'creating':
        return 'projectRowCreateAnimation';
      case 'deleting':
        return 'projectRowDeleteAnimation';
      case 'updating':
        return 'projectRowUpdateAnimation';
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
