import React from 'react';
import { Wifi, WifiOff } from 'lucide-react';
import { useIsReconnecting, useWebSocketError } from '../../store/websocket';

/**
 * The realtime-status chip the task and project headers share.
 *
 * "Offline" on its own does not say what happened, and the two reasons the store already records were
 * being dropped at the surface: `isReconnecting` because a retry in progress is not the same state as
 * having given up, and `error` because an authentication refusal carries the SERVER'S reason string -
 * the only thing that distinguishes a scope refusal from a bad credential - which nothing rendered.
 * The chip keeps the connected label driven by the caller, so a header's existing source stays the
 * source of truth for "connected", while the reason comes from the store the socket events write to.
 */
export const SocketStateBadge: React.FC<{ isConnected: boolean }> = ({ isConnected }) => {
  const isReconnecting = useIsReconnecting();
  const error = useWebSocketError();

  const className = isConnected
    ? 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400'
    : 'bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-400';

  const label = isConnected ? 'Live' : isReconnecting ? 'Reconnecting…' : 'Offline';

  return (
    <div
      className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs ${className}`}
      title={error ?? undefined}
    >
      {isConnected ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
      <span>{label}</span>
    </div>
  );
};
