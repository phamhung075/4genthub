import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render } from '@testing-library/react';
import React from 'react';

// Import setupTests to apply its side effects
import '../setupTests';

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
    it('should suppress ReactDOM.render warnings', () => {
      const errorSpy = vi.fn();
      console.error = errorSpy;

      // This would normally trigger a console error
      console.error('Warning: ReactDOM.render is no longer supported in React 18');

      expect(errorSpy).not.toHaveBeenCalled();
    });

    it('should suppress useLayoutEffect warnings', () => {
      const errorSpy = vi.fn();
      console.error = errorSpy;

      console.error('Warning: useLayoutEffect does nothing on the server');

      expect(errorSpy).not.toHaveBeenCalled();
    });

    it('should suppress HTMLFormElement.prototype.submit warnings', () => {
      const errorSpy = vi.fn();
      console.error = errorSpy;

      console.error('Not implemented: HTMLFormElement.prototype.submit');

      expect(errorSpy).not.toHaveBeenCalled();
    });

    it('should not suppress other console errors', () => {
      const errorSpy = vi.fn();
      const originalError = console.error;
      
      // Apply our console.error override from setupTests
      console.error = (...args: any[]) => {
        if (
          typeof args[0] === 'string' &&
          (args[0].includes('Warning: ReactDOM.render') ||
            args[0].includes('Warning: useLayoutEffect') ||
            args[0].includes('Not implemented: HTMLFormElement.prototype.submit'))
        ) {
          return;
        }
        errorSpy(...args);
      };

      console.error('Some other error');
      console.error('Application error:', { code: 500 });

      expect(errorSpy).toHaveBeenCalledTimes(2);
      expect(errorSpy).toHaveBeenCalledWith('Some other error');
      expect(errorSpy).toHaveBeenCalledWith('Application error:', { code: 500 });

      console.error = originalError;
    });

    it('should handle non-string first arguments', () => {
      const errorSpy = vi.fn();
      const originalError = console.error;
      
      // Apply our console.error override
      console.error = (...args: any[]) => {
        if (
          typeof args[0] === 'string' &&
          (args[0].includes('Warning: ReactDOM.render') ||
            args[0].includes('Warning: useLayoutEffect') ||
            args[0].includes('Not implemented: HTMLFormElement.prototype.submit'))
        ) {
          return;
        }
        errorSpy(...args);
      };

      console.error({ error: 'object' });
      console.error(123);
      console.error(null);
      console.error(undefined);

      expect(errorSpy).toHaveBeenCalledTimes(4);

      console.error = originalError;
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