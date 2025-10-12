import { EventEmitter } from '../utils/EventEmitter';
import { config } from '../config/environment';
import type { WebSocketConfig, WSMessage } from '../types/websocketTypes';
import logger from '../utils/logger';

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
  private wsConfig: WebSocketConfig;
  private aiBuffer: WSMessage[] = [];
  private aiBufferTimer: NodeJS.Timeout | null = null;
  private sequenceNumber = 0;
  private isConnecting = false;
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private processedMessages = new Set<string>();
  private readonly MAX_PROCESSED_MESSAGES = 1000;

  constructor(
    private userId: string,
    private token: string,
    wsConfig?: Partial<WebSocketConfig>
  ) {
    super();

    // Initialize WebSocket configuration with defaults from environment and allow overrides
    this.wsConfig = {
      maxReconnectAttempts: wsConfig?.maxReconnectAttempts ?? config.websocket.maxReconnectAttempts,
      reconnectDelay: wsConfig?.reconnectDelay ?? config.websocket.reconnectDelay,
      aiBufferTimeout: wsConfig?.aiBufferTimeout ?? config.websocket.aiBufferTimeout,
      maxReconnectDelay: wsConfig?.maxReconnectDelay ?? config.websocket.maxReconnectDelay,
      heartbeatInterval: wsConfig?.heartbeatInterval ?? config.websocket.heartbeatInterval,
    };
  }

  /**
   * Connect to WebSocket server (v2.0 protocol only)
   */
  connect(): void {
    if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.OPEN)) {
      logger.debug('[WebSocket v2.0] Already connecting or connected, skipping');
      return;
    }

    this.isConnecting = true;
    // Use configuration instead of direct environment access
    const wsBaseUrl = config.websocket.url;

    // Enhanced debugging for WebSocket URL configuration
    logger.debug('[WebSocket v2.0] 🔍 DEBUG: WebSocket Configuration Check:');
    logger.debug('  - config.websocket.url:', wsBaseUrl);
    logger.debug('  - config object:', config);
    logger.debug('  - typeof wsBaseUrl:', typeof wsBaseUrl);
    logger.debug('  - wsBaseUrl length:', wsBaseUrl?.length);
    logger.debug('  - Environment check completed');

    if (!wsBaseUrl) {
      logger.error('[WebSocket v2.0] ❌ WebSocket URL is not configured');
      logger.error('[WebSocket v2.0] 🚨 CRITICAL: config.websocket.url is:', wsBaseUrl);
      logger.error('[WebSocket v2.0] 🚨 CRITICAL: Full config object:', JSON.stringify(config, null, 2));
      this.emit('error', new Error('WebSocket URL not configured'));
      this.isConnecting = false;
      return;
    }

    const wsUrl = `${wsBaseUrl}/ws/realtime?token=${this.token}`;

    logger.debug('[WebSocket v2.0] 🔌 DEBUG: Attempting WebSocket connection');
    logger.debug('  - Full WebSocket URL:', wsUrl.replace(/token=[^&]+/, 'token=***'));
    logger.debug('  - Base URL:', wsBaseUrl);
    logger.debug('  - Token length:', this.token ? this.token.length : 0);
    logger.debug('  - User ID:', this.userId);
    logger.debug('  - About to create WebSocket object...');

    this.ws = new WebSocket(wsUrl);

    logger.debug('[WebSocket v2.0] ✅ WebSocket object created successfully');
    logger.debug('  - WebSocket readyState:', this.ws.readyState);
    logger.debug('  - WebSocket URL:', this.ws.url.replace(/token=[^&]+/, 'token=***'));

    this.ws.onopen = this.handleOpen.bind(this);
    this.ws.onmessage = this.handleMessage.bind(this);
    this.ws.onerror = this.handleError.bind(this);
    this.ws.onclose = this.handleClose.bind(this);
  }

  private handleOpen(): void {
    logger.debug('[WebSocket v2.0] ✅ Connected successfully');
    logger.debug('[WebSocket v2.0] 📡 Connection state:', this.ws?.readyState);
    logger.debug('[WebSocket v2.0] 🎯 Event listeners count:', this.listenerCount('connected'));

    this.isConnecting = false;
    this.reconnectAttempts = 0;

    logger.debug('[WebSocket v2.0] 🔊 Emitting "connected" event');
    this.emit('connected');

    // Start heartbeat
    this.startHeartbeat();
    logger.debug('[WebSocket v2.0] 💓 Heartbeat started');
  }

  private handleMessage(event: MessageEvent): void {
    logger.debug('[WebSocket v2.0] 📨 🚨 DELETE DEBUG: Raw message received:', {
      type: typeof event.data,
      length: event.data?.length,
      preview: event.data?.substring(0, 200)
    });

    try {
      const message: WSMessage = JSON.parse(event.data);

      logger.debug('[WebSocket v2.0] 📋 🚨 DELETE DEBUG: Parsed message:', {
        id: message.id,
        version: message.version,
        type: message.type,
        entity: message.payload?.entity,
        action: message.payload?.action,
        source: message.metadata?.source
      });

      // Special detailed logging for DELETE operations
      if (message.payload?.action?.toLowerCase().includes('delete')) {
        logger.warn('🗑️ DELETE MESSAGE RECEIVED IN WEBSOCKET CLIENT:');
        logger.warn('  Message ID:', message.id);
        logger.warn('  Entity:', message.payload?.entity);
        logger.warn('  Action:', message.payload?.action);
        logger.warn('  Data:', message.payload?.data);
        logger.warn('  Metadata:', message.metadata);
        logger.warn('  Full message:', message);
      }

      // ONLY accept v2.0 messages - reject all others
      if (message.version !== '2.0') {
        logger.error('[WebSocket] ❌ Rejected non-v2.0 message:', message.version);
        return;
      }

      // Handle heartbeat
      if (message.type === 'heartbeat') {
        logger.debug('[WebSocket v2.0] 💓 Heartbeat received');
        return;
      }

      logger.debug('[WebSocket v2.0] 🎯 🚨 DELETE DEBUG: Routing message based on source:', message.metadata?.source);

      // Route based on source for dual-track processing
      if (message.metadata?.source === 'mcp-ai') {
        if (message.payload?.action?.toLowerCase().includes('delete')) {
          logger.warn('[WebSocket v2.0] 🤖 🗑️ DELETE: Buffering AI update');
        } else {
          logger.debug('[WebSocket v2.0] 🤖 Buffering AI update');
        }
        this.bufferAIUpdate(message);
      } else {
        if (message.payload?.action?.toLowerCase().includes('delete')) {
          logger.warn('[WebSocket v2.0] ⚡ 🗑️ DELETE: Processing immediate update');
        } else {
          logger.debug('[WebSocket v2.0] ⚡ Processing immediate update');
        }
        this.processImmediateUpdate(message);
      }
    } catch (error) {
      logger.error('[WebSocket] ❌ Failed to parse message:', error);
      logger.error('[WebSocket] 📝 Raw data:', event.data);
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

    // Process batch after configured timeout
    this.aiBufferTimer = setTimeout(() => {
      this.processAIBatch();
    }, this.wsConfig.aiBufferTimeout);
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

    logger.debug(`[WebSocket] Processed batch of ${batchSize} AI updates`);
  }

  /**
   * Process user updates immediately (no batching)
   */
  private processImmediateUpdate(message: WSMessage): void {
    logger.debug('[WebSocket v2.0] ⚡ 🚨 DELETE DEBUG: Processing immediate update:', {
      entity: message.payload?.entity,
      action: message.payload?.action,
      messageId: message.id,
      updateListeners: this.listenerCount('update'),
      userActionListeners: this.listenerCount('userAction')
    });

    // CRITICAL FIX: Deduplicate messages by ID to prevent duplicate notifications
    if (this.processedMessages.has(message.id)) {
      logger.debug('[WebSocket v2.0] ⏭️ Skipping duplicate message:', {
        messageId: message.id,
        entity: message.payload?.entity,
        action: message.payload?.action
      });
      return;
    }

    // Add to processed messages set
    this.processedMessages.add(message.id);

    // Prevent memory leak: keep only last MAX_PROCESSED_MESSAGES
    if (this.processedMessages.size > this.MAX_PROCESSED_MESSAGES) {
      const firstMessage = this.processedMessages.values().next().value;
      this.processedMessages.delete(firstMessage);
    }

    // Special detailed logging for DELETE operations
    if (message.payload?.action?.toLowerCase().includes('delete')) {
      logger.warn('🗑️ DELETE IMMEDIATE UPDATE PROCESSING:');
      logger.warn('  Message ID:', message.id);
      logger.warn('  Entity:', message.payload?.entity);
      logger.warn('  Action:', message.payload?.action);
      logger.warn('  Update Listeners:', this.listenerCount('update'));
      logger.warn('  User Action Listeners:', this.listenerCount('userAction'));
      logger.warn('  Processed Messages Count:', this.processedMessages.size);
      logger.warn('  About to emit "update" event...');
    }

    logger.debug('[WebSocket v2.0] 🔊 🚨 DELETE DEBUG: Emitting "update" event');
    this.emit('update', message);

    if (message.payload?.action?.toLowerCase().includes('delete')) {
      logger.warn('✅ DELETE "update" event emitted successfully');
    }

    // Special handling for user actions
    if (message.metadata?.source === 'user') {
      logger.debug('[WebSocket v2.0] 🔊 Emitting "userAction" event');
      this.emit('userAction', message);

      if (message.payload?.action?.toLowerCase().includes('delete')) {
        logger.warn('✅ DELETE "userAction" event emitted successfully');
      }
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
        const updateCascade = update.payload.data.cascade;
        // Process each cascade key explicitly
        if (updateCascade.branches && Array.isArray(updateCascade.branches)) {
          cascade.branches.push(...updateCascade.branches);
        }
        if (updateCascade.tasks && Array.isArray(updateCascade.tasks)) {
          cascade.tasks.push(...updateCascade.tasks);
        }
        if (updateCascade.projects && Array.isArray(updateCascade.projects)) {
          cascade.projects.push(...updateCascade.projects);
        }
        if (updateCascade.subtasks && Array.isArray(updateCascade.subtasks)) {
          cascade.subtasks.push(...updateCascade.subtasks);
        }
        if (updateCascade.contexts && Array.isArray(updateCascade.contexts)) {
          cascade.contexts.push(...updateCascade.contexts);
        }
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
  send(message: Record<string, unknown> & { type?: string }): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      logger.error('[WebSocket] Not connected');
      return;
    }

    const { type, ...rest } = message;
    const fullMessage = {
      id: `msg-${Date.now()}`,
      version: '2.0',
      timestamp: new Date().toISOString(),
      sequence: this.sequenceNumber++,
      type: typeof type === 'string' ? type : 'update',
      ...rest
    };

    this.ws.send(JSON.stringify(fullMessage));
  }

  private handleError(error: Event): void {
    logger.error('[WebSocket v2.0] ❌ Connection error:', error);
    logger.error('[WebSocket v2.0] 📊 Connection state:', this.ws?.readyState);
    logger.error('[WebSocket v2.0] 🔗 URL:', this.ws?.url?.replace(/token=[^&]+/, 'token=***'));
    this.emit('error', error);
  }

  private handleClose(event?: CloseEvent): void {
    logger.debug('[WebSocket v2.0] 🔌 Connection closed:', {
      code: event?.code,
      reason: event?.reason,
      wasClean: event?.wasClean,
      readyState: this.ws?.readyState
    });
    this.isConnecting = false;
    this.stopHeartbeat();
    this.emit('disconnected');

    // Check for authentication failure (code 1008 or 4001-4003)
    if (event?.code === 1008 || (event?.code && event.code >= 4001 && event.code <= 4003)) {
      logger.error('[WebSocket] Authentication failed - not attempting reconnect');
      this.emit('authenticationFailed', event.reason || 'Authentication failed');
      return;
    }

    // Attempt reconnection with exponential backoff for other disconnections
    if (this.reconnectAttempts < this.wsConfig.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = Math.min(
        this.wsConfig.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1),
        this.wsConfig.maxReconnectDelay
      );

      logger.debug(`[WebSocket] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.wsConfig.maxReconnectAttempts})`);
      setTimeout(() => this.connect(), delay);
    } else {
      logger.error('[WebSocket] Max reconnection attempts reached');
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
    }, this.wsConfig.heartbeatInterval);
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
    // Guard: Don't disconnect if already disconnected or disconnecting
    if (!this.ws && !this.isConnecting) {
      logger.debug('[WebSocket v2.0] Already disconnected, skipping disconnect');
      return;
    }

    // Guard: Don't disconnect if WebSocket is already closed
    if (this.ws && this.ws.readyState === WebSocket.CLOSED) {
      logger.debug('[WebSocket v2.0] WebSocket already closed, cleaning up');
      this.ws = null;
      this.isConnecting = false;
      return;
    }

    logger.debug('[WebSocket v2.0] Disconnecting WebSocket', {
      readyState: this.ws?.readyState,
      isConnecting: this.isConnecting
    });

    this.reconnectAttempts = this.wsConfig.maxReconnectAttempts; // Prevent auto-reconnect

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
    this.processedMessages.clear(); // Clear processed messages on disconnect
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

  /**
   * Get current WebSocket configuration
   */
  getConfig(): WebSocketConfig {
    return { ...this.wsConfig };
  }
}
