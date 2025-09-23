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
  total_tasks: number; // Primary task count field
  task_count?: number; // Deprecated - for backwards compatibility only
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