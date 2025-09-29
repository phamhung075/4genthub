/**
 * Context Types
 * Type definitions for global, project, branch, and task contexts
 */

// Re-export context data types from contextHelpers
export type {
  ContextProgress,
  ContextMetadata,
  GlobalContextData,
  ProjectContextData,
  BranchContextData,
  TaskContextData
} from '../utils/contextHelpers';

// =============================================================================
// Global Context Types
// =============================================================================

export interface GlobalContext {
  [key: string]: any;
  organization_standards?: Record<string, any>;
  compliance_requirements?: Record<string, any>;
  shared_resources?: Record<string, any>;
  reusable_patterns?: Record<string, any>;
  global_preferences?: Record<string, any>;
}

// =============================================================================
// Context Field Metadata
// =============================================================================

export interface ContextFieldMetadata {
  key: string;
  label: string;
  description: string;
  category: 'standards' | 'preferences' | 'resources' | 'patterns' | 'compliance' | 'other';
  icon?: string;
  color?: 'blue' | 'green' | 'purple' | 'orange' | 'red' | 'gray';
}

export const GLOBAL_CONTEXT_FIELD_METADATA: ContextFieldMetadata[] = [
  {
    key: 'organization_standards',
    label: 'Organization Standards',
    description: 'Company-wide coding standards and guidelines',
    category: 'standards',
    icon: 'Shield',
    color: 'blue'
  },
  {
    key: 'compliance_requirements',
    label: 'Compliance Requirements',
    description: 'Regulatory and compliance requirements',
    category: 'compliance',
    icon: 'AlertCircle',
    color: 'red'
  },
  {
    key: 'shared_resources',
    label: 'Shared Resources',
    description: 'Common libraries, tools, and resources',
    category: 'resources',
    icon: 'Package',
    color: 'green'
  },
  {
    key: 'reusable_patterns',
    label: 'Reusable Patterns',
    description: 'Design patterns and code templates',
    category: 'patterns',
    icon: 'Code',
    color: 'purple'
  },
  {
    key: 'global_preferences',
    label: 'Global Preferences',
    description: 'Organization-wide preferences and settings',
    category: 'preferences',
    icon: 'Settings',
    color: 'gray'
  }
];

// =============================================================================
// Utility Functions
// =============================================================================

export function categorizeField(key: string): ContextFieldMetadata | null {
  return GLOBAL_CONTEXT_FIELD_METADATA.find(metadata => metadata.key === key) || null;
}