/**
 * Mock WebSocket Server for Testing
 *
 * This mock server simulates real WebSocket behavior for comprehensive testing.
 * It supports:
 * - Message sending/receiving
 * - Connection simulation
 * - Reconnection scenarios
 * - Subscription tracking
 * - Real server behavior simulation
 */

import { WSMessage } from '../../services/WebSocketClient';
import type { MockWebSocketServerConfig, ClientSubscription, MockWebSocketClient } from '../../types/testTypes';

export class MockWebSocketServer {
  private config: MockWebSocketServerConfig;
  private clients: Map<string, MockWebSocketClient> = new Map();
  private isRunning: boolean = false;
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private messageSequence: number = 0;
  private networkIssueTimer: NodeJS.Timeout | null = null;
  private eventListeners: Map<string, Function[]> = new Map();

  constructor(config: Partial<MockWebSocketServerConfig> = {}) {
    this.config = {
      url: 'ws://localhost:8000/ws/realtime',
      autoConnect: true,
      connectionDelay: 100,
      heartbeatInterval: 30000,
      reconnectDelay: 1000,
      maxReconnectAttempts: 5,
      simulateNetworkIssues: false,
      ...config
    };
  }

  /**
   * Start the mock server
   */
  start(): void {
    if (this.isRunning) {
      console.warn('[MockWebSocketServer] Server already running');
      return;
    }

    this.isRunning = true;
    console.log('[MockWebSocketServer] 🚀 Starting server on', this.config.url);

    // Start heartbeat
    this.startHeartbeat();

    // Simulate network issues if enabled
    if (this.config.simulateNetworkIssues) {
      this.startNetworkIssueSimulation();
    }

    this.emit('server_started', { url: this.config.url });
  }

  /**
   * Stop the mock server
   */
  stop(): void {
    if (!this.isRunning) {
      return;
    }

    this.isRunning = false;
    console.log('[MockWebSocketServer] 🛑 Stopping server');

    // Disconnect all clients
    this.clients.forEach(client => {
      this.disconnectClient(client.id, 1000, 'Server shutdown');
    });

    // Clear timers
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }

    if (this.networkIssueTimer) {
      clearInterval(this.networkIssueTimer);
      this.networkIssueTimer = null;
    }

    this.clients.clear();
    this.emit('server_stopped');
  }

  /**
   * Simulate client connection
   */
  connectClient(userId: string, token: string): string {
    const clientId = `client-${userId}-${Date.now()}`;

    setTimeout(() => {
      const client: MockWebSocketClient = {
        id: clientId,
        connected: true,
        subscriptions: [],
        messageQueue: [],
        lastSeen: Date.now()
      };

      this.clients.set(clientId, client);

      console.log('[MockWebSocketServer] 📱 Client connected:', clientId);
      this.emit('client_connected', { clientId, userId, token });

      // Send connection acknowledgment
      this.sendToClient(clientId, this.createMessage('system', 'connected', {
        primary: { clientId, timestamp: Date.now() }
      }, { source: 'system' }));

    }, this.config.connectionDelay);

    return clientId;
  }

  /**
   * Simulate client disconnection
   */
  disconnectClient(clientId: string, code: number = 1000, reason: string = 'Normal closure'): void {
    const client = this.clients.get(clientId);
    if (!client) return;

    client.connected = false;
    this.clients.delete(clientId);

    console.log('[MockWebSocketServer] 📱 Client disconnected:', clientId, 'Code:', code, 'Reason:', reason);
    this.emit('client_disconnected', { clientId, code, reason });
  }

  /**
   * Send message to specific client
   */
  sendToClient(clientId: string, message: WSMessage): boolean {
    const client = this.clients.get(clientId);
    if (!client || !client.connected) {
      console.warn('[MockWebSocketServer] Client not connected:', clientId);
      return false;
    }

    client.messageQueue.push(message);
    client.lastSeen = Date.now();

    console.log('[MockWebSocketServer] 📤 Sending message to client:', clientId, message.type);
    this.emit('message_sent', { clientId, message });

    return true;
  }

  /**
   * Broadcast message to all connected clients
   */
  broadcast(message: WSMessage, filter?: (client: MockWebSocketClient) => boolean): number {
    let sentCount = 0;

    this.clients.forEach((client, clientId) => {
      if (!client.connected) return;

      if (filter && !filter(client)) return;

      if (this.sendToClient(clientId, message)) {
        sentCount++;
      }
    });

    console.log('[MockWebSocketServer] 📢 Broadcast message to', sentCount, 'clients');
    return sentCount;
  }

  /**
   * Simulate receiving message from client
   */
  receiveFromClient(clientId: string, message: Record<string, any>): void {
    const client = this.clients.get(clientId);
    if (!client || !client.connected) {
      console.warn('[MockWebSocketServer] Cannot receive from disconnected client:', clientId);
      return;
    }

    client.lastSeen = Date.now();

    console.log('[MockWebSocketServer] 📥 Received message from client:', clientId, message.type);
    this.emit('message_received', { clientId, message });

    // Handle different message types
    switch (message.type) {
      case 'subscribe':
        this.handleSubscription(clientId, message);
        break;
      case 'unsubscribe':
        this.handleUnsubscription(clientId, message);
        break;
      case 'heartbeat':
        this.handleHeartbeat(clientId, message);
        break;
      case 'update':
        this.handleUpdate(clientId, message);
        break;
      default:
        console.warn('[MockWebSocketServer] Unknown message type:', message.type);
    }
  }

  /**
   * Handle client subscription
   */
  private handleSubscription(clientId: string, message: any): void {
    const client = this.clients.get(clientId);
    if (!client) return;

    const subscription: ClientSubscription = {
      clientId,
      scope: message.scope || 'global',
      filters: message.filters || {},
      active: true
    };

    client.subscriptions.push(subscription);

    console.log('[MockWebSocketServer] 🔔 Client subscribed:', clientId, subscription.scope);

    // Send subscription confirmation
    this.sendToClient(clientId, this.createMessage('system', 'subscribed', {
      primary: { scope: subscription.scope, filters: subscription.filters }
    }, { source: 'system' }));
  }

  /**
   * Handle client unsubscription
   */
  private handleUnsubscription(clientId: string, message: any): void {
    const client = this.clients.get(clientId);
    if (!client) return;

    client.subscriptions = client.subscriptions.filter(sub =>
      !(sub.scope === message.scope && JSON.stringify(sub.filters) === JSON.stringify(message.filters))
    );

    console.log('[MockWebSocketServer] 🔕 Client unsubscribed:', clientId, message.scope);
  }

  /**
   * Handle heartbeat from client
   */
  private handleHeartbeat(clientId: string, message: any): void {
    const client = this.clients.get(clientId);
    if (!client) return;

    client.lastSeen = Date.now();

    // Send heartbeat response
    this.sendToClient(clientId, this.createMessage('system', 'pong', {
      primary: { timestamp: Date.now() }
    }, { source: 'system' }));
  }

  /**
   * Handle update from client
   */
  private handleUpdate(clientId: string, message: any): void {
    console.log('[MockWebSocketServer] 🔄 Processing update from client:', clientId);

    // Echo the update to subscribed clients
    const updateMessage = this.createMessage(
      message.payload?.entity || 'unknown',
      message.payload?.action || 'update',
      message.payload?.data || { primary: {} },
      {
        source: 'user',
        userId: clientId,
        ...message.metadata
      }
    );

    this.broadcastToSubscribers(updateMessage, message.payload?.entity);
  }

  /**
   * Broadcast to clients with matching subscriptions
   */
  private broadcastToSubscribers(message: WSMessage, entity?: string): number {
    return this.broadcast(message, (client) => {
      return client.subscriptions.some(sub => {
        if (!sub.active) return false;

        // Check if subscription matches the message
        if (entity && sub.scope !== entity && sub.scope !== 'global') {
          return false;
        }

        // Check filters
        if (sub.filters.branch_id && message.metadata?.parent_branch_id !== sub.filters.branch_id) {
          return false;
        }

        if (sub.filters.task_id && message.metadata?.entity_id !== sub.filters.task_id) {
          return false;
        }

        return true;
      });
    });
  }

  /**
   * Create standardized WebSocket message
   */
  createMessage(entity: string, action: string, data: any, metadata: any = {}): WSMessage {
    return {
      id: `mock-msg-${++this.messageSequence}`,
      version: '2.0',
      type: 'update',
      timestamp: new Date().toISOString(),
      sequence: this.messageSequence,
      payload: {
        entity,
        action,
        data
      },
      metadata: {
        source: 'system',
        ...metadata
      }
    };
  }

  /**
   * Simulate task creation
   */
  createTask(task: any, branchId: string): void {
    const message = this.createMessage('task', 'create', {
      primary: {
        id: task.id || `task-${Date.now()}`,
        title: task.title || 'Test Task',
        status: task.status || 'todo',
        priority: task.priority || 'medium',
        git_branch_id: branchId,
        created_at: new Date().toISOString(),
        ...task
      }
    }, {
      source: 'mcp-ai',
      parent_branch_id: branchId,
      entity_type: 'task',
      entity_id: task.id
    });

    console.log('[MockWebSocketServer] 🆕 Simulating task creation:', task.id);
    this.broadcastToSubscribers(message, 'task');
  }

  /**
   * Simulate task update
   */
  updateTask(taskId: string, updates: any, branchId: string): void {
    const message = this.createMessage('task', 'update', {
      primary: {
        id: taskId,
        updated_at: new Date().toISOString(),
        ...updates
      }
    }, {
      source: 'mcp-ai',
      parent_branch_id: branchId,
      entity_type: 'task',
      entity_id: taskId
    });

    console.log('[MockWebSocketServer] ✏️ Simulating task update:', taskId);
    this.broadcastToSubscribers(message, 'task');
  }

  /**
   * Simulate task deletion
   */
  deleteTask(taskId: string, branchId: string): void {
    const message = this.createMessage('task', 'delete', {
      primary: { id: taskId }
    }, {
      source: 'user',
      parent_branch_id: branchId,
      entity_type: 'task',
      entity_id: taskId
    });

    console.log('[MockWebSocketServer] 🗑️ Simulating task deletion:', taskId);
    this.broadcastToSubscribers(message, 'task');
  }

  /**
   * Simulate connection loss and reconnection
   */
  simulateConnectionLoss(clientId: string, duration: number = 5000): void {
    const client = this.clients.get(clientId);
    if (!client) return;

    console.log('[MockWebSocketServer] 🔌 Simulating connection loss for:', clientId);

    // Disconnect client
    this.disconnectClient(clientId, 1006, 'Connection lost');

    // Reconnect after duration
    setTimeout(() => {
      console.log('[MockWebSocketServer] 🔌 Reconnecting client:', clientId);
      // Client would initiate new connection in real scenario
      this.emit('reconnection_available', { clientId });
    }, duration);
  }

  /**
   * Simulate network issues
   */
  private startNetworkIssueSimulation(): void {
    this.networkIssueTimer = setInterval(() => {
      if (Math.random() < 0.1) { // 10% chance every interval
        const clientIds = Array.from(this.clients.keys());
        if (clientIds.length > 0) {
          const randomClient = clientIds[Math.floor(Math.random() * clientIds.length)];
          this.simulateConnectionLoss(randomClient, 2000);
        }
      }
    }, 10000); // Check every 10 seconds
  }

  /**
   * Start heartbeat for all clients
   */
  private startHeartbeat(): void {
    this.heartbeatTimer = setInterval(() => {
      const heartbeatMessage = this.createMessage('system', 'ping', {
        primary: { timestamp: Date.now() }
      }, { source: 'system' });

      this.broadcast(heartbeatMessage);

      // Check for inactive clients
      const now = Date.now();
      this.clients.forEach((client, clientId) => {
        if (now - client.lastSeen > this.config.heartbeatInterval * 2) {
          console.warn('[MockWebSocketServer] ⚠️ Client inactive, disconnecting:', clientId);
          this.disconnectClient(clientId, 1001, 'Client inactive');
        }
      });
    }, this.config.heartbeatInterval);
  }

  /**
   * Get server statistics
   */
  getStats(): any {
    return {
      isRunning: this.isRunning,
      clientCount: this.clients.size,
      totalSubscriptions: Array.from(this.clients.values())
        .reduce((total, client) => total + client.subscriptions.length, 0),
      messageSequence: this.messageSequence,
      uptime: this.isRunning ? Date.now() : 0
    };
  }

  /**
   * Get client information
   */
  getClient(clientId: string): MockWebSocketClient | undefined {
    return this.clients.get(clientId);
  }

  /**
   * Get all clients
   */
  getAllClients(): MockWebSocketClient[] {
    return Array.from(this.clients.values());
  }

  /**
   * Event listener management
   */
  on(event: string, listener: Function): void {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, []);
    }
    this.eventListeners.get(event)!.push(listener);
  }

  off(event: string, listener: Function): void {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      const index = listeners.indexOf(listener);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    }
  }

  private emit(event: string, data?: any): void {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      listeners.forEach(listener => listener(data));
    }
  }

  /**
   * Reset server state
   */
  reset(): void {
    this.stop();
    this.messageSequence = 0;
    this.eventListeners.clear();
  }
}

/**
 * Helper function to create a configured mock server
 */
export function createMockWebSocketServer(config?: Partial<MockWebSocketServerConfig>): MockWebSocketServer {
  return new MockWebSocketServer(config);
}

/**
 * Test helper: Create server with realistic test data
 */
export function createTestWebSocketServer(): MockWebSocketServer {
  const server = createMockWebSocketServer({
    connectionDelay: 0, // Instant connection for tests
    heartbeatInterval: 1000, // Fast heartbeat for tests
    simulateNetworkIssues: false // Disable for predictable tests
  });

  // Add some test data methods
  (server as any).createTestScenario = function(scenario: string) {
    switch (scenario) {
      case 'multiple_tasks':
        this.createTask({ id: 'test-task-1', title: 'Test Task 1', status: 'todo' }, 'test-branch-1');
        this.createTask({ id: 'test-task-2', title: 'Test Task 2', status: 'in_progress' }, 'test-branch-1');
        this.createTask({ id: 'test-task-3', title: 'Test Task 3', status: 'done' }, 'test-branch-1');
        break;

      case 'rapid_updates':
        const taskId = 'rapid-task-1';
        this.createTask({ id: taskId, title: 'Rapid Task', status: 'todo' }, 'test-branch-1');
        setTimeout(() => this.updateTask(taskId, { status: 'in_progress' }, 'test-branch-1'), 100);
        setTimeout(() => this.updateTask(taskId, { status: 'review' }, 'test-branch-1'), 200);
        setTimeout(() => this.updateTask(taskId, { status: 'done' }, 'test-branch-1'), 300);
        break;

      case 'delete_sequence':
        this.createTask({ id: 'delete-task-1', title: 'Delete Task 1' }, 'test-branch-1');
        this.createTask({ id: 'delete-task-2', title: 'Delete Task 2' }, 'test-branch-1');
        setTimeout(() => this.deleteTask('delete-task-1', 'test-branch-1'), 500);
        setTimeout(() => this.deleteTask('delete-task-2', 'test-branch-1'), 1000);
        break;
    }
  };

  return server;
}

export default MockWebSocketServer;