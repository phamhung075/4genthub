// ============================================
// Consolidated Task Types for the entire application
// ============================================

// ============================================
// Core Task Types
// ============================================

export type TaskStatus = 'todo' | 'in_progress' | 'blocked' | 'review' | 'testing' | 'done' | 'cancelled';
export type TaskPriority = 'low' | 'medium' | 'high' | 'urgent' | 'critical';

export interface TaskSummary {
  id: string;
  title: string;
  status: string;
  priority: string;
  subtask_count: number;
  assignees_count: number;
  assignees?: string[];
  has_dependencies: boolean;
  dependency_count?: number;
  has_context: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface SubtaskSummary {
  id: string;
  title: string;
  status: string;
  priority: string;
  assignees_count: number;
  assignees?: string[];
  progress_percentage?: number;
  created_at?: string;
  updated_at?: string;
}

export interface TaskListBranchSummary {
  task_count?: number;
  task_counts?: {
    total?: number;
    completed?: number;
    in_progress?: number;
    pending?: number;
    [key: string]: number | undefined;
  };
  [key: string]: any;
}

// ============================================
// LazyTaskList Types
// ============================================

// =============================================================================
// Constants
// =============================================================================

export const TASKS_PER_PAGE = 20;

// =============================================================================
// Component Props
// =============================================================================

export interface LazyTaskListProps {
  projectId: string;
  taskTreeId: string;
  onTasksChanged?: () => void;
}

export type DialogType = 'details' | 'edit' | 'delete' | 'complete' | 'context' | 'assign' | 'agent-info' | 'subtask-details' | 'subtask-edit' | 'subtask-complete';

export interface ActiveDialog {
  type: DialogType | null;
  taskId?: string;
  data?: any;
}

export interface DialogManagerState {
  activeDialog: ActiveDialog;
  saving: boolean;
  isClosingRef: React.MutableRefObject<boolean>; // Ref to prevent race condition on close
}

// ============================================
// TaskRow Types
// ============================================

export interface TaskRowProps {
  summary: TaskSummary;
  isExpanded: boolean;
  isLoading: boolean;
  fullTask: any; // Task from API
  isHighlighted: boolean;
  isHovered: boolean;
  projectId: string;
  taskTreeId: string;
  isMobile: boolean;
  onToggleExpansion: () => void;
  onOpenDialog: (type: string, taskId?: string, extraData?: any) => void;
  onHover: (taskId: string | null) => void;
}

export interface TaskRowMobileProps {
  summary: TaskSummary;
  fullTask: any; // Task from API
  isHighlighted: boolean;
  isHovered: boolean;
  isExpanded: boolean;
  isLoading: boolean;
  projectId: string;
  taskTreeId: string;
  onToggleExpansion: () => void;
  onOpenDialog: (type: string, taskId?: string, extraData?: any) => void;
  onHover: (taskId: string | null) => void;
  elementRef: React.RefObject<HTMLDivElement>;
}

export interface TaskRowDesktopProps {
  summary: TaskSummary;
  fullTask: any; // Task from API
  isHighlighted: boolean;
  isHovered: boolean;
  isExpanded: boolean;
  isLoading: boolean;
  projectId: string;
  taskTreeId: string;
  onToggleExpansion: () => void;
  onOpenDialog: (type: string, taskId?: string, extraData?: any) => void;
  onHover: (taskId: string | null) => void;
  elementRef: React.RefObject<HTMLTableRowElement>;
}

export interface TaskRowActionsProps {
  taskId: string;
  projectId: string;
  taskTreeId: string;
  onOpenDialog: (type: string, taskId?: string, extraData?: any) => void;
  variant?: 'mobile' | 'desktop';
}