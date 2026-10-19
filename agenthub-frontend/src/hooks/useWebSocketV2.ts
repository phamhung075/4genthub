import { useEffect, useRef, useCallback } from 'react';
import { WebSocketClient, WSMessage } from '../services/WebSocketClient';
import {
  useIsConnected,
  useIsReconnecting,
  useWebSocketError,
  getWebSocketState,
} from '../store/websocket';
import { webSocketAnimationService } from '../services/WebSocketAnimationService';
import logger from '../utils/logger';
import {
  validateWebSocketMessage,
  logWSValidationResult,
  WSValidationStats,
} from '../utils/websocketValidator';


// Global WebSocket instance to ensure singleton
let globalWebSocketClient: WebSocketClient | null = null;
// Track if integrations have been initialized for the global client to prevent duplicates
let globalIntegrationsInitialized = false;

/**
 * `EventEmitter` types every listener as `(...args: unknown[]) => void`. This adapter restores the
 * concrete argument types the client emits for a given event, so the handlers below stay typed.
 */
const onEvent = <TArgs extends unknown[]>(
  client: WebSocketClient,
  event: string,
  handler: (...args: TArgs) => void
): void => {
  client.on(event, handler as (...args: unknown[]) => void);
};

/**
 * React Hook for WebSocket v2.0
 * Provides WebSocket connection management and real-time updates
 * Implements singleton pattern to prevent multiple connections
 */
export function useWebSocket(userId: string, token: string) {
  const clientRef = useRef<WebSocketClient | null>(null);
  const prevCredentialsRef = useRef<{userId: string, token: string} | null>(null);

  // Get WebSocket state from Zustand store
  const isConnected = useIsConnected();
  const isReconnecting = useIsReconnecting();
  const wsError = useWebSocketError();

  useEffect(() => {
    // Check if this is a credential CHANGE (logout/expiry) vs mount cycle
    const hadCredentials = prevCredentialsRef.current !== null;
    const hasCredentials = !!(userId && token);

    // CRITICAL FIX: Only disconnect on actual logout (had credentials → no credentials)
    // This prevents premature disconnect during React Strict Mode remount
    if (hadCredentials && !hasCredentials) {
      logger.warn('[useWebSocket] 🚨 Logout/expiry detected - disconnecting WebSocket for security', {
        previousUserId: prevCredentialsRef.current?.userId,
      }, 'useWebSocketV2.ts');

      // SECURITY FIX: Disconnect global WebSocket singleton when credentials are cleared
      if (globalWebSocketClient) {
        const isConnecting = globalWebSocketClient.isConnectingNow;
        const connectionState = globalWebSocketClient.isConnected() ? 'connected' :
                              isConnecting ? 'connecting' : 'disconnected';

        if (connectionState === 'connected' || connectionState === 'connecting') {
          globalWebSocketClient.disconnect();
          globalWebSocketClient = null;
          globalIntegrationsInitialized = false;
        }
      }

      prevCredentialsRef.current = null;
      return;
    }

    // Skip if no credentials (initial mount or React Strict Mode remount)
    if (!hasCredentials) {
      logger.debug('[useWebSocket] No credentials yet - waiting (React Strict Mode safe)', {
        hadPreviousCredentials: hadCredentials,
      }, 'useWebSocketV2.ts');
      return;
    }


    // Update credential tracking ref for next change detection
    prevCredentialsRef.current = {userId, token};

    // Check if we already have a global client with the same credentials
    if (globalWebSocketClient) {
      const { userId: existingClientUserId, token: existingClientToken } = globalWebSocketClient.credentials;

      if (existingClientUserId === userId && existingClientToken === token) {
        clientRef.current = globalWebSocketClient;

        // FIX: Only initialize integrations if not already done for this global client
        // Prevents duplicate event listeners that cause 3x message processing
        logger.debug('[useWebSocket] Reusing existing WebSocket client', {
          integrationsInitialized: globalIntegrationsInitialized,
        }, 'useWebSocketV2.ts');

        // Services should only be initialized once per global client instance
        // Return cleanup function that doesn't affect the global integrations
        return () => {
          clientRef.current = null;
          logger.debug('[useWebSocket] Component unmounted, keeping global client and integrations alive', undefined, 'useWebSocketV2.ts');
        };
      } else {
        globalWebSocketClient.disconnect();
        globalWebSocketClient = null;
        globalIntegrationsInitialized = false;
      }
    }

    // Create new WebSocket client
    const client = new WebSocketClient(token, userId);
    clientRef.current = client;
    globalWebSocketClient = client;

    // Handle updates (both immediate and batched)
    onEvent(client, 'update', (message: WSMessage) => {
      // WEBSOCKET VALIDATION: Validate message structure in development
      if (import.meta.env.DEV || import.meta.env.VITE_VALIDATE_RESPONSES === 'true') {
        const validationResult = validateWebSocketMessage(message);
        logWSValidationResult(validationResult, message);
        WSValidationStats.record(validationResult);
      }

      // Add message to Zustand store
      getWebSocketState().addMessage(message);

      // Note: Cascade data integration removed - was write-only (stored but never read)
    });

    // Handle user actions (immediate feedback)
    onEvent(client, 'userAction', (message: WSMessage) => {
      // WEBSOCKET VALIDATION: Validate user action messages in development
      if (import.meta.env.DEV || import.meta.env.VITE_VALIDATE_RESPONSES === 'true') {
        const validationResult = validateWebSocketMessage(message);
        logWSValidationResult(validationResult, message);
        WSValidationStats.record(validationResult);
      }

      // User actions are already captured in the main update handler
    });

    // Handle connection events
    client.on('connected', () => {
      logger.info('[WebSocket] ✅ Connected');
      getWebSocketState().setConnected();
    });

    client.on('disconnected', () => {
      logger.warn('[WebSocket] ❌ Disconnected');
      getWebSocketState().setDisconnected();
    });

    // Handle reconnecting event with attempt details
    onEvent(client, 'reconnecting', (details: {attempt: number, maxAttempts: number, delay: number}) => {
      logger.info(`[WebSocket] 🔄 Reconnecting (${details.attempt}/${details.maxAttempts})`);
      getWebSocketState().setReconnecting(details.attempt);
    });

    onEvent(client, 'error', (errorEvent: unknown) => {
      logger.error('[WebSocket] ❌ Error:', errorEvent);
      getWebSocketState().setError('WebSocket connection error');
    });

    client.on('reconnectFailed', () => {
      logger.error('[WebSocket] ❌ Reconnect failed');
      getWebSocketState().setReconnectFailed();
    });

    onEvent(client, 'authenticationFailed', (reason: string) => {
      logger.error('[WebSocket] ❌ Auth failed:', reason);
      getWebSocketState().setError(`WebSocket authentication failed: ${reason}`);
    });

    // Initialize services only once per global client
    logger.info('[useWebSocket] Initializing WebSocket integrations for new client', undefined, 'useWebSocketV2.ts');

    webSocketAnimationService.init({
      on: (event: string, handler: (message: WSMessage) => void) => onEvent(client, event, handler),
    });

    // Mark integrations as initialized
    globalIntegrationsInitialized = true;

    // Connect to server
    client.connect();

    // Cleanup on unmount or credential change
    return () => {
      clientRef.current = null;
      logger.debug('[useWebSocket] Component cleanup executed', undefined, 'useWebSocketV2.ts');
    };
  }, [userId, token]);

  /**
   * Send message to WebSocket server
   */
  const sendMessage = useCallback((message: Record<string, unknown>) => {
    if (clientRef.current) {
      clientRef.current.send(message);
    } else {
      logger.error('[WebSocket] Client not initialized');
    }
  }, []);

  /**
   * Manually reconnect
   */
  const reconnect = useCallback(() => {
    if (clientRef.current) {
      clientRef.current.resetReconnectAttempts();
      clientRef.current.connect();
    }
  }, []);

  /**
   * Disconnect WebSocket (for logout or cleanup)
   */
  const disconnect = useCallback(() => {
    if (clientRef.current) {
      clientRef.current.disconnect();
      if (globalWebSocketClient === clientRef.current) {
        globalWebSocketClient = null;
        globalIntegrationsInitialized = false;
      }
    }
  }, []);

  return {
    client: clientRef.current,
    isConnected,
    isReconnecting,
    error: wsError ? new Error(wsError) : null,
    sendMessage,
    reconnect,
    disconnect
  };
}

/**
 * Specialized hook for branch real-time updates
 */
export function useBranchWebSocket(userId: string, token: string, branchId?: string) {
  const { sendMessage, ...wsState } = useWebSocket(userId, token);

  const subscribeToBranch = useCallback(() => {
    if (branchId) {
      sendMessage({
        type: 'subscribe',
        scope: 'branch',
        filters: {
          branch_id: branchId
        }
      });
    }
  }, [branchId, sendMessage]);

  useEffect(() => {
    if (wsState.isConnected && branchId) {
      subscribeToBranch();
    }
  }, [wsState.isConnected, branchId, subscribeToBranch]);

  return {
    ...wsState,
    sendMessage
  };
}
