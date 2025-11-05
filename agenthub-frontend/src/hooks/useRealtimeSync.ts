// Custom hook for WebSocket → React Query cache synchronization
import { useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import type { Branch, Project, Subtask, Task } from '../types/api.types';
import type { WSMessage } from '../types/websocketTypes';
import logger from '../utils/logger';

/**
 * Hook to sync WebSocket events with React Query cache
 * Replaces the cascade Redux pattern with direct cache updates
 *
 * @param webSocketClient WebSocket client instance to listen to
 * @param enabled Whether to enable real-time sync
 */
export const useRealtimeSync = (
  webSocketClient: any | null,
  enabled: boolean = true
) => {
  const queryClient = useQueryClient();
  const handlersRef = useRef<Map<string, (message: WSMessage) => void>>(new Map());

  useEffect(() => {
    if (!enabled || !webSocketClient) {
      logger.debug('[useRealtimeSync] Sync disabled or no client');
      return;
    }

    logger.info('[useRealtimeSync] Initializing real-time sync');

    // Handler for task updates
    const handleTaskUpdate = (message: WSMessage) => {
      const { action, data } = message.payload;
      const taskData = data.primary as Task;

      if (!taskData?.id) {
        logger.warn('[useRealtimeSync] Task update missing ID');
        return;
      }

      logger.debug('[useRealtimeSync] Task event:', action, taskData.id);

      switch (action) {
        case 'created':
          // Invalidate tasks list to refetch with new task
          if (taskData.git_branch_id) {
            queryClient.invalidateQueries({ queryKey: ['tasks', taskData.git_branch_id] });
          }
          queryClient.invalidateQueries({ queryKey: ['tasks'] });
          break;

        case 'updated':
          // Update individual task cache
          queryClient.setQueryData(['task', taskData.id, false], taskData);
          queryClient.setQueryData(['task', taskData.id, true], taskData);

          // Update task in the tasks list
          if (taskData.git_branch_id) {
            queryClient.setQueryData<Task[]>(
              ['tasks', taskData.git_branch_id],
              (old) => {
                if (!old) return old;
                return old.map(t => t.id === taskData.id ? taskData : t);
              }
            );
          }

          // Update in generic tasks list
          queryClient.setQueryData<Task[]>(['tasks'], (old) => {
            if (!old) return old;
            return old.map(t => t.id === taskData.id ? taskData : t);
          });
          break;

        case 'deleted':
          // Remove from all caches
          queryClient.removeQueries({ queryKey: ['task', taskData.id] });

          if (taskData.git_branch_id) {
            queryClient.setQueryData<Task[]>(
              ['tasks', taskData.git_branch_id],
              (old) => {
                if (!old) return old;
                return old.filter(t => t.id !== taskData.id);
              }
            );
          }

          queryClient.setQueryData<Task[]>(['tasks'], (old) => {
            if (!old) return old;
            return old.filter(t => t.id !== taskData.id);
          });
          break;

        case 'completed':
          // Mark as completed in cache
          const completedTask = { ...taskData, status: 'done', progress_percentage: 100 };
          queryClient.setQueryData(['task', taskData.id, false], completedTask);
          queryClient.setQueryData(['task', taskData.id, true], completedTask);

          if (taskData.git_branch_id) {
            queryClient.setQueryData<Task[]>(
              ['tasks', taskData.git_branch_id],
              (old) => {
                if (!old) return old;
                return old.map(t => t.id === taskData.id ? completedTask : t);
              }
            );
          }
          break;
      }
    };

    // Handler for subtask updates
    const handleSubtaskUpdate = (message: WSMessage) => {
      const { action, data } = message.payload;
      const subtaskData = data.primary as Subtask;

      if (!subtaskData?.id) {
        logger.warn('[useRealtimeSync] Subtask update missing ID');
        return;
      }

      logger.debug('[useRealtimeSync] Subtask event:', action, subtaskData.id);

      const taskId = subtaskData.task_id || subtaskData.parent_task_id;

      switch (action) {
        case 'created':
          // Invalidate subtasks list and parent task
          if (taskId) {
            queryClient.invalidateQueries({ queryKey: ['subtasks', taskId] });
            queryClient.invalidateQueries({ queryKey: ['task', taskId] });
          }
          break;

        case 'updated':
          // Update subtask in the subtasks list
          if (taskId) {
            queryClient.setQueryData<Subtask[]>(
              ['subtasks', taskId],
              (old) => {
                if (!old) return old;
                return old.map(s => s.id === subtaskData.id ? subtaskData : s);
              }
            );

            // Also invalidate parent task to update counts
            queryClient.invalidateQueries({ queryKey: ['task', taskId] });
          }
          break;

        case 'deleted':
          // Remove from cache
          if (taskId) {
            queryClient.setQueryData<Subtask[]>(
              ['subtasks', taskId],
              (old) => {
                if (!old) return old;
                return old.filter(s => s.id !== subtaskData.id);
              }
            );

            queryClient.invalidateQueries({ queryKey: ['task', taskId] });
          }
          break;

        case 'completed':
          // Mark as completed
          const completedSubtask = { ...subtaskData, status: 'done', progress_percentage: 100 };

          if (taskId) {
            queryClient.setQueryData<Subtask[]>(
              ['subtasks', taskId],
              (old) => {
                if (!old) return old;
                return old.map(s => s.id === subtaskData.id ? completedSubtask : s);
              }
            );

            queryClient.invalidateQueries({ queryKey: ['task', taskId] });
          }
          break;
      }
    };

    // Handler for project updates
    const handleProjectUpdate = (message: WSMessage) => {
      const { action, data } = message.payload;
      const projectData = data.primary as Project;

      if (!projectData?.id) {
        logger.warn('[useRealtimeSync] Project update missing ID');
        return;
      }

      logger.debug('[useRealtimeSync] Project event:', action, projectData.id);

      switch (action) {
        case 'created':
          queryClient.invalidateQueries({ queryKey: ['projects'] });
          break;

        case 'updated':
          queryClient.setQueryData(['projects', projectData.id], projectData);

          queryClient.setQueryData<Project[]>(['projects'], (old) => {
            if (!old) return old;
            return old.map(p => p.id === projectData.id ? projectData : p);
          });
          break;

        case 'deleted':
          queryClient.removeQueries({ queryKey: ['projects', projectData.id] });

          queryClient.setQueryData<Project[]>(['projects'], (old) => {
            if (!old) return old;
            return old.filter(p => p.id !== projectData.id);
          });
          break;
      }
    };

    // Handler for branch updates
    const handleBranchUpdate = (message: WSMessage) => {
      const { action, data } = message.payload;
      const branchData = data.primary as Branch;

      if (!branchData?.id) {
        logger.warn('[useRealtimeSync] Branch update missing ID');
        return;
      }

      logger.debug('[useRealtimeSync] Branch event:', action, branchData.id);

      const projectId = branchData.project_id;

      switch (action) {
        case 'created':
          if (projectId) {
            queryClient.invalidateQueries({ queryKey: ['branches', projectId] });
            queryClient.invalidateQueries({ queryKey: ['projects', projectId] });
          }
          break;

        case 'updated':
          if (projectId) {
            queryClient.setQueryData<Branch[]>(
              ['branches', projectId],
              (old) => {
                if (!old) return old;
                return old.map(b => b.id === branchData.id ? branchData : b);
              }
            );
          }
          break;

        case 'deleted':
          if (projectId) {
            queryClient.setQueryData<Branch[]>(
              ['branches', projectId],
              (old) => {
                if (!old) return old;
                return old.filter(b => b.id !== branchData.id);
              }
            );

            queryClient.invalidateQueries({ queryKey: ['projects', projectId] });
            // Also invalidate tasks for this branch
            queryClient.invalidateQueries({ queryKey: ['tasks', branchData.id] });
          }
          break;
      }
    };

    // Generic message handler
    const handleMessage = (message: WSMessage) => {
      // Only process v2.0 update messages
      if (message.version !== '2.0' || message.type !== 'update') {
        return;
      }

      const { entity } = message.payload;

      // Route to appropriate handler based on entity type
      switch (entity) {
        case 'task':
          handleTaskUpdate(message);
          break;
        case 'subtask':
          handleSubtaskUpdate(message);
          break;
        case 'project':
          handleProjectUpdate(message);
          break;
        case 'branch':
          handleBranchUpdate(message);
          break;
        default:
          logger.debug('[useRealtimeSync] Unknown entity type:', entity);
      }

      // Handle cascade data if present
      if (message.payload.data.cascade) {
        const cascade = message.payload.data.cascade;

        if (cascade.tasks && Array.isArray(cascade.tasks)) {
          cascade.tasks.forEach((task: Task) => {
            if (task.git_branch_id) {
              queryClient.invalidateQueries({ queryKey: ['tasks', task.git_branch_id] });
            }
          });
        }

        if (cascade.subtasks && Array.isArray(cascade.subtasks)) {
          cascade.subtasks.forEach((subtask: Subtask) => {
            const taskId = subtask.task_id || subtask.parent_task_id;
            if (taskId) {
              queryClient.invalidateQueries({ queryKey: ['subtasks', taskId] });
            }
          });
        }

        if (cascade.branches && Array.isArray(cascade.branches)) {
          cascade.branches.forEach((branch: Branch) => {
            if (branch.project_id) {
              queryClient.invalidateQueries({ queryKey: ['branches', branch.project_id] });
            }
          });
        }

        if (cascade.projects && Array.isArray(cascade.projects)) {
          queryClient.invalidateQueries({ queryKey: ['projects'] });
        }
      }
    };

    // Store handler reference
    handlersRef.current.set('message', handleMessage);

    // Subscribe to WebSocket messages
    webSocketClient.on('message', handleMessage);

    logger.info('[useRealtimeSync] Real-time sync initialized');

    // Cleanup
    return () => {
      logger.info('[useRealtimeSync] Cleaning up real-time sync');
      webSocketClient.off('message', handleMessage);
      handlersRef.current.delete('message');
    };
  }, [webSocketClient, enabled, queryClient]);

  return {
    enabled,
    isActive: enabled && !!webSocketClient
  };
};
