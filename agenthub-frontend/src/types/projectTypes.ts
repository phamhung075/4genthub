/**
 * Project Management Component Types
 * Consolidated types for ProjectList component and related functionality
 */

import type { Project } from './api.types';

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
 * @deprecated Import from componentTypes instead
 * @see {import('./componentTypes').ProjectFormData}
 */
// REMOVED: Duplicate of componentTypes.ProjectFormData - import from there instead

// =============================================================================
// Dialog State Types
// =============================================================================

/**
 * State for branch deletion dialog
 * @deprecated Import from componentTypes instead
 * @see {import('./componentTypes').DeleteBranchDialogState}
 */
// REMOVED: Duplicate of componentTypes.DeleteBranchDialogState - import from there instead