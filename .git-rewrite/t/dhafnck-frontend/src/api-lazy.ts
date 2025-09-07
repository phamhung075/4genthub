// Enhanced API service with lazy loading support
// Provides lightweight endpoints for improved performance

import Cookies from 'js-cookie';

const API_BASE = "http://localhost:8000/api";

// Helper function to get auth headers
function getAuthHeaders(): HeadersInit {
  const token = Cookies.get('access_token');
  const headers: HeadersInit = {
    'Content-Type': 'application/json'
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  return headers;
}

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
  progress_percentage?: number;
}

export interface SubtaskSummariesResponse {
  subtasks: SubtaskSummary[];
  parent_task_id: string;
  total_count: number;
  progress_summary: {
    total: number;
    completed: number;
    in_progress: number;
    todo: number;
    blocked: number;
    completion_percentage: number;
  };
}

export interface AgentSummary {
  id: string;
  name: string;
  type: string;
}

export interface AgentSummariesResponse {
  available_agents: AgentSummary[];
  project_agents: AgentSummary[];
  total_available: number;
  total_assigned: number;
}

export interface BranchSummary {
  id: string;
  name: string;
  description?: string;
  status?: string;
  priority?: string;
  created_at?: string;
  updated_at?: string;
  assigned_agent_id?: string;
  task_counts: {
    total: number;
    by_status: {
      todo: number;
      in_progress: number;
      done: number;
      blocked: number;
    };
    by_priority: {
      urgent: number;
      high: number;
    };
    completion_percentage: number;
  };
  has_tasks: boolean;
  has_urgent_tasks: boolean;
  is_active: boolean;
  is_completed: boolean;
}

export interface BranchSummariesResponse {
  branches: BranchSummary[];
  project_summary: {
    branches: {
      total: number;
      active: number;
      inactive: number;
    };
    tasks: {
      total: number;
      todo: number;
      in_progress: number;
      done: number;
      urgent: number;
    };
    completion_percentage: number;
  };
  total_branches: number;
  cache_status: string;
}

// --- Lazy Loading API Functions ---

/**
 * Get lightweight branch summaries with task counts for sidebar
 * Uses single optimized query to avoid N+1 problem
 */
export async function getBranchSummaries(project_id: string): Promise<BranchSummariesResponse> {
  try {
    const response = await fetch(`${API_BASE}/branches/summaries`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ project_id })
    });

    if (response.ok) {
      return await response.json();
    }
    
    // Fallback to empty response if endpoint not available
    return {
      branches: [],
      project_summary: {
        branches: { total: 0, active: 0, inactive: 0 },
        tasks: { total: 0, todo: 0, in_progress: 0, done: 0, urgent: 0 },
        completion_percentage: 0
      },
      total_branches: 0,
      cache_status: 'uncached'
    };
  } catch (error) {
    console.warn('Branch summaries endpoint not available:', error);
    return {
      branches: [],
      project_summary: {
        branches: { total: 0, active: 0, inactive: 0 },
        tasks: { total: 0, todo: 0, in_progress: 0, done: 0, urgent: 0 },
        completion_percentage: 0
      },
      total_branches: 0,
      cache_status: 'error'
    };
  }
}

/**
 * Get lightweight task summaries for list views
 */
export async function getTaskSummaries(params: {
  git_branch_id: string;
  page?: number;
  limit?: number;
  include_counts?: boolean;
  status_filter?: string;
  priority_filter?: string;
}): Promise<TaskSummariesResponse> {
  
  // Try the lightweight endpoint first
  try {
    const response = await fetch(`${API_BASE}/tasks/summaries`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        git_branch_id: params.git_branch_id,
        page: params.page || 1,
        limit: params.limit || 20,
        include_counts: params.include_counts !== false,
        status_filter: params.status_filter,
        priority_filter: params.priority_filter
      })
    });

    if (response.ok) {
      return await response.json();
    }
  } catch (error) {
    console.warn('Lightweight task summaries endpoint not available, falling back to MCP');
  }

  // Fallback to existing MCP endpoint
  return await getTaskSummariesFromMcp(params);
}

/**
 * Fallback function using existing MCP endpoint
 */
async function getTaskSummariesFromMcp(params: {
  git_branch_id: string;
  page?: number;
  limit?: number;
}): Promise<TaskSummariesResponse> {
  
  const { listTasks } = await import('./api');
  const tasks = await listTasks({ git_branch_id: params.git_branch_id });
  
  // Convert full tasks to summaries
  const page = params.page || 1;
  const limit = params.limit || 20;
  const startIndex = (page - 1) * limit;
  const endIndex = startIndex + limit;
  
  const taskSummaries: TaskSummary[] = tasks.slice(startIndex, endIndex).map(task => ({
    id: task.id,
    title: task.title,
    status: task.status,
    priority: task.priority,
    subtask_count: task.subtasks?.length || 0,
    assignees_count: task.assignees?.length || 0,
    has_dependencies: Boolean(task.dependencies?.length),
    has_context: Boolean(task.context_id || task.context_data),
    created_at: task.created_at,
    updated_at: task.updated_at
  }));
  
  return {
    tasks: taskSummaries,
    total: tasks.length,
    page,
    limit,
    has_more: endIndex < tasks.length
  };
}

/**
 * Get full task data on demand
 */
export async function getFullTask(taskId: string) {
  
  // Try the lightweight endpoint first
  try {
    const response = await fetch(`${API_BASE}/tasks/${taskId}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });

    if (response.ok) {
      return await response.json();
    }
  } catch (error) {
    console.warn('Lightweight task endpoint not available, falling back to MCP');
  }

  // Fallback to existing MCP endpoint
  const { listTasks } = await import('./api');
  const tasks = await listTasks({});
  return tasks.find(task => task.id === taskId) || null;
}

/**
 * Get lightweight subtask summaries
 */
export async function getSubtaskSummaries(parentTaskId: string): Promise<SubtaskSummariesResponse> {
  
  // Try the v2 endpoint with proper authentication
  try {
    const response = await fetch(`${API_BASE}/v2/tasks/${parentTaskId}/subtasks/summaries`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        include_counts: true
      })
    });

    if (response.ok) {
      return await response.json();
    }
  } catch (error) {
    console.warn('Lightweight subtask summaries endpoint not available, falling back to MCP');
  }

  // Fallback to existing MCP endpoint
  return await getSubtaskSummariesFromMcp(parentTaskId);
}

/**
 * Fallback function using existing MCP endpoint
 */
async function getSubtaskSummariesFromMcp(parentTaskId: string): Promise<SubtaskSummariesResponse> {
  
  const { listSubtasks } = await import('./api');
  const subtasks = await listSubtasks(parentTaskId);
  
  // Convert to summaries
  const subtaskSummaries: SubtaskSummary[] = subtasks.map(subtask => ({
    id: subtask.id,
    title: subtask.title,
    status: subtask.status,
    priority: subtask.priority,
    assignees_count: subtask.assignees?.length || 0,
    progress_percentage: subtask.progress_percentage
  }));

  // Calculate progress summary
  const statusCounts = { todo: 0, in_progress: 0, done: 0, blocked: 0 };
  subtasks.forEach(subtask => {
    if (subtask.status in statusCounts) {
      statusCounts[subtask.status as keyof typeof statusCounts]++;
    }
  });

  const total = subtasks.length;
  const progress_summary = {
    total,
    completed: statusCounts.done,
    in_progress: statusCounts.in_progress,
    todo: statusCounts.todo,
    blocked: statusCounts.blocked,
    completion_percentage: total > 0 ? Math.round((statusCounts.done / total) * 100) : 0
  };

  return {
    subtasks: subtaskSummaries,
    parent_task_id: parentTaskId,
    total_count: total,
    progress_summary
  };
}

/**
 * Check if a task has context (lightweight)
 */
export async function getTaskContextSummary(taskId: string): Promise<{
  has_context: boolean;
  context_size?: number;
  last_updated?: string;
}> {
  
  try {
    const response = await fetch(`${API_BASE}/tasks/${taskId}/context/summary`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });

    if (response.ok) {
      return await response.json();
    }
  } catch (error) {
    console.warn('Context summary endpoint not available');
  }

  // Fallback: try to load context to check if it exists
  try {
    const { getTaskContext } = await import('./api');
    const context = await getTaskContext(taskId);
    return {
      has_context: Boolean(context),
      context_size: context ? JSON.stringify(context).length : 0
    };
  } catch {
    return { has_context: false };
  }
}

/**
 * Get lightweight agent summaries
 */
export async function getAgentSummaries(projectId: string): Promise<AgentSummariesResponse> {
  
  try {
    const response = await fetch(`${API_BASE}/agents/summary?project_id=${projectId}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });

    if (response.ok) {
      return await response.json();
    }
  } catch (error) {
    console.warn('Agent summary endpoint not available, falling back to full load');
  }

  // Fallback to existing endpoints
  try {
    const { listAgents, getAvailableAgents } = await import('./api');
    const [projectAgents, availableAgents] = await Promise.all([
      listAgents(projectId),
      getAvailableAgents()
    ]);

    const availableAgentSummaries: AgentSummary[] = availableAgents.map(agentId => ({
      id: agentId,
      name: agentId.replace('@', '').replace('_', ' '),
      type: 'unknown'
    }));

    return {
      available_agents: availableAgentSummaries,
      project_agents: projectAgents,
      total_available: availableAgents.length,
      total_assigned: projectAgents.length
    };
  } catch (error) {
    console.error('Failed to load agent summaries:', error);
    return {
      available_agents: [],
      project_agents: [],
      total_available: 0,
      total_assigned: 0
    };
  }
}

/**
 * Performance monitoring
 */
export async function getPerformanceMetrics() {
  try {
    const response = await fetch(`${API_BASE}/performance/metrics`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });

    if (response.ok) {
      return await response.json();
    }
  } catch (error) {
    console.warn('Performance metrics endpoint not available');
  }

  return {
    endpoints: {},
    recommendations: [
      'Implement lazy loading endpoints for better performance',
      'Add caching for frequently accessed data',
      'Consider pagination for large data sets'
    ]
  };
}

// --- Enhanced Caching System ---

interface CacheEntry<T> {
  data: T;
  timestamp: number;
  expiresAt: number;
}

class LazyCache {
  private cache = new Map<string, CacheEntry<any>>();
  private defaultTtl = 5 * 60 * 1000; // 5 minutes

  set<T>(key: string, data: T, ttl?: number): void {
    const now = Date.now();
    const expiresAt = now + (ttl || this.defaultTtl);
    
    this.cache.set(key, {
      data,
      timestamp: now,
      expiresAt
    });
  }

  get<T>(key: string): T | null {
    const entry = this.cache.get(key);
    
    if (!entry) {
      return null;
    }

    if (Date.now() > entry.expiresAt) {
      this.cache.delete(key);
      return null;
    }

    return entry.data as T;
  }

  invalidate(pattern: string): void {
    const keys = Array.from(this.cache.keys());
    keys.forEach(key => {
      if (key.includes(pattern)) {
        this.cache.delete(key);
      }
    });
  }

  clear(): void {
    this.cache.clear();
  }

  size(): number {
    return this.cache.size;
  }
}

// Global cache instance
export const lazyCache = new LazyCache();

// --- Cached API Functions ---

export async function getCachedTaskSummaries(params: {
  git_branch_id: string;
  page?: number;
  limit?: number;
}): Promise<TaskSummariesResponse> {
  
  const cacheKey = `task-summaries-${params.git_branch_id}-${params.page || 1}-${params.limit || 20}`;
  
  // Check cache first
  const cached = lazyCache.get<TaskSummariesResponse>(cacheKey);
  if (cached) {
    return cached;
  }

  // Load fresh data
  const data = await getTaskSummaries(params);
  
  // Cache for 2 minutes (tasks change frequently)
  lazyCache.set(cacheKey, data, 2 * 60 * 1000);
  
  return data;
}

export async function getCachedSubtaskSummaries(parentTaskId: string): Promise<SubtaskSummariesResponse> {
  
  const cacheKey = `subtask-summaries-${parentTaskId}`;
  
  // Check cache first
  const cached = lazyCache.get<SubtaskSummariesResponse>(cacheKey);
  if (cached) {
    return cached;
  }

  // Load fresh data
  const data = await getSubtaskSummaries(parentTaskId);
  
  // Cache for 3 minutes (subtasks change less frequently)
  lazyCache.set(cacheKey, data, 3 * 60 * 1000);
  
  return data;
}

export async function getCachedAgentSummaries(projectId: string): Promise<AgentSummariesResponse> {
  
  const cacheKey = `agent-summaries-${projectId}`;
  
  // Check cache first
  const cached = lazyCache.get<AgentSummariesResponse>(cacheKey);
  if (cached) {
    return cached;
  }

  // Load fresh data
  const data = await getAgentSummaries(projectId);
  
  // Cache for 10 minutes (agents change rarely)
  lazyCache.set(cacheKey, data, 10 * 60 * 1000);
  
  return data;
}

// --- Cache Management ---

export function invalidateTaskCache(git_branch_id?: string): void {
  if (git_branch_id) {
    lazyCache.invalidate(`task-summaries-${git_branch_id}`);
    lazyCache.invalidate(`subtask-summaries`); // Invalidate all subtasks
  } else {
    lazyCache.invalidate('task-summaries');
    lazyCache.invalidate('subtask-summaries');
  }
}

export function invalidateAgentCache(projectId?: string): void {
  if (projectId) {
    lazyCache.invalidate(`agent-summaries-${projectId}`);
  } else {
    lazyCache.invalidate('agent-summaries');
  }
}

export function clearAllCache(): void {
  lazyCache.clear();
}