/**
 * React Hook for WebSocket real-time updates
 */

import { useEffect, useCallback, useRef } from 'react';
import { websocketService, WebSocketMessage, DataChangeHandler } from '../services/websocketService';

interface UseWebSocketOptions {
  onTaskUpdate?: (taskId: string, data: any) => void;
  onSubtaskUpdate?: (subtaskId: string, parentTaskId: string, data: any) => void;
  onProjectUpdate?: (projectId: string, data: any) => void;
  onBranchUpdate?: (branchId: string, data: any) => void;
  onContextUpdate?: (contextId: string, level: string, data: any) => void;
  onAnyUpdate?: (message: WebSocketMessage) => void;
}

/**
 * Hook for subscribing to WebSocket updates
 */
export function useWebSocket(options: UseWebSocketOptions = {}) {
  // Store refs to avoid recreating handlers
  const optionsRef = useRef(options);
  optionsRef.current = options;

  // Create stable handlers
  const handleTaskUpdate = useCallback((message: WebSocketMessage) => {
    const taskId = message.metadata?.entity_id;
    if (taskId && optionsRef.current.onTaskUpdate) {
      optionsRef.current.onTaskUpdate(taskId, message.data);
    }
    optionsRef.current.onAnyUpdate?.(message);
  }, []);

  const handleSubtaskUpdate = useCallback((message: WebSocketMessage) => {
    const subtaskId = message.metadata?.entity_id;
    const parentTaskId = message.metadata?.parent_task_id;
    if (subtaskId && parentTaskId && optionsRef.current.onSubtaskUpdate) {
      optionsRef.current.onSubtaskUpdate(subtaskId, parentTaskId, message.data);
    }
    optionsRef.current.onAnyUpdate?.(message);
  }, []);

  const handleProjectUpdate = useCallback((message: WebSocketMessage) => {
    const projectId = message.metadata?.entity_id;
    if (projectId && optionsRef.current.onProjectUpdate) {
      optionsRef.current.onProjectUpdate(projectId, message.data);
    }
    optionsRef.current.onAnyUpdate?.(message);
  }, []);

  const handleBranchUpdate = useCallback((message: WebSocketMessage) => {
    const branchId = message.metadata?.entity_id;
    if (branchId && optionsRef.current.onBranchUpdate) {
      optionsRef.current.onBranchUpdate(branchId, message.data);
    }
    optionsRef.current.onAnyUpdate?.(message);
  }, []);

  const handleContextUpdate = useCallback((message: WebSocketMessage) => {
    const contextId = message.metadata?.entity_id || message.context_id;
    const level = message.metadata?.context_level || message.level;
    if (contextId && level && optionsRef.current.onContextUpdate) {
      optionsRef.current.onContextUpdate(contextId, level, message.data);
    }
    optionsRef.current.onAnyUpdate?.(message);
  }, []);

  const handleAnyUpdate = useCallback((message: WebSocketMessage) => {
    optionsRef.current.onAnyUpdate?.(message);
  }, []);

  useEffect(() => {
    // Register handlers
    const unsubscribers: Array<() => void> = [];

    if (options.onTaskUpdate) {
      unsubscribers.push(websocketService.on('task', handleTaskUpdate));
    }

    if (options.onSubtaskUpdate) {
      unsubscribers.push(websocketService.on('subtask', handleSubtaskUpdate));
    }

    if (options.onProjectUpdate) {
      unsubscribers.push(websocketService.on('project', handleProjectUpdate));
    }

    if (options.onBranchUpdate) {
      unsubscribers.push(websocketService.on('branch', handleBranchUpdate));
    }

    if (options.onContextUpdate) {
      unsubscribers.push(websocketService.on('context', handleContextUpdate));
    }

    if (options.onAnyUpdate && !options.onTaskUpdate && !options.onSubtaskUpdate &&
        !options.onProjectUpdate && !options.onBranchUpdate && !options.onContextUpdate) {
      // Only register universal handler if no specific handlers are registered
      unsubscribers.push(websocketService.on('*', handleAnyUpdate));
    }

    // Cleanup
    return () => {
      unsubscribers.forEach(unsubscribe => unsubscribe());
    };
  }, [
    handleTaskUpdate,
    handleSubtaskUpdate,
    handleProjectUpdate,
    handleBranchUpdate,
    handleContextUpdate,
    handleAnyUpdate,
    options.onTaskUpdate,
    options.onSubtaskUpdate,
    options.onProjectUpdate,
    options.onBranchUpdate,
    options.onContextUpdate,
    options.onAnyUpdate
  ]);

  // Return connection status and manual control functions
  return {
    isConnected: websocketService.isConnected(),
    subscribeToProject: websocketService.subscribeToProject.bind(websocketService),
    subscribeToBranch: websocketService.subscribeToBranch.bind(websocketService),
    subscribeToTask: websocketService.subscribeToTask.bind(websocketService)
  };
}

/**
 * Hook for auto-refreshing data when updates are received
 */
export function useAutoRefresh(
  entityType: 'task' | 'subtask' | 'project' | 'branch' | 'context',
  entityId: string | null,
  refreshFunction: () => void,
  dependencies: any[] = []
) {
  const refreshFunctionRef = useRef(refreshFunction);
  refreshFunctionRef.current = refreshFunction;

  useEffect(() => {
    if (!entityId) return;

    const handleUpdate = (message: WebSocketMessage) => {
      const messageEntityId = message.metadata?.entity_id || message.context_id;

      // Check if this update is for our entity
      if (messageEntityId === entityId) {
        console.log(`Auto-refreshing ${entityType} ${entityId} due to update`);
        refreshFunctionRef.current();
      }

      // Also refresh if this is a parent entity update that affects us
      if (entityType === 'subtask' && message.metadata?.parent_task_id === entityId) {
        console.log(`Auto-refreshing task ${entityId} due to subtask update`);
        refreshFunctionRef.current();
      }
    };

    const unsubscribe = websocketService.on(entityType, handleUpdate);

    // Subscribe to specific entity updates if applicable
    if (entityType === 'project') {
      websocketService.subscribeToProject(entityId);
    } else if (entityType === 'branch') {
      websocketService.subscribeToBranch(entityId);
    } else if (entityType === 'task') {
      websocketService.subscribeToTask(entityId);
    }

    return unsubscribe;
  }, [entityType, entityId, ...dependencies]);
}