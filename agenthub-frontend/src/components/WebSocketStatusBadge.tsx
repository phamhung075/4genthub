/**
 * WebSocket Status Badge
 *
 * Displays reconnection status when WebSocket connection is unstable.
 * Automatically hides when connected.
 */

import { useAppSelector } from '../store/hooks';
import { selectIsConnected, selectIsReconnecting } from '../store/slices/webSocketSlice';

export function WebSocketStatusBadge() {
  const isConnected = useAppSelector(selectIsConnected);
  const isReconnecting = useAppSelector(selectIsReconnecting);

  // Only show when reconnecting or disconnected (not on initial connect)
  if (isConnected && !isReconnecting) {
    return null;
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 animate-in fade-in slide-in-from-bottom-2 duration-300">
      <div className="flex items-center gap-2 bg-orange-500 text-white px-4 py-2 rounded-lg shadow-lg">
        {/* Spinner */}
        <div className="flex items-center justify-center">
          <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
        </div>

        {/* Message */}
        <span className="text-sm font-medium">
          {isReconnecting ? 'Reconnecting...' : 'Connection lost'}
        </span>

        {/* Pulse indicator */}
        {isReconnecting && (
          <div className="w-2 h-2 bg-white rounded-full animate-pulse" />
        )}
      </div>
    </div>
  );
}
