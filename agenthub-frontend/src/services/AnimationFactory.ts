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
  ElementRegistration
} from '../types/animationTypes';

class AnimationFactory {
  // Animation definitions with synchronized CSS durations
  private readonly animationRegistry: Record<AnimationType, AnimationDefinition> = {
    create: {
      cssClass: 'draw-in-left-to-right',
      duration: 1000, // 1s - enhanced duration for better visibility
      description: 'Fade in animation for newly created tasks'
    },
    delete: {
      cssClass: 'fade-out-left-to-right',
      duration: 1000, // 1s - enhanced duration for better visibility
      description: 'Fade out animation for deleted tasks'
    },
    update: {
      cssClass: 'content-update',
      duration: 1200, // 1.2s - matches CSS animation duration
      description: 'Content flash animation for updated tasks'
    },
    complete: {
      cssClass: 'task-celebration',
      duration: 3000, // 3s - matches CSS animation duration
      description: 'Celebration animation for completed tasks'
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
   */
  registerElement(
    elementId: string,
    element: HTMLElement,
    callbacks?: {
      onAnimationStart?: (type: AnimationType) => void;
      onAnimationEnd?: (type: AnimationType) => void;
    }
  ): void {
    //console.log('🎬 [AnimationFactory] Registering element:', {
    //  elementId,
    //  elementType: element.tagName,
    //  hasCallbacks: !!callbacks
    //});

    this.elementRegistry.set(elementId, { element, callbacks });
  }

  /**
   * Unregister an element from animations
   */
  unregisterElement(elementId: string): void {
    //console.log('🎬 [AnimationFactory] Unregistering element:', elementId);

    // Clean up any active animation state
    this.animationStates.delete(elementId);
    this.elementRegistry.delete(elementId);
  }

  /**
   * Trigger animation for a specific element
   */
  animate(elementId: string, type: AnimationType, source: AnimationSource = 'callback'): boolean {
    //console.log('🎬 [AnimationFactory] Animation request:', {
    //  elementId,
    //  type,
    //  source,
    //  timestamp: new Date().toISOString()
    //});

    // Check if element is registered
    const registration = this.elementRegistry.get(elementId);
    if (!registration) {
      console.warn('🎬 [AnimationFactory] Element not registered:', elementId);
      return false;
    }

    // Check if animation should be allowed (coordination logic)
    if (!this.shouldAllowAnimation(elementId, type, source)) {
      //console.log('🎬 [AnimationFactory] Animation blocked by coordination logic:', {
      //  elementId,
      //  type,
      //  source
      //});
      return false;
    }

    // Get animation definition
    const animationDef = this.animationRegistry[type];
    if (!animationDef) {
      //console.error('🎬 [AnimationFactory] Unknown animation type:', type);
      return false;
    }

    // Record animation start
    this.animationStates.set(elementId, {
      type,
      startTime: Date.now(),
      source
    });

    //console.log('🎬 [AnimationFactory] Applying animation:', {
    //  elementId,
    //  type,
    //  cssClass: animationDef.cssClass,
    //  duration: animationDef.duration,
    //  description: animationDef.description
    //});

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
  getAvailableAnimations(): Record<AnimationType, AnimationDefinition> {
    return { ...this.animationRegistry };
  }

  /**
   * Force clear animation state (for cleanup)
   */
  clearAnimationState(elementId: string): void {
    this.animationStates.delete(elementId);
  }

  /**
   * Apply animation to element with proper cleanup
   */
  private applyAnimation(
    registration: ElementRegistration,
    animationDef: AnimationDefinition,
    type: AnimationType
  ): void {
    const { element, callbacks } = registration;

    // Remove any existing animation classes
    Object.values(this.animationRegistry).forEach(def => {
      element.classList.remove(def.cssClass);
    });

    // Trigger start callback
    callbacks?.onAnimationStart?.(type);

    // Add animation class
    element.classList.add(animationDef.cssClass);

    //console.log('🎬 [AnimationFactory] CSS class applied:', {
    //  className: animationDef.cssClass,
    //  element: element.tagName,
    //  currentClasses: Array.from(element.classList)
    //});

    // Schedule cleanup
    setTimeout(() => {
      element.classList.remove(animationDef.cssClass);

      // Clear animation state
      this.animationStates.delete(this.getElementId(element));

      // Trigger end callback
      callbacks?.onAnimationEnd?.(type);

      //console.log('🎬 [AnimationFactory] Animation cleanup completed:', {
      //  className: animationDef.cssClass,
      //  type
      //});
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
      //console.log('🎬 [AnimationFactory] Mount-time animation overriding current:', {
      //  elementId,
      //  newType: type,
      //  currentType: currentState.type,
      //  source
      //});
      return true;
    }

    // Allow WebSocket animations to override callbacks
    if (source === 'websocket' && currentState.source === 'callback') {
      //console.log('🎬 [AnimationFactory] WebSocket animation overriding callback:', {
      //  elementId,
      //  newType: type,
      //  currentType: currentState.type
      //});
      return true;
    }

    // Block everything else
    //console.log('🎬 [AnimationFactory] Animation blocked by coordination:', {
    //  elementId,
    //  requestedType: type,
    //  requestedSource: source,
    //  currentType: currentState.type,
    //  currentSource: currentState.source,
    //  timeSinceLastAnimation,
    //  reason: timeSinceLastAnimation <= this.ANIMATION_COOLDOWN ? 'cooldown' : 'priority'
    //});

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

// DEBUG: Export to window for debugging and testing
if (typeof window !== 'undefined') {
  (window as any).animationFactory = animationFactory;
  console.log('🎬 AnimationFactory: Exposed to window.animationFactory for debugging');
}

export default animationFactory;