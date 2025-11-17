import { useState, useCallback, useEffect, useRef } from 'react';
import { animationFactory, AnimationType } from '../services/AnimationFactory';
import { Project } from '../types/api.types';
import logger from '../utils/logger';
import { projectDeletionTracker } from '../services/projectDeletionTracker';

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

  // Track previous values to detect updates
  const prevNameRef = useRef<string>(project.name);
  const prevStatusRef = useRef<string | undefined>(project.status);
  const prevDescriptionRef = useRef<string | undefined>(project.description);
  const hasMountedRef = useRef(false);

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

      animationFactory.registerElement(project.id, currentElement, {
        onAnimationStart: (type: AnimationType) => {
          logger.debug('🎬 Animation started', { projectId: project.id, type }, 'useProjectAnimation.ts');
        },
        onAnimationEnd: (type: AnimationType) => {
          logger.debug('🎬 Animation completed', { projectId: project.id, type }, 'useProjectAnimation.ts');
        }
      });

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
    // Only animate if project was created recently (within last 2 seconds)
    // This prevents ALL projects from animating when the list re-renders
    if (project.created_at) {
      const createdAt = new Date(project.created_at);
      const now = new Date();
      const ageInMs = now.getTime() - createdAt.getTime();
      const isNewProject = ageInMs < 2000; // Created within last 2 seconds

      if (isNewProject) {
        // Small delay to ensure DOM is ready, then trigger animation
        setTimeout(() => {
          playCreateAnimation('mount');
          hasMountedRef.current = true;
        }, 50);
      } else {
        hasMountedRef.current = true;
      }
    } else {
      hasMountedRef.current = true;
    }
  }, []); // Only run on mount

  // Detect ANY changes after mount and trigger update animation
  useEffect(() => {
    if (!hasMountedRef.current) {
      // Skip on first mount (create animation handles that)
      return;
    }

    // Check if ANY field changed
    const nameChanged = prevNameRef.current !== project.name;
    const statusChanged = prevStatusRef.current !== project.status;
    const descriptionChanged = prevDescriptionRef.current !== project.description;

    if (nameChanged || statusChanged || descriptionChanged) {
      logger.debug('🎬 [useProjectAnimation] Project update detected', {
        projectId: project.id,
        nameChanged,
        statusChanged,
        descriptionChanged,
        oldName: prevNameRef.current,
        newName: project.name
      }, 'useProjectAnimation.ts');

      // Trigger update animation
      playUpdateAnimation('websocket');

      // Update refs for next comparison
      prevNameRef.current = project.name;
      prevStatusRef.current = project.status;
      prevDescriptionRef.current = project.description;
    }
  }, [project.name, project.status, project.description, playUpdateAnimation]); // Run when any field changes

  // Detect when project is marked for deletion and trigger delete animation
  useEffect(() => {
    const checkInterval = setInterval(() => {
      if (projectDeletionTracker.isMarkedForDeletion(project.id)) {
        logger.debug('🗑️ [useProjectAnimation] Project marked for deletion, triggering animation', { projectId: project.id }, 'useProjectAnimation.ts');
        playDeleteAnimation('websocket');
        // Stop checking once we've triggered the animation
        clearInterval(checkInterval);
      }
    }, 50); // Check every 50ms

    // Cleanup interval on unmount
    return () => clearInterval(checkInterval);
  }, [project.id, playDeleteAnimation]);

  // Helper function to get fallback animation class - matches task/subtask implementation
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
