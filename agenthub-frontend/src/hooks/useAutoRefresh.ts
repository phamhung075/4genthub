import { useEffect, useRef } from 'react';
import logger from '../utils/logger';

/**
 * Hook that automatically refreshes data at a specified interval
 * and when WebSocket messages are received.
 */
export function useAutoRefresh(
  refreshCallback: () => void,
  dependencies: any[] = [],
  intervalMs: number = 5000 // Poll every 5 seconds
) {
  const intervalRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    // Initial fetch
    refreshCallback();

    // Set up polling interval
    intervalRef.current = setInterval(() => {
      logger.debug('Auto-refreshing data...');
      refreshCallback();
    }, intervalMs);

    // Cleanup
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, dependencies);

  // Manual refresh function
  const refresh = () => {
    refreshCallback();
  };

  return { refresh };
}