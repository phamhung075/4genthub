/**
 * WebSocket Connection Test Utility
 * This utility helps debug WebSocket connection issues
 */

export function testWebSocketConnection(userId: string, token: string, backendUrl?: string) {
  console.log('=== WebSocket Connection Test ===');
  console.log('User ID:', userId);
  console.log('Token (first 20 chars):', token?.substring(0, 20) + '...');
  console.log('Backend URL:', backendUrl || 'Using default');

  // Determine WebSocket URL
  let wsUrl: string;
  const backend = backendUrl || import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

  if (backend.startsWith('https')) {
    const host = backend.replace('https://', '');
    wsUrl = `wss://${host}/ws/${userId}?token=${token}`;
  } else {
    const host = backend.replace('http://', '');
    wsUrl = `ws://${host}/ws/${userId}?token=${token}`;
  }

  console.log('Attempting connection to:', wsUrl.replace(/token=[^&]+/, 'token=***'));

  const ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    console.log('✅ WebSocket Connected Successfully!');
    console.log('Ready State:', ws.readyState);
    console.log('Protocol:', ws.protocol);
    console.log('URL:', ws.url?.replace(/token=[^&]+/, 'token=***'));

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

    console.log('Sending test message:', testMessage);
    ws.send(JSON.stringify(testMessage));
  };

  ws.onmessage = (event) => {
    console.log('📨 Message received:', event.data);
    try {
      const message = JSON.parse(event.data);
      console.log('Parsed message:', message);
    } catch (e) {
      console.log('Raw message (not JSON):', event.data);
    }
  };

  ws.onerror = (error) => {
    console.error('❌ WebSocket Error:', error);
    console.error('Ready State:', ws.readyState);
    console.error('URL:', ws.url?.replace(/token=[^&]+/, 'token=***'));
  };

  ws.onclose = (event) => {
    console.log('🔌 WebSocket Closed');
    console.log('Code:', event.code);
    console.log('Reason:', event.reason || 'No reason provided');
    console.log('Was Clean:', event.wasClean);

    // Interpret close codes
    if (event.code === 1000) {
      console.log('Normal closure');
    } else if (event.code === 1001) {
      console.log('Going away (page navigation)');
    } else if (event.code === 1006) {
      console.log('Abnormal closure - Connection lost');
    } else if (event.code === 1008) {
      console.log('Policy violation - likely authentication issue');
    } else if (event.code >= 4000 && event.code <= 4999) {
      console.log('Application error - check authentication and permissions');
    }
  };

  return ws;
}

// Export as window function for console testing
if (typeof window !== 'undefined') {
  (window as any).testWebSocket = testWebSocketConnection;
  console.log('WebSocket test utility loaded. Use window.testWebSocket(userId, token) to test connection.');
}