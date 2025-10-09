/**
 * WebSocket Connection Test Utility
 * This utility helps debug WebSocket connection issues
 */

import logger from './logger';

export function testWebSocketConnection(userId: string, token: string, backendUrl?: string) {
  logger.info('=== WebSocket Connection Test ===', { component: 'testWebSocket' });
  logger.info('User ID', { userId, component: 'testWebSocket' });
  logger.info('Token (first 20 chars)', { token: token?.substring(0, 20) + '...', component: 'testWebSocket' });
  logger.info('Backend URL', { backendUrl: backendUrl || 'Using default', component: 'testWebSocket' });

  // Determine WebSocket URL
  let wsUrl: string;
  const backend = backendUrl || import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

  if (backend.startsWith('https')) {
    const host = backend.replace('https://', '');
    wsUrl = `wss://${host}/ws/realtime?token=${token}`;
  } else {
    const host = backend.replace('http://', '');
    wsUrl = `ws://${host}/ws/realtime?token=${token}`;
  }

  logger.info('Attempting connection', { url: wsUrl.replace(/token=[^&]+/, 'token=***'), component: 'testWebSocket' });

  const ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    logger.info('WebSocket Connected Successfully!', { component: 'testWebSocket' });
    logger.info('Connection details', {
      readyState: ws.readyState,
      protocol: ws.protocol,
      url: ws.url?.replace(/token=[^&]+/, 'token=***'),
      component: 'testWebSocket'
    });

    // Send a test message
    const testMessage = {
      id: `test-${Date.now()}`,
      version: '2.0',
      type: 'heartbeat',
      timestamp: new Date().toISOString(),
      sequence: 0,
      payload: {
        entity: 'system',
        action: 'ping',
        data: {
          primary: { test: true }
        }
      },
      metadata: {
        source: 'test'
      }
    };

    logger.info('Sending test message', { testMessage, component: 'testWebSocket' });
    ws.send(JSON.stringify(testMessage));
  };

  ws.onmessage = (event) => {
    logger.info('Message received', { data: event.data, component: 'testWebSocket' });
    try {
      const message = JSON.parse(event.data);
      logger.info('Parsed message', { message, component: 'testWebSocket' });
    } catch (e) {
      logger.info('Raw message (not JSON)', { data: event.data, component: 'testWebSocket' });
    }
  };

  ws.onerror = (error) => {
    logger.error('WebSocket Error', {
      error,
      readyState: ws.readyState,
      url: ws.url?.replace(/token=[^&]+/, 'token=***'),
      component: 'testWebSocket'
    });
  };

  ws.onclose = (event) => {
    logger.info('WebSocket Closed', {
      code: event.code,
      reason: event.reason || 'No reason provided',
      wasClean: event.wasClean,
      component: 'testWebSocket'
    });

    // Interpret close codes
    let closeReason = '';
    if (event.code === 1000) {
      closeReason = 'Normal closure';
    } else if (event.code === 1001) {
      closeReason = 'Going away (page navigation)';
    } else if (event.code === 1006) {
      closeReason = 'Abnormal closure - Connection lost';
    } else if (event.code === 1008) {
      closeReason = 'Policy violation - likely authentication issue';
    } else if (event.code >= 4000 && event.code <= 4999) {
      closeReason = 'Application error - check authentication and permissions';
    }

    if (closeReason) {
      logger.info('Close code interpretation', { closeReason, code: event.code, component: 'testWebSocket' });
    }
  };

  return ws;
}

// Export as window function for console testing
if (typeof window !== 'undefined') {
  (window as any).testWebSocket = testWebSocketConnection;
  logger.info('WebSocket test utility loaded. Use window.testWebSocket(userId, token) to test connection.', { component: 'testWebSocket' });
}