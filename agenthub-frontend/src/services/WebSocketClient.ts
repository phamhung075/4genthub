import { EventEmitter } from '../utils/EventEmitter';

/**
 * WebSocket Protocol v2.0 Message Interface
 * NO BACKWARD COMPATIBILITY - v2.0 ONLY
 */
export interface WSMessage {
  id: string;
  version: '2.0';  // ONLY v2.0 supported
  type: 'update' | 'bulk' | 'sync' | 'heartbeat' | 'error';
  timestamp: string;
  sequence: number;
  payload: {
    entity: string;
    action: string;
    data: {
      primary: any | any[];
      cascade?: {
        branches?: any[];
        tasks?: any[];
        projects?: any[];
        subtasks?: any[];
        contexts?: any[];
      };
    };
  };
  metadata: {
    source: 'mcp-ai' | 'user' | 'system';
    userId?: string;
    sessionId?: string;
    correlationId?: string;
    batchId?: string;
  };
}

/**
 * WebSocket Client v2.0 - Clean Implementation
 * Features:
 * - Dual-track message processing (immediate user, batched AI)
 * - Auto-reconnect with exponential backoff
 * - Cascade data merging and deduplication
 * - NO legacy protocol support
 */
export class WebSocketClient extends EventEmitter {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private aiBuffer: WSMessage[] = [];
  private aiBufferTimer: NodeJS.Timeout | null = null;
  private sequenceNumber = 0;
  private isConnecting = false;
  private heartbeatInterval: NodeJS.Timeout | null = null;

  constructor(
    private userId: string,
    private token: string
  ) {
    super();
  }

  /**
   * Connect to WebSocket server (v2.0 protocol only)
   */
  connect(): void {
    if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.OPEN)) {
      return;
    }

    this.isConnecting = true;
    const wsUrl = `${import.meta.env.VITE_WS_URL || 'ws://localhost:8000'}/ws/${this.userId}?token=${this.token}`;

    console.log('[WebSocket v2.0] Connecting...');
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = this.handleOpen.bind(this);
    this.ws.onmessage = this.handleMessage.bind(this);
    this.ws.onerror = this.handleError.bind(this);
    this.ws.onclose = this.handleClose.bind(this);
  }

  private handleOpen(): void {
    console.log('[WebSocket v2.0] Connected successfully');
    this.isConnecting = false;
    this.reconnectAttempts = 0;
    this.emit('connected');

    // Start heartbeat
    this.startHeartbeat();
  }

  private handleMessage(event: MessageEvent): void {
    try {
      const message: WSMessage = JSON.parse(event.data);

      // ONLY accept v2.0 messages - reject all others
      if (message.version !== '2.0') {
        console.error('[WebSocket] Rejected non-v2.0 message:', message.version);
        return;
      }

      // Handle heartbeat
      if (message.type === 'heartbeat') {
        return;
      }

      // Route based on source for dual-track processing
      if (message.metadata?.source === 'mcp-ai') {
        this.bufferAIUpdate(message);
      } else {
        this.processImmediateUpdate(message);
      }
    } catch (error) {
      console.error('[WebSocket] Failed to parse message:', error);
    }
  }

  /**
   * Buffer AI updates for 500ms batching
   */
  private bufferAIUpdate(message: WSMessage): void {
    this.aiBuffer.push(message);

    // Clear existing timer
    if (this.aiBufferTimer) {
      clearTimeout(this.aiBufferTimer);
    }

    // Process batch after 500ms
    this.aiBufferTimer = setTimeout(() => {
      this.processAIBatch();
    }, 500);
  }

  /**
   * Process batched AI updates with deduplication
   */
  private processAIBatch(): void {
    if (this.aiBuffer.length === 0) return;

    const batchSize = this.aiBuffer.length;
    const mergedUpdate = this.mergeAIUpdates(this.aiBuffer);

    // Emit merged update
    this.emit('update', mergedUpdate);

    // Clear buffer
    this.aiBuffer = [];
    this.aiBufferTimer = null;

    console.log(`[WebSocket] Processed batch of ${batchSize} AI updates`);
  }

  /**
   * Process user updates immediately (no batching)
   */
  private processImmediateUpdate(message: WSMessage): void {
    this.emit('update', message);

    // Special handling for user actions
    if (message.metadata?.source === 'user') {
      this.emit('userAction', message);
    }
  }

  /**
   * Merge multiple AI updates into single message with cascade deduplication
   */
  private mergeAIUpdates(updates: WSMessage[]): WSMessage {
    const primaryUpdates: any[] = [];
    const cascade: Record<string, any[]> = {
      branches: [],
      tasks: [],
      projects: [],
      subtasks: [],
      contexts: []
    };

    // Collect all updates
    updates.forEach(update => {
      // Primary data
      if (Array.isArray(update.payload.data.primary)) {
        primaryUpdates.push(...update.payload.data.primary);
      } else {
        primaryUpdates.push(update.payload.data.primary);
      }

      // Cascade data
      if (update.payload.data.cascade) {
        Object.keys(update.payload.data.cascade).forEach(key => {
          const cascadeKey = key as keyof typeof cascade;
          if (update.payload.data.cascade![cascadeKey]) {
            cascade[cascadeKey].push(...update.payload.data.cascade![cascadeKey]);
          }
        });
      }
    });

    // Deduplicate cascade data by ID
    Object.keys(cascade).forEach(key => {
      const seen = new Set<string>();
      cascade[key] = cascade[key].filter((item: any) => {
        if (seen.has(item.id)) return false;
        seen.add(item.id);
        return true;
      });
    });

    return {
      id: `batch-${Date.now()}`,
      version: '2.0',
      type: 'bulk',
      timestamp: new Date().toISOString(),
      sequence: this.sequenceNumber++,
      payload: {
        entity: 'multiple',
        action: 'update',
        data: {
          primary: primaryUpdates,
          cascade: cascade.branches.length || cascade.tasks.length ||
                  cascade.projects.length || cascade.subtasks.length ||
                  cascade.contexts.length ? cascade : undefined
        }
      },
      metadata: {
        source: 'mcp-ai',
        batchId: `batch-${Date.now()}`
      }
    };
  }

  /**
   * Send message to server (v2.0 protocol only)
   */
  send(message: Partial<WSMessage>): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.error('[WebSocket] Not connected');
      return;
    }

    const fullMessage: WSMessage = {
      id: `msg-${Date.now()}`,
      version: '2.0',
      timestamp: new Date().toISOString(),
      sequence: this.sequenceNumber++,
      type: 'update',
      ...message
    } as WSMessage;

    this.ws.send(JSON.stringify(fullMessage));
  }

  private handleError(error: Event): void {
    console.error('[WebSocket] Error:', error);
    this.emit('error', error);
  }

  private handleClose(): void {
    console.log('[WebSocket] Disconnected');
    this.isConnecting = false;
    this.stopHeartbeat();
    this.emit('disconnected');

    // Attempt reconnection with exponential backoff
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

      console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
      setTimeout(() => this.connect(), delay);
    } else {
      console.error('[WebSocket] Max reconnection attempts reached');
      this.emit('reconnectFailed');
    }
  }

  /**
   * Start heartbeat to keep connection alive
   */
  private startHeartbeat(): void {
    this.stopHeartbeat();

    this.heartbeatInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.send({
          type: 'heartbeat',
          payload: {
            entity: 'system',
            action: 'ping',
            data: { primary: { timestamp: Date.now() } }
          },
          metadata: { source: 'system' }
        });
      }
    }, 30000); // Every 30 seconds
  }

  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  /**
   * Disconnect and cleanup
   */
  disconnect(): void {
    this.reconnectAttempts = this.maxReconnectAttempts; // Prevent auto-reconnect

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    if (this.aiBufferTimer) {
      clearTimeout(this.aiBufferTimer);
      this.aiBufferTimer = null;
    }

    this.stopHeartbeat();
    this.aiBuffer = [];
    this.isConnecting = false;
  }

  /**
   * Get connection status
   */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  /**
   * Reset reconnection attempts
   */
  resetReconnectAttempts(): void {
    this.reconnectAttempts = 0;
  }
}