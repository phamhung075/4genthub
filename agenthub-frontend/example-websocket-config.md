# WebSocket Configuration Examples

## Environment Variables (.env)

```bash
# WebSocket Configuration
VITE_WS_URL=ws://localhost:8000
VITE_WS_MAX_RECONNECT_ATTEMPTS=5
VITE_WS_RECONNECT_DELAY=1000
VITE_WS_AI_BUFFER_TIMEOUT=500
VITE_WS_MAX_RECONNECT_DELAY=30000
VITE_WS_HEARTBEAT_INTERVAL=30000
```

## Usage Examples

### Default Configuration (from environment)
```typescript
import { WebSocketClient } from './services/WebSocketClient';

// Uses all defaults from environment
const wsClient = new WebSocketClient(userId, token);
```

### Custom Configuration Override
```typescript
import { WebSocketClient } from './services/WebSocketClient';

// Override specific values
const wsClient = new WebSocketClient(userId, token, {
  maxReconnectAttempts: 3,     // Lower retry count for testing
  heartbeatInterval: 10000,    // More frequent heartbeat
  aiBufferTimeout: 200,        // Faster AI batch processing
});
```

### Production Configuration
```typescript
// Production optimized settings
const wsClient = new WebSocketClient(userId, token, {
  maxReconnectAttempts: 10,    // More resilient
  reconnectDelay: 2000,        // Slower initial retry
  maxReconnectDelay: 60000,    // Longer max delay (1 minute)
  heartbeatInterval: 60000,    // Less frequent heartbeat
  aiBufferTimeout: 1000,       // Longer batching for efficiency
});
```

### Check Current Configuration
```typescript
const currentConfig = wsClient.getConfig();
console.log('WebSocket Configuration:', currentConfig);
```

## Migration from Hardcoded Values

### Before (Hardcoded)
```typescript
// Old hardcoded values
private maxReconnectAttempts = 5;
private reconnectDelay = 1000;
// setTimeout(..., 500); // AI buffer timeout
// Math.min(..., 30000); // Max reconnect delay
// setInterval(..., 30000); // Heartbeat interval
```

### After (Configurable)
```typescript
// New configurable values
private wsConfig: WebSocketConfig;

constructor(userId: string, token: string, wsConfig?: Partial<WebSocketConfig>) {
  this.wsConfig = {
    maxReconnectAttempts: wsConfig?.maxReconnectAttempts ?? config.websocket.maxReconnectAttempts,
    reconnectDelay: wsConfig?.reconnectDelay ?? config.websocket.reconnectDelay,
    aiBufferTimeout: wsConfig?.aiBufferTimeout ?? config.websocket.aiBufferTimeout,
    maxReconnectDelay: wsConfig?.maxReconnectDelay ?? config.websocket.maxReconnectDelay,
    heartbeatInterval: wsConfig?.heartbeatInterval ?? config.websocket.heartbeatInterval,
  };
}
```