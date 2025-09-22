// Lazy loading API - Direct V2 API usage (no backward compatibility)
// Provides lightweight endpoints for improved performance

import {
  taskApiV2,
  projectApiV2,
  subtaskApiV2,
  branchApiV2
} from './services/apiV2';
import Cookies from 'js-cookie';
import { API_BASE_URL } from './config/environment';
import logger from './utils/logger';

// --- Lazy Loading Interfaces ---
export interface TaskSummary {
  id: string;
  title: string;
  status: string;
  priority: string;
  subtask_count: number;
  assignees_count: number;
  has_dependencies: boolean;
  has_context: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface TaskSummariesResponse {
  tasks: TaskSummary[];
  total: number;
  page: number;
  limit: number;
  has_more: boolean;
}

export interface SubtaskSummary {
  id: string;
  title: string;
  status: string;
  priority: string;
  assignees_count: number;
  created_at?: string;
  updated_at?: string;
}

export interface BranchSummary {
  id: string;
  git_branch_name: string;
  project_id: string;
  task_count: number;
  active_task_count: number;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
  task_counts?: {
    total: number;
    todo: number;
    in_progress: number;
    done: number;
    blocked: number;
  };
}

// --- Task Lazy Loading ---
export const getTaskSummaries = async (params?: {
  page?: number;
  limit?: number;
  git_branch_id?: string;
}): Promise<TaskSummariesResponse> => {
  // For now, get full tasks and convert to summaries
  // Backend could optimize this with a dedicated endpoint
  const response = await taskApiV2.getTasks({ git_branch_id: params?.git_branch_id });
  const tasks = response.tasks || [];
  
  const summaries: TaskSummary[] = tasks.map(task => ({
    id: task.id,
    title: task.title,
    status: task.status,
    priority: task.priority,
    subtask_count: task.subtasks?.length || 0,
    assignees_count: task.assignees?.length || 0,
    has_dependencies: !!(task.dependencies?.length),
    has_context: !!task.context_id,
    created_at: task.created_at,
    updated_at: task.updated_at
  }));
  
  return {
    tasks: summaries,
    total: summaries.length,
    page: params?.page || 1,
    limit: params?.limit || 50,
    has_more: false
  };
};

export const getFullTask = async (task_id: string): Promise<any> => {
  const response = await taskApiV2.getTask(task_id);
  return response.task || response;
};

// --- Subtask Lazy Loading ---
export const getSubtaskSummaries = async (task_id: string, params?: {
  page?: number;
  limit?: number;
}): Promise<{ subtasks: SubtaskSummary[]; total: number }> => {

  const response = await subtaskApiV2.listSubtasksForTask(task_id);
  const subtasks = response.subtasks || [];
  
  const summaries: SubtaskSummary[] = subtasks.map(subtask => ({
    id: subtask.id,
    title: subtask.title,
    status: subtask.status,
    priority: subtask.priority,
    assignees_count: subtask.assignees?.length || 0,
    created_at: subtask.created_at,
    updated_at: subtask.updated_at
  }));
  
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

  if (!response.ok) {
    logger.error(`Failed to fetch branch summaries: ${response.status}`);
    return { branches: [], total: 0 };
  }

  const data = await response.json();
  const branches = data.branches || [];
  
  // Map the optimized response to BranchSummary format
  const summaries: BranchSummary[] = branches.map((branch: any) => ({
    id: branch.id,
    git_branch_name: branch.name || branch.git_branch_name,
    project_id: project_id,
    task_count: branch.task_counts?.total || branch.total_tasks || branch.task_count || 0,
    active_task_count: branch.task_counts?.in_progress || branch.in_progress_tasks || branch.active_task_count || 0,
    is_active: (branch.task_counts?.in_progress || branch.in_progress_tasks || 0) > 0,
    created_at: branch.created_at,
    updated_at: branch.updated_at,
    // Include the full task_counts object for detailed info
    task_counts: branch.task_counts || {
      total: branch.total_tasks || branch.task_count || 0,
      todo: branch.todo_tasks || 0,
      in_progress: branch.in_progress_tasks || branch.active_task_count || 0,
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
export const getProjectSummaries = async (params?: {
  page?: number;
  limit?: number;
}): Promise<any> => {
  const response = await projectApiV2.getProjects();
  const projects = response.projects || [];
  
  return {
    projects: projects.map(p => ({
      id: p.id,
      name: p.name,
      description: p.description,
      branch_count: p.branches?.length || 0,
      created_at: p.created_at,
      updated_at: p.updated_at
    })),
    total: projects.length,
    page: params?.page || 1,
    limit: params?.limit || 50,
    has_more: false
  };
};