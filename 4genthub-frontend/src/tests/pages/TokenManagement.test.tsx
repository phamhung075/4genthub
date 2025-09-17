import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { vi } from 'vitest';
import '@testing-library/jest-dom';
import { TokenManagement } from '../../pages/TokenManagement';
import { tokenService } from '../../services/tokenService';
import { format } from 'date-fns';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from '../../contexts/AuthContext';

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
    <BrowserRouter>
      <AuthProvider>
        {component}
      </AuthProvider>
    </BrowserRouter>
  );
};

describe('TokenManagement', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockTokenService.listTokens.mockResolvedValue({ data: mockTokens, total: mockTokens.length });
  });

  describe('Tab functionality', () => {
    it('should display Generate Token tab by default', () => {
      renderWithProviders(<TokenManagement />);
      
      // Check that Generate Token tab content is visible
      expect(screen.getByText('Generate New API Token')).toBeInTheDocument();
      expect(screen.getByLabelText('Token Name')).toBeInTheDocument();
    });

    it('should switch to Active Tokens tab and fetch tokens', async () => {
      renderWithProviders(<TokenManagement />);
      
      // Click on Active Tokens tab
      const activeTokensTab = screen.getByRole('tab', { name: /active tokens/i });
      fireEvent.click(activeTokensTab);
      
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

    it('should show Settings tab with info message', () => {
      renderWithProviders(<TokenManagement />);
      
      // Click on Settings tab
      const settingsTab = screen.getByRole('tab', { name: /settings/i });
      fireEvent.click(settingsTab);
      
      expect(screen.getByText('Token Settings')).toBeInTheDocument();
      expect(screen.getByText(/Token settings configuration will be available in a future update/i)).toBeInTheDocument();
    });
  });

  it('renders the page title and description', () => {
    renderWithProviders(<TokenManagement />);
    
    expect(screen.getByText('API Token Management')).toBeInTheDocument();
    expect(screen.getByText(/Generate and manage API tokens for MCP authentication/i)).toBeInTheDocument();
  });

  describe('Scope selection', () => {
    it('should have correct available scopes', () => {
      renderWithProviders(<TokenManagement />);
      
      // Check for scope checkboxes
      const scopeCheckboxes = screen.getAllByRole('checkbox');
      
      // Get all chip labels which represent scopes
      const chipElements = screen.getAllByText(/Read|Write|Execute/i);
      const scopeNames = chipElements.map(el => el.textContent);
      
      expect(scopeNames).toContain('Read Tasks');
      expect(scopeNames).toContain('Write Tasks');
      expect(scopeNames).toContain('Read Context');
      expect(scopeNames).toContain('Write Context');
      expect(scopeNames).toContain('Read Agents');
      expect(scopeNames).toContain('Write Agents');
      expect(scopeNames).toContain('Execute MCP');
      expect(scopeNames).not.toContain('Admin');
    });
  });

  it('creates a new token with form data', async () => {
    const newToken: APIToken = {
      id: '3',
      name: 'New Token',
      scopes: ['read:tasks', 'write:tasks'],
      token: 'generated-token-value',
      is_active: true,
      rate_limit: 200,
      created_at: '2024-01-04T00:00:00Z',
      expires_at: '2024-02-04T00:00:00Z',
      last_used_at: undefined,
      usage_count: 0,
    };
    
    mockTokenService.generateToken.mockResolvedValue({ data: newToken });
    mockTokenService.listTokens
      .mockResolvedValueOnce({ data: mockTokens, total: mockTokens.length })
      .mockResolvedValueOnce({ data: [...mockTokens, newToken], total: mockTokens.length + 1 });
    
    renderWithProviders(<TokenManagement />);
    
    // Fill form
    const nameInput = screen.getByLabelText(/Token Name/i);
    fireEvent.change(nameInput, { target: { value: 'New Token' } });
    
    // Select scopes
    const readTasksCheckbox = screen.getByRole('checkbox', { name: /read tasks/i });
    const writeTasksCheckbox = screen.getByRole('checkbox', { name: /write tasks/i });
    fireEvent.click(readTasksCheckbox);
    fireEvent.click(writeTasksCheckbox);
    
    // Set expiry days
    const expiryInput = screen.getByLabelText(/Expiry \(days\)/i);
    fireEvent.change(expiryInput, { target: { value: '30' } });
    
    // Set rate limit
    const rateLimitInput = screen.getByLabelText(/Rate Limit/i);
    fireEvent.change(rateLimitInput, { target: { value: '200' } });

    // Submit form
    const submitButton = screen.getByRole('button', { name: /Generate Token/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockTokenService.generateToken).toHaveBeenCalledWith({
        name: 'New Token',
        scopes: ['read:tasks', 'write:tasks'],
        expires_in_days: 30,
        rate_limit: 200,
      });
    });

    // Check if token display dialog is shown
    await waitFor(() => {
      expect(screen.getByText(/Token Generated Successfully/i)).toBeInTheDocument();
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
      scopes: ['read:tasks'],
      is_active: true,
      rate_limit: 100,
      created_at: '2024-01-04T00:00:00Z',
      expires_at: '2024-02-04T00:00:00Z',
      usage_count: 0,
    };
    
    mockTokenService.generateToken.mockResolvedValue({ data: newToken });
    
    renderWithProviders(<TokenManagement />);
    
    // Create a token
    const nameInput = screen.getByLabelText(/Token Name/i);
    fireEvent.change(nameInput, { target: { value: 'New Token' } });
    
    // Select at least one scope
    const readTasksCheckbox = screen.getByRole('checkbox', { name: /read tasks/i });
    fireEvent.click(readTasksCheckbox);
    
    const submitButton = screen.getByRole('button', { name: /Generate Token/i });
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
    fireEvent.click(activeTokensTab);
    
    await waitFor(() => {
      expect(screen.getByText('Test Token 1')).toBeInTheDocument();
    });

    // Find delete button for first token
    const firstTokenRow = screen.getByText('Test Token 1').closest('tr')!;
    const deleteButton = within(firstTokenRow).getByRole('button');
    
    fireEvent.click(deleteButton);

    // Confirm deletion
    await waitFor(() => {
      expect(screen.getByText(/Revoke API Token/i)).toBeInTheDocument();
    });
    
    const confirmButton = screen.getByRole('button', { name: /Revoke Token/i });
    fireEvent.click(confirmButton);

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
    fireEvent.click(activeTokensTab);
    
    await waitFor(() => {
      expect(screen.getByText('Test Token 1')).toBeInTheDocument();
    });

    // Find delete button for first token
    const firstTokenRow = screen.getByText('Test Token 1').closest('tr')!;
    const deleteButton = within(firstTokenRow).getByRole('button');
    
    fireEvent.click(deleteButton);

    // Cancel deletion
    await waitFor(() => {
      expect(screen.getByText(/Revoke API Token/i)).toBeInTheDocument();
    });
    
    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    fireEvent.click(cancelButton);

    await waitFor(() => {
      expect(screen.queryByText(/Revoke API Token/i)).not.toBeInTheDocument();
    });

    expect(mockTokenService.revokeToken).not.toHaveBeenCalled();
  });

  it('displays error message when token generation fails', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    mockTokenService.generateToken.mockRejectedValue(new Error('Generation failed'));
    
    renderWithProviders(<TokenManagement />);
    
    // Fill and submit form
    const nameInput = screen.getByLabelText(/Token Name/i);
    fireEvent.change(nameInput, { target: { value: 'New Token' } });
    
    // Select at least one scope
    const readTasksCheckbox = screen.getByRole('checkbox', { name: /read tasks/i });
    fireEvent.click(readTasksCheckbox);
    
    const submitButton = screen.getByRole('button', { name: /Generate Token/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(consoleErrorSpy).toHaveBeenCalledWith('Error generating token:', expect.any(Error));
    });

    // Should show error alert
    await waitFor(() => {
      expect(screen.getByText('Generation failed')).toBeInTheDocument();
    });

    consoleErrorSpy.mockRestore();
  });

  it('displays error message when loading tokens fails', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    mockTokenService.listTokens.mockRejectedValue(new Error('Load failed'));
    
    renderWithProviders(<TokenManagement />);
    
    // Switch to Active Tokens tab to trigger loading
    const activeTokensTab = screen.getByRole('tab', { name: /active tokens/i });
    fireEvent.click(activeTokensTab);

    await waitFor(() => {
      expect(consoleErrorSpy).toHaveBeenCalledWith('Error fetching tokens:', expect.any(Error));
    });

    // Should show error alert
    await waitFor(() => {
      expect(screen.getByText('Load failed')).toBeInTheDocument();
    });

    consoleErrorSpy.mockRestore();
  });

  it('formats dates correctly', async () => {
    renderWithProviders(<TokenManagement />);
    
    // Switch to Active Tokens tab
    const activeTokensTab = screen.getByRole('tab', { name: /active tokens/i });
    fireEvent.click(activeTokensTab);
    
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
    fireEvent.click(activeTokensTab);
    
    await waitFor(() => {
      expect(screen.getByText('Test Token 1')).toBeInTheDocument();
    });

    // Check usage count
    expect(screen.getByText('42 requests')).toBeInTheDocument();
    expect(screen.getByText('0 requests')).toBeInTheDocument();
  });

  it('validates form fields before submission', async () => {
    renderWithProviders(<TokenManagement />);
    
    // Try to submit with empty name
    const submitButton = screen.getByRole('button', { name: /Generate Token/i });
    fireEvent.click(submitButton);

    // Should show error
    await waitFor(() => {
      expect(screen.getByText('Token name is required')).toBeInTheDocument();
    });

    // Fill name but no scopes
    const nameInput = screen.getByLabelText(/Token Name/i);
    fireEvent.change(nameInput, { target: { value: 'Test' } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('At least one scope must be selected')).toBeInTheDocument();
    });

    expect(mockTokenService.generateToken).not.toHaveBeenCalled();
  });
});