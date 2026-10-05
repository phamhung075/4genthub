import React from 'react';
import { render, screen, fireEvent, waitFor, within } from './../test-utils';
import { vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { TokenManagement } from '../../pages/TokenManagement';
import { tokenService } from '../../services/tokenService';
import { format } from 'date-fns';
import { AuthProvider } from '../../contexts/AuthContext';
import { ThemeProvider } from '../../contexts/ThemeContext';
import logger from '../../utils/logger';

// Mock dependencies
vi.mock('../../services/tokenService');
vi.mock('../../hooks/useAuth', () => ({
  useAuth: () => ({
    user: { id: 'test-user', email: 'test@example.com' }
  })
}));
vi.mock('date-fns', () => ({
  format: vi.fn((date) => 'formatted-date'),
}));

const mockTokenService = vi.mocked(tokenService);

interface APIToken {
  id: string;
  name: string;
  token?: string;
  scopes: string[];
  created_at: string;
  expires_at: string;
  last_used_at?: string;
  usage_count: number;
  rate_limit?: number;
  is_active: boolean;
}

const mockTokens: APIToken[] = [
  {
    id: '1',
    name: 'Test Token 1',
    scopes: ['read:tasks', 'write:tasks'],
    is_active: true,
    rate_limit: 100,
    created_at: '2024-01-01T00:00:00Z',
    expires_at: '2024-02-01T00:00:00Z',
    last_used_at: '2024-01-02T00:00:00Z',
    usage_count: 42,
  },
  {
    id: '2',
    name: 'Test Token 2',
    scopes: ['read:context'],
    is_active: false,
    rate_limit: 50,
    created_at: '2024-01-03T00:00:00Z',
    expires_at: '2024-02-03T00:00:00Z',
    last_used_at: undefined,
    usage_count: 0,
  },
];

const renderWithProviders = (component: React.ReactElement) => {
  return render(
    <ThemeProvider>
      <AuthProvider>
        {component}
      </AuthProvider>
    </ThemeProvider>
  );
};

describe('TokenManagement', () => {
  // Scope cards render a resource span ("Tasks") and a verb badge ("Read").
  // Find the card that matches a specific resource/verb pair.
  const getScopeCard = (resource: string, verb: string) => {
    const cards = screen.getAllByText(resource)
      .map((el) => el.closest('.cursor-pointer'))
      .filter((card): card is HTMLElement => card instanceof HTMLElement);

    const match = cards.find((card) => within(card).queryByText(verb));
    if (!match) {
      throw new Error(`Scope card "${resource} / ${verb}" not found`);
    }
    return match;
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Reset the service mocks (clears any queued once-implementations) without
    // touching the global mocks installed by src/setupTests.ts.
    mockTokenService.listTokens.mockReset();
    mockTokenService.generateToken.mockReset();
    mockTokenService.revokeToken.mockReset();
    vi.mocked(format).mockImplementation(() => 'formatted-date');
    mockTokenService.listTokens.mockResolvedValue({ data: mockTokens, total: mockTokens.length });
  });

  describe('Tab functionality', () => {
    it('should display Generate Token tab by default', () => {
      renderWithProviders(<TokenManagement />);

      // Check that Generate Token tab content is visible
      expect(screen.getByText('Generate New API Token')).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/Production API/)).toBeInTheDocument();
    });

    it('should switch to Active Tokens tab and fetch tokens', async () => {
      renderWithProviders(<TokenManagement />);

      // Click on Active Tokens tab (Radix activates on mousedown/pointer events)
      const activeTokensTab = screen.getByRole('tab', { name: /active tokens/i });
      await userEvent.click(activeTokensTab);

      // Wait for tokens to be fetched
      await waitFor(() => {
        expect(mockTokenService.listTokens).toHaveBeenCalled();
      });

      // Check that tokens are displayed
      await waitFor(() => {
        expect(screen.getByText('Test Token 1')).toBeInTheDocument();
        expect(screen.getByText('Test Token 2')).toBeInTheDocument();
      });
    });

    it('should show Settings tab with info message', async () => {
      renderWithProviders(<TokenManagement />);

      // Click on Settings tab
      const settingsTab = screen.getByRole('tab', { name: /settings/i });
      await userEvent.click(settingsTab);

      expect(screen.getByText('Token Settings')).toBeInTheDocument();
      expect(screen.getByText(/Token settings configuration will be available in a future update/i)).toBeInTheDocument();
    });
  });

  it('renders the page title and description', () => {
    renderWithProviders(<TokenManagement />);

    expect(screen.getByText('API Token Management')).toBeInTheDocument();
    expect(screen.getByText(/Generate and manage secure API tokens for MCP authentication/i)).toBeInTheDocument();
  });

  describe('Scope selection', () => {
    it('should have correct available scopes', () => {
      renderWithProviders(<TokenManagement />);

      // Scopes are grouped by category headings
      const categories = ['Core', 'API', 'Projects', 'Tasks', 'Subtasks', 'Contexts', 'Agents', 'Branches', 'Execute', 'Sessions'];
      categories.forEach((category) => {
        expect(screen.getByText(`${category} Permissions`)).toBeInTheDocument();
      });

      // The four Tasks CRUD scopes render as four "Tasks" scope cards
      expect(screen.getAllByText('Tasks')).toHaveLength(4);
      // Execute MCP is represented by the "Execute" verb badge
      expect(screen.getAllByText('Execute').length).toBeGreaterThanOrEqual(1);
      // Admin is not an available scope
      expect(screen.queryByText('Admin')).not.toBeInTheDocument();
    });

    it('offers the session-stream connector scope and sends it with the token', async () => {
      renderWithProviders(<TokenManagement />);

      const nameInput = screen.getByPlaceholderText(/Production API/);
      fireEvent.change(nameInput, { target: { value: 'Connector Token' } });

      // Fails when the connector scope is absent from the picker: getScopeCard throws.
      fireEvent.click(getScopeCard('Sessions', 'Write'));

      fireEvent.click(screen.getByRole('button', { name: /Generate API Token/i }));

      await waitFor(() => {
        expect(mockTokenService.generateToken).toHaveBeenCalledWith(
          expect.objectContaining({ name: 'Connector Token', scopes: ['sessions:write'] })
        );
      });
    });

    it('Full Access selects every scope except the connector scope (literal set)', async () => {
      renderWithProviders(<TokenManagement />);

      fireEvent.change(screen.getByPlaceholderText(/Production API/), { target: { value: 'Full Access Token' } });
      fireEvent.click(screen.getByRole('button', { name: /Full Access/i }));
      fireEvent.click(screen.getByRole('button', { name: /Generate API Token/i }));

      // Literal, never derived from AVAILABLE_SCOPES: adding any scope must turn this red so the
      // Full Access decision is deliberate. The connector scope is deliberately absent.
      const FULL_ACCESS_SCOPES = [
        'openid', 'profile', 'email', 'offline_access', 'mcp-api', 'mcp-roles', 'mcp-profile',
        'projects:create', 'projects:read', 'projects:update', 'projects:delete',
        'tasks:create', 'tasks:read', 'tasks:update', 'tasks:delete',
        'subtasks:create', 'subtasks:read', 'subtasks:update', 'subtasks:delete',
        'contexts:create', 'contexts:read', 'contexts:update', 'contexts:delete',
        'agents:create', 'agents:read', 'agents:update', 'agents:delete',
        'branches:create', 'branches:read', 'branches:update', 'branches:delete',
        'mcp:execute', 'mcp:delegate',
      ];

      await waitFor(() => {
        expect(mockTokenService.generateToken).toHaveBeenCalledWith(
          expect.objectContaining({ scopes: FULL_ACCESS_SCOPES })
        );
      });
    });
  });

  it('creates a new token with form data', async () => {
    const newToken: APIToken = {
      id: '3',
      name: 'New Token',
      scopes: ['tasks:read', 'tasks:update'],
      token: 'generated-token-value',
      is_active: true,
      rate_limit: 200,
      created_at: '2024-01-04T00:00:00Z',
      expires_at: '2024-02-04T00:00:00Z',
      last_used_at: undefined,
      usage_count: 0,
    };

    mockTokenService.generateToken.mockResolvedValue({ data: newToken });

    renderWithProviders(<TokenManagement />);

    // Fill form
    const nameInput = screen.getByPlaceholderText(/Production API/);
    fireEvent.change(nameInput, { target: { value: 'New Token' } });

    // Select scopes
    fireEvent.click(getScopeCard('Tasks', 'Read'));
    fireEvent.click(getScopeCard('Tasks', 'Update'));

    // Set expiry days and rate limit (the two number inputs)
    const [expiryInput, rateLimitInput] = screen.getAllByRole('spinbutton');
    fireEvent.change(expiryInput, { target: { value: '30' } });
    fireEvent.change(rateLimitInput, { target: { value: '200' } });

    // Submit form
    const submitButton = screen.getByRole('button', { name: /Generate API Token/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockTokenService.generateToken).toHaveBeenCalledWith({
        name: 'New Token',
        scopes: ['tasks:read', 'tasks:update'],
        expires_in_days: 30,
        rate_limit: 200,
      });
    });

    // Check if the generated token dialog is shown
    await waitFor(() => {
      expect(screen.getByText(/MCP Configuration Generated/i)).toBeInTheDocument();
      expect(screen.getByText('generated-token-value')).toBeInTheDocument();
    });
  });

  it('copies token to clipboard when copy button is clicked', async () => {
    const mockClipboard = {
      writeText: vi.fn().mockResolvedValue(undefined),
    };
    Object.assign(navigator, { clipboard: mockClipboard });

    const newToken: APIToken = {
      id: '3',
      name: 'New Token',
      token: 'test-token-to-copy',
      scopes: ['tasks:read'],
      is_active: true,
      rate_limit: 100,
      created_at: '2024-01-04T00:00:00Z',
      expires_at: '2024-02-04T00:00:00Z',
      usage_count: 0,
    };

    mockTokenService.generateToken.mockResolvedValue({ data: newToken });

    renderWithProviders(<TokenManagement />);

    // Create a token
    const nameInput = screen.getByPlaceholderText(/Production API/);
    fireEvent.change(nameInput, { target: { value: 'New Token' } });

    // Select at least one scope
    fireEvent.click(getScopeCard('Tasks', 'Read'));

    const submitButton = screen.getByRole('button', { name: /Generate API Token/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('test-token-to-copy')).toBeInTheDocument();
    });

    // Click copy button
    const copyButton = screen.getByRole('button', { name: /Copy Token Only/i });
    fireEvent.click(copyButton);

    expect(mockClipboard.writeText).toHaveBeenCalledWith('test-token-to-copy');

    await waitFor(() => {
      expect(screen.getByText(/Copied to clipboard/i)).toBeInTheDocument();
    });
  });

  it('revokes a token when delete button is clicked and confirmed', async () => {
    mockTokenService.revokeToken.mockResolvedValue(undefined);
    mockTokenService.listTokens
      .mockResolvedValueOnce({ data: mockTokens, total: mockTokens.length })
      .mockResolvedValueOnce({ data: [mockTokens[1]], total: 1 });

    renderWithProviders(<TokenManagement />);

    // Switch to Active Tokens tab
    const activeTokensTab = screen.getByRole('tab', { name: /active tokens/i });
    await userEvent.click(activeTokensTab);

    await waitFor(() => {
      expect(screen.getByText('Test Token 1')).toBeInTheDocument();
    });

    // Find revoke button for first token and open the dialog
    const revokeButtons = screen.getAllByRole('button', { name: /Revoke Token/i });
    fireEvent.click(revokeButtons[0]);

    // Confirm deletion
    await waitFor(() => {
      expect(screen.getByText(/Revoke API Token/i)).toBeInTheDocument();
    });

    const dialog = screen.getByText('Revoke API Token').closest('.theme-modal')!;
    fireEvent.click(within(dialog).getByRole('button', { name: /Revoke Token/i }));

    await waitFor(() => {
      expect(mockTokenService.revokeToken).toHaveBeenCalledWith('1');
    });

    // Check if tokens are refreshed
    await waitFor(() => {
      expect(mockTokenService.listTokens).toHaveBeenCalledTimes(2);
    });
  });

  it('cancels token revocation when cancel is clicked', async () => {
    renderWithProviders(<TokenManagement />);

    // Switch to Active Tokens tab
    const activeTokensTab = screen.getByRole('tab', { name: /active tokens/i });
    await userEvent.click(activeTokensTab);

    await waitFor(() => {
      expect(screen.getByText('Test Token 1')).toBeInTheDocument();
    });

    // Find revoke button for first token and open the dialog
    const revokeButtons = screen.getAllByRole('button', { name: /Revoke Token/i });
    fireEvent.click(revokeButtons[0]);

    // Cancel deletion
    await waitFor(() => {
      expect(screen.getByText(/Revoke API Token/i)).toBeInTheDocument();
    });

    const dialog = screen.getByText('Revoke API Token').closest('.theme-modal')!;
    fireEvent.click(within(dialog).getByRole('button', { name: /cancel/i }));

    await waitFor(() => {
      expect(screen.queryByText(/Revoke API Token/i)).not.toBeInTheDocument();
    });

    expect(mockTokenService.revokeToken).not.toHaveBeenCalled();
  });

  it('displays error message when token generation fails', async () => {
    const loggerErrorSpy = vi.spyOn(logger, 'error').mockImplementation(() => {});
    mockTokenService.generateToken.mockRejectedValue(new Error('Generation failed'));

    renderWithProviders(<TokenManagement />);

    // Fill and submit form
    const nameInput = screen.getByPlaceholderText(/Production API/);
    fireEvent.change(nameInput, { target: { value: 'New Token' } });

    // Select at least one scope
    fireEvent.click(getScopeCard('Tasks', 'Read'));

    const submitButton = screen.getByRole('button', { name: /Generate API Token/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(loggerErrorSpy).toHaveBeenCalledWith('Error generating token:', expect.any(Error));
    });

    // Should show error alert
    await waitFor(() => {
      expect(screen.getByText('Generation failed')).toBeInTheDocument();
    });

    loggerErrorSpy.mockRestore();
  });

  it('displays error message when loading tokens fails', async () => {
    const loggerErrorSpy = vi.spyOn(logger, 'error').mockImplementation(() => {});
    mockTokenService.listTokens.mockRejectedValue(new Error('Load failed'));

    renderWithProviders(<TokenManagement />);

    // Switch to Active Tokens tab to trigger loading
    const activeTokensTab = screen.getByRole('tab', { name: /active tokens/i });
    await userEvent.click(activeTokensTab);

    await waitFor(() => {
      expect(loggerErrorSpy).toHaveBeenCalledWith('Error fetching tokens:', expect.any(Error));
    });

    // Should show error alert
    await waitFor(() => {
      expect(screen.getByText('Load failed')).toBeInTheDocument();
    });

    loggerErrorSpy.mockRestore();
  });

  it('formats dates correctly', async () => {
    renderWithProviders(<TokenManagement />);

    // Switch to Active Tokens tab
    const activeTokensTab = screen.getByRole('tab', { name: /active tokens/i });
    await userEvent.click(activeTokensTab);

    await waitFor(() => {
      expect(screen.getByText('Test Token 1')).toBeInTheDocument();
    });

    // Check if date formatting function was called
    expect(format).toHaveBeenCalled();
  });

  it('displays usage count and last used information', async () => {
    renderWithProviders(<TokenManagement />);

    // Switch to Active Tokens tab
    const activeTokensTab = screen.getByRole('tab', { name: /active tokens/i });
    await userEvent.click(activeTokensTab);

    await waitFor(() => {
      expect(screen.getByText('Test Token 1')).toBeInTheDocument();
    });

    // Check usage count
    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText('0')).toBeInTheDocument();
    expect(screen.getByText(/Last used:/)).toBeInTheDocument();
  });

  it('should require a token name and at least one scope before submission', async () => {
    renderWithProviders(<TokenManagement />);

    // Button starts disabled with an empty form
    const submitButton = screen.getByRole('button', { name: /Generate API Token/i });
    expect(submitButton).toBeDisabled();

    // Fill name but no scopes
    const nameInput = screen.getByPlaceholderText(/Production API/);
    fireEvent.change(nameInput, { target: { value: 'Test' } });
    expect(submitButton).toBeDisabled();

    // Select a scope -> now the button is enabled
    fireEvent.click(getScopeCard('Tasks', 'Read'));
    await waitFor(() => {
      expect(submitButton).not.toBeDisabled();
    });

    expect(mockTokenService.generateToken).not.toHaveBeenCalled();
  });
});
