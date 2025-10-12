/**
 * Component Props and State Types
 * Centralized type definitions for React component props and internal state
 */

import { Task, Subtask } from '../api';

// ========================================
// COMPONENT PROPS INTERFACES
// ========================================

/**
 * Props for TaskSearch component
 * Handles task and subtask search functionality
 */
export interface TaskSearchProps {
  projectId: string;
  taskTreeId: string;
  onTaskSelect?: (task: Task) => void;
  onSubtaskSelect?: (subtask: Subtask, parentTask: Task) => void;
}

/**
 * Search result structure containing both tasks and subtasks
 */
export interface SearchResult {
  tasks: Task[];
  subtasksWithParent: Array<{
    subtask: Subtask;
    parentTask: Task;
  }>;
}

// ========================================
// AUTHENTICATION COMPONENT TYPES
// ========================================

import type { User, AuthTokens, SignupResult } from './authTypes';

/**
 * Auth context type for authentication state management
 */
export interface AuthContextType {
  user: User | null;
  tokens: AuthTokens | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, username: string, password: string) => Promise<SignupResult>;
  logout: () => void;
  refreshToken: () => Promise<void>;
  setTokens: (tokens: AuthTokens) => void;
}

// ========================================
// UI COMPONENT PROP TYPES
// ========================================

/**
 * Input component props extending React HTML input attributes
 */
export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

/**
 * Dialog component props extending React HTML div attributes
 */
export interface DialogProps extends React.HTMLAttributes<HTMLDivElement> {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: React.ReactNode;
}

/**
 * Badge component props
 * Supports multiple visual variants for different contexts
 */
export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "secondary" | "destructive" | "outline";
}

/**
 * Button component props
 * Supports multiple variants and sizes
 */
export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "outline" | "secondary" | "ghost" | "link" | "destructive";
  size?: "default" | "sm" | "lg" | "icon";
}

/**
 * Textarea component props extending React HTML textarea attributes
 */
export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {}

/**
 * Select component props extending React HTML select attributes
 */
export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {}

/**
 * Sidebar component props extending React HTML div attributes
 */
export interface SidebarProps extends React.HTMLAttributes<HTMLDivElement> {}

/**
 * Enhanced Button component props with animation support
 * Extends ButtonProps with additional animation options
 */
export interface EnhancedButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "outline" | "secondary" | "ghost" | "link" | "destructive";
  size?: "default" | "sm" | "lg" | "icon";
  animation?: "none" | "shimmer" | "glow" | "sweep" | "pulse" | "gradient" | "aurora" | "dual-rotating" | "dual-rotating-glow";
}

/**
 * Toast notification types
 */
export type ToastType = 'success' | 'error' | 'warning' | 'info';

/**
 * Toast notification structure
 */
export interface Toast {
  id: string;
  type: ToastType;
  title: string;
  description?: string;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}

/**
 * Progress state for tasks and operations
 */
export type ProgressState = 'initial' | 'in_progress' | 'complete';

// ========================================
// PROJECT LIST COMPONENT PROP TYPES
// ========================================

import type { Project } from '../api';
import type { BranchSummary } from './api.types';

/**
 * Props for ProjectListHeader component
 * Handles header actions and display
 */
export interface ProjectListHeaderProps {
  loading: boolean;
  loadingBulkSummaries: boolean;
  isConnected: boolean;
  onRefresh: () => void;
  onShowGlobalContext?: () => void;
  onCreateProject: () => void;
}

/**
 * Props for ProjectListContent component
 * Handles rendering of projects and branches with animations
 */
export interface ProjectListContentProps {
  projects: Project[];
  branchSummaries: Record<string, BranchSummary[]>;
  taskCounts: Record<string, number>;
  openProjects: Record<string, boolean>;
  selected: string | null;
  // Animation states
  newBranches: Set<string>;
  fadingOutBranches: Set<string>;
  deletingBranches: Set<string>;
  animatingCounts: Map<string, 'up' | 'down'>;
  // Handlers
  onToggleProject: (projectId: string) => void;
  onSelectBranch: (projectId: string, branchId: string) => void;
  onShowProjectDetails?: (project: Project) => void;
  onShowBranchDetails?: (project: Project, branch: any) => void;
  onCreateBranch: (project: Project) => void;
  onEditProject: (project: Project) => void;
  onDeleteProject: (project: Project) => void;
  onDeleteBranch: (dialogState: { project: Project; branch: any }) => void;
}

/**
 * Delete branch dialog state structure
 */
export interface DeleteBranchDialogState {
  project: Project;
  branch: any;
}

/**
 * Project form data structure for create/edit operations
 */
export interface ProjectFormData {
  name: string;
  description: string;
}

/**
 * Props for ProjectDialogs component
 * Handles all project and branch dialog interactions
 */
export interface ProjectDialogsProps {
  // Dialog states
  showCreate: boolean;
  showEdit: Project | null;
  showDelete: Project | null;
  showCreateBranch: Project | null;
  showDeleteBranch: DeleteBranchDialogState | null;
  // Form data
  form: ProjectFormData;
  saving: boolean;
  // Handlers
  onCloseCreate: () => void;
  onCloseEdit: () => void;
  onCloseDelete: () => void;
  onCloseCreateBranch: () => void;
  onCloseDeleteBranch: () => void;
  onFormChange: (e: React.ChangeEvent<HTMLInputElement>, field: 'name' | 'description') => void;
  onCreateProject: () => void;
  onEditProject: () => void;
  onDeleteProject: () => void;
  onCreateBranch: () => void;
  onDeleteBranch: () => void;
}