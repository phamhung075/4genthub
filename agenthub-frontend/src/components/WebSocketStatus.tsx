import { useEffect, useState } from 'react';
import { useAppSelector } from '../store/hooks';
import { selectIsConnected, selectIsReconnecting, selectWebSocketError } from '../store/slices/webSocketSlice';
import { Wifi, WifiOff, RefreshCw, AlertCircle } from 'lucide-react';

export function WebSocketStatus() {
  const isConnected = useAppSelector(selectIsConnected);
  const isReconnecting = useAppSelector(selectIsReconnecting);
  const error = useAppSelector(selectWebSocketError);
  const [showDetails, setShowDetails] = useState(false);

  // Auto-show details on error
  useEffect(() => {
    if (error) {
      setShowDetails(true);
      setTimeout(() => setShowDetails(false), 5000); // Hide after 5 seconds
    }
  }, [error]);

  const getStatusIcon = () => {
    if (isConnected) {
      return <Wifi className="h-4 w-4 text-green-500" />;
    }
    if (isReconnecting) {
      return <RefreshCw className="h-4 w-4 text-yellow-500 animate-spin" />;
    }
    if (error) {
      return <AlertCircle className="h-4 w-4 text-red-500" />;
    }
    return <WifiOff className="h-4 w-4 text-gray-500" />;
  };

  const getStatusText = () => {
    if (isConnected) return 'Connected';
    if (isReconnecting) return 'Reconnecting...';
    if (error) return 'Connection Error';
    return 'Disconnected';
  };

  const getStatusColor = () => {
    if (isConnected) return 'text-green-600 dark:text-green-400';
    if (isReconnecting) return 'text-yellow-600 dark:text-yellow-400';
    if (error) return 'text-red-600 dark:text-red-400';
    return 'text-gray-600 dark:text-gray-400';
  };

  return (
    <div className="relative">
      <button
        onClick={() => setShowDetails(!showDetails)}
        className={`flex items-center space-x-2 px-3 py-1.5 rounded-md transition-colors hover:bg-gray-100 dark:hover:bg-gray-800 ${getStatusColor()}`}
        title="WebSocket Status"
      >
        {getStatusIcon()}
        <span className="text-xs font-medium hidden sm:inline">{getStatusText()}</span>
      </button>

      {showDetails && (
        <div className="absolute right-0 mt-2 w-64 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-4 z-50">
          <h3 className="text-sm font-semibold mb-2">WebSocket Status</h3>

          <div className="space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Status:</span>
              <span className={getStatusColor()}>{getStatusText()}</span>
            </div>

            {error && (
              <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
                <p className="text-red-600 dark:text-red-400 text-xs">{error}</p>
              </div>
            )}

            <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
              <p className="text-gray-600 dark:text-gray-400">
                Real-time updates {isConnected ? 'active' : 'paused'}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}