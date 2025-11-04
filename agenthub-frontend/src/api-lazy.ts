// Lazy loading API - Direct V2 API usage (no backward compatibility)
// Provides lightweight endpoints for improved performance

import Cookies from 'js-cookie';
import { Project, Subtask, Task } from './api';
import { API_BASE_URL } from './config/environment';
import {
  projectApiV2,
  subtaskApiV2,
  taskApiV2
} from './services/apiV2';
import logger from './utils/logger';
import { TaskSummary, SubtaskSummary } from './types/taskTypes';
import { BranchSummary } from './types/api.types';

export type { TaskSummary, SubtaskSummary } from './types/taskTypes';
export type { BranchSummary } from './types/api.types';

// --- Import Lazy Loading Interfaces ---
import type { TaskSummariesResponse } from './types/serviceTypes';

// --- Task Lazy Loading ---
export const getFullTask = async (task_id: string): Promise<any> => {
  const response = await taskApiV2.getTask(task_id);
  return (response as any).task || response;
};

// --- Subtask Lazy Loading ---
export const getSubtaskSummaries = async (task_id: string, _params?: {
  page?: number;
  limit?: number;
}): Promise<{ subtasks: SubtaskSummary[]; total: number }> => {
  // params reserved for future pagination implementation
  logger.debug('🔍 [getSubtaskSummaries] ENTRY - task_id:', task_id);

  const response = await subtaskApiV2.listSubtasksForTask(task_id);
  logger.debug('🔍 [getSubtaskSummaries] RAW API RESPONSE:', {
    responseType: typeof response,
    responseKeys: Object.keys(response || {}),
    response: response
  });

  const subtasks = (response as any).subtasks || [];
  logger.debug('🔍 [getSubtaskSummaries] EXTRACTED SUBTASKS ARRAY:', {
    count: subtasks.length,
    subtaskIds: subtasks.map((s: any) => s.id),
    subtasks: subtasks
  });

  const summaries: SubtaskSummary[] = subtasks.map((subtask: Subtask) => ({
    id: subtask.id,
    title: subtask.title,
    status: subtask.status,
    priority: subtask.priority,
    assignees_count: subtask.assignees?.length || 0,
    assignees: subtask.assignees, // Include full assignee information
    progress_percentage: subtask.progress_percentage,
    created_at: subtask.created_at,
    updated_at: subtask.updated_at
  }));

  logger.debug('🔍 [getSubtaskSummaries] MAPPED SUMMARIES:', {
    count: summaries.length,
    summaryIds: summaries.map(s => s.id),
    summaries: summaries
  });

  logger.debug('🔍 [getSubtaskSummaries] EXIT - returning:', {
    subtaskCount: summaries.length,
    total: summaries.length
  });

  return {
    subtasks: summaries,
    total: summaries.length
  };
};

// --- Branch Lazy Loading ---
export const getBranchSummaries = async (project_id: string): Promise<{
  branches: BranchSummary[];
  total: number;
}> => {
  // Use the optimized endpoint for branch summaries with task counts
  const token = Cookies.get('access_token');
  if (!token) {
    return { branches: [], total: 0 };
  }

  const response = await fetch(`${API_BASE_URL}/api/v2/branches/project/${project_id}/summaries`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    }
  });

  if (!(response as any).ok) {
    logger.error(`Failed to fetch branch summaries: ${(response as any).status}`);
    return { branches: [], total: 0 };
  }

  const data = await (response as any).json();
  const branches = data.branches || [];
  
  // Map the optimized response to BranchSummary format
  const summaries: BranchSummary[] = branches.map((branch: any) => ({
    id: branch.id,
    project_id,
    name: branch.name || branch.git_branch_name || 'Unnamed branch',
    git_branch_name: branch.git_branch_name || branch.name,
    status: branch.status,
    priority: branch.priority,
    task_count: branch.task_count || 0,
    completed_tasks: branch.completed_tasks || 0,
    in_progress_tasks: branch.in_progress_tasks || 0,
    blocked_tasks: branch.blocked_tasks || 0,
    todo_tasks: branch.todo_tasks || 0,
    progress_percentage: branch.progress_percentage ?? 0,
    last_activity: branch.last_activity,
    has_urgent_tasks: branch.has_urgent_tasks,
    is_completed: branch.is_completed,
    is_active: (branch.in_progress_tasks || 0) > 0,
    active_task_count: branch.in_progress_tasks || 0,
    created_at: branch.created_at,
    updated_at: branch.updated_at,
    task_counts: {
      total: branch.task_count || 0,
      todo: branch.todo_tasks || 0,
      in_progress: branch.in_progress_tasks || 0,
      done: branch.completed_tasks || 0,
      blocked: branch.blocked_tasks || 0
    }
  }));
  
  return {
    branches: summaries,
    total: summaries.length
  };
};

// --- Project Lazy Loading ---
// Note: getProjectSummaries removed - use projectApiV2.getProjects() directly
