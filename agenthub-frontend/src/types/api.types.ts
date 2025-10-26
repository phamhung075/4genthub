/**
 * API Types - Complete type definitions for API responses
 *
 * PHASE 2 OPTIMIZATION NOTES (2025-10-26):
 * Backend completed Phase 2 optimizations that changed response structure at DTO serialization level.
 * These changes implement conditional field inclusion based on response context to reduce token usage.
 *
 * Key Changes:
 * 1. Context Metadata Duplicates Removed:
 *    - context_data.metadata no longer includes: task_id, status, priority, timestamp when embedded in task response
 *    - These fields are only at task level (task.id, task.status, task.priority, meta.timestamp)
 *    - Saves duplication when context is part of task response
 *
 * 2. Subtask parent_task_id Now Conditional:
 *    - When subtasks nested in parent task response → parent_task_id NOT included
 *    - When subtasks returned standalone → parent_task_id IS included
 *    - Type: parent_task_id?: string (optional)
 *
 * 3. Context ID Conditional:
 *    - context_data.id removed when context embedded in task response
 *    - Only included when context returned standalone
 *    - Type: id?: string (optional)
 *
 * Token Savings: ~355 tokens per response from these optimizations
 * Backend Evidence: context.py added `embedded` parameter, subtask.py added `include_parent_id` parameter
 */

// ============================================
// Core Entity Types
// ============================================

/**
 * Context Interface - Represents context data attached to tasks
 *
 * Phase 2 Optimization Notes:
 * - `id` is optional: Only included when context returned standalone, omitted when embedded in task response
 * - `metadata` fields are conditionally serialized: task_id, status, priority, timestamp are omitted when embedded
 *   (these fields are already present at task level, so duplication is removed)
 */
export interface Context {
  id?: string; // Optional: Only included when context returned standalone, omitted when embedded in parent task
  level?: string; // Context level: 'global', 'project', 'branch', 'task'
  context_data?: {
    metadata?: {
      // Conditional fields - only included in standalone context responses:
      // task_id, status, priority, timestamp are omitted when context is embedded
      [key: string]: any;
    };
    progress?: {
      current_session_summary?: string;
      completion_percentage?: number;
      next_steps?: string[];
      completed_actions?: string[];
    };
    [key: string]: any; // Additional context-level specific fields
  };
  created_at?: string;
  updated_at?: string;
}

export interface Task {
  id: string;
  title: string;
  description?: string;
  status: string;
  priority: string;
  assignees?: string[];
  has_dependencies: boolean;
  dependencies?: string[];
  has_context: boolean;
  context_id?: string;
  context_data?: Context; // Phase 2: Context embedded without id and with conditional metadata serialization
  git_branch_id: string;
  project_id: string;
  created_at?: string;
  updated_at?: string;
  due_date?: string;
  estimated_effort?: string;
  labels?: string[];
  details?: string;
  progress_percentage?: number;
  subtasks?: Subtask[] | string[]; // Phase 2: Can be array of subtask objects (without parent_task_id) or subtask IDs
  parent_task_id?: string; // Identifies if this task is actually a subtask
  progress_history?: Record<string, any>; // Progress history entries
}

export interface Subtask {
  id: string;
  task_id: string;
  parent_task_id?: string; // Optional: Only included when subtask returned standalone, omitted when nested in parent task response
  title: string;
  description?: string;
  status: string;
  priority: string;
  assignees?: string[];
  progress_percentage?: number;
  created_at?: string;
  updated_at?: string;
  progress_notes?: string;
  completion_summary?: string;
}

export interface Project {
  id: string;
  name: string;
  description?: string;
  created_at?: string;
  updated_at?: string;
  owner_id?: string;
  status?: string;
  git_branchs?: Record<string, Branch>; // API returns branches as a Record with branch IDs as keys
  branches?: Branch[]; // Legacy array format for backward compatibility
}

export interface Branch {
  id: string;
  project_id: string;
  name: string;
  git_branch_name: string;
  description?: string;
  status?: string;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface Rule {
  id: string;
  name: string;
  description?: string;
  category?: string;
  content?: string;
  enabled?: boolean;
  created_at?: string;
  updated_at?: string;
}

// ============================================
// API Response Types
// ============================================

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
  timestamp?: string;
}

export interface TaskResponse extends ApiResponse {
  task: Task;
}

export interface TasksResponse extends ApiResponse {
  tasks: Task[];
  total?: number;
  page?: number;
  limit?: number;
}

export interface SubtaskResponse extends ApiResponse {
  subtask: Subtask;
}

export interface SubtasksResponse extends ApiResponse {
  subtasks: Subtask[];
  total?: number;
}

export interface ProjectResponse extends ApiResponse {
  project: Project;
}

export interface ProjectsResponse extends ApiResponse {
  projects: Project[];
  total?: number;
}

export interface BranchResponse extends ApiResponse {
  branch: Branch;
}

export interface BranchesResponse extends ApiResponse {
  branches: Branch[];
  total?: number;
}

export interface ContextResponse extends ApiResponse {
  context: any;
  level?: string;
  inherited?: any;
}

export interface DeleteResponse extends ApiResponse {
  deleted?: boolean;
  id?: string;
}

export interface HealthResponse extends ApiResponse {
  status: string;
  version?: string;
  timestamp: string;
}

export interface AgentsResponse extends ApiResponse {
  agents: any[];
  total?: number;
}

/**
 * API Types for Bulk Summary Operations
 *
 * These types correspond to the bulk API endpoint:
 * POST /api/v2/branches/summaries/bulk
 */

export interface BulkSummaryRequest {
  projectIds?: string[];
  userId?: string;
  includeArchived?: boolean;
}

export interface BranchSummary {
  id: string;
  project_id: string;
  name: string;
  git_branch_name?: string; // For compatibility with existing UI
  status?: string;
  priority?: string;
  task_count: number; // Standardized task count field
  completed_tasks: number;
  in_progress_tasks: number;
  blocked_tasks: number;
  todo_tasks: number;
  progress_percentage: number;
  last_activity?: string; // ISO date string
  has_urgent_tasks?: boolean; // Flag for urgent tasks
  is_completed?: boolean; // Flag for completed branches
  task_counts?: { // Additional task count details
    total: number;
    [key: string]: any;
  };
}

export interface ProjectSummary {
  id: string;
  name: string;
  description?: string;
  branchCount: number;
  totalTasks: number;
  completedTasks: number;
}

export interface BulkSummaryMetadata {
  count: number;
  queryTimeMs: number;
  fromCache: boolean;
}

export interface BulkSummaryResponse {
  success: boolean;
  summaries: Record<string, BranchSummary>;
  projects: Record<string, ProjectSummary>;
  metadata: BulkSummaryMetadata;
  timestamp: string;
  message?: string;
}

// Legacy interfaces for backward compatibility (will be removed in future versions)
export interface LegacyBranchResponse {
  branches: BranchSummary[];
  project_summary?: ProjectSummary;
  total_branches?: number;
}

// ============================================
// Request Options Types
// ============================================

export interface TaskRequestOptions {
  includeContext?: boolean;
}

export interface SubtaskRequestOptions {
  includeContext?: boolean;
}

export interface ProjectRequestOptions {
  includeContext?: boolean;
}

export interface BranchRequestOptions {
  includeContext?: boolean;
}
