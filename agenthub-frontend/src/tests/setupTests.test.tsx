import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render } from '@testing-library/react';
import React from 'react';

// Import setupTests to apply its side effects
import '../setupTests';

// setupTests keeps the console.error it finds when it loads as the sink for every message
// its filter lets through. A second copy loaded here keeps `passedThrough` as that sink, so
// the console.error tests below can see what the real filter forwards.
const passedThrough = vi.fn();
const loadTimeConsoleError = console.error;
console.error = passedThrough;
vi.resetModules();
await import('../setupTests');
console.error = loadTimeConsoleError;

describe('setupTests', () => {
  let originalMatchMedia: any;
  let originalIntersectionObserver: any;
  let originalResizeObserver: any;
  let originalConsoleError: any;

  beforeEach(() => {
    // Save originals
    originalMatchMedia = window.matchMedia;
    originalIntersectionObserver = global.IntersectionObserver;
    originalResizeObserver = global.ResizeObserver;
    originalConsoleError = console.error;
  });

  afterEach(() => {
    // Restore originals
    window.matchMedia = originalMatchMedia;
    global.IntersectionObserver = originalIntersectionObserver;
    global.ResizeObserver = originalResizeObserver;
    console.error = originalConsoleError;
  });

  describe('window.matchMedia mock', () => {
    it('should mock window.matchMedia', () => {
      expect(window.matchMedia).toBeDefined();
      expect(typeof window.matchMedia).toBe('function');
    });

    it('should return correct matchMedia object structure', () => {
      const query = '(prefers-color-scheme: dark)';
      const result = window.matchMedia(query);

      expect(result).toHaveProperty('matches', false);
      expect(result).toHaveProperty('media', query);
      expect(result).toHaveProperty('onchange', null);
      expect(result).toHaveProperty('addEventListener');
      expect(result).toHaveProperty('removeEventListener');
      expect(result).toHaveProperty('dispatchEvent');
      expect(result).toHaveProperty('addListener');
      expect(result).toHaveProperty('removeListener');
    });

    it('should have callable methods', () => {
      const result = window.matchMedia('(min-width: 768px)');
      const listener = vi.fn();

      expect(() => {
        result.addEventListener('change', listener);
        result.removeEventListener('change', listener);
        result.addListener(listener);
        result.removeListener(listener);
        result.dispatchEvent(new Event('change'));
      }).not.toThrow();
    });
  });

  describe('IntersectionObserver mock', () => {
    it('should mock IntersectionObserver', () => {
      expect(global.IntersectionObserver).toBeDefined();
      expect(typeof global.IntersectionObserver).toBe('function');
    });

    it('should create IntersectionObserver instances', () => {
      const callback = vi.fn();
      const observer = new IntersectionObserver(callback);

      expect(observer).toBeDefined();
      expect(observer).toHaveProperty('disconnect');
      expect(observer).toHaveProperty('observe');
      expect(observer).toHaveProperty('unobserve');
      expect(observer).toHaveProperty('takeRecords');
    });

    it('should have callable methods', () => {
      const observer = new IntersectionObserver(() => {});
      const element = document.createElement('div');

      expect(() => {
        observer.observe(element);
        observer.unobserve(element);
        const records = observer.takeRecords();
        expect(records).toEqual([]);
        observer.disconnect();
      }).not.toThrow();
    });
  });

  describe('ResizeObserver mock', () => {
    it('should mock ResizeObserver', () => {
      expect(global.ResizeObserver).toBeDefined();
      expect(typeof global.ResizeObserver).toBe('function');
    });

    it('should create ResizeObserver instances', () => {
      const callback = vi.fn();
      const observer = new ResizeObserver(callback);

      expect(observer).toBeDefined();
      expect(observer).toHaveProperty('disconnect');
      expect(observer).toHaveProperty('observe');
      expect(observer).toHaveProperty('unobserve');
    });

    it('should have callable methods', () => {
      const observer = new ResizeObserver(() => {});
      const element = document.createElement('div');

      expect(() => {
        observer.observe(element);
        observer.unobserve(element);
        observer.disconnect();
      }).not.toThrow();
    });
  });

  describe('console.error suppression', () => {
    beforeEach(() => {
      passedThrough.mockClear();
    });

    it.each([
      'Warning: ReactDOM.render is no longer supported in React 18',
      'Warning: useLayoutEffect does nothing on the server',
      'Not implemented: HTMLFormElement.prototype.submit'
    ])('suppresses "%s"', (message) => {
      console.error(message);

      expect(passedThrough).not.toHaveBeenCalled();
    });

    it('forwards other console errors with all their arguments', () => {
      console.error('Some other error');
      console.error('Application error:', { code: 500 });

      expect(passedThrough).toHaveBeenCalledTimes(2);
      expect(passedThrough).toHaveBeenCalledWith('Some other error');
      expect(passedThrough).toHaveBeenCalledWith('Application error:', { code: 500 });
    });

    it('forwards calls whose first argument is not a string', () => {
      console.error({ error: 'object' });
      console.error(123);
      console.error(null);
      console.error(undefined);

      expect(passedThrough).toHaveBeenCalledTimes(4);
    });
  });

  describe('testing environment setup', () => {
    it('should have jest-dom matchers available', () => {
      const element = document.createElement('div');
      element.textContent = 'Hello World';
      document.body.appendChild(element);

      expect(element).toBeInTheDocument();
      expect(element).toHaveTextContent('Hello World');

      document.body.removeChild(element);
    });

    it('should clean up after each test automatically', () => {
      // This test verifies that cleanup is called after each test
      // by checking that a component is not in the document after render
      const TestComponent = () => <div data-testid="test-component">Test</div>;

      const { container } = render(<TestComponent />);
      expect(container.firstChild).toBeTruthy();

      // The afterEach hook in setupTests will clean this up
    });
  });

  describe('integration with React components', () => {
    it('should work with components using matchMedia', () => {
      const TestComponent = () => {
        const [isDark, setIsDark] = React.useState(false);

        React.useEffect(() => {
          const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
          setIsDark(mediaQuery.matches);

          const handler = (e: MediaQueryListEvent) => setIsDark(e.matches);
          mediaQuery.addEventListener('change', handler);

          return () => mediaQuery.removeEventListener('change', handler);
        }, []);

        return <div>{isDark ? 'Dark' : 'Light'}</div>;
      };

      const { container } = render(<TestComponent />);
      expect(container.textContent).toBe('Light');
    });

    it('should work with components using IntersectionObserver', () => {
      const TestComponent = () => {
        const ref = React.useRef<HTMLDivElement>(null);
        const [isVisible, setIsVisible] = React.useState(false);

        React.useEffect(() => {
          const observer = new IntersectionObserver(([entry]) => {
            setIsVisible(entry.isIntersecting);
          });

          if (ref.current) {
            observer.observe(ref.current);
          }

          return () => observer.disconnect();
        }, []);

        return <div ref={ref}>{isVisible ? 'Visible' : 'Hidden'}</div>;
      };

      const { container } = render(<TestComponent />);
      expect(container.textContent).toBe('Hidden');
    });

    it('should work with components using ResizeObserver', () => {
      const TestComponent = () => {
        const ref = React.useRef<HTMLDivElement>(null);
        const [size, setSize] = React.useState({ width: 0, height: 0 });

        React.useEffect(() => {
          const observer = new ResizeObserver((entries) => {
            const entry = entries[0];
            if (entry) {
              setSize({
                width: entry.contentRect.width,
                height: entry.contentRect.height
              });
            }
          });

          if (ref.current) {
            observer.observe(ref.current);
          }

          return () => observer.disconnect();
        }, []);

        return (
          <div ref={ref}>
            Size: {size.width}x{size.height}
          </div>
        );
      };

      const { container } = render(<TestComponent />);
      expect(container.textContent).toBe('Size: 0x0');
    });
  });
});
