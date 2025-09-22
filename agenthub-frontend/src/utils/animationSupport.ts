/**
 * Animation Support Utilities
 *
 * Provides feature detection and fallback strategies for CSS animations
 * to ensure consistent behavior across all browsers.
 */

// Cache for feature detection results
let propertySupport: boolean | null = null;
let animationSupport: boolean | null = null;

/**
 * Check if CSS @property is supported
 */
export const supportsCssProperty = (): boolean => {
  if (propertySupport !== null) return propertySupport;

  try {
    // @ts-ignore
    propertySupport = !!(CSS && CSS.supports && CSS.supports('@property', '--test'));
  } catch {
    propertySupport = false;
  }

  return propertySupport;
};

/**
 * Check if CSS animations are supported
 */
export const supportsCssAnimations = (): boolean => {
  if (animationSupport !== null) return animationSupport;

  try {
    const element = document.createElement('div');
    animationSupport = 'animation' in element.style ||
                     'webkitAnimation' in element.style ||
                     'mozAnimation' in element.style;
  } catch {
    animationSupport = false;
  }

  return animationSupport;
};

/**
 * Get the appropriate shimmer CSS based on browser capabilities
 */
export const getShimmerCSS = (color: string = '#06b6d4'): string => {
  if (supportsCssProperty()) {
    // Modern browsers with @property support
    return `
      @property --shimmer-angle {
        syntax: '<angle>';
        initial-value: 0deg;
        inherits: false;
      }

      @keyframes shimmer-modern {
        to {
          --shimmer-angle: 360deg;
        }
      }

      .shimmer-animation {
        background: conic-gradient(from var(--shimmer-angle), transparent 15%, ${color}, transparent 60%);
        animation: shimmer-modern 2.5s linear infinite;
      }
    `;
  } else {
    // Fallback for older browsers
    return `
      @keyframes shimmer-fallback {
        0% {
          background-position: -200% 0;
        }
        100% {
          background-position: 200% 0;
        }
      }

      .shimmer-animation {
        background: linear-gradient(
          90deg,
          transparent 0%,
          transparent 40%,
          ${color}88 50%,
          transparent 60%,
          transparent 100%
        );
        background-size: 200% 100%;
        animation: shimmer-fallback 2.5s linear infinite;
      }
    `;
  }
};

/**
 * Get browser info for debugging
 */
export const getBrowserInfo = () => {
  const ua = navigator.userAgent;
  const isChrome = /Chrome/.test(ua) && /Google Inc/.test(navigator.vendor);
  const isFirefox = /Firefox/.test(ua);
  const isSafari = /Safari/.test(ua) && !isChrome;
  const isEdge = /Edg/.test(ua);

  return {
    userAgent: ua,
    isChrome,
    isFirefox,
    isSafari,
    isEdge,
    supportsProperty: supportsCssProperty(),
    supportsAnimations: supportsCssAnimations()
  };
};

/**
 * Create a performance-safe animation observer
 */
export const createAnimationObserver = (callback: (supported: boolean) => void) => {
  // Test animation support
  const testElement = document.createElement('div');
  testElement.style.cssText = 'animation: test 1s; opacity: 0; position: absolute; pointer-events: none;';
  document.body.appendChild(testElement);

  // Check if animation actually runs
  setTimeout(() => {
    const computedStyle = getComputedStyle(testElement);
    const hasAnimation = computedStyle.animationName !== 'none';
    document.body.removeChild(testElement);
    callback(hasAnimation);
  }, 100);
};

/**
 * Debug animation capabilities
 */
export const debugAnimationSupport = () => {
  const info = getBrowserInfo();
  console.group('🎬 Animation Support Debug');
  console.log('Browser:', info.userAgent);
  console.log('CSS @property support:', info.supportsProperty);
  console.log('CSS animations support:', info.supportsAnimations);
  console.log('Browser type:', {
    Chrome: info.isChrome,
    Firefox: info.isFirefox,
    Safari: info.isSafari,
    Edge: info.isEdge
  });
  console.groupEnd();
  return info;
};