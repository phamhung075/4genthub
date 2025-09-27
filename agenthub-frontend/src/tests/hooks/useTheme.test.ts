import { renderHook } from '@testing-library/react';
import React from 'react';
import { useTheme } from '../../hooks/useTheme';
import { ThemeContext } from '../../contexts/ThemeContext';

describe('useTheme', () => {
  it('throws error when used outside ThemeProvider', () => {
    // Suppress console.error for this test
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    
    const { result } = renderHook(() => useTheme());
    
    expect(result.error).toEqual(
      new Error('useTheme must be used within a ThemeProvider')
    );
    
    consoleSpy.mockRestore();
  });

  it('returns theme context value when used within ThemeProvider', () => {
    const mockContextValue = {
      theme: 'light' as const,
      toggleTheme: jest.fn(),
      setTheme: jest.fn(),
    };

    const wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
      <ThemeContext.Provider value={mockContextValue}>
        {children}
      </ThemeContext.Provider>
    );

    const { result } = renderHook(() => useTheme(), { wrapper });

    expect(result.current).toEqual(mockContextValue);
    expect(result.current.theme).toBe('light');
    expect(result.current.toggleTheme).toBe(mockContextValue.toggleTheme);
    expect(result.current.setTheme).toBe(mockContextValue.setTheme);
  });

  it('returns dark theme context value', () => {
    const mockContextValue = {
      theme: 'dark' as const,
      toggleTheme: jest.fn(),
      setTheme: jest.fn(),
    };

    const wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
      <ThemeContext.Provider value={mockContextValue}>
        {children}
      </ThemeContext.Provider>
    );

    const { result } = renderHook(() => useTheme(), { wrapper });

    expect(result.current.theme).toBe('dark');
  });

  it('updates when context value changes', () => {
    let theme: 'light' | 'dark' = 'light';
    const toggleTheme = jest.fn(() => {
      theme = theme === 'light' ? 'dark' : 'light';
    });
    const setTheme = jest.fn((newTheme: 'light' | 'dark') => {
      theme = newTheme;
    });

    const Wrapper = ({ children }: { children: React.ReactNode }) => {
      const [currentTheme, setCurrentTheme] = React.useState<'light' | 'dark'>(theme);
      
      React.useEffect(() => {
        setCurrentTheme(theme);
      }, []);

      const contextValue = {
        theme: currentTheme,
        toggleTheme: () => {
          toggleTheme();
          setCurrentTheme(theme === 'light' ? 'dark' : 'light');
        },
        setTheme: (newTheme: 'light' | 'dark') => {
          setTheme(newTheme);
          setCurrentTheme(newTheme);
        },
      };

      return (
        <ThemeContext.Provider value={contextValue}>
          {children}
        </ThemeContext.Provider>
      );
    };

    const { result, rerender } = renderHook(() => useTheme(), { 
      wrapper: Wrapper,
    });

    expect(result.current.theme).toBe('light');

    // Toggle theme
    result.current.toggleTheme();
    rerender();
    
    expect(result.current.theme).toBe('dark');
    expect(toggleTheme).toHaveBeenCalled();
  });

  it('maintains referential equality of functions', () => {
    const mockContextValue = {
      theme: 'light' as const,
      toggleTheme: jest.fn(),
      setTheme: jest.fn(),
    };

    const wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
      <ThemeContext.Provider value={mockContextValue}>
        {children}
      </ThemeContext.Provider>
    );

    const { result, rerender } = renderHook(() => useTheme(), { wrapper });

    const firstToggleTheme = result.current.toggleTheme;
    const firstSetTheme = result.current.setTheme;

    rerender();

    expect(result.current.toggleTheme).toBe(firstToggleTheme);
    expect(result.current.setTheme).toBe(firstSetTheme);
  });

  it('allows calling context functions', () => {
    const mockToggleTheme = jest.fn();
    const mockSetTheme = jest.fn();

    const mockContextValue = {
      theme: 'light' as const,
      toggleTheme: mockToggleTheme,
      setTheme: mockSetTheme,
    };

    const wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
      <ThemeContext.Provider value={mockContextValue}>
        {children}
      </ThemeContext.Provider>
    );

    const { result } = renderHook(() => useTheme(), { wrapper });

    // Call toggleTheme
    result.current.toggleTheme();
    expect(mockToggleTheme).toHaveBeenCalledTimes(1);

    // Call setTheme
    result.current.setTheme('dark');
    expect(mockSetTheme).toHaveBeenCalledWith('dark');
    expect(mockSetTheme).toHaveBeenCalledTimes(1);
  });

  it('works with multiple hooks in the same provider', () => {
    const mockContextValue = {
      theme: 'light' as const,
      toggleTheme: jest.fn(),
      setTheme: jest.fn(),
    };

    const wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
      <ThemeContext.Provider value={mockContextValue}>
        {children}
      </ThemeContext.Provider>
    );

    const { result: result1 } = renderHook(() => useTheme(), { wrapper });
    const { result: result2 } = renderHook(() => useTheme(), { wrapper });

    // Both hooks should return the same context value
    expect(result1.current).toBe(result2.current);
    expect(result1.current.theme).toBe(result2.current.theme);
    expect(result1.current.toggleTheme).toBe(result2.current.toggleTheme);
    expect(result1.current.setTheme).toBe(result2.current.setTheme);
  });
});