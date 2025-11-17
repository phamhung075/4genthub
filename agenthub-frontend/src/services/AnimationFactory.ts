/**
 * AnimationFactory - Centralized Animation Management System
 *
 * Single source of truth for all WebSocket and component animations.
 * Provides clean API, prevents double-triggering, and ensures consistent behavior.
 */

import type {
  AnimationDefinition,
  AnimationSource,
  AnimationState,
  AnimationType,
  ElementRegistration,
  EntityType
} from '../types/animationTypes';
import logger from '../utils/logger';

class AnimationFactory {
  // Animation definitions with synchronized CSS durations
  // ✅ FIX 2025-11-22: Removed hardcoded task-specific CSS classes
  // Now dynamically built based on entity type (task/subtask/branch/project)
  // CSS classes are defined in:
  //   - src/styles/task-animations.css (taskRow*Animation)
  //   - src/styles/subtask-animations.css (subtaskRow*Animation)
  private readonly animationRegistry: Record<AnimationType, Omit<AnimationDefinition, 'cssClass'>> = {
    create: {
      duration: 800, // 0.8s - matches slideIn animation
      description: 'Slide in animation for newly created entities'
    },
    delete: {
      duration: 800, // 0.8s - matches slideOut animation
      description: 'Slide out animation for deleted entities'
    },
    update: {
      duration: 1700, // 1.7s - matches flash animation (3 flashes)
      description: 'Flash background animation for updated entities'
    },
    complete: {
      duration: 1700, // 1.7s - matches flash animation (3 flashes)
      description: 'Flash background animation for completed entities'
    }
  };

  // Element registry for targeted animations
  private elementRegistry = new Map<string, ElementRegistration>();

  // Animation coordination to prevent double-triggering
  private animationStates = new Map<string, AnimationState>();

  // Minimum time between animations for same element (ms)
  private readonly ANIMATION_COOLDOWN = 100;

  /**
   * Register an element for animations
   * ✅ FIX 2025-11-22: Added entityType parameter to build correct CSS class names
   */
  registerElement(
    elementId: string,
    element: HTMLElement,
    entityType: EntityType,
    callbacks?: {
      onAnimationStart?: (type: AnimationType) => void;
      onAnimationEnd?: (type: AnimationType) => void;
    }
  ): void {
    this.elementRegistry.set(elementId, { element, entityType, callbacks });
  }

  /**
   * Unregister an element from animations
   */
  unregisterElement(elementId: string): void {
    // Clean up any active animation state
    this.animationStates.delete(elementId);
    this.elementRegistry.delete(elementId);
  }

  /**
   * Trigger animation for a specific element
   */
  animate(elementId: string, type: AnimationType, source: AnimationSource = 'callback'): boolean {
    // Check if element is registered
    const registration = this.elementRegistry.get(elementId);
    if (!registration) {
      logger.warn('🎬 [AnimationFactory] Element not registered:', elementId);
      return false;
    }

    // Check if animation should be allowed (coordination logic)
    if (!this.shouldAllowAnimation(elementId, type, source)) {
      return false;
    }

    // Get animation definition
    const animationDef = this.animationRegistry[type];
    if (!animationDef) {
      return false;
    }

    // Record animation start
    this.animationStates.set(elementId, {
      type,
      startTime: Date.now(),
      source
    });

    // Apply animation
    this.applyAnimation(registration, animationDef, type);

    return true;
  }

  /**
   * Check if an animation is currently in progress for an element
   */
  isAnimationInProgress(elementId: string): boolean {
    const state = this.animationStates.get(elementId);
    if (!state) return false;

    const animationDef = this.animationRegistry[state.type];
    const elapsed = Date.now() - state.startTime;

    return elapsed < animationDef.duration;
  }

  /**
   * Get current animation state for an element
   */
  getAnimationState(elementId: string): AnimationState | null {
    return this.animationStates.get(elementId) || null;
  }

  /**
   * Get all available animation types and their definitions
   */
  getAvailableAnimations(): Record<AnimationType, Omit<AnimationDefinition, 'cssClass'>> {
    return { ...this.animationRegistry };
  }

  /**
   * Build CSS class name based on entity type and animation type
   * ✅ FIX 2025-11-22: Dynamically builds correct CSS class for each entity type
   *
   * Examples:
   * - buildCssClass('task', 'delete') → 'taskRowDeleteAnimation'
   * - buildCssClass('subtask', 'delete') → 'subtaskRowDeleteAnimation'
   * - buildCssClass('branch', 'create') → 'branchRowCreateAnimation'
   */
  private buildCssClass(entityType: EntityType, animationType: AnimationType): string {
    // Capitalize first letter of animation type (delete → Delete)
    const capitalizedType = animationType.charAt(0).toUpperCase() + animationType.slice(1);

    // Build class name: {entityType}Row{AnimationType}Animation
    // task + Delete → taskRowDeleteAnimation
    // subtask + Create → subtaskRowCreateAnimation
    return `${entityType}Row${capitalizedType}Animation`;
  }

  /**
   * Force clear animation state (for cleanup)
   */
  clearAnimationState(elementId: string): void {
    this.animationStates.delete(elementId);
  }

  /**
   * Apply animation to element with proper cleanup
   * ✅ FIX 2025-11-22: Uses entity-specific CSS classes instead of hardcoded task classes
   */
  private applyAnimation(
    registration: ElementRegistration,
    animationDef: Omit<AnimationDefinition, 'cssClass'>,
    type: AnimationType
  ): void {
    const { element, entityType, callbacks } = registration;

    // Build entity-specific CSS class name
    const cssClass = this.buildCssClass(entityType, type);

    // Remove any existing animation classes for this entity type
    const allAnimationTypes: AnimationType[] = ['create', 'delete', 'update', 'complete'];
    allAnimationTypes.forEach(animType => {
      const classToRemove = this.buildCssClass(entityType, animType);
      element.classList.remove(classToRemove);
    });

    // Trigger start callback
    callbacks?.onAnimationStart?.(type);

    // Add entity-specific animation class
    element.classList.add(cssClass);

    logger.debug(`🎬 [AnimationFactory] Applied animation`, {
      entityType,
      animationType: type,
      cssClass,
      elementId: this.getElementId(element)
    });

    // Schedule cleanup
    setTimeout(() => {
      element.classList.remove(cssClass);

      // Clear animation state
      this.animationStates.delete(this.getElementId(element));

      // Trigger end callback
      callbacks?.onAnimationEnd?.(type);
    }, animationDef.duration);
  }

  /**
   * Coordination logic to prevent double-triggering
   */
  private shouldAllowAnimation(elementId: string, type: AnimationType, source: AnimationSource): boolean {
    const currentState = this.animationStates.get(elementId);
    const now = Date.now();

    // Allow if no animation is currently running
    if (!currentState) {
      return true;
    }

    const timeSinceLastAnimation = now - currentState.startTime;

    // Priority system:
    // 1. Mount-time animations have highest priority (new task just created)
    // 2. WebSocket animations have medium priority (real-time updates)
    // 3. Callback animations have lowest priority (user interactions)

    // Allow if enough time has passed (cooldown period)
    if (timeSinceLastAnimation > this.ANIMATION_COOLDOWN) {
      return true;
    }

    // Allow mount-time animations to override others
    if (source === 'mount') {
      return true;
    }

    // Allow WebSocket animations to override callbacks
    if (source === 'websocket' && currentState.source === 'callback') {
      return true;
    }

    // Block everything else
    return false;
  }

  /**
   * Helper to get element ID from the registry (reverse lookup)
   */
  private getElementId(targetElement: HTMLElement): string {
    for (const [elementId, registration] of this.elementRegistry.entries()) {
      if (registration.element === targetElement) {
        return elementId;
      }
    }
    return '';
  }

  /**
   * Debug method to get current system state
   */
  getDebugInfo(): {
    registeredElements: string[];
    activeAnimations: Array<{elementId: string; state: AnimationState}>;
    animationDefinitions: Record<AnimationType, AnimationDefinition>;
  } {
    return {
      registeredElements: Array.from(this.elementRegistry.keys()),
      activeAnimations: Array.from(this.animationStates.entries()).map(([elementId, state]) => ({
        elementId,
        state
      })),
      animationDefinitions: this.animationRegistry
    };
  }
}

// Export singleton instance
export const animationFactory = new AnimationFactory();

// Re-export types for convenience
export type { AnimationType, AnimationSource, AnimationState, AnimationDefinition } from '../types/animationTypes';

// DEBUG: Export to window for debugging and testing
if (typeof window !== 'undefined') {
  (window as any).animationFactory = animationFactory;
  logger.debug('🎬 AnimationFactory: Exposed to window.animationFactory for debugging', {}, 'AnimationFactory.ts');
}

export default animationFactory;
