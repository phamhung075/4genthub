// MCPTokenManager Component Tests
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import '@testing-library/jest-dom';
import MCPTokenManager from '../../components/MCPTokenManager';
import { mcpTokenService } from '../../services/mcpTokenService';

// Mock the mcpTokenService
vi.mock('../../services/mcpTokenService', () => ({
  mcpTokenService: {
    isAuthenticated: vi.fn(),
    getTokenStats: vi.fn(),
    generateMCPToken: vi.fn(),
    testMCPToken: vi.fn(),
    revokeTokens: vi.fn(),
    getMCPToken: vi.fn(),
    clearCache: vi.fn(),
  },
}));

describe('MCPTokenManager', () => {
  const mockToken = 'test-mcp-token-12345';
  const mockExpiry = '2024-12-31T23:59:59Z';
  const mockStats = {
    total_tokens: 10,
    active_tokens: 3,
    expired_tokens: 7,
    unique_users: 5,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Default to authenticated state
    (mcpTokenService.isAuthenticated as ReturnType<typeof vi.fn>).mockReturnValue(true);
    (mcpTokenService.getTokenStats as ReturnType<typeof vi.fn>).mockResolvedValue({
      success: true,
      stats: mockStats,
    });
    (mcpTokenService.getMCPToken as ReturnType<typeof vi.fn>).mockResolvedValue(null);
  });

  describe('Authentication Check', () => {
    it('should show authentication required message when not authenticated', () => {
      (mcpTokenService.isAuthenticated as ReturnType<typeof vi.fn>).mockReturnValue(false);
      
      render(<MCPTokenManager />);
      
      expect(screen.getByText('Authentication Required')).toBeInTheDocument();
      expect(screen.getByText('Please log in with Supabase to manage MCP tokens.')).toBeInTheDocument();
      expect(screen.queryByText('MCP Token Manager')).not.toBeInTheDocument();
    });

    it('should show token manager when authenticated', () => {
      render(<MCPTokenManager />);
      
      expect(screen.getByText('MCP Token Manager')).toBeInTheDocument();
      expect(screen.queryByText('Authentication Required')).not.toBeInTheDocument();
    });
  });

  describe('Initial Load', () => {
    it('should load stats and check for current token on mount', async () => {
      render(<MCPTokenManager />);
      
      await waitFor(() => {
        expect(mcpTokenService.getTokenStats).toHaveBeenCalled();
        expect(mcpTokenService.getMCPToken).toHaveBeenCalled();
      });
    });

    it('should display stats when loaded successfully', async () => {
      render(<MCPTokenManager />);
      
      await waitFor(() => {
        expect(screen.getByText('3')).toBeInTheDocument(); // active_tokens
        expect(screen.getByText('7')).toBeInTheDocument(); // expired_tokens
        expect(screen.getByText('10')).toBeInTheDocument(); // total_tokens
        expect(screen.getByText('5')).toBeInTheDocument(); // unique_users
      });
    });

    it('should show "No token generated" when no current token exists', () => {
      render(<MCPTokenManager />);
      
      expect(screen.getByText('No token generated')).toBeInTheDocument();
    });

    it('should display current token if exists', async () => {
      (mcpTokenService.getMCPToken as ReturnType<typeof vi.fn>).mockResolvedValue(mockToken);
      
      render(<MCPTokenManager />);
      
      await waitFor(() => {
        expect(screen.getByText(mockToken)).toBeInTheDocument();
        expect(screen.getByText('Current MCP token retrieved')).toBeInTheDocument();
      });
    });
  });

  describe('Generate Token', () => {
    it('should generate token successfully', async () => {
      (mcpTokenService.generateMCPToken as ReturnType<typeof vi.fn>).mockResolvedValue({
        success: true,
        token: mockToken,
        expires_at: mockExpiry,
      });
      
      render(<MCPTokenManager />);
      
      const generateButton = screen.getByRole('button', { name: 'Generate New Token' });
      fireEvent.click(generateButton);
      
      expect(generateButton).toBeDisabled();
      expect(screen.getByText('Generating...')).toBeInTheDocument();
      
      await waitFor(() => {
        expect(mcpTokenService.generateMCPToken).toHaveBeenCalledWith(24);
        expect(screen.getByText(mockToken)).toBeInTheDocument();
        expect(screen.getByText('MCP token generated successfully!')).toBeInTheDocument();
        expect(screen.getByText(new Date(mockExpiry).toLocaleString())).toBeInTheDocument();
      });
      
      expect(generateButton).not.toBeDisabled();
    });

    it('should show error message when token generation fails', async () => {
      (mcpTokenService.generateMCPToken as ReturnType<typeof vi.fn>).mockResolvedValue({
        success: false,
        message: 'Generation failed',
      });
      
      render(<MCPTokenManager />);
      
      fireEvent.click(screen.getByRole('button', { name: 'Generate New Token' }));
      
      await waitFor(() => {
        expect(screen.getByText('Failed to generate token: Generation failed')).toBeInTheDocument();
      });
    });

    it('should handle generation errors', async () => {
      (mcpTokenService.generateMCPToken as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Network error'));
      
      render(<MCPTokenManager />);
      
      fireEvent.click(screen.getByRole('button', { name: 'Generate New Token' }));
      
      await waitFor(() => {
        expect(screen.getByText('Error: Network error')).toBeInTheDocument();
      });
    });
  });

  describe('Test Token', () => {
    beforeEach(async () => {
      (mcpTokenService.getMCPToken as ReturnType<typeof vi.fn>).mockResolvedValue(mockToken);
      render(<MCPTokenManager />);
      await waitFor(() => {
        expect(screen.getByText(mockToken)).toBeInTheDocument();
      });
    });

    it('should test token successfully', async () => {
      (mcpTokenService.testMCPToken as ReturnType<typeof vi.fn>).mockResolvedValue({
        success: true,
        message: 'Token is valid',
      });
      
      const testButton = screen.getByRole('button', { name: 'Test Token' });
      fireEvent.click(testButton);
      
      expect(testButton).toBeDisabled();
      expect(screen.getByText('Testing...')).toBeInTheDocument();
      
      await waitFor(() => {
        expect(mcpTokenService.testMCPToken).toHaveBeenCalled();
        expect(screen.getByText('Token is valid')).toBeInTheDocument();
      });
      
      expect(testButton).not.toBeDisabled();
    });

    it('should show error message when test fails', async () => {
      (mcpTokenService.testMCPToken as ReturnType<typeof vi.fn>).mockResolvedValue({
        success: false,
        message: 'Token is invalid',
      });
      
      fireEvent.click(screen.getByRole('button', { name: 'Test Token' }));
      
      await waitFor(() => {
        expect(screen.getByText('Token is invalid')).toBeInTheDocument();
      });
    });

    it('should handle test errors', async () => {
      (mcpTokenService.testMCPToken as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Test failed'));
      
      fireEvent.click(screen.getByRole('button', { name: 'Test Token' }));
      
      await waitFor(() => {
        expect(screen.getByText('Test failed: Test failed')).toBeInTheDocument();
      });
    });

    it('should be disabled when no token exists', async () => {
      (mcpTokenService.getMCPToken as ReturnType<typeof vi.fn>).mockResolvedValue(null);
      render(<MCPTokenManager />);
      
      await waitFor(() => {
        const testButton = screen.getByRole('button', { name: 'Test Token' });
        expect(testButton).toBeDisabled();
      });
    });
  });

  describe('Revoke Tokens', () => {
    it('should revoke tokens successfully', async () => {
      (mcpTokenService.revokeTokens as ReturnType<typeof vi.fn>).mockResolvedValue(true);
      (mcpTokenService.getMCPToken as ReturnType<typeof vi.fn>).mockResolvedValue(mockToken);
      
      render(<MCPTokenManager />);
      
      await waitFor(() => {
        expect(screen.getByText(mockToken)).toBeInTheDocument();
      });
      
      const revokeButton = screen.getByRole('button', { name: 'Revoke All Tokens' });
      fireEvent.click(revokeButton);
      
      expect(revokeButton).toBeDisabled();
      expect(screen.getByText('Revoking...')).toBeInTheDocument();
      
      await waitFor(() => {
        expect(mcpTokenService.revokeTokens).toHaveBeenCalled();
        expect(screen.getByText('All MCP tokens revoked successfully!')).toBeInTheDocument();
        expect(screen.getByText('No token generated')).toBeInTheDocument();
      });
      
      expect(revokeButton).not.toBeDisabled();
    });

    it('should show error when revoke fails', async () => {
      (mcpTokenService.revokeTokens as ReturnType<typeof vi.fn>).mockResolvedValue(false);
      
      render(<MCPTokenManager />);
      
      fireEvent.click(screen.getByRole('button', { name: 'Revoke All Tokens' }));
      
      await waitFor(() => {
        expect(screen.getByText('Failed to revoke tokens')).toBeInTheDocument();
      });
    });

    it('should handle revoke errors', async () => {
      (mcpTokenService.revokeTokens as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Revoke error'));
      
      render(<MCPTokenManager />);
      
      fireEvent.click(screen.getByRole('button', { name: 'Revoke All Tokens' }));
      
      await waitFor(() => {
        expect(screen.getByText('Error: Revoke error')).toBeInTheDocument();
      });
    });
  });

  describe('Get Current Token', () => {
    it('should get current token successfully', async () => {
      (mcpTokenService.getMCPToken as ReturnType<typeof vi.fn>)
        .mockResolvedValueOnce(null) // Initial load
        .mockResolvedValueOnce(mockToken); // Get current token click
      
      render(<MCPTokenManager />);
      
      await waitFor(() => {
        expect(screen.getByText('No token generated')).toBeInTheDocument();
      });
      
      const getCurrentButton = screen.getByRole('button', { name: 'Get Current Token' });
      fireEvent.click(getCurrentButton);
      
      expect(getCurrentButton).toBeDisabled();
      expect(screen.getByText('Loading...')).toBeInTheDocument();
      
      await waitFor(() => {
        expect(screen.getByText(mockToken)).toBeInTheDocument();
        expect(screen.getByText('Current MCP token retrieved')).toBeInTheDocument();
      });
      
      expect(getCurrentButton).not.toBeDisabled();
    });

    it('should show info message when no token found', async () => {
      (mcpTokenService.getMCPToken as ReturnType<typeof vi.fn>).mockResolvedValue(null);
      
      render(<MCPTokenManager />);
      
      fireEvent.click(screen.getByRole('button', { name: 'Get Current Token' }));
      
      await waitFor(() => {
        expect(screen.getByText('No valid MCP token found')).toBeInTheDocument();
      });
    });

    it('should handle get current token errors', async () => {
      (mcpTokenService.getMCPToken as ReturnType<typeof vi.fn>)
        .mockResolvedValueOnce(null)
        .mockRejectedValueOnce(new Error('Fetch error'));
      
      render(<MCPTokenManager />);
      
      fireEvent.click(screen.getByRole('button', { name: 'Get Current Token' }));
      
      await waitFor(() => {
        expect(screen.getByText('Error: Fetch error')).toBeInTheDocument();
      });
    });
  });

  describe('Clear Cache', () => {
    it('should clear cache and reset token state', async () => {
      (mcpTokenService.getMCPToken as ReturnType<typeof vi.fn>).mockResolvedValue(mockToken);
      
      render(<MCPTokenManager />);
      
      await waitFor(() => {
        expect(screen.getByText(mockToken)).toBeInTheDocument();
      });
      
      const clearCacheButton = screen.getByRole('button', { name: 'Clear Cache' });
      fireEvent.click(clearCacheButton);
      
      expect(mcpTokenService.clearCache).toHaveBeenCalled();
      expect(screen.getByText('Token cache cleared')).toBeInTheDocument();
      expect(screen.getByText('No token generated')).toBeInTheDocument();
    });
  });

  describe('Refresh Stats', () => {
    it('should refresh stats when button clicked', async () => {
      render(<MCPTokenManager />);
      
      // Clear the initial call
      (mcpTokenService.getTokenStats as ReturnType<typeof vi.fn>).mockClear();
      
      const refreshButton = screen.getByRole('button', { name: 'Refresh Stats' });
      fireEvent.click(refreshButton);
      
      await waitFor(() => {
        expect(mcpTokenService.getTokenStats).toHaveBeenCalled();
      });
    });
  });

  describe('Message Display', () => {
    it('should display success messages with correct styling', async () => {
      (mcpTokenService.generateMCPToken as ReturnType<typeof vi.fn>).mockResolvedValue({
        success: true,
        token: mockToken,
        expires_at: mockExpiry,
      });
      
      render(<MCPTokenManager />);
      
      fireEvent.click(screen.getByRole('button', { name: 'Generate New Token' }));
      
      await waitFor(() => {
        const message = screen.getByText('MCP token generated successfully!');
        expect(message).toBeInTheDocument();
        expect(message.parentElement).toHaveClass('bg-green-50', 'text-green-800', 'border-green-200');
      });
    });

    it('should display error messages with correct styling', async () => {
      (mcpTokenService.generateMCPToken as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Test error'));
      
      render(<MCPTokenManager />);
      
      fireEvent.click(screen.getByRole('button', { name: 'Generate New Token' }));
      
      await waitFor(() => {
        const message = screen.getByText('Error: Test error');
        expect(message).toBeInTheDocument();
        expect(message.parentElement).toHaveClass('bg-red-50', 'text-red-800', 'border-red-200');
      });
    });

    it('should display info messages with correct styling', async () => {
      render(<MCPTokenManager />);
      
      fireEvent.click(screen.getByRole('button', { name: 'Clear Cache' }));
      
      const message = screen.getByText('Token cache cleared');
      expect(message).toBeInTheDocument();
      expect(message.parentElement).toHaveClass('bg-blue-50', 'text-blue-800', 'border-blue-200');
    });

    it('should auto-hide messages after 5 seconds', async () => {
      vi.useFakeTimers();
      
      render(<MCPTokenManager />);
      
      fireEvent.click(screen.getByRole('button', { name: 'Clear Cache' }));
      
      expect(screen.getByText('Token cache cleared')).toBeInTheDocument();
      
      vi.advanceTimersByTime(5000);
      
      await waitFor(() => {
        expect(screen.queryByText('Token cache cleared')).not.toBeInTheDocument();
      });
      
      vi.useRealTimers();
    });
  });

  describe('UI Elements', () => {
    it('should render all main sections', () => {
      render(<MCPTokenManager />);
      
      expect(screen.getByText('MCP Token Manager')).toBeInTheDocument();
      expect(screen.getByText(/Manage tokens for MCP/)).toBeInTheDocument();
      expect(screen.getByText('Current Token')).toBeInTheDocument();
      expect(screen.getByText('Statistics')).toBeInTheDocument();
      expect(screen.getByText('How it works')).toBeInTheDocument();
    });

    it('should render all help information', () => {
      render(<MCPTokenManager />);
      
      expect(screen.getByText(/Frontend requests/)).toBeInTheDocument();
      expect(screen.getByText(/MCP requests/)).toBeInTheDocument();
      expect(screen.getByText(/Tokens are automatically cached/)).toBeInTheDocument();
      expect(screen.getByText(/All tokens expire after 24 hours/)).toBeInTheDocument();
      expect(screen.getByText(/Revoking tokens will require regeneration/)).toBeInTheDocument();
    });

    it('should render all action buttons', () => {
      render(<MCPTokenManager />);
      
      expect(screen.getByRole('button', { name: 'Generate New Token' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Test Token' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Get Current Token' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Refresh Stats' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Clear Cache' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Revoke All Tokens' })).toBeInTheDocument();
    });

    it('should render statistics with correct labels', async () => {
      render(<MCPTokenManager />);
      
      await waitFor(() => {
        expect(screen.getByText('Active Tokens')).toBeInTheDocument();
        expect(screen.getByText('Expired')).toBeInTheDocument();
        expect(screen.getByText('Total')).toBeInTheDocument();
        expect(screen.getByText('Users')).toBeInTheDocument();
      });
    });
  });

  describe('Edge Cases', () => {
    it('should handle missing stats gracefully', async () => {
      (mcpTokenService.getTokenStats as ReturnType<typeof vi.fn>).mockResolvedValue({
        success: false,
      });
      
      render(<MCPTokenManager />);
      
      await waitFor(() => {
        expect(screen.getByText('Loading statistics...')).toBeInTheDocument();
      });
    });

    it('should handle unknown errors', async () => {
      (mcpTokenService.generateMCPToken as ReturnType<typeof vi.fn>).mockRejectedValue('String error');
      
      render(<MCPTokenManager />);
      
      fireEvent.click(screen.getByRole('button', { name: 'Generate New Token' }));
      
      await waitFor(() => {
        expect(screen.getByText('Error: Unknown error')).toBeInTheDocument();
      });
    });

    it('should handle missing token expiry', async () => {
      (mcpTokenService.generateMCPToken as ReturnType<typeof vi.fn>).mockResolvedValue({
        success: true,
        token: mockToken,
        expires_at: null,
      });
      
      render(<MCPTokenManager />);
      
      fireEvent.click(screen.getByRole('button', { name: 'Generate New Token' }));
      
      await waitFor(() => {
        expect(screen.getByText(mockToken)).toBeInTheDocument();
        expect(screen.queryByText('Expires')).not.toBeInTheDocument();
      });
    });
  });
});