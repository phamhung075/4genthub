import { vi } from 'vitest';

export const animationFactory = {
  registerElement: vi.fn(),
  unregisterElement: vi.fn(),
  animate: vi.fn().mockReturnValue(true),
  getAnimationState: vi.fn().mockReturnValue(null),
  reset: vi.fn(),
};

export default animationFactory;

export type { AnimationType, AnimationSource, AnimationState, AnimationDefinition } from '../../types/animationTypes';
