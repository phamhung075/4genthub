// ============================================
// Consolidated Task Types for the entire application
// ============================================

import type { ProgressHistoryEntry } from './utilityTypes';

// ============================================
// Core Task Types
// ============================================

export type TaskStatus = 'todo' | 'in_progress' | 'blocked' | 'review' | 'testing' | 'done' | 'cancelled';
export type TaskPriority = 'low' | 'medium' | 'high' | 'urgent' | 'critical';

// ============================================
// Execution ledger - the task_events stream
// ============================================

/**
 * The kinds the ledger's CHECK constraint enforces: `ck_task_event_kind` in
 * `agenthub_go/fastmcp/task_management/infrastructure/database/task_event_tables.go:40` (the table's
 * single DDL string), whose list `TaskEventKindValues` mirrors in
 * `agenthub_go/fastmcp/task_management/domain/entities/task_event.go:56-68`.
 *
 * READ THIS BEFORE TREATING A KIND AS LIVE: the twelve ARE the closed vocabulary, but `status_changed`
 * is the only kind any writer emits today (`RecordStatusChange`,
 * `application/services/task_event_recorder.go:74`), and it is the only kind whose payload shape is
 * defined - `{ old, new }`. The other eleven carry no payload shape yet, so a payload for them must be
 * treated as unknown rather than assumed - the timeline says so on screen (`LEDGER_NOT_RECORDED`)
 * instead of inventing a reason for the row.
 *
 * THE TYPE IS DERIVED FROM THE ARRAY BELOW so this file holds ONE source for the vocabulary: adding a
 * member here makes every `Record<TaskEventKind, string>` label map fail to compile until it covers the
 * new kind, which is the coverage invariant `src/tests/lib/taskTimeline.test.ts` also asserts at run
 * time.
 */
export const TASK_EVENT_KINDS = [
  'assigned',
  'claimed',
  'delivered',
  'context_loaded',
  'progress',
  'status_changed',
  'evidence_submitted',
  'gate_verdict',
  'escalated',
  'human_decision',
  'handover',
  'context_updated',
] as const;

export type TaskEventKind = (typeof TASK_EVENT_KINDS)[number];

/**
 * Who acted: the ledger's other CHECK constraint, `ck_task_event_actor_kind`, in the same DDL string
 * (`task_event_tables.go:40`) and the same constants (`domain/entities/task_event.go:82-86`). There is
 * deliberately NO `system` - every entry is attributed to whoever acted, and an unattributable write is
 * refused rather than stamped - so a class nothing acted as cannot appear here either.
 */
export const TASK_EVENT_ACTOR_KINDS = ['seat', 'client', 'gate', 'human'] as const;

export type TaskEventActorKind = (typeof TASK_EVENT_ACTOR_KINDS)[number];

/** One row of the execution ledger, as `GET /api/v2/tasks/{id}/events` serializes it. */
export interface TaskEvent {
  id: string;
  task_id: string;
  /** Gapless per task, ascending; the reader's `after_seq` is EXCLUSIVE against it. */
  seq: number;
  kind: TaskEventKind;
  actor_kind: TaskEventActorKind;
  actor_id: string;
  payload: Record<string, unknown> | null;
  created_at: string;
}

/** The body of `GET /api/v2/tasks/{id}/events` - a bare 200, no `data` wrapper. */
export interface TaskEventsResponse {
  success: boolean;
  events: TaskEvent[];
  count: number;
  /** Echoes the `after_seq` the request carried, so a caller knows the cursor it read past. */
  after_seq: number;
}

/**
 * TaskSummary - Lightweight task data for list views
 *
 * This is the optimized version of Task used in LazyTaskList for performance.
 * Loads only essential fields without full task details.
 *
 * @property id - Unique task identifier (UUID)
 * @property title - Task title (max 200 chars)
 * @property status - Current task status ('todo' | 'in_progress' | 'done' | etc.)
 * @property priority - Task priority level ('low' | 'medium' | 'high' | 'urgent' | 'critical')
 * @property assignees - Optional array of assigned agent IDs
 * @property has_dependencies - Whether task has blocking dependencies
 * @property has_context - Whether task has additional context data
 * @property created_at - ISO 8601 timestamp
 * @property updated_at - ISO 8601 timestamp
 *
 * @example
 * const taskSummary: TaskSummary = {
 *   id: '123e4567-e89b-12d3-a456-426614174000',
 *   title: 'Implement user authentication',
 *   status: 'in_progress',
 *   priority: 'high',
 *   assignees: ['agent-1', 'agent-2'],
 *   has_dependencies: false,
 *   has_context: true
 * };
 */
export interface TaskSummary {
  id: string;
  title: string;
  status: string;
  priority: string;
  assignees?: string[];
  has_dependencies: boolean;
  has_context: boolean;
  created_at?: string;
  updated_at?: string;
  subtask_count?: number; // Total number of subtasks
  completed_subtasks?: number; // Number of completed subtasks
  dependency_count?: number; // Total number of dependencies
  dependencies?: string[]; // Array of dependency task IDs
  subtasks?: any[]; // Array of subtask objects or IDs
}

/**
 * SubtaskSummary - Lightweight subtask data for list views
 *
 * Optimized version of Subtask used in LazySubtaskList component.
 * Reduces API payload by loading only essential fields.
 *
 * @property id - Unique subtask identifier (UUID)
 * @property title - Subtask title
 * @property status - Current subtask status
 * @property priority - Subtask priority level
 * @property assignees - Optional array of assigned agent IDs (inherited from parent if not set)
 * @property progress_percentage - Completion percentage (0-100)
 * @property created_at - ISO 8601 timestamp
 * @property updated_at - ISO 8601 timestamp
 *
 * @see {@link SubtaskSummary} matches backend SubtaskSummaryDTO
 */
/**
 * ProgressEntry - Individual progress entry with timestamp
 * @see {import('./utilityTypes').ProgressHistoryEntry}
 * Note: Import from utilityTypes - duplicate removed to avoid barrel export conflicts
 */

export interface SubtaskSummary {
  id: string;
  title: string;
  status: string;
  priority: string;
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

// Dialog types
export type TaskDialogType = 'details' | 'edit' | 'delete' | 'complete' | 'context' | 'assign' | 'create';
export type SubtaskDialogType = 'subtask-details' | 'subtask-edit' | 'subtask-complete';
export type DialogType = TaskDialogType | SubtaskDialogType;

export interface ActiveDialog {
  type: DialogType | null;
  taskId?: string;
  data?: any;
}

export interface TaskActiveDialog {
  type: TaskDialogType | null;
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
  elementRef: React.RefObject<HTMLDivElement | null>;
  animationClass?: string; // Fallback animation CSS class
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
  elementRef: React.RefObject<HTMLTableRowElement | null>;
  animationClass?: string; // Fallback animation CSS class
}

export interface TaskRowActionsProps {
  taskId: string;
  projectId: string;
  taskTreeId: string;
  onOpenDialog: (type: string, taskId?: string, extraData?: any) => void;
  variant?: 'mobile' | 'desktop';
}
