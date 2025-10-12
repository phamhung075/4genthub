/**
 * API Types - Complete type definitions for API responses
 */

// ============================================
// Core Entity Types
// ============================================

export interface Task {
  id: string;
  title: string;
  description?: string;
  status: string;
  priority: string;
  assignees?: string[];
  assignees_count: number;
  subtask_count: number;
  has_dependencies: boolean;
  dependency_count?: number;
  dependencies?: string[];
  has_context: boolean;
  context_id?: string;
  context_data?: any;
  git_branch_id: string;
  project_id: string;
  created_at?: string;
  updated_at?: string;
  due_date?: string;
  estimated_effort?: string;
  labels?: string[];
  details?: string;
  progress_percentage?: number;
  subtasks?: Subtask[] | string[]; // Can be array of subtask objects or subtask IDs
  parent_task_id?: string; // Identifies if this task is actually a subtask
  progress_history?: Record<string, any>; // Progress history entries
  progress_count?: number; // Total number of progress entries
}

export interface Subtask {
  id: string;
  task_id: string;
  title: string;
  description?: string;
  status: string;
  priority: string;
  assignees?: string[];
  assignees_count: number;
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
  branch_count?: number;
  task_count?: number;
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
  task_count?: number;
  completed_tasks?: number;
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
