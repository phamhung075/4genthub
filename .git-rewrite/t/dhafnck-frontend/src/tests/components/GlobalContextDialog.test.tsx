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

  it('displays no context available state when context is null', async () => {
    (api.getGlobalContext as any).mockResolvedValue(null);

    render(
      <GlobalContextDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        onClose={mockOnClose}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('No Global Context Available')).toBeInTheDocument();
      expect(screen.getByText('Initialize Global Context')).toBeInTheDocument();
    });
  });

  it('displays global context data in tabs', async () => {
    const mockContext = {
      data: {
        resolved_context: {
          id: '7fa54328-bfb4-523c-ab6f-465e05e1bba5',
          global_settings: {
            autonomous_rules: { rule1: 'value1' },
            security_policies: { policy1: 'value2' },
            coding_standards: { standard1: 'value3' },
            workflow_templates: { template1: 'Template description' },
            delegation_rules: { rule1: 'delegation1' }
          }
        }
      }
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
      expect(screen.getByText('Organization Settings')).toBeInTheDocument();
    });

    // Check default tab (settings)
    expect(screen.getByText(/rule1: value1/)).toBeInTheDocument();
    expect(screen.getByText(/policy1: value2/)).toBeInTheDocument();
    expect(screen.getByText(/standard1: value3/)).toBeInTheDocument();
  });

  it('switches between tabs correctly', async () => {
    const mockContext = {
      data: {
        resolved_context: {
          id: '7fa54328-bfb4-523c-ab6f-465e05e1bba5',
          global_settings: {
            autonomous_rules: { rule1: 'value1' },
            workflow_templates: { auth_pattern: 'JWT authentication implementation' }
          }
        }
      }
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
      expect(screen.getByText('Organization Settings')).toBeInTheDocument();
    });

    // Switch to patterns tab
    fireEvent.click(screen.getByText('Global Patterns'));

    // Should see patterns content
    expect(screen.getByText(/auth_pattern:/)).toBeInTheDocument();
    expect(screen.getByText(/JWT authentication implementation/)).toBeInTheDocument();
  });

  it('enters edit mode when Edit button is clicked', async () => {
    const mockContext = {
      data: {
        resolved_context: {
          id: '7fa54328-bfb4-523c-ab6f-465e05e1bba5',
          global_settings: {}
        }
      }
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
      const editButton = screen.getAllByText('Edit')[0].parentElement;
      expect(editButton).toBeInTheDocument();
      fireEvent.click(editButton!);
    });

    // Should see textarea for editing
    expect(screen.getByTestId('textarea')).toBeInTheDocument();
    expect(screen.getByText('Save All')).toBeInTheDocument();
    expect(screen.getByText('Cancel')).toBeInTheDocument();
  });

  it('updates content when typing in edit mode', async () => {
    const mockContext = {
      data: {
        resolved_context: {
          id: '7fa54328-bfb4-523c-ab6f-465e05e1bba5',
          global_settings: {}
        }
      }
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
      const editButton = screen.getAllByText('Edit')[0].parentElement;
      fireEvent.click(editButton!);
    });

    const textarea = screen.getByTestId('textarea');
    fireEvent.change(textarea, { target: { value: 'api_url: https://api.example.com' } });

    expect(textarea).toHaveValue('api_url: https://api.example.com');
  });

  it('saves changes when Save button is clicked', async () => {
    const mockContext = {
      data: {
        resolved_context: {
          id: '7fa54328-bfb4-523c-ab6f-465e05e1bba5',
          global_settings: {}
        }
      }
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
      const editButton = screen.getAllByText('Edit')[0].parentElement;
      fireEvent.click(editButton!);
    });

    // Update content
    const textarea = screen.getByTestId('textarea');
    fireEvent.change(textarea, { target: { value: 'api_url: https://api.example.com' } });

    // Click save
    const saveButton = screen.getByText('Save All');
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(api.updateGlobalContext).toHaveBeenCalledWith({
        organizationSettings: { api_url: 'https://api.example.com' },
        globalPatterns: {},
        sharedCapabilities: [],
        metadata: expect.objectContaining({
          lastUpdated: expect.any(String),
          updatedBy: 'user'
        })
      });
    });
  });

  it('cancels edit mode when Cancel button is clicked', async () => {
    const mockContext = {
      data: {
        resolved_context: {
          id: '7fa54328-bfb4-523c-ab6f-465e05e1bba5',
          global_settings: {
            autonomous_rules: { original: 'value' }
          }
        }
      }
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
      const editButton = screen.getAllByText('Edit')[0].parentElement;
      fireEvent.click(editButton!);
    });

    // Change content
    const textarea = screen.getByTestId('textarea');
    fireEvent.change(textarea, { target: { value: 'new: value' } });

    // Cancel
    const cancelButton = screen.getByText('Cancel');
    fireEvent.click(cancelButton);

    // Should exit edit mode and restore original content
    await waitFor(() => {
      expect(screen.queryByTestId('textarea')).not.toBeInTheDocument();
      expect(screen.getByText(/original: value/)).toBeInTheDocument();
    });
  });

  it('copies JSON to clipboard when Copy JSON button is clicked', async () => {
    const mockContext = {
      data: {
        resolved_context: {
          id: '7fa54328-bfb4-523c-ab6f-465e05e1bba5',
          global_settings: {}
        }
      }
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

    expect(mockWriteText).toHaveBeenCalledWith(JSON.stringify(mockContext, null, 2));

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

  it('shows placeholder text for each tab in edit mode', async () => {
    const mockContext = {
      data: {
        resolved_context: {
          id: '7fa54328-bfb4-523c-ab6f-465e05e1bba5',
          global_settings: {}
        }
      }
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
      const editButton = screen.getAllByText('Edit')[0].parentElement;
      fireEvent.click(editButton!);
    });

    // Check settings tab placeholder
    const settingsTextarea = screen.getByTestId('textarea');
    expect(settingsTextarea).toHaveAttribute('placeholder', expect.stringContaining('key: value'));

    // Switch to patterns tab
    fireEvent.click(screen.getByText('Global Patterns'));
    expect(screen.getByTestId('textarea')).toHaveAttribute('placeholder', expect.stringContaining('pattern_name:'));

    // Switch to capabilities tab
    fireEvent.click(screen.getByText('Shared Capabilities'));
    expect(screen.getByTestId('textarea')).toHaveAttribute('placeholder', expect.stringContaining('- Authentication system'));

    // Switch to metadata tab
    fireEvent.click(screen.getByText('Metadata'));
    expect(screen.getByTestId('textarea')).toHaveAttribute('placeholder', expect.stringContaining('version: 1.0.0'));
  });

  it('parses patterns markdown correctly', async () => {
    const mockContext = {
      data: {
        resolved_context: {
          id: '7fa54328-bfb4-523c-ab6f-465e05e1bba5',
          global_settings: {}
        }
      }
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
      const editButton = screen.getAllByText('Edit')[0].parentElement;
      fireEvent.click(editButton!);
    });

    // Switch to patterns tab
    fireEvent.click(screen.getByText('Global Patterns'));

    const textarea = screen.getByTestId('textarea');
    fireEvent.change(textarea, { 
      target: { 
        value: 'auth_pattern:\nJWT authentication with refresh tokens\n\nvalidation_pattern:\nInput validation using zod schema' 
      } 
    });

    // Save
    fireEvent.click(screen.getByText('Save All'));

    await waitFor(() => {
      expect(api.updateGlobalContext).toHaveBeenCalledWith(
        expect.objectContaining({
          globalPatterns: {
            auth_pattern: 'JWT authentication with refresh tokens',
            validation_pattern: 'Input validation using zod schema'
          }
        })
      );
    });
  });

  it('initializes empty global context when Initialize button is clicked', async () => {
    (api.getGlobalContext as any).mockResolvedValue(null);

    render(
      <GlobalContextDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        onClose={mockOnClose}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Initialize Global Context')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Initialize Global Context'));

    // Should enter edit mode with empty fields
    expect(screen.getByTestId('textarea')).toBeInTheDocument();
    expect(screen.getByText('Save All')).toBeInTheDocument();
  });

  it('displays JSON view in details element', async () => {
    const mockContext = {
      data: {
        resolved_context: {
          id: '7fa54328-bfb4-523c-ab6f-465e05e1bba5',
          global_settings: {
            autonomous_rules: { rule1: 'value1' }
          }
        }
      }
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
      expect(screen.getByText('View Complete JSON Context')).toBeInTheDocument();
    });

    // JSON should be in the document but hidden in details
    const jsonText = JSON.stringify(mockContext, null, 2);
    expect(screen.getByText((content, element) => {
      return element?.tagName === 'PRE' && content.includes('resolved_context');
    })).toBeInTheDocument();
  });

  it('handles save errors with alert', async () => {
    const mockContext = {
      data: {
        resolved_context: {
          id: '7fa54328-bfb4-523c-ab6f-465e05e1bba5',
          global_settings: {}
        }
      }
    };

    (api.getGlobalContext as any).mockResolvedValue(mockContext);
    (api.updateGlobalContext as any).mockRejectedValue(new Error('Save failed'));

    // Mock window.alert
    const mockAlert = vi.spyOn(window, 'alert').mockImplementation(() => {});

    render(
      <GlobalContextDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        onClose={mockOnClose}
      />
    );

    await waitFor(() => {
      const editButton = screen.getAllByText('Edit')[0].parentElement;
      fireEvent.click(editButton!);
    });

    // Save
    fireEvent.click(screen.getByText('Save All'));

    await waitFor(() => {
      expect(mockAlert).toHaveBeenCalledWith('Failed to save global context. Please try again.');
    });

    mockAlert.mockRestore();
  });

  it('maintains separate content for each tab', async () => {
    const mockContext = {
      data: {
        resolved_context: {
          id: '7fa54328-bfb4-523c-ab6f-465e05e1bba5',
          global_settings: {}
        }
      }
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
      const editButton = screen.getAllByText('Edit')[0].parentElement;
      fireEvent.click(editButton!);
    });

    // Update settings tab
    const settingsTextarea = screen.getByTestId('textarea');
    fireEvent.change(settingsTextarea, { target: { value: 'setting1: value1' } });

    // Switch to patterns tab and update
    fireEvent.click(screen.getByText('Global Patterns'));
    const patternsTextarea = screen.getByTestId('textarea');
    fireEvent.change(patternsTextarea, { target: { value: 'pattern1:\nPattern description' } });

    // Switch back to settings - should maintain content
    fireEvent.click(screen.getByText('Organization Settings'));
    expect(screen.getByTestId('textarea')).toHaveValue('setting1: value1');

    // Switch to patterns - should maintain content
    fireEvent.click(screen.getByText('Global Patterns'));
    expect(screen.getByTestId('textarea')).toHaveValue('pattern1:\nPattern description');
  });
});