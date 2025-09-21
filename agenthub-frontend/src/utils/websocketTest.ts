/**
 * WebSocket connection test utility
 * This helps test if the WebSocket connection works with proper authentication
 */

import logger from './logger';

interface TestResult {
  success: boolean;
  message: string;
  details?: any;
}

export class WebSocketTester {
  /**
   * Test WebSocket connection manually with detailed steps
   */
  async testConnection(token?: string): Promise<TestResult> {
    logger.info('🧪 WebSocket Test: Starting manual connection test...');

    try {
      // Step 1: Check authentication token (same logic as WebSocket service)
      let authToken = token;
      if (!authToken) {
        const cookieToken = document.cookie.split('; ').find(row => row.startsWith('access_token='))?.split('=')[1];
        const localStorageToken = localStorage.getItem('access_token');
        authToken = cookieToken || localStorageToken;
      }

      if (!authToken) {
        const cookieToken = document.cookie.split('; ').find(row => row.startsWith('access_token='))?.split('=')[1];
        const localStorageToken = localStorage.getItem('access_token');

        return {
          success: false,
          message: 'No authentication token found',
          details: {
            localStorage: !!localStorageToken,
            cookies: !!cookieToken,
            provided: !!token
          }
        };
      }

      logger.info('🧪 WebSocket Test: Token found, length:', authToken.length);

      // Step 2: Build WebSocket URL
      const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
      const apiUrl = import.meta.env?.VITE_BACKEND_URL || 'http://localhost:8000';
      const backendHost = apiUrl.replace(/^https?:\/\//, '');
      const wsUrl = `${wsProtocol}://${backendHost}/ws/realtime?token=${encodeURIComponent(authToken)}`;

      logger.info('🧪 WebSocket Test: Connecting to:', wsUrl.replace(/token=[^&]+/, 'token=***'));

      // Step 3: Create WebSocket connection
      return new Promise<TestResult>((resolve) => {
        const ws = new WebSocket(wsUrl);
        let resolved = false;

        const timeout = setTimeout(() => {
          if (!resolved) {
            resolved = true;
            ws.close();
            resolve({
              success: false,
              message: 'Connection timeout after 10 seconds',
              details: { timeout: true }
            });
          }
        }, 10000);

        ws.onopen = () => {
          logger.info('🧪 WebSocket Test: ✅ Connection opened successfully');
          if (!resolved) {
            resolved = true;
            clearTimeout(timeout);
            ws.close();
            resolve({
              success: true,
              message: 'WebSocket connection successful',
              details: { connected: true }
            });
          }
        };

        ws.onmessage = (event) => {
          logger.info('🧪 WebSocket Test: Received message:', event.data);
          try {
            const message = JSON.parse(event.data);
            if (message.type === 'welcome') {
              logger.info('🧪 WebSocket Test: ✅ Received welcome message, authentication successful');
            }
          } catch (e) {
            logger.warn('🧪 WebSocket Test: Could not parse message as JSON');
          }
        };

        ws.onerror = (error) => {
          logger.error('🧪 WebSocket Test: ❌ Connection error:', error);
          if (!resolved) {
            resolved = true;
            clearTimeout(timeout);
            resolve({
              success: false,
              message: 'WebSocket connection error',
              details: { error: error }
            });
          }
        };

        ws.onclose = (event) => {
          logger.info('🧪 WebSocket Test: Connection closed:', {
            code: event.code,
            reason: event.reason,
            wasClean: event.wasClean
          });

          if (!resolved) {
            resolved = true;
            clearTimeout(timeout);

            if (event.code === 4001) {
              resolve({
                success: false,
                message: 'Authentication failed - invalid or expired token',
                details: {
                  code: event.code,
                  reason: event.reason,
                  authError: true
                }
              });
            } else if (event.code === 1006) {
              resolve({
                success: false,
                message: 'Connection failed - server may be down',
                details: {
                  code: event.code,
                  reason: event.reason,
                  serverError: true
                }
              });
            } else {
              resolve({
                success: false,
                message: `Connection closed with code ${event.code}: ${event.reason}`,
                details: {
                  code: event.code,
                  reason: event.reason
                }
              });
            }
          }
        };
      });

    } catch (error) {
      logger.error('🧪 WebSocket Test: ❌ Test failed with exception:', error);
      return {
        success: false,
        message: 'Test failed with exception',
        details: { error: error }
      };
    }
  }

  /**
   * Test if the backend server is reachable
   */
  async testBackendReachability(): Promise<TestResult> {
    logger.info('🧪 Backend Test: Checking if backend server is reachable...');

    try {
      const apiUrl = import.meta.env?.VITE_BACKEND_URL || 'http://localhost:8000';
      const healthUrl = `${apiUrl}/health`;

      logger.info('🧪 Backend Test: Trying health endpoint:', healthUrl);

      const response = await fetch(healthUrl, {
        method: 'GET',
        headers: {
          'Accept': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        logger.info('🧪 Backend Test: ✅ Backend is reachable:', data);
        return {
          success: true,
          message: 'Backend server is reachable',
          details: { status: response.status, data }
        };
      } else {
        logger.warn('🧪 Backend Test: ⚠️ Backend responded with non-OK status:', response.status);
        return {
          success: false,
          message: `Backend returned status ${response.status}`,
          details: { status: response.status }
        };
      }
    } catch (error) {
      logger.error('🧪 Backend Test: ❌ Backend is not reachable:', error);
      return {
        success: false,
        message: 'Backend server is not reachable',
        details: { error: error }
      };
    }
  }

  /**
   * Run a comprehensive test suite
   */
  async runFullTest(): Promise<void> {
    logger.info('🧪 WebSocket Test Suite: Starting comprehensive test...');

    // Test 1: Backend reachability
    const backendResult = await this.testBackendReachability();
    logger.info('🧪 Test 1 - Backend Reachability:', backendResult.success ? '✅ PASS' : '❌ FAIL', backendResult.message);

    if (!backendResult.success) {
      logger.error('🧪 Test Suite: Backend is not reachable. WebSocket tests will likely fail.');
      return;
    }

    // Test 2: WebSocket connection
    const wsResult = await this.testConnection();
    logger.info('🧪 Test 2 - WebSocket Connection:', wsResult.success ? '✅ PASS' : '❌ FAIL', wsResult.message);

    if (wsResult.success) {
      logger.info('🧪 Test Suite: ✅ ALL TESTS PASSED - WebSocket connection is working correctly!');
    } else {
      logger.error('🧪 Test Suite: ❌ WebSocket connection failed:', wsResult.details);

      // Provide helpful debugging information
      if (wsResult.details?.authError) {
        logger.info('🧪 Debugging Help: Authentication failed. Try:');
        logger.info('  1. Log out and log back in to refresh your token');
        logger.info('  2. Check if your session has expired');
        logger.info('  3. Verify Keycloak configuration is correct');
      } else if (wsResult.details?.serverError) {
        logger.info('🧪 Debugging Help: Server connection failed. Try:');
        logger.info('  1. Check if the backend server is running');
        logger.info('  2. Verify the VITE_BACKEND_URL environment variable');
        logger.info('  3. Check network connectivity');
      } else {
        logger.info('🧪 Debugging Help: General WebSocket failure. Try:');
        logger.info('  1. Check browser console for additional errors');
        logger.info('  2. Verify WebSocket endpoint is available');
        logger.info('  3. Check if there are any proxy/firewall issues');
      }
    }
  }
}

// Create and export singleton instance
export const wsTest = new WebSocketTester();

// Make it available globally for console debugging
if (typeof window !== 'undefined') {
  (window as any).wsTest = wsTest;

  // Show test instructions if connection issues are detected
  setTimeout(() => {
    logger.info('🧪 WebSocket Test: Available console commands:');
    logger.info('  wsTest.runFullTest() - Run comprehensive test suite');
    logger.info('  wsTest.testConnection() - Test WebSocket connection only');
    logger.info('  wsTest.testBackendReachability() - Test backend server');
  }, 2000);
}