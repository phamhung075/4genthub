/**
 * Animation Types
 * Consolidated types for animation system and WebSocket animations
 */

import type { EntityType } from './serviceTypes';

// =============================================================================
// Animation Factory Types
// =============================================================================

export type AnimationType = 'create' | 'delete' | 'update' | 'complete';
export type AnimationSource = 'websocket' | 'callback' | 'mount';

export interface AnimationDefinition {
  cssClass: string;
  duration: number; // milliseconds
  description: string;
}

export interface AnimationState {
  type: AnimationType;
  startTime: number;
  source: AnimationSource;
}

export interface ElementRegistration {
  element: HTMLElement;
  entityType: EntityType; // ✅ FIX 2025-11-22: Added entity type for correct CSS class selection
  callbacks?: {
    onAnimationStart?: (type: AnimationType) => void;
    onAnimationEnd?: (type: AnimationType) => void;
  };
}

// =============================================================================
// Subtask Animation Types
// =============================================================================

export type SubtaskAnimationState = 'none' | 'creating' | 'deleting' | 'updating';

export interface AnimationCallbacks {
  playCreateAnimation: () => void;
  playDeleteAnimation: () => void;
  playUpdateAnimation: () => void;
}
