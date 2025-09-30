/**
 * Project Management Component Types
 * Consolidated types for ProjectList component and related functionality
 */

import type { Project } from './api.types';
import type { BranchSummary } from './api.types';

// =============================================================================
// Component Props
// =============================================================================

/**
 * Props for ProjectList component
 */
export interface ProjectListProps {
  onSelect?: (projectId: string, branchId: string) => void;
  selectedProjectId?: string;
  selectedBranchId?: string;
  onShowGlobalContext?: () => void;
  onShowProjectDetails?: (project: Project) => void;
  onShowBranchDetails?: (project: Project, branch: any) => void;
}

// =============================================================================
// Form State Types
// =============================================================================

/**
 * Form data structure for project creation/editing
 */
export interface ProjectFormData {
  name: string;
  description: string;
}

// =============================================================================
// Dialog State Types
// =============================================================================

/**
 * State for branch deletion dialog
 */
export interface DeleteBranchDialogState {
  project: Project;
  branch: BranchSummary;
}