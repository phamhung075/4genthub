// MCP Token Manager Component
import React, { useState, useEffect } from 'react';
import { mcpTokenService } from '../services/mcpTokenService';

interface TokenStats {
  total_tokens: number;
  active_tokens: number;
  expired_tokens: number;
  unique_users: number;
}

const MCPTokenManager: React.FC = () => {
  const [token, setToken] = useState<string | null>(null);
  const [tokenExpiry, setTokenExpiry] = useState<string | null>(null);
  const [stats, setStats] = useState<TokenStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string>('');
  const [messageType, setMessageType] = useState<'success' | 'error' | 'info'>('info');

  const showMessage = (text: string, type: 'success' | 'error' | 'info' = 'info') => {
    setMessage(text);
    setMessageType(type);
    setTimeout(() => setMessage(''), 5000);
  };

  const loadStats = async () => {
    const result = await mcpTokenService.getTokenStats();
    if (result && result.success) {
      setStats(result.stats);
    }
  };

  const generateToken = async () => {
    setLoading(true);
    try {
      const result = await mcpTokenService.generateMCPToken(24);
      
      if (result.success && result.token) {
        setToken(result.token);
        setTokenExpiry(result.expires_at || null);
        showMessage('MCP token generated successfully!', 'success');
        await loadStats();
      } else {
        showMessage(`Failed to generate token: ${result.message}`, 'error');
      }
    } catch (error) {
      showMessage(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const testToken = async () => {
    setLoading(true);
    try {
      const result = await mcpTokenService.testMCPToken();
      showMessage(result.message, result.success ? 'success' : 'error');
    } catch (error) {
      showMessage(`Test failed: ${error instanceof Error ? error.message : 'Unknown error'}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const revokeTokens = async () => {
    setLoading(true);
    try {
      const success = await mcpTokenService.revokeTokens();
      
      if (success) {
        setToken(null);
        setTokenExpiry(null);
        showMessage('All MCP tokens revoked successfully!', 'success');
        await loadStats();
      } else {
        showMessage('Failed to revoke tokens', 'error');
      }
    } catch (error) {
      showMessage(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const getCurrentToken = async () => {
    setLoading(true);
    try {
      const currentToken = await mcpTokenService.getMCPToken();
      if (currentToken) {
        setToken(currentToken);
        showMessage('Current MCP token retrieved', 'success');
      } else {
        showMessage('No valid MCP token found', 'info');
      }
    } catch (error) {
      showMessage(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const clearCache = () => {
    mcpTokenService.clearCache();
    setToken(null);
    setTokenExpiry(null);
    showMessage('Token cache cleared', 'info');
  };

  useEffect(() => {
    // Load initial stats
    loadStats();
    
    // Get current token if exists
    getCurrentToken();
  }, []);

  if (!mcpTokenService.isAuthenticated()) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
        <h3 className="text-lg font-medium text-yellow-800 mb-2">Authentication Required</h3>
        <p className="text-yellow-700">Please log in with Supabase to manage MCP tokens.</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div className="bg-white shadow-sm border border-gray-200 rounded-lg p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">MCP Token Manager</h2>
        <p className="text-gray-600 mb-6">
          Manage tokens for MCP (Model Context Protocol) requests. These tokens are used to authenticate
          MCP operations separate from your browser session.
        </p>

        {message && (
          <div className={`mb-4 p-3 rounded-md ${
            messageType === 'success' ? 'bg-green-50 text-green-800 border border-green-200' :
            messageType === 'error' ? 'bg-red-50 text-red-800 border border-red-200' :
            'bg-blue-50 text-blue-800 border border-blue-200'
          }`}>
            {message}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Token Information */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium text-gray-900">Current Token</h3>
            
            {token ? (
              <div className="space-y-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Token</label>
                  <div className="mt-1 p-2 bg-gray-50 border border-gray-200 rounded text-xs font-mono break-all">
                    {token}
                  </div>
                </div>
                
                {tokenExpiry && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Expires</label>
                    <div className="mt-1 p-2 bg-gray-50 border border-gray-200 rounded text-sm">
                      {new Date(tokenExpiry).toLocaleString()}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-gray-500 italic">No token generated</p>
            )}
          </div>

          {/* Token Statistics */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium text-gray-900">Statistics</h3>
            
            {stats ? (
              <div className="grid grid-cols-2 gap-4">
                <div className="text-center p-3 bg-blue-50 rounded">
                  <div className="text-2xl font-bold text-blue-600">{stats.active_tokens}</div>
                  <div className="text-sm text-blue-800">Active Tokens</div>
                </div>
                <div className="text-center p-3 bg-gray-50 rounded">
                  <div className="text-2xl font-bold text-gray-600">{stats.expired_tokens}</div>
                  <div className="text-sm text-gray-800">Expired</div>
                </div>
                <div className="text-center p-3 bg-green-50 rounded">
                  <div className="text-2xl font-bold text-green-600">{stats.total_tokens}</div>
                  <div className="text-sm text-green-800">Total</div>
                </div>
                <div className="text-center p-3 bg-purple-50 rounded">
                  <div className="text-2xl font-bold text-purple-600">{stats.unique_users}</div>
                  <div className="text-sm text-purple-800">Users</div>
                </div>
              </div>
            ) : (
              <p className="text-gray-500 italic">Loading statistics...</p>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="mt-6 pt-6 border-t border-gray-200">
          <div className="flex flex-wrap gap-3">
            <button
              onClick={generateToken}
              disabled={loading}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            >
              {loading ? 'Generating...' : 'Generate New Token'}
            </button>

            <button
              onClick={testToken}
              disabled={loading || !token}
              className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50"
            >
              {loading ? 'Testing...' : 'Test Token'}
            </button>

            <button
              onClick={getCurrentToken}
              disabled={loading}
              className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 disabled:opacity-50"
            >
              {loading ? 'Loading...' : 'Get Current Token'}
            </button>

            <button
              onClick={loadStats}
              disabled={loading}
              className="px-4 py-2 bg-yellow-600 text-white rounded-md hover:bg-yellow-700 focus:outline-none focus:ring-2 focus:ring-yellow-500 disabled:opacity-50"
            >
              Refresh Stats
            </button>

            <button
              onClick={clearCache}
              disabled={loading}
              className="px-4 py-2 bg-gray-400 text-white rounded-md hover:bg-gray-500 focus:outline-none focus:ring-2 focus:ring-gray-300 disabled:opacity-50"
            >
              Clear Cache
            </button>

            <button
              onClick={revokeTokens}
              disabled={loading}
              className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 disabled:opacity-50"
            >
              {loading ? 'Revoking...' : 'Revoke All Tokens'}
            </button>
          </div>
        </div>

        {/* Help Information */}
        <div className="mt-6 pt-6 border-t border-gray-200">
          <h4 className="text-sm font-medium text-gray-900 mb-2">How it works</h4>
          <ul className="text-sm text-gray-600 space-y-1 list-disc list-inside">
            <li><strong>Frontend requests</strong> (like this page) use your Supabase authentication cookies</li>
            <li><strong>MCP requests</strong> use generated tokens for authentication</li>
            <li>Tokens are automatically cached and refreshed as needed</li>
            <li>All tokens expire after 24 hours by default</li>
            <li>Revoking tokens will require regeneration for MCP requests</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default MCPTokenManager;