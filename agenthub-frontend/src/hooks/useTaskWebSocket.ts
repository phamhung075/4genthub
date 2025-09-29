import { useCallback, useRef, useEffect, useMemo } from 'react';
import { useTaskWebSocket as useTaskWebSocketV2 } from './useWebSocketV2';
import { useEntityChanges } from './useChangeSubscription';
import { useAppSelector } from '../store/hooks';
import { TaskSummary } from '../types/taskTypes';
import logger from '../utils/logger';

interface UseTaskWebSocketOptions {
  userId: string;
  token: string;
  taskTreeId: string;
  projectId: string;
  onTaskUpdate?: (notification: any) => boolean; // Returns true if handled
}

interface UseTaskWebSocketReturn {
  isConnected: boolean;
  isReconnecting: boolean;
  error: Error | null;
  branchTaskTotal: number | undefined;
  handleTaskChanges: (notification?: any) => Promise<void>;
}

export function useTaskWebSocket({
  userId,
  token,
  taskTreeId,
  projectId,
  onTaskUpdate
}: UseTaskWebSocketOptions): UseTaskWebSocketReturn {

  // Initialize WebSocket for real-time task updates
  const { isConnected, isReconnecting, error } = useTaskWebSocketV2(userId, token);

  // Real-time branch summary from WebSocket cascade store
  const branchSummary = useAppSelector(state => state.cascade?.branches?.[taskTreeId]);

  // Debounce timer ref for batching rapid changes
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const isLoadingRef = useRef(false);

  // Derive branch-reported totals from WebSocket cascade payload
  const branchTaskTotal = useMemo(() => {
    if (!branchSummary) return undefined;

    const counts = branchSummary.task_counts;
    if (counts && typeof counts.total === "number") {
      return counts.total;
    }

    // Use standardized task_count property
    const candidateTotals = [branchSummary.task_count];

    for (const value of candidateTotals) {
      if (typeof value === "number") {
        return value;
      }
    }

    return undefined;
  }, [branchSummary]);

  // Optimized task change handler with WebSocket-first strategy and debouncing
  const handleTaskChanges = useCallback(async (notification?: any) => {
    console.log('🚀 [useTaskWebSocket] OPTIMIZED CHANGE EVENT - WebSocket-first strategy');

    // Clear any existing debounce timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
      debounceTimerRef.current = null;
    }

    // PHASE 1: Try to process with WebSocket data first (0 API calls)
    if (notification && onTaskUpdate) {
      console.log('🚀 [useTaskWebSocket] Attempting WebSocket-first update:', {
        entityType: notification.entityType,
        entityId: notification.entityId,
        eventType: notification.eventType,
        hasData: !!notification.data,
        timestamp: new Date().toISOString()
      });

      // Try to update from WebSocket data
      const wasProcessed = onTaskUpdate(notification);

      if (wasProcessed) {
        console.log('✅ [useTaskWebSocket] Successfully processed via WebSocket - NO API CALL NEEDED');
        logger.info('Task update processed via WebSocket (performance optimized)', {
          component: 'useTaskWebSocket',
          entityId: notification.entityId,
          eventType: notification.eventType
        });
        return; // EARLY EXIT - no API call needed!
      } else {
        console.log('⚠️ [useTaskWebSocket] WebSocket processing failed, falling back to API call');
      }
    }

    // PHASE 2: Debounced fallback to API call (only when WebSocket data insufficient)
    console.log('🚀 [useTaskWebSocket] Setting up debounced API fallback (200ms delay)');

    debounceTimerRef.current = setTimeout(async () => {
      // Prevent duplicate calls during debounce period
      if (isLoadingRef.current) {
        console.log('🚀 [useTaskWebSocket] API call already in progress, skipping debounced call');
        return;
      }

      console.log('🚀 [useTaskWebSocket] Executing debounced API fallback');
      isLoadingRef.current = true;

      try {
        // Signal that we need to fallback to API call
        // This will be handled by the component using this hook
        console.log('🚀 [useTaskWebSocket] API fallback needed - signaling to parent component');

        // The actual API call should be handled by the parent component
        // since it has access to the task data state
        if (onTaskUpdate) {
          // Pass a special notification to indicate API fallback is needed
          onTaskUpdate({
            entityType: 'task',
            eventType: 'api_fallback_needed',
            entityId: null,
            data: null,
            metadata: { git_branch_id: taskTreeId }
          });
        }

        console.log('✅ [useTaskWebSocket] API fallback signal sent');
        logger.info('Task update fallback signal sent', {
          component: 'useTaskWebSocket'
        });

      } catch (error: any) {
        console.error('❌ [useTaskWebSocket] Fallback signaling failed:', error);
        logger.error('Failed to signal API fallback', {
          component: 'useTaskWebSocket',
          error
        });
      } finally {
        isLoadingRef.current = false;
      }
    }, 200); // 200ms debounce delay
  }, [taskTreeId, onTaskUpdate]);

  // Subscribe to centralized change pool for real-time updates
  useEntityChanges(
    'useTaskWebSocket',
    ['task', 'subtask'],
    handleTaskChanges,
    {
      branchId: taskTreeId,
      projectId: projectId,
      enabled: true
    }
  );

  // Cleanup debounce timer on unmount
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  return {
    isConnected,
    isReconnecting,
    error,
    branchTaskTotal,
    handleTaskChanges,
  };
}
