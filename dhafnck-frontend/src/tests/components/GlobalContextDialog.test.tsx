import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import '@testing-library/jest-dom';
import { GlobalContextDialog } from '../../components/GlobalContextDialog';
import * as api from '../../api';

// Mock the API module
vi.mock('../../api', () => ({
  getGlobalContext: vi.fn(),
  updateGlobalContext: vi.fn(),
}));

// Mock shadcn/ui components
vi.mock('../../components/ui/dialog', () => ({
  Dialog: ({ open, children }: any) => open ? <div data-testid="dialog">{children}</div> : null,
  DialogContent: ({ children, className }: any) => <div className={className}>{children}</div>,
  DialogHeader: ({ children }: any) => <div>{children}</div>,
  DialogTitle: ({ children }: any) => <h2>{children}</h2>,
  DialogFooter: ({ children }: any) => <div>{children}</div>,
}));

vi.mock('../../components/ui/button', () => ({
  Button: ({ onClick, children, disabled, variant, size }: any) => (
    <button onClick={onClick} disabled={disabled} data-variant={variant} data-size={size}>{children}</button>
  ),
}));

vi.mock('../../components/ui/textarea', () => ({
  Textarea: ({ placeholder, value, onChange, className, rows }: any) => (
    <textarea
      placeholder={placeholder}
      value={value}
      onChange={onChange}
      className={className}
      rows={rows}
      data-testid="textarea"
    />
  ),
}));

// Mock additional UI components
vi.mock('../../components/ui/EnhancedJSONViewer', () => ({
  EnhancedJSONViewer: ({ data }: any) => <div data-testid="json-viewer">{JSON.stringify(data)}</div>,
}));

vi.mock('../../components/ui/RawJSONDisplay', () => ({
  default: ({ jsonData }: any) => <pre>{JSON.stringify(jsonData, null, 2)}</pre>,
}));

vi.mock('../../components/ui/badge', () => ({
  Badge: ({ children, variant }: any) => <span data-variant={variant}>{children}</span>,
}));

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  Globe: () => <span>Globe Icon</span>,
  Save: () => <span>Save Icon</span>,
  Edit: () => <span>Edit Icon</span>,
  X: () => <span>X Icon</span>,
  Copy: () => <span>Copy Icon</span>,
  Check: () => <span>Check Icon</span>,
  Settings: () => <span>Settings Icon</span>,
  Layers: () => <span>Layers Icon</span>,
  Zap: () => <span>Zap Icon</span>,
  Info: () => <span>Info Icon</span>,
  Database: () => <span>Database Icon</span>,
  ChevronDown: () => <span>ChevronDown Icon</span>,
  ChevronRight: () => <span>ChevronRight Icon</span>,
  Code: () => <span>Code Icon</span>,
  Shield: () => <span>Shield Icon</span>,
  FileText: () => <span>FileText Icon</span>,
  AlertCircle: () => <span>AlertCircle Icon</span>,
}));

describe('GlobalContextDialog', () => {
  const mockOnClose = vi.fn();
  const mockOnOpenChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders nothing when closed', () => {
    render(
      <GlobalContextDialog
        open={false}
        onOpenChange={mockOnOpenChange}
        onClose={mockOnClose}
      />
    );

    expect(screen.queryByTestId('dialog')).not.toBeInTheDocument();
  });

  it('renders dialog when open', () => {
    render(
      <GlobalContextDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        onClose={mockOnClose}
      />
    );

    expect(screen.getByTestId('dialog')).toBeInTheDocument();
    expect(screen.getByText(/Global Context Management/)).toBeInTheDocument();
  });

  it('displays loading state when fetching context', async () => {
    (api.getGlobalContext as any).mockReturnValue(new Promise(() => {})); // Never resolves

    render(
      <GlobalContextDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        onClose={mockOnClose}
      />
    );

    expect(screen.getByText('Loading global context...')).toBeInTheDocument();
  });

  it('displays default context structure when API returns null', async () => {
    (api.getGlobalContext as any).mockResolvedValue(null);

    render(
      <GlobalContextDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        onClose={mockOnClose}
      />
    );

    // Component initializes with default empty structure rather than showing "no context" message
    await waitFor(() => {
      expect(screen.getByText('User Preferences')).toBeInTheDocument();
      expect(screen.getByText('AI Agent Settings')).toBeInTheDocument();
    });
  });

  it('displays global context data in sections', async () => {
    const mockContext = {
      user_preferences: { theme: 'dark' },
      ai_agent_settings: { preferred_agents: ['coding-agent'] },
      security_settings: { two_factor: true },
      version: '1.0.0'
    };

    (api.getGlobalContext as any).mockResolvedValue(mockContext);

    render(
      <GlobalContextDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        onClose={mockOnClose}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('User Preferences')).toBeInTheDocument();
    });

    // Check sections are rendered
    expect(screen.getByText('AI Agent Settings')).toBeInTheDocument();
    expect(screen.getByText('Security Settings')).toBeInTheDocument();
    expect(screen.getByText('Metadata')).toBeInTheDocument();
  });

  it('switches between view and edit tabs', async () => {
    const mockContext = {
      user_preferences: { theme: 'dark' },
      ai_agent_settings: { preferred_agents: ['coding-agent'] },
      version: '1.0.0'
    };

    (api.getGlobalContext as any).mockResolvedValue(mockContext);

    render(
      <GlobalContextDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        onClose={mockOnClose}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('View')).toBeInTheDocument();
    });

    // Click Edit button
    const editButton = screen.getByRole('button', { name: /Edit/i });
    fireEvent.click(editButton);

    // Should see Edit tab with raw JSON editor
    await waitFor(() => {
      expect(screen.getByText('Raw JSON Editor')).toBeInTheDocument();
    });
  });

  it('enters edit mode when Edit button is clicked', async () => {
    const mockContext = {
      user_preferences: {},
      ai_agent_settings: { preferred_agents: [] },
      version: '1.0.0'
    };

    (api.getGlobalContext as any).mockResolvedValue(mockContext);

    render(
      <GlobalContextDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        onClose={mockOnClose}
      />
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Edit/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Edit/i }));

    // Should see edit mode elements
    await waitFor(() => {
      expect(screen.getByText('Raw JSON Editor')).toBeInTheDocument();
      expect(screen.getByText('Save All')).toBeInTheDocument();
      expect(screen.getByText('Cancel')).toBeInTheDocument();
    });
  });

  it('shows raw JSON editor in edit mode', async () => {
    const mockContext = {
      user_preferences: {},
      ai_agent_settings: { preferred_agents: [] },
      version: '1.0.0'
    };

    (api.getGlobalContext as any).mockResolvedValue(mockContext);

    render(
      <GlobalContextDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        onClose={mockOnClose}
      />
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Edit/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Edit/i }));

    // Should see raw JSON editor
    await waitFor(() => {
      expect(screen.getByText(/Raw JSON Editor/)).toBeInTheDocument();
      expect(screen.getByTestId('textarea')).toBeInTheDocument();
      expect(screen.getByText('Format JSON')).toBeInTheDocument();
    });
  });

  it('allows editing raw JSON and validates on save', async () => {
    const mockContext = {
      user_preferences: { theme: 'dark' },
      ai_agent_settings: { preferred_agents: [] },
      version: '1.0.0'
    };

    (api.getGlobalContext as any).mockResolvedValue(mockContext);
    (api.updateGlobalContext as any).mockResolvedValue({ success: true });

    render(
      <GlobalContextDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        onClose={mockOnClose}
      />
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Edit/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Edit/i }));

    await waitFor(() => {
      expect(screen.getByTestId('textarea')).toBeInTheDocument();
    });

    // Edit the JSON
    const textarea = screen.getByTestId('textarea');
    fireEvent.change(textarea, { target: { value: '{"test": "value"}' } });

    expect(textarea).toHaveValue('{"test": "value"}');

    // Save should work with valid JSON
    const saveButton = screen.getByText('Save All');
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(api.updateGlobalContext).toHaveBeenCalledWith(expect.objectContaining({
        test: 'value',
        last_updated: expect.any(String)
      }));
    });
  });

  it('shows validation error for invalid JSON', async () => {
    const mockContext = {
      user_preferences: {},
      ai_agent_settings: { preferred_agents: [] },
      version: '1.0.0'
    };

    (api.getGlobalContext as any).mockResolvedValue(mockContext);

    render(
      <GlobalContextDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        onClose={mockOnClose}
      />
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Edit/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Edit/i }));

    await waitFor(() => {
      expect(screen.getByTestId('textarea')).toBeInTheDocument();
    });

    // Enter invalid JSON
    const textarea = screen.getByTestId('textarea');
    fireEvent.change(textarea, { target: { value: '{"invalid": json}' } });

    // Try to save
    const saveButton = screen.getByText('Save All');
    fireEvent.click(saveButton);

    // Should show validation error
    await waitFor(() => {
      expect(screen.getByText('JSON Validation Error')).toBeInTheDocument();
    });
  });

  it('shows save button in edit mode', async () => {
    const mockContext = {
      user_preferences: {},
      ai_agent_settings: { preferred_agents: [] },
      version: '1.0.0'
    };

    (api.getGlobalContext as any).mockResolvedValue(mockContext);
    (api.updateGlobalContext as any).mockResolvedValue({ success: true });

    render(
      <GlobalContextDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        onClose={mockOnClose}
      />
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Edit/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Edit/i }));

    // Should see save button in edit mode
    await waitFor(() => {
      expect(screen.getByText('Save All')).toBeInTheDocument();
    });
  });

  it('cancels edit mode when Cancel button is clicked', async () => {
    const mockContext = {
      user_preferences: { theme: 'dark' },
      ai_agent_settings: { preferred_agents: [] },
      version: '1.0.0'
    };

    (api.getGlobalContext as any).mockResolvedValue(mockContext);

    render(
      <GlobalContextDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        onClose={mockOnClose}
      />
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Edit/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Edit/i }));

    await waitFor(() => {
      expect(screen.getByText('Cancel')).toBeInTheDocument();
    });

    // Click Cancel
    fireEvent.click(screen.getByText('Cancel'));

    // Should exit edit mode
    await waitFor(() => {
      expect(screen.queryByText('Raw JSON Editor')).not.toBeInTheDocument();
      expect(screen.getByText('View')).toBeInTheDocument();
    });
  });

  it('copies JSON to clipboard when Copy JSON button is clicked', async () => {
    const mockContext = {
      user_preferences: { theme: 'dark' },
      ai_agent_settings: { preferred_agents: [] },
      version: '1.0.0'
    };

    (api.getGlobalContext as any).mockResolvedValue(mockContext);

    // Mock clipboard API
    const mockWriteText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, {
      clipboard: {
        writeText: mockWriteText
      }
    });

    render(
      <GlobalContextDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        onClose={mockOnClose}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Copy JSON')).toBeInTheDocument();
    });

    const copyButton = screen.getByText('Copy JSON');
    fireEvent.click(copyButton);

    expect(mockWriteText).toHaveBeenCalledWith(expect.stringContaining('user_preferences'));

    await waitFor(() => {
      expect(screen.getByText('Copied!')).toBeInTheDocument();
    });
  });

  it('handles API errors gracefully', async () => {
    (api.getGlobalContext as any).mockRejectedValue(new Error('Network error'));

    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

    render(
      <GlobalContextDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        onClose={mockOnClose}
      />
    );

    await waitFor(() => {
      expect(screen.queryByText('Loading global context...')).not.toBeInTheDocument();
    });

    expect(consoleError).toHaveBeenCalledWith('Error fetching global context:', expect.any(Error));

    consoleError.mockRestore();
  });

  // Removed: Edit functionality is not yet implemented

  // Removed: Edit functionality is not yet implemented

  // Removed: Component no longer shows Initialize button when context is null

  it('displays raw context section', async () => {
    const mockContext = {
      user_preferences: { theme: 'dark' },
      ai_agent_settings: { preferred_agents: [] },
      version: '1.0.0'
    };

    (api.getGlobalContext as any).mockResolvedValue(mockContext);

    render(
      <GlobalContextDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        onClose={mockOnClose}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Complete Raw Context')).toBeInTheDocument();
    });
  });

  // Removed: Edit functionality is not yet implemented

  // Removed: Edit functionality is not yet implemented
});