import React from 'react';
import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';
import '@testing-library/jest-dom';
import { MuiThemeWrapper } from '../../contexts/MuiThemeProvider';
import { useTheme } from '../../hooks/useTheme';
import { getTheme } from '../../theme/muiTheme';
import { ThemeProvider as MuiThemeProvider, CssBaseline } from '@mui/material';

// Mock dependencies
vi.mock('../../hooks/useTheme');
vi.mock('../../theme/muiTheme');

// Mock Material-UI components
vi.mock('@mui/material', () => ({
  ThemeProvider: ({ theme, children }: any) => (
    <div data-testid="mui-theme-provider" data-theme={JSON.stringify(theme)}>
      {children}
    </div>
  ),
  CssBaseline: () => <div data-testid="css-baseline" />,
}));

describe('MuiThemeWrapper', () => {
  const mockUseTheme = useTheme as ReturnType<typeof vi.fn>;
  const mockGetTheme = getTheme as ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders children correctly', () => {
    mockUseTheme.mockReturnValue({
      theme: 'light',
      toggleTheme: vi.fn(),
      setTheme: vi.fn(),
    });
    mockGetTheme.mockReturnValue({ palette: { mode: 'light' } } as any);

    render(
      <MuiThemeWrapper>
        <div>Test Child Content</div>
      </MuiThemeWrapper>
    );

    expect(screen.getByText('Test Child Content')).toBeInTheDocument();
  });

  it('provides light theme when theme is light', () => {
    const lightTheme = { palette: { mode: 'light' }, custom: 'light-value' };
    mockUseTheme.mockReturnValue({
      theme: 'light',
      toggleTheme: vi.fn(),
      setTheme: vi.fn(),
    });
    mockGetTheme.mockReturnValue(lightTheme as any);

    render(
      <MuiThemeWrapper>
        <div>Content</div>
      </MuiThemeWrapper>
    );

    expect(mockGetTheme).toHaveBeenCalledWith('light');
    
    const themeProvider = screen.getByTestId('mui-theme-provider');
    expect(themeProvider).toHaveAttribute('data-theme', JSON.stringify(lightTheme));
  });

  it('provides dark theme when theme is dark', () => {
    const darkTheme = { palette: { mode: 'dark' }, custom: 'dark-value' };
    mockUseTheme.mockReturnValue({
      theme: 'dark',
      toggleTheme: vi.fn(),
      setTheme: vi.fn(),
    });
    mockGetTheme.mockReturnValue(darkTheme as any);

    render(
      <MuiThemeWrapper>
        <div>Content</div>
      </MuiThemeWrapper>
    );

    expect(mockGetTheme).toHaveBeenCalledWith('dark');
    
    const themeProvider = screen.getByTestId('mui-theme-provider');
    expect(themeProvider).toHaveAttribute('data-theme', JSON.stringify(darkTheme));
  });

  it('includes CssBaseline component', () => {
    mockUseTheme.mockReturnValue({
      theme: 'light',
      toggleTheme: vi.fn(),
      setTheme: vi.fn(),
    });
    mockGetTheme.mockReturnValue({ palette: { mode: 'light' } } as any);

    render(
      <MuiThemeWrapper>
        <div>Content</div>
      </MuiThemeWrapper>
    );

    expect(screen.getByTestId('css-baseline')).toBeInTheDocument();
  });

  it('updates theme when theme changes', () => {
    const lightTheme = { palette: { mode: 'light' } };
    const darkTheme = { palette: { mode: 'dark' } };
    
    mockUseTheme.mockReturnValue({
      theme: 'light',
      toggleTheme: vi.fn(),
      setTheme: vi.fn(),
    });
    mockGetTheme.mockReturnValue(lightTheme as any);

    const { rerender } = render(
      <MuiThemeWrapper>
        <div>Content</div>
      </MuiThemeWrapper>
    );

    expect(mockGetTheme).toHaveBeenCalledWith('light');

    // Change to dark theme
    mockUseTheme.mockReturnValue({
      theme: 'dark',
      toggleTheme: vi.fn(),
      setTheme: vi.fn(),
    });
    mockGetTheme.mockReturnValue(darkTheme as any);

    rerender(
      <MuiThemeWrapper>
        <div>Content</div>
      </MuiThemeWrapper>
    );

    expect(mockGetTheme).toHaveBeenCalledWith('dark');
  });

  it('renders multiple children correctly', () => {
    mockUseTheme.mockReturnValue({
      theme: 'light',
      toggleTheme: vi.fn(),
      setTheme: vi.fn(),
    });
    mockGetTheme.mockReturnValue({ palette: { mode: 'light' } } as any);

    render(
      <MuiThemeWrapper>
        <div>First Child</div>
        <div>Second Child</div>
        <span>Third Child</span>
      </MuiThemeWrapper>
    );

    expect(screen.getByText('First Child')).toBeInTheDocument();
    expect(screen.getByText('Second Child')).toBeInTheDocument();
    expect(screen.getByText('Third Child')).toBeInTheDocument();
  });

  it('handles null children gracefully', () => {
    mockUseTheme.mockReturnValue({
      theme: 'light',
      toggleTheme: vi.fn(),
      setTheme: vi.fn(),
    });
    mockGetTheme.mockReturnValue({ palette: { mode: 'light' } } as any);

    render(
      <MuiThemeWrapper>
        {null}
      </MuiThemeWrapper>
    );

    expect(screen.getByTestId('mui-theme-provider')).toBeInTheDocument();
    expect(screen.getByTestId('css-baseline')).toBeInTheDocument();
  });

  it('passes through complex React elements', () => {
    mockUseTheme.mockReturnValue({
      theme: 'light',
      toggleTheme: vi.fn(),
      setTheme: vi.fn(),
    });
    mockGetTheme.mockReturnValue({ palette: { mode: 'light' } } as any);

    const ComplexComponent = () => (
      <div>
        <h1>Title</h1>
        <p>Paragraph</p>
        <button>Button</button>
      </div>
    );

    render(
      <MuiThemeWrapper>
        <ComplexComponent />
      </MuiThemeWrapper>
    );

    expect(screen.getByText('Title')).toBeInTheDocument();
    expect(screen.getByText('Paragraph')).toBeInTheDocument();
    expect(screen.getByText('Button')).toBeInTheDocument();
  });

  it('renders MuiThemeProvider with correct theme', () => {
    const theme = { palette: { mode: 'light' }, typography: {} };
    mockUseTheme.mockReturnValue({
      theme: 'light',
      toggleTheme: vi.fn(),
      setTheme: vi.fn(),
    });
    mockGetTheme.mockReturnValue(theme as any);

    render(
      <MuiThemeWrapper>
        <div>Content</div>
      </MuiThemeWrapper>
    );

    const provider = screen.getByTestId('mui-theme-provider');
    expect(provider).toHaveAttribute('data-theme', JSON.stringify(theme));
  });

  it('renders CssBaseline component', () => {
    mockUseTheme.mockReturnValue({
      theme: 'light',
      toggleTheme: vi.fn(),
      setTheme: vi.fn(),
    });
    mockGetTheme.mockReturnValue({ palette: { mode: 'light' } } as any);

    render(
      <MuiThemeWrapper>
        <div>Content</div>
      </MuiThemeWrapper>
    );

    expect(screen.getByTestId('css-baseline')).toBeInTheDocument();
  });
});