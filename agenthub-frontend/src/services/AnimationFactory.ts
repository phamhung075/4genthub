/**
 * AnimationFactory - Centralized Animation Management System
 *
 * Single source of truth for all WebSocket and component animations.
 * Provides clean API, prevents double-triggering, and ensures consistent behavior.
 */

import type {
  AnimatedEntityType,
  AnimationDefinition,
  AnimationSource,
  AnimationState,
  AnimationType,
  ElementRegistration
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

  // Animation coordination, PER ELEMENT AND TYPE. One entry per element was not
  // enough to answer the two questions this has to answer: has THIS element played
  // its create already (so a remount must not replay it), and has THIS element
  // played THIS type inside the cooldown (so one event reported by two sources
  // animates once). Widened 2026-10-07 after the owner reported animations firing
  // more than once per event.
  private animationStates = new Map<string, Partial<Record<AnimationType, AnimationState>>>();

  // How many elements keep their played-types record. The record deliberately
  // OUTLIVES unregisterElement - that is what makes a remount idempotent - so it
  // needs a bound: the oldest element is evicted past this many.
  private readonly MAX_TRACKED_ELEMENTS = 10_000;

  // Minimum time between animations for same element (ms)
  private readonly ANIMATION_COOLDOWN = 100;

  /**
   * Register an element for animations
   * ✅ FIX 2025-11-22: Added entityType parameter to build correct CSS class names
   */
  registerElement(
    elementId: string,
    element: HTMLElement,
    entityType: AnimatedEntityType,
    callbacks?: {
      onAnimationStart?: (type: AnimationType) => void;
      onAnimationEnd?: (type: AnimationType) => void;
    }
  ): void {
    this.elementRegistry.set(elementId, { element, entityType, callbacks });
  }

  /**
   * Unregister an element from animations.
   *
   * THE PLAYED-TYPES RECORD IS DELIBERATELY NOT CLEARED HERE. A remount is not a
   * new element: the same row re-rendering must not animate its create again, and
   * the only way to know it already has is to keep what it played. The record is
   * bounded by MAX_TRACKED_ELEMENTS rather than by unmounting.
   */
  unregisterElement(elementId: string): void {
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

    // Record that this element has played this type. The record OUTLIVES
    // unregisterElement on purpose (a remount is not a new element), so it is kept
    // bounded here instead: past MAX_TRACKED_ELEMENTS the oldest element is evicted.
    let played = this.animationStates.get(elementId);
    if (!played) {
      if (this.animationStates.size >= this.MAX_TRACKED_ELEMENTS) {
        const oldest = this.animationStates.keys().next().value;
        if (oldest !== undefined) this.animationStates.delete(oldest);
      }
      played = {};
      this.animationStates.set(elementId, played);
    }
    played[type] = { type, startTime: Date.now(), source };

    // Apply animation
    this.applyAnimation(registration, animationDef, type);

    return true;
  }

  /**
   * Check if an animation is currently in progress for an element
   */
  isAnimationInProgress(elementId: string): boolean {
    const played = this.animationStates.get(elementId);
    if (!played) return false;

    const now = Date.now();
    return Object.values(played).some((state) =>
      state ? now - state.startTime < this.animationRegistry[state.type].duration : false
    );
  }

  /**
   * Get current animation state for an element
   */
  getAnimationState(elementId: string): AnimationState | null {
    const played = this.animationStates.get(elementId);
    if (!played) return null;
    let latest: AnimationState | null = null;
    for (const state of Object.values(played)) {
      if (state && (!latest || state.startTime > latest.startTime)) {
        latest = state;
      }
    }
    return latest;
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
  private buildCssClass(entityType: AnimatedEntityType, animationType: AnimationType): string {
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
   * Coordination logic, PER ELEMENT AND TYPE.
   *
   * TWO RULES CARRY THE OWNER'S REPORT (2026-10-07 - "animation triggers multiple
   * times"):
   *  1. MOUNT IS ALLOWED ONCE PER ELEMENT ID. It used to return true
   *     unconditionally, so any remount of a row - a list re-render, a key change,
   *     another page of results - replayed the create animation for a row nothing
   *     had happened to.
   *  2. THE SAME TYPE FOR THE SAME ELEMENT IS DEDUPED INSIDE THE COOLDOWN,
   *     whichever source asks. One event reported by both the callback path and the
   *     WebSocket path animated twice, because a WebSocket animation was allowed to
   *     override a callback one.
   */
  private shouldAllowAnimation(elementId: string, type: AnimationType, source: AnimationSource): boolean {
    const played = this.animationStates.get(elementId);
    const now = Date.now();

    // Every block names its reason and is LOGGED. This is the one place in the
    // animation system that used to fail with no output at all, and a dropped
    // animation and a message that never arrived look identical in a console while
    // having opposite fixes - so each new rule added here has to say why it fired.
    let blocked: string | null = null;

    // Rule 2: this element has already played THIS type inside the cooldown, so
    // this is the same event arriving twice rather than a new one.
    const sameType = played?.[type];
    if (sameType && now - sameType.startTime <= this.ANIMATION_COOLDOWN) {
      blocked = `the same '${type}' already played for this element ${now - sameType.startTime}ms ago`;
    } else if (source === 'mount') {
      // Rule 1: a mount is a new element's first appearance, and "once per element
      // id" is what new means here - a remount is not a new element.
      if (played?.create?.source !== 'mount') {
        return true;
      }
      blocked = 'this element already played its mount animation, so a remount is not a new element';
    } else {
      let mostRecent: AnimationState | undefined;
      for (const state of Object.values(played ?? {})) {
        if (state && (!mostRecent || state.startTime > mostRecent.startTime)) {
          mostRecent = state;
        }
      }
      if (!mostRecent || now - mostRecent.startTime > this.ANIMATION_COOLDOWN) {
        return true;
      }
      // A WebSocket animation may override a callback one: that is a DIFFERENT event
      // arriving mid-animation, which is why it is allowed and the same type twice
      // is not.
      if (!(source === 'websocket' && mostRecent.source === 'callback')) {
        blocked = `a '${source}' request arrived ${now - mostRecent.startTime}ms after this element's last '${mostRecent.source}' animation`;
      }
    }

    if (blocked === null) {
      return true;
    }

    logger.debug(
      `🎬 [AnimationFactory] Animation dropped for '${elementId}': ${blocked} (cooldown ${this.ANIMATION_COOLDOWN}ms)`,
      {
        elementId,
        requestedType: type,
        requestedSource: source,
        cooldownMs: this.ANIMATION_COOLDOWN
      },
      'AnimationFactory.ts'
    );
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
    animationDefinitions: Record<AnimationType, Omit<AnimationDefinition, 'cssClass'>>;
  } {
    return {
      registeredElements: Array.from(this.elementRegistry.keys()),
      activeAnimations: Array.from(this.animationStates.entries()).flatMap(([elementId, played]) =>
        Object.values(played)
          .filter((state): state is AnimationState => Boolean(state))
          .map((state) => ({ elementId, state }))
      ),
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
