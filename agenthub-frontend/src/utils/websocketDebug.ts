/**
 * WebSocket debugging utilities for troubleshooting connection issues
 */

import { websocketService } from '../services/websocketService';
import { changePoolService } from '../services/changePoolService';
import logger from './logger';

interface DebugReport {
  websocket: {
    connected: boolean;
    state: string;
    connectionCount: number;
    reconnectAttempts: number;
  };
  authentication: {
    hasToken: boolean;
    tokenSource: string;
    tokenLength: number;
  };
  changePool: {
    subscriptions: number;
    recentChanges: number;
  };
  browser: {
    url: string;
    protocol: string;
    userAgent: string;
  };
  environment: {
    backendUrl: string;
    isDevelopment: boolean;
  };
}

class WebSocketDebugger {
  /**
   * Generate a comprehensive debug report
   */
  generateReport(): DebugReport {
    // Use same token detection logic as WebSocket service
    const cookieToken = document.cookie.split('; ').find(row => row.startsWith('access_token='))?.split('=')[1];
    const localStorageToken = localStorage.getItem('access_token');
    const authToken = cookieToken || localStorageToken;

    return {
      websocket: {
        connected: websocketService.isConnected(),
        state: this.getWebSocketStateText(),
        connectionCount: this.getConnectionCount(),
        reconnectAttempts: (websocketService as any).reconnectAttempts || 0
      },
      authentication: {
        hasToken: !!authToken,
        tokenSource: cookieToken ? 'cookies' : localStorageToken ? 'localStorage' : 'none',
        tokenLength: authToken?.length || 0
      },
      changePool: {
        subscriptions: changePoolService.getSubscriptions().length,
        recentChanges: changePoolService.getChangeHistory().length
      },
      browser: {
        url: window.location.href,
        protocol: window.location.protocol,
        userAgent: navigator.userAgent.substring(0, 100) + '...'
      },
      environment: {
        backendUrl: import.meta.env?.VITE_BACKEND_URL || 'http://localhost:8000',
        isDevelopment: import.meta.env.DEV
      }
    };
  }

  private getWebSocketStateText(): string {
    const ws = (websocketService as any).ws;
    if (!ws) return 'NOT_CREATED';

    switch (ws.readyState) {
      case WebSocket.CONNECTING: return 'CONNECTING';
      case WebSocket.OPEN: return 'OPEN';
      case WebSocket.CLOSING: return 'CLOSING';
      case WebSocket.CLOSED: return 'CLOSED';
      default: return 'UNKNOWN';
    }
  }

  private getConnectionCount(): number {
    return websocketService.isConnected() ? 1 : 0;
  }

  /**
   * Test WebSocket connection with detailed logging
   */
  async testConnection(): Promise<void> {
    logger.info('🔧 WebSocket Debug: Starting connection test...');

    const report = this.generateReport();
    logger.info('🔧 WebSocket Debug: Current state report:', report);

    if (!report.authentication.hasToken) {
      logger.error('🔧 WebSocket Debug: ❌ No authentication token found!');
      logger.info('🔧 WebSocket Debug: 💡 To fix this:');
      logger.info('  1. Make sure you are logged in');
      logger.info('  2. Check that login sets the access_token in localStorage or cookies');
      logger.info('  3. Verify the token is valid and not expired');
      return;
    }

    if (websocketService.isConnected()) {
      logger.info('🔧 WebSocket Debug: ✅ Already connected');
      return;
    }

    logger.info('🔧 WebSocket Debug: Attempting new connection...');
    try {
      await websocketService.connect();
      logger.info('🔧 WebSocket Debug: ✅ Connection attempt completed');
    } catch (error) {
      logger.error('🔧 WebSocket Debug: ❌ Connection failed:', error);
    }

    // Wait a moment and check status
    setTimeout(() => {
      const newReport = this.generateReport();
      logger.info('🔧 WebSocket Debug: Post-connection report:', newReport);
    }, 2000);
  }

  /**
   * Simulate a task deletion event to test the full flow
   */
  simulateTaskDeletion(): void {
    logger.info('🔧 WebSocket Debug: Simulating task deletion event...');

    const fakeNotification = {
      entityType: 'task' as const,
      entityId: 'test-task-id',
      eventType: 'deleted' as const,
      userId: 'test-user',
      data: { title: 'Test Task' },
      metadata: {
        entity_type: 'task',
        entity_id: 'test-task-id',
        event_type: 'deleted'
      },
      timestamp: new Date().toISOString()
    };

    changePoolService.processChange(fakeNotification);
    logger.info('🔧 WebSocket Debug: Fake notification sent to change pool');
  }

  /**
   * Show recent WebSocket message history
   */
  showMessageHistory(): void {
    const history = changePoolService.getChangeHistory();
    logger.info('🔧 WebSocket Debug: Recent message history:', history);

    if (history.length === 0) {
      logger.warn('🔧 WebSocket Debug: No messages received yet');
      logger.info('🔧 WebSocket Debug: This could mean:');
      logger.info('  1. WebSocket is not connected');
      logger.info('  2. No data changes have occurred');
      logger.info('  3. Messages are not reaching the change pool');
    }
  }

  /**
   * Show active subscriptions
   */
  showSubscriptions(): void {
    const subscriptions = changePoolService.getSubscriptions();
    logger.info('🔧 WebSocket Debug: Active subscriptions:', subscriptions);

    if (subscriptions.length === 0) {
      logger.warn('🔧 WebSocket Debug: No active subscriptions');
      logger.info('🔧 WebSocket Debug: Components may not be using useEntityChanges hook');
    }
  }

  /**
   * Force reconnect WebSocket
   */
  async forceReconnect(): Promise<void> {
    logger.info('🔧 WebSocket Debug: Forcing reconnection...');

    // Disconnect first
    (websocketService as any).disconnect?.();

    // Wait a moment
    await new Promise(resolve => setTimeout(resolve, 1000));

    // Reconnect
    await this.testConnection();
  }

  /**
   * Test subtask animation notifications specifically
   */
  testSubtaskAnimations(parentTaskId: string): void {
    logger.info('🎬 WebSocket Debug: Testing subtask animations for parent:', parentTaskId);

    // Simulate different subtask events
    const mockSubtaskEvents = [
      {
        entityType: 'subtask' as const,
        entityId: `test-subtask-create-${Date.now()}`,
        eventType: 'created' as const,
        userId: 'test-user',
        data: {
          title: 'Test Create Subtask',
          status: 'todo',
          priority: 'medium'
        },
        metadata: {
          entity_type: 'subtask',
          entity_id: `test-subtask-create-${Date.now()}`,
          event_type: 'created',
          parent_task_id: parentTaskId,
          subtask_title: 'Test Create Subtask',
          parent_task_title: 'Test Parent Task',
          timestamp: new Date().toISOString()
        },
        timestamp: new Date().toISOString()
      },
      {
        entityType: 'subtask' as const,
        entityId: `test-subtask-delete-${Date.now()}`,
        eventType: 'deleted' as const,
        userId: 'test-user',
        data: {
          title: 'Test Delete Subtask',
          status: 'todo',
          priority: 'medium'
        },
        metadata: {
          entity_type: 'subtask',
          entity_id: `test-subtask-delete-${Date.now()}`,
          event_type: 'deleted',
          parent_task_id: parentTaskId,
          subtask_title: 'Test Delete Subtask',
          parent_task_title: 'Test Parent Task',
          timestamp: new Date().toISOString()
        },
        timestamp: new Date().toISOString()
      }
    ];

    // Send create event
    setTimeout(() => {
      logger.info('🎬 WebSocket Debug: Sending mock CREATE subtask notification...');
      changePoolService.processChange(mockSubtaskEvents[0]);
    }, 1000);

    // Send delete event
    setTimeout(() => {
      logger.info('🎬 WebSocket Debug: Sending mock DELETE subtask notification...');
      changePoolService.processChange(mockSubtaskEvents[1]);
    }, 3000);

    logger.info('🎬 WebSocket Debug: Mock events scheduled. Watch for animation responses.');
  }

  /**
   * Monitor WebSocket messages with filtering for subtasks
   */
  startWebSocketMonitoring(parentTaskId?: string): () => void {
    logger.info('📡 WebSocket Debug: Starting WebSocket message monitoring...');

    const unsubscribe = websocketService.on('*', (message) => {
      const isSubtaskMessage = message.metadata?.entity_type === 'subtask';
      const matchesParent = !parentTaskId || message.metadata?.parent_task_id === parentTaskId;

      if (isSubtaskMessage) {
        logger.info('📋 WebSocket Debug: Subtask message received:', {
          eventType: message.metadata?.event_type || message.event_type,
          subtaskId: message.metadata?.entity_id,
          parentTaskId: message.metadata?.parent_task_id,
          matchesFilter: matchesParent,
          title: message.metadata?.subtask_title,
          fullMessage: message
        });

        if (matchesParent) {
          logger.info('✅ WebSocket Debug: This subtask message matches our parent filter!');
        } else {
          logger.info('❌ WebSocket Debug: This subtask message does not match our parent filter');
        }
      }
    });

    logger.info('📡 WebSocket Debug: Monitoring started. Call the returned function to stop.');
    return unsubscribe;
  }
}

// Create singleton instance
export const wsDebugger = new WebSocketDebugger();

// Make it available globally for console debugging
if (typeof window !== 'undefined') {
  (window as any).wsDebug = wsDebugger;

  // Log instructions on how to use the debugger
  setTimeout(() => {
    if (!websocketService.isConnected()) {
      logger.info('🔧 WebSocket Debug: Connection issues detected!');
      logger.info('🔧 WebSocket Debug: Use these console commands to debug:');
      logger.info('  wsDebug.generateReport() - Show current status');
      logger.info('  wsDebug.testConnection() - Test connection');
      logger.info('  wsDebug.showMessageHistory() - Show recent messages');
      logger.info('  wsDebug.showSubscriptions() - Show active subscriptions');
      logger.info('  wsDebug.forceReconnect() - Force reconnection');
      logger.info('  wsDebug.testSubtaskAnimations("parent-task-id") - Test subtask animations');
      logger.info('  wsDebug.startWebSocketMonitoring("parent-task-id") - Monitor WebSocket messages');
    }
  }, 3000);
}