import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import '@testing-library/jest-dom';
import { ThemeContext, ThemeProvider } from '../../contexts/ThemeContext';
import { applyThemeToRoot } from '../../theme/themeConfig';

// Mock the theme config module
vi.mock('../../theme/themeConfig', () => ({
  applyThemeToRoot: vi.fn(),
}));

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

// Mock matchMedia
const matchMediaMock = vi.fn();
Object.defineProperty(window, 'matchMedia', {
  value: matchMediaMock,
});

// Test component to consume context
const TestComponent = () => {
  const context = React.useContext(ThemeContext);
  if (!context) {
    return <div>No context</div>;
  }
  return (
    <div>
      <div>Theme: {context.theme}</div>
      <button onClick={context.toggleTheme}>Toggle Theme</button>
      <button onClick={() => context.setTheme('dark')}>Set Dark</button>
      <button onClick={() => context.setTheme('light')}>Set Light</button>
    </div>
  );
};

describe('ThemeContext', () => {
  const mockApplyThemeToRoot = applyThemeToRoot as ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();
    document.documentElement.classList.remove('light', 'dark');
    
    // Default matchMedia mock
    matchMediaMock.mockImplementation((query) => ({
      matches: false,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
    }));
  });

  describe('ThemeProvider', () => {
    it('provides default theme as light', () => {
      localStorageMock.getItem.mockReturnValue(null);
      
      render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      );

      expect(screen.getByText('Theme: light')).toBeInTheDocument();
    });

    it('uses custom default theme', () => {
      localStorageMock.getItem.mockReturnValue(null);
      
      render(
        <ThemeProvider defaultTheme="dark">
          <TestComponent />
        </ThemeProvider>
      );

      expect(screen.getByText('Theme: dark')).toBeInTheDocument();
    });

    it('loads theme from localStorage', () => {
      localStorageMock.getItem.mockReturnValue('dark');
      
      render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      );

      expect(screen.getByText('Theme: dark')).toBeInTheDocument();
      expect(localStorageMock.getItem).toHaveBeenCalledWith('theme');
    });

    it('respects system preference when no saved theme', () => {
      localStorageMock.getItem.mockReturnValue(null);
      matchMediaMock.mockImplementation((query) => ({
        matches: query === '(prefers-color-scheme: dark)',
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      }));
      
      render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      );

      expect(screen.getByText('Theme: dark')).toBeInTheDocument();
    });

    it('applies theme class to document root', () => {
      localStorageMock.getItem.mockReturnValue('dark');
      
      render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      );

      expect(document.documentElement.classList.contains('dark')).toBe(true);
      expect(document.documentElement.classList.contains('light')).toBe(false);
    });

    it('calls applyThemeToRoot with correct parameter', () => {
      localStorageMock.getItem.mockReturnValue('dark');
      
      render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      );

      expect(mockApplyThemeToRoot).toHaveBeenCalledWith(true);
    });

    it('saves theme to localStorage', () => {
      localStorageMock.getItem.mockReturnValue('light');
      
      render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      );

      expect(localStorageMock.setItem).toHaveBeenCalledWith('theme', 'light');
    });

    it('toggles theme correctly', () => {
      localStorageMock.getItem.mockReturnValue('light');
      
      render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      );

      expect(screen.getByText('Theme: light')).toBeInTheDocument();

      fireEvent.click(screen.getByText('Toggle Theme'));

      expect(screen.getByText('Theme: dark')).toBeInTheDocument();
      expect(document.documentElement.classList.contains('dark')).toBe(true);
      expect(localStorageMock.setItem).toHaveBeenCalledWith('theme', 'dark');
      expect(mockApplyThemeToRoot).toHaveBeenCalledWith(true);
    });

    it('sets theme directly', () => {
      localStorageMock.getItem.mockReturnValue('light');
      
      render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      );

      fireEvent.click(screen.getByText('Set Dark'));

      expect(screen.getByText('Theme: dark')).toBeInTheDocument();
      expect(document.documentElement.classList.contains('dark')).toBe(true);
      expect(localStorageMock.setItem).toHaveBeenCalledWith('theme', 'dark');
    });

    it('removes previous theme class when changing', () => {
      localStorageMock.getItem.mockReturnValue('light');
      
      render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      );

      expect(document.documentElement.classList.contains('light')).toBe(true);

      fireEvent.click(screen.getByText('Toggle Theme'));

      expect(document.documentElement.classList.contains('light')).toBe(false);
      expect(document.documentElement.classList.contains('dark')).toBe(true);
    });

    it('listens to system theme changes', () => {
      const addEventListener = vi.fn();
      const removeEventListener = vi.fn();
      
      localStorageMock.getItem.mockReturnValue(null);
      matchMediaMock.mockImplementation(() => ({
        matches: false,
        addEventListener,
        removeEventListener,
      }));
      
      const { unmount } = render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      );

      expect(addEventListener).toHaveBeenCalledWith('change', expect.any(Function));

      unmount();

      expect(removeEventListener).toHaveBeenCalledWith('change', expect.any(Function));
    });

    it('uses fallback listeners for older browsers', () => {
      const addListener = vi.fn();
      const removeListener = vi.fn();
      
      localStorageMock.getItem.mockReturnValue(null);
      matchMediaMock.mockImplementation(() => ({
        matches: false,
        addListener,
        removeListener,
      }));
      
      const { unmount } = render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      );

      expect(addListener).toHaveBeenCalledWith(expect.any(Function));

      unmount();

      expect(removeListener).toHaveBeenCalledWith(expect.any(Function));
    });

    it('responds to system theme change when no saved preference', () => {
      let changeHandler: any;
      const addEventListener = vi.fn((event, handler) => {
        if (event === 'change') changeHandler = handler;
      });
      
      localStorageMock.getItem.mockReturnValue(null);
      matchMediaMock.mockImplementation(() => ({
        matches: false,
        addEventListener,
        removeEventListener: vi.fn(),
      }));
      
      render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      );

      expect(screen.getByText('Theme: light')).toBeInTheDocument();

      // Simulate system theme change
      localStorageMock.getItem.mockReturnValue(null); // Still no saved preference
      changeHandler({ matches: true });

      waitFor(() => {
        expect(screen.getByText('Theme: dark')).toBeInTheDocument();
      });
    });

    it('ignores system theme change when there is saved preference', () => {
      let changeHandler: any;
      const addEventListener = vi.fn((event, handler) => {
        if (event === 'change') changeHandler = handler;
      });
      
      localStorageMock.getItem.mockReturnValue('light');
      matchMediaMock.mockImplementation(() => ({
        matches: false,
        addEventListener,
        removeEventListener: vi.fn(),
      }));
      
      render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      );

      expect(screen.getByText('Theme: light')).toBeInTheDocument();

      // Simulate system theme change but with saved preference
      changeHandler({ matches: true });

      // Should still be light because there's a saved preference
      expect(screen.getByText('Theme: light')).toBeInTheDocument();
    });

    it('validates saved theme from localStorage', () => {
      localStorageMock.getItem.mockReturnValue('invalid-theme');
      
      render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      );

      // Should fallback to default theme
      expect(screen.getByText('Theme: light')).toBeInTheDocument();
    });

    it('renders multiple children correctly', () => {
      localStorageMock.getItem.mockReturnValue(null);
      
      render(
        <ThemeProvider>
          <div>First Child</div>
          <div>Second Child</div>
          <TestComponent />
        </ThemeProvider>
      );

      expect(screen.getByText('First Child')).toBeInTheDocument();
      expect(screen.getByText('Second Child')).toBeInTheDocument();
      expect(screen.getByText('Theme: light')).toBeInTheDocument();
    });
  });

  describe('ThemeContext without Provider', () => {
    it('returns undefined when used outside provider', () => {
      render(<TestComponent />);
      
      expect(screen.getByText('No context')).toBeInTheDocument();
    });
  });
});