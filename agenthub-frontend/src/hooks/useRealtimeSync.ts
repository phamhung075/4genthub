// Custom hook for WebSocket → React Query cache synchronization
import { useEffect, useRef, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import type { Branch, Project, Subtask, Task } from '../types/api.types';
import logger from '../utils/logger';
import { useSuccessToast, useInfoToast, useWarningToast } from '../components/ui/toast';
import {
  type WSMessage,
  isBranchDeletePayload,
  isSubtaskDeletePayload,
  isProjectDeletePayload,
  isTaskDeletePayload,
  getEntityId,
  getDisplayName
} from '../types/websocket-protocol';

// 🔥 GLOBAL toast deduplication tracker (module-level, shared across ALL hook instances)
// This prevents duplicate toasts when multiple components use useRealtimeSync
const globalRecentToastsMap = new Map<string, number>();

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

  // Initialize toast notifications
  const showSuccess = useSuccessToast();
  const showInfo = useInfoToast();
  const showWarning = useWarningToast();

  // Helper to deduplicate toasts GLOBALLY (prevents toasts from multiple hook instances)
  const showToastOnce = useCallback((key: string, showFn: () => void) => {
    const now = Date.now();
    const lastShown = globalRecentToastsMap.get(key);

    // Only show if not shown in last 2 seconds
    if (!lastShown || now - lastShown > 2000) {
      showFn();
      globalRecentToastsMap.set(key, now);

      // Cleanup old entries after 5 seconds
      setTimeout(() => {
        const current = globalRecentToastsMap.get(key);
        if (current === now) {
          globalRecentToastsMap.delete(key);
        }
      }, 5000);
    } else {
      // Log deduplication for debugging
      logger.debug('[useRealtimeSync] Toast deduplicated (shown recently)', {
        key,
        lastShownMs: now - lastShown,
        threshold: 2000
      });
    }
  }, []);

  useEffect(() => {
    if (!enabled || !webSocketClient) {
      return;
    }

    logger.info('[useRealtimeSync] Initializing real-time sync');

    // Handler for task updates
    const handleTaskUpdate = (message: WSMessage) => {
      const { action, data } = message.payload;
      const taskData = data.primary as Task;

      // Use getEntityId helper for safe ID extraction (with fallback to metadata)
      const taskId = getEntityId(message);
      if (!taskId) {
        logger.warn('[useRealtimeSync] Task update missing ID');
        return;
      }

      logger.debug('[useRealtimeSync] Task event:', action, taskId);
      const taskTitle = getDisplayName(message);

      switch (action) {
        case 'created':
          // Direct cache update - add new task to the lists (check for duplicates)
          if (taskData.git_branch_id) {
            queryClient.setQueryData<Task[]>(
              ['tasks', taskData.git_branch_id],
              (old) => {
                if (!old) return [taskData];

                // ✨ FIX: Check if task already exists (from optimistic update)
                const exists = old.some(t => t.id === taskId);
                if (exists) {
                  return old.map(t => t.id === taskId ? taskData : t);
                }

                return [...old, taskData];
              }
            );
          }

          // Also add to generic tasks list (check for duplicates)
          queryClient.setQueryData<Task[]>(['tasks'], (old) => {
            if (!old) return [taskData];

            // ✨ FIX: Check if task already exists
            const exists = old.some(t => t.id === taskId);
            if (exists) {
              return old.map(t => t.id === taskId ? taskData : t);
            }

            return [...old, taskData];
          });

          // 🔥 CRITICAL FIX: Invalidate branchSummaries to update parent branch's task_count in sidebar
          if (taskData.git_branch_id) {
            queryClient.invalidateQueries({ queryKey: ['branchSummaries'] });
          }

          // Show success toast (deduplicated)
          showToastOnce(`task-created-${taskId}`, () => {
            showSuccess(`Task "${taskTitle}" created successfully`);
          });
          break;

        case 'updated':
          // CRITICAL: Delay cache update to allow update animation to play (~150ms)
          // If we update immediately, React re-renders before animation triggers
          setTimeout(() => {

            // Update individual task cache
            queryClient.setQueryData(['task', taskId, false], taskData);
            queryClient.setQueryData(['task', taskId, true], taskData);

            // Update task in the tasks list
            if (taskData.git_branch_id) {
              queryClient.setQueryData<Task[]>(
                ['tasks', taskData.git_branch_id],
                (old) => {
                  if (!old) return old;
                  return old.map(t => t.id === taskId ? taskData : t);
                }
              );
            }

            // Update in generic tasks list
            queryClient.setQueryData<Task[]>(['tasks'], (old) => {
              if (!old) return old;
              return old.map(t => t.id === taskId ? taskData : t);
            });
          }, 150); // Match UPDATE animation duration from WebSocketAnimationService.ts

          // 🔇 SUPPRESS toast for automatic task updates (subtask count changes)
          // Only show toast if this is a real user-initiated task update
          // Automatic updates from subtask operations shouldn't show toasts (prevents duplicates)
          const isAutomaticUpdate = message.metadata?.source === 'system' ||
                                    message.metadata?.event_type === 'subtask_count_update';

          if (!isAutomaticUpdate) {
            // Show info toast (deduplicated) only for real updates
            showToastOnce(`task-updated-${taskId}`, () => {
              showInfo(`Task "${taskTitle}" updated`);
            });
          }
          break;

        case 'deleted':
          // 🔍 DEBUG: Log payload structure for validation

          // Type guard validation: ensure payload has required fields for delete
          if (!isTaskDeletePayload(data.primary)) {
            logger.warn('[useRealtimeSync] Task delete payload validation failed - missing required fields');
            return;
          }


          // Show warning toast FIRST (before cache update)
          showToastOnce(`task-deleted-${taskId}`, () => {
            showWarning(`Task "${taskTitle}" deleted`);
          });

          // CRITICAL: Delay cache update to allow delete animation to play (~600ms)
          setTimeout(() => {

            // Remove from individual task cache
            queryClient.removeQueries({ queryKey: ['task', taskId] });

            // Remove from branch-specific tasks cache
            if (taskData.git_branch_id) {
              queryClient.setQueryData<Task[]>(
                ['tasks', taskData.git_branch_id],
                (old) => {
                  if (!old) {
                    return old;
                  }
                  return old.filter(t => t.id !== taskId);
                }
              );
            }

            // Remove from generic tasks cache
            queryClient.setQueryData<Task[]>(['tasks'], (old) => {
              if (!old) {
                return old;
              }
              return old.filter(t => t.id !== taskId);
            });

            // 🔥 CRITICAL FIX: Invalidate branchSummaries to update parent branch's task_count in sidebar
            if (taskData.git_branch_id) {
              queryClient.invalidateQueries({ queryKey: ['branchSummaries'] });
            }

          }, 600);
          break;

        case 'completed':
          // Show success toast FIRST (immediate user feedback)
          showToastOnce(`task-completed-${taskId}`, () => {
            showSuccess(`Task "${taskTitle}" completed`);
          });

          // CRITICAL: Delay cache update to allow completion animation to play (~150ms)
          // If we update immediately, React re-renders before animation triggers
          setTimeout(() => {
            // ✨ CRITICAL FIX: Completion payload is MINIMAL (id, title, status, completion_summary, testing_notes, completed_at)
            // We must MERGE with existing task data, not replace entirely, to preserve fields like git_branch_id, created_at, etc.

            // ✅ FIX: Get git_branch_id from ALL possible cache locations
            // First try generic tasks list, then try taskData from WebSocket payload
            const genericTasks = queryClient.getQueryData<Task[]>(['tasks']);
            const existingTask = genericTasks?.find(t => t.id === taskId);
            const branchId = existingTask?.git_branch_id || taskData.git_branch_id;

            // 🔥 CRITICAL FIX: If we still don't have branchId, search all ['tasks', *] caches
            let resolvedBranchId = branchId;
            if (!resolvedBranchId) {
              const allTaskCaches = queryClient.getQueriesData<Task[]>({ queryKey: ['tasks'] });
              for (const [queryKey, tasks] of allTaskCaches) {
                if (tasks && Array.isArray(tasks)) {
                  const found = tasks.find(t => t.id === taskId);
                  if (found?.git_branch_id) {
                    resolvedBranchId = found.git_branch_id;
                    logger.debug(`[useRealtimeSync] Found branchId from cache:`, queryKey, resolvedBranchId);
                    break;
                  }
                }
              }
            }

            // Update individual task cache (merge with existing data)
            queryClient.setQueryData(['task', taskId, false], (old: Task | undefined) => {
              if (!old) return existingTask ? { ...existingTask, ...taskData, status: 'done' } : taskData;
              return { ...old, ...taskData, status: 'done' };
            });
            queryClient.setQueryData(['task', taskId, true], (old: Task | undefined) => {
              if (!old) return existingTask ? { ...existingTask, ...taskData, status: 'done' } : taskData;
              return { ...old, ...taskData, status: 'done' };
            });

            // Update task in branch-specific cache (use resolved branchId)
            if (resolvedBranchId) {
              queryClient.setQueryData<Task[]>(
                ['tasks', resolvedBranchId],
                (old) => {
                  if (!old) return old;
                  return old.map(t => t.id === taskId ? { ...t, ...taskData, status: 'done' } : t);
                }
              );
              logger.debug(`[useRealtimeSync] Updated task ${taskId} status to 'done' in branch cache:`, resolvedBranchId);
            } else {
              logger.warn(`[useRealtimeSync] Could not resolve branchId for completed task ${taskId} - branch-specific cache not updated`);
            }

            // ✨ FIX: Also update generic tasks list cache (merge with existing data)
            queryClient.setQueryData<Task[]>(['tasks'], (old) => {
              if (!old) return old;
              return old.map(t => t.id === taskId ? { ...t, ...taskData, status: 'done' } : t);
            });
          }, 150); // Match COMPLETE animation duration from WebSocketAnimationService.ts
          break;
      }
    };

    // Handler for subtask updates
    const handleSubtaskUpdate = (message: WSMessage) => {
      // CRITICAL FIX: Validate message structure before processing
      if (!message?.payload?.data?.primary) {
        logger.error('[useRealtimeSync] Subtask update missing payload.data.primary', { message });
        return;
      }

      const { action, data } = message.payload;
      const subtaskData = data.primary as Subtask;

      // Additional validation: ensure subtaskData is an object
      if (!subtaskData || typeof subtaskData !== 'object' || Array.isArray(subtaskData)) {
        logger.error('[useRealtimeSync] Subtask data is not a valid object', { subtaskData });
        return;
      }

      // Use getEntityId helper for safe ID extraction
      const subtaskId = getEntityId(message);
      if (action !== 'deleted' && !subtaskId) {
        logger.warn('[useRealtimeSync] Subtask update missing ID');
        return;
      }

      logger.debug('[useRealtimeSync] Subtask event:', action, subtaskId || 'unknown');

      const taskId = subtaskData.task_id || subtaskData.parent_task_id;
      const subtaskTitle = getDisplayName(message);

      // Validate taskId for non-delete operations
      if (action !== 'deleted' && !taskId) {
        logger.error('[useRealtimeSync] Subtask missing task_id/parent_task_id', {
          action,
          subtaskId,
          subtaskData
        });
        return;
      }

      switch (action) {
        case 'created':
          // Direct cache update - add new subtask to the list (check for duplicates)
          if (taskId) {
            queryClient.setQueryData<Subtask[]>(
              ['subtasks', taskId],
              (old) => {
                if (!old) return [subtaskData];

                // ✨ FIX: Check if subtask already exists (from optimistic update)
                const exists = old.some(s => s.id === subtaskData.id);
                if (exists) {
                  return old.map(s => s.id === subtaskData.id ? subtaskData : s);
                }

                return [...old, subtaskData];
              }
            );

            // 🔥 REMOVED invalidateQueries - causes queuing and delays
            // Parent task update will arrive separately via WebSocket (see line 382 in backend)
            // This prevents React Query refetch from blocking subsequent operations

            // Parent task counts updated by separate WebSocket message (backend line 382)
            // No need to invalidate here - cache is already updated with fresh data
          }

          // Show success toast (deduplicated)
          showToastOnce(`subtask-created-${subtaskData.id}`, () => {
            showSuccess(`Subtask "${subtaskTitle}" created successfully`);
          });
          break;

        case 'updated':
          // CRITICAL: Delay cache update to allow update animation to play (~150ms)
          // If we update immediately, React re-renders before animation triggers
          setTimeout(() => {

            // Update subtask in the subtasks list
            if (taskId) {
              queryClient.setQueryData<Subtask[]>(
                ['subtasks', taskId],
                (old) => {
                  if (!old) return old;
                  // ✅ FIX: Merge with existing data to preserve fields that might not be in the update payload
                  // This prevents loss of title, description, or other fields if backend sends partial data
                  return old.map(s => s.id === subtaskData.id ? { ...s, ...subtaskData } : s);
                }
              );

              // Also invalidate parent task to update counts
              queryClient.invalidateQueries({ queryKey: ['task', taskId] });
            }
          }, 150); // Match UPDATE animation duration from WebSocketAnimationService.ts

          // Show info toast (deduplicated)
          showToastOnce(`subtask-updated-${subtaskData.id}`, () => {
            showInfo(`Subtask "${subtaskTitle}" updated`);
          });
          break;

        case 'deleted':
          // 🔍 DEBUG: Log payload structure for validation

          // Validate delete payload using type guard
          if (!isSubtaskDeletePayload(subtaskData)) {
            const data = subtaskData as any; // Cast for error checking
            const missingFields = [];
            if (!data?.id) missingFields.push('id');
            if (!data?.task_id && !data?.parent_task_id) missingFields.push('task_id');

            logger.warn('[useRealtimeSync] Invalid subtask delete payload', {
              data: subtaskData,
              reason: `Missing required fields: ${missingFields.join(', ')}`,
            });
            return;
          }


          // Show warning toast FIRST (before cache update)
          showToastOnce(`subtask-deleted-${subtaskData.id}`, () => {
            showWarning(`Subtask "${subtaskTitle}" deleted`);
          });

          // CRITICAL: Delay cache update to allow delete animation to play (~600ms)
          setTimeout(() => {

            // Remove from cache
            if (taskId) {
              queryClient.setQueryData<Subtask[]>(
                ['subtasks', taskId],
                (old) => {
                  if (!old) {
                    return old;
                  }
                  return old.filter(s => s.id !== subtaskData.id);
                }
              );

              queryClient.invalidateQueries({ queryKey: ['task', taskId] });
            } else {
            }
          }, 600);
          break;

        case 'completed':
          // Show success toast FIRST (immediate user feedback)
          showToastOnce(`subtask-completed-${subtaskData.id}`, () => {
            showSuccess(`Subtask "${subtaskTitle}" completed`);
          });

          // CRITICAL: Delay cache update to allow completion animation to play (~150ms)
          // If we update immediately, React re-renders before animation triggers
          setTimeout(() => {
            // ✅ FIX: Merge with existing data to preserve fields even during completion
            if (taskId) {
              queryClient.setQueryData<Subtask[]>(
                ['subtasks', taskId],
                (old) => {
                  if (!old) return old;
                  // Merge with existing data, ensuring status='done' is applied
                  return old.map(s => s.id === subtaskData.id ? { ...s, ...subtaskData, status: 'done' } : s);
                }
              );

              queryClient.invalidateQueries({ queryKey: ['task', taskId] });
            }
          }, 150); // Match COMPLETE animation duration from WebSocketAnimationService.ts
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

          // Direct cache update - add new project to the list (check for duplicates)
          queryClient.setQueryData<Project[]>(['projects'], (old) => {
            if (!old) {
              return [projectData];
            }

            // ✨ FIX: Check if project already exists (from optimistic update)
            const exists = old.some(p => p.id === projectData.id);
            if (exists) {
              return old.map(p => p.id === projectData.id ? projectData : p);
            }

            return [...old, projectData];
          });


          // Show success toast (deduplicated to prevent double toasts from dual broadcasts)
          showToastOnce(`project-created-${projectData.id}`, () => {
            showSuccess(`Project "${projectData.name}" created successfully`);
          });
          break;

        case 'updated':

          // CRITICAL: Delay cache update to allow update animation to play (~150ms)
          // If we update immediately, React re-renders before animation triggers
          setTimeout(() => {

            queryClient.setQueryData(['projects', projectData.id], projectData);

            queryClient.setQueryData<Project[]>(['projects'], (old) => {
              if (!old) return old;
              return old.map(p => p.id === projectData.id ? projectData : p);
            });
          }, 150); // Match UPDATE animation duration from WebSocketAnimationService.ts

          // Show info toast (deduplicated)
          showToastOnce(`project-updated-${projectData.id}`, () => {
            showInfo(`Project "${projectData.name}" updated`);
          });
          break;

        case 'deleted':
          // Validate payload using type guard
          if (!isProjectDeletePayload(projectData)) {
            logger.warn('[useRealtimeSync] Project delete payload validation failed', {
              payload: projectData,
              requiredFields: ['id', 'name']
            });
            return;
          }


          // Show warning toast FIRST (before cache update)
          // Use getDisplayName helper for consistent display name extraction
          try {
            const displayName = getDisplayName(message);
            showToastOnce(`project-deleted-${projectData.id}`, () => {
              showWarning(`Project "${displayName}" deleted`);
            });
          } catch (err) {
          }

          // CRITICAL: Delay cache update to allow delete animation to play (~600ms)
          // If we update immediately, React unmounts the component and animation can't play
          setTimeout(() => {

            // Only update cache, DON'T invalidate/refetch
            queryClient.setQueryData<Project[]>(['projects'], (old) => {
              if (!old) {
                return old;
              }
              const filtered = old.filter(p => p.id !== projectData.id);
              return filtered;
            });

            // Also remove individual project query cache
            queryClient.setQueryData(['projects', projectData.id], undefined);

            // Verify deletion persisted after another 400ms (total 1 second from start)
            setTimeout(() => {
              const currentProjects = queryClient.getQueryData<Project[]>(['projects']);
              const projectExists = currentProjects?.some(p => p.id === projectData.id);
              if (projectExists) {
              } else {
              }
            }, 400);
          }, 600);
          break;

        default:
      }
    };

    // Handler for branch updates
    const handleBranchUpdate = (message: WSMessage) => {
      const { action, data } = message.payload;
      const branchData = data.primary as Branch;

      const branchId = getEntityId(message);
      if (!branchId) {
        logger.warn('[useRealtimeSync] Branch update missing ID');
        return;
      }

      logger.debug('[useRealtimeSync] Branch event:', action, branchId);

      const projectId = branchData.project_id;
      const branchName = getDisplayName(message);

      switch (action) {
        case 'created':
          // Direct cache update - add new branch to the list (check for duplicates)
          if (projectId) {
            // 1. Update ['branches', projectId] cache
            queryClient.setQueryData<Branch[]>(
              ['branches', projectId],
              (old) => {
                if (!old) return [branchData];

                // ✨ FIX: Check if branch already exists (from optimistic update)
                const exists = old.some(b => b.id === branchData.id);
                if (exists) {
                  return old.map(b => b.id === branchData.id ? branchData : b);
                }

                return [...old, branchData];
              }
            );

            // 2. Update ['branchSummaries'] cache
            const branchSummariesQueries = queryClient.getQueriesData<{ branches: any[]; projects: any[] }>({
              queryKey: ['branchSummaries']
            });

            branchSummariesQueries.forEach(([queryKey, data]) => {
              if (data?.branches) {
                // ✨ FIX: Check if branch summary already exists
                const exists = data.branches.some((b: any) => b.id === branchData.id);

                if (exists) {
                  queryClient.setQueryData(queryKey, {
                    ...data,
                    branches: data.branches.map((b: any) =>
                      b.id === branchData.id ? {
                        ...b,
                        name: branchData.name || branchData.git_branch_name || b.name,
                        git_branch_name: branchData.git_branch_name || branchData.name || b.git_branch_name,
                        status: branchData.status || b.status
                      } : b
                    )
                  });
                } else {
                  // Create a branch summary object from the branch data
                  const newSummary = {
                    id: branchData.id,
                    project_id: branchData.project_id,
                    name: branchData.name || branchData.git_branch_name || '',
                    git_branch_name: branchData.git_branch_name || branchData.name || '',
                    status: branchData.status || 'active',
                    task_count: 0,
                    completed_tasks: 0,
                    in_progress_tasks: 0,
                    blocked_tasks: 0,
                    todo_tasks: 0,
                    progress_percentage: 0
                  };

                  queryClient.setQueryData(queryKey, {
                    ...data,
                    branches: [...data.branches, newSummary]
                  });
                }
              }
            });

            // 3. 🔥 CRITICAL FIX: Invalidate branchSummaries to update sidebar counts
            queryClient.invalidateQueries({ queryKey: ['branchSummaries'] });
            // Also invalidate project to update branch count
            queryClient.invalidateQueries({ queryKey: ['projects', projectId] });
          }

          // Show success toast (deduplicated)
          showToastOnce(`branch-created-${branchData.id}`, () => {
            showSuccess(`Branch "${branchName}" created successfully`);
          });
          break;

        case 'updated':
          // CRITICAL: Delay cache update to allow update animation to play (~150ms)
          // If we update immediately, React re-renders before animation triggers
          setTimeout(() => {

            if (projectId) {
              // 1. Update ['branches', projectId] cache
              queryClient.setQueryData<Branch[]>(
                ['branches', projectId],
                (old) => {
                  if (!old) return old;
                  return old.map(b => b.id === branchData.id ? branchData : b);
                }
              );

              // 2. Update ['branchSummaries'] cache
              const branchSummariesQueries = queryClient.getQueriesData<{ branches: any[]; projects: any[] }>({
                queryKey: ['branchSummaries']
              });

              branchSummariesQueries.forEach(([queryKey, data]) => {
                if (data?.branches) {
                  queryClient.setQueryData(queryKey, {
                    ...data,
                    branches: data.branches.map((b: any) => {
                      if (b.id === branchData.id) {
                        // Update summary with new branch data
                        return {
                          ...b,
                          name: branchData.name || branchData.git_branch_name || b.name,
                          git_branch_name: branchData.git_branch_name || branchData.name || b.git_branch_name,
                          status: branchData.status || b.status
                        };
                      }
                      return b;
                    })
                  });
                }
              });
            }
          }, 150); // Match UPDATE animation duration from WebSocketAnimationService.ts

          // Show info toast (deduplicated)
          showToastOnce(`branch-updated-${branchData.id}`, () => {
            showInfo(`Branch "${branchName}" updated`);
          });
          break;

        case 'deleted':
          // 🔍 DEBUG: Log payload structure for TDD verification

          // Validate payload with type guard before processing
          if (!isBranchDeletePayload(branchData)) {
            logger.warn('[useRealtimeSync] Invalid branch delete payload - missing required fields', branchData);
            return;
          }


          // Show warning toast FIRST (before cache update)
          showToastOnce(`branch-deleted-${branchData.id}`, () => {
            showWarning(`Branch "${branchName}" deleted`);
          });

          // CRITICAL: Delay cache update to allow delete animation to play (~600ms)
          setTimeout(() => {

            if (projectId) {
              // 1. Update ['branches', projectId] cache (for detail views)
              queryClient.setQueryData<Branch[]>(
                ['branches', projectId],
                (old) => {
                  if (!old) {
                    return old;
                  }
                  const filtered = old.filter(b => b.id !== branchData.id);
                  return filtered;
                }
              );

              // 2. Update ['branchSummaries'] cache (for ProjectList component)
              // Get all branchSummaries queries (there might be multiple with different projectIds filters)
              const branchSummariesQueries = queryClient.getQueriesData<{ branches: any[]; projects: any[] }>({
                queryKey: ['branchSummaries']
              });


              // Update each branchSummaries query to remove the deleted branch
              branchSummariesQueries.forEach(([queryKey, data]) => {
                if (data?.branches) {
                  queryClient.setQueryData(queryKey, {
                    ...data,
                    branches: data.branches.filter((b: any) => b.id !== branchData.id)
                  });
                }
              });

              // 3. 🔥 CRITICAL FIX: Remove cached data for the deleted branch
              // Don't invalidate (refetch), just remove the cache entries
              queryClient.removeQueries({ queryKey: ['branch', branchData.id] });
              queryClient.removeQueries({ queryKey: ['tasks', branchData.id] });

              // 4. Invalidate aggregate queries to update counts
              queryClient.invalidateQueries({ queryKey: ['branchSummaries'] });
              queryClient.invalidateQueries({ queryKey: ['projects', projectId] });

            } else {
            }
          }, 600);
          break;
      }
    };

    // Handler for agent instance updates
    const handleAgentUpdate = (message: WSMessage) => {
      const { action, data } = message.payload;
      const agentData = data.primary as any;

      if (!agentData || typeof agentData !== 'object' || Array.isArray(agentData) || !agentData.id) {
        logger.warn('[useRealtimeSync] Agent update missing ID or invalid data');
        return;
      }

      const agentId = agentData.id;
      const agentName = agentData.name || agentData.agent_name || message.metadata?.agent_name || `Agent ${agentId.slice(0, 8)}`;

      logger.debug('[useRealtimeSync] Agent event:', action, agentId);

      switch (action) {
        case 'created':
          // Optimistic update: add new agent to cache
          queryClient.setQueryData(['userAgentInstances'], (old: any[] = []) => {
            // Check if agent already exists (from optimistic update)
            const exists = old.some((a: any) => a.id === agentId);
            if (exists) {
              return old.map((a: any) => a.id === agentId ? agentData : a);
            }
            return [...old, agentData];
          });

          // Show success toast (deduplicated)
          showToastOnce(`agent-created-${agentId}`, () => {
            showSuccess(`Agent "${agentName}" created successfully`);
          });
          break;

        case 'updated':
          // Optimistic update: update existing agent in cache
          queryClient.setQueryData(['userAgentInstances'], (old: any[] = []) => {
            if (!old) return old;
            return old.map((a: any) => a.id === agentId ? { ...a, ...agentData } : a);
          });

          // Show info toast (deduplicated)
          showToastOnce(`agent-updated-${agentId}`, () => {
            showInfo(`Agent "${agentName}" updated`);
          });
          break;

        case 'deleted':
          // Show warning toast FIRST
          showToastOnce(`agent-deleted-${agentId}`, () => {
            showWarning(`Agent "${agentName}" deleted`);
          });

          // Optimistic update: remove agent from cache (with delay for animation)
          setTimeout(() => {
            queryClient.setQueryData(['userAgentInstances'], (old: any[] = []) => {
              if (!old) return old;
              return old.filter((a: any) => a.id !== agentId);
            });
          }, 150); // Small delay to allow delete animation
          break;

        default:
          // For unknown actions, just invalidate the cache
          logger.debug(`[useRealtimeSync] Unknown agent action: ${action}, invalidating cache`);
          queryClient.invalidateQueries({ queryKey: ['userAgentInstances'] });
      }

      // Also invalidate agent templates in case template-related changes occurred
      if (action === 'created' || action === 'updated') {
        queryClient.invalidateQueries({ queryKey: ['agentTemplates'] });
      }
    };

    // Generic message handler with comprehensive error handling
    const handleMessage = (message: WSMessage) => {
      try {
        // Only process v2.0 update messages
        if (message.version !== '2.0' || message.type !== 'update') {
          return;
        }

        const { entity } = message.payload;

        // CRITICAL FIX: Wrap each entity handler in try-catch to prevent crashes
        // This ensures one failing handler doesn't break WebSocket connection
        try {
          // Route to appropriate handler based on entity type
          switch (entity as string) {
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
            case 'agent':
            case 'agent_instance':
              handleAgentUpdate(message);
              break;
            default:
              logger.debug('[useRealtimeSync] Unknown entity type:', entity);
          }
        } catch (handlerError) {
          // CRITICAL: Log but don't throw - preserve WebSocket connection
          logger.error(`[useRealtimeSync] Error in ${entity} handler:`, {
            error: handlerError,
            message: message,
            stack: handlerError instanceof Error ? handlerError.stack : undefined
          });
          // Don't re-throw - let WebSocket continue processing other messages
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
      } catch (error) {
        logger.error('[useRealtimeSync] Error handling WebSocket message:', error);
        // Don't break the event listener - log error and continue
      }
    };

    // Store handler reference
    handlersRef.current.set('update', handleMessage);

    // Subscribe to WebSocket update events (WebSocketClient emits 'update', not 'message')
    webSocketClient.on('update', handleMessage);
    logger.info('[useRealtimeSync] Real-time sync initialized - listening to "update" events');

    // Cleanup
    return () => {
      logger.info('[useRealtimeSync] Cleaning up real-time sync');
      webSocketClient.off('update', handleMessage);
      handlersRef.current.delete('update');
    };
  }, [webSocketClient, enabled, queryClient, showSuccess, showInfo, showWarning, showToastOnce]);

  return {
    enabled,
    isActive: enabled && !!webSocketClient
  };
};
