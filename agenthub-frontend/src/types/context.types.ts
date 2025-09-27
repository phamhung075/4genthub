/**
 * Context Types for Global Context Data
 *
 * These types define the structure of nested global context data
 * returned from the backend, including CLAUDE.md rules and custom fields.
 */

// CLAUDE.md Rules Structure
export interface ClaudeMdRules {
  clean_code?: string;
  test_hierarchy?: string;
  enterprise_identity?: string;
  master_orchestrator?: string;
  token_economy?: string;
  documentation_rules?: string;
  git_workflow?: string;
  agent_coordination?: string;
  [key: string]: string | undefined; // Allow additional rule fields
}

// User Preferences Structure
export interface UserPreferences {
  theme?: 'light' | 'dark' | 'system';
  language?: string;
  timezone?: string;
  notifications?: {
    email?: boolean;
    push?: boolean;
    task_updates?: boolean;
    agent_notifications?: boolean;
  };
  ui_preferences?: {
    default_view?: string;
    items_per_page?: number;
    auto_refresh?: boolean;
  };
  [key: string]: any; // Allow additional preference fields
}

// AI Agent Settings Structure
export interface AiAgentSettings {
  preferred_agents?: string[];
  default_agent?: string;
  agent_coordination?: {
    auto_delegate?: boolean;
    parallel_execution?: boolean;
    max_concurrent_agents?: number;
  };
  communication_style?: 'formal' | 'casual' | 'technical';
  output_format?: 'detailed' | 'summary' | 'minimal';
  [key: string]: any; // Allow additional agent settings
}

// Security Settings Structure
export interface SecuritySettings {
  two_factor_enabled?: boolean;
  session_timeout?: number; // minutes
  password_policy?: {
    min_length?: number;
    require_special_chars?: boolean;
    require_numbers?: boolean;
    require_uppercase?: boolean;
  };
  access_permissions?: {
    can_delete_tasks?: boolean;
    can_manage_projects?: boolean;
    can_assign_agents?: boolean;
  };
  audit_logging?: boolean;
  [key: string]: any; // Allow additional security fields
}

// Workflow Preferences Structure
export interface WorkflowPreferences {
  default_task_priority?: 'low' | 'medium' | 'high' | 'urgent' | 'critical';
  auto_task_assignment?: boolean;
  task_templates?: Array<{
    name: string;
    template: any;
  }>;
  notification_triggers?: {
    task_completion?: boolean;
    task_assignment?: boolean;
    deadline_reminders?: boolean;
  };
  branch_naming_convention?: string;
  [key: string]: any; // Allow additional workflow fields
}

// Development Tools Settings
export interface DevelopmentTools {
  preferred_editor?: string;
  code_formatting?: {
    auto_format?: boolean;
    style_guide?: string;
  };
  testing_preferences?: {
    auto_run_tests?: boolean;
    coverage_threshold?: number;
  };
  deployment_settings?: {
    auto_deploy?: boolean;
    environment_order?: string[];
  };
  [key: string]: any; // Allow additional dev tool settings
}

// Dashboard Settings Structure
export interface DashboardSettings {
  layout?: 'grid' | 'list' | 'kanban';
  widgets?: Array<{
    type: string;
    position: { x: number; y: number };
    size: { width: number; height: number };
    config?: any;
  }>;
  default_filters?: {
    status?: string[];
    priority?: string[];
    assignee?: string[];
  };
  refresh_interval?: number; // seconds
  [key: string]: any; // Allow additional dashboard settings
}

// Main Global Context Interface
export interface GlobalContext {
  // Core CLAUDE.md rules - the main focus of this update
  claude_md_rules?: ClaudeMdRules;

  // Standard context sections
  user_preferences?: UserPreferences;
  ai_agent_settings?: AiAgentSettings;
  security_settings?: SecuritySettings;
  workflow_preferences?: WorkflowPreferences;
  development_tools?: DevelopmentTools;
  dashboard_settings?: DashboardSettings;

  // System metadata
  version?: string;
  last_updated?: string;
  created_at?: string;
  updated_at?: string;
  user_id?: string;
  id?: string;

  // Project-specific fields mentioned in the task
  project_status?: string;
  system_architecture?: string;

  // Flexible structure for additional custom fields
  [key: string]: any;
}

// Response wrapper for API calls
export interface GlobalContextResponse {
  success?: boolean;
  message?: string;
  error?: string;
  context?: GlobalContext;
  global_settings?: GlobalContext; // Alternative response structure
  data?: {
    global_settings?: GlobalContext;
  };
  [key: string]: any;
}

// Context field metadata for UI rendering
export interface ContextFieldMetadata {
  key: string;
  label: string;
  description?: string;
  type: 'object' | 'string' | 'boolean' | 'number' | 'array';
  category: 'core' | 'settings' | 'metadata' | 'custom';
  icon?: string; // Lucide icon name
  color?: string; // Tailwind color class
  collapsible?: boolean;
  defaultExpanded?: boolean;
}

// Predefined field metadata for known fields
export const GLOBAL_CONTEXT_FIELD_METADATA: ContextFieldMetadata[] = [
  {
    key: 'claude_md_rules',
    label: 'CLAUDE.md Rules',
    description: 'Core AI agent rules and guidelines from CLAUDE.md',
    type: 'object',
    category: 'core',
    icon: 'FileText',
    color: 'blue',
    collapsible: true,
    defaultExpanded: true
  },
  {
    key: 'user_preferences',
    label: 'User Preferences',
    description: 'Personal settings and preferences',
    type: 'object',
    category: 'settings',
    icon: 'Settings',
    color: 'green',
    collapsible: true,
    defaultExpanded: false
  },
  {
    key: 'ai_agent_settings',
    label: 'AI Agent Settings',
    description: 'Configuration for AI agents and coordination',
    type: 'object',
    category: 'settings',
    icon: 'Bot',
    color: 'purple',
    collapsible: true,
    defaultExpanded: false
  },
  {
    key: 'security_settings',
    label: 'Security Settings',
    description: 'Security and access control configuration',
    type: 'object',
    category: 'settings',
    icon: 'Shield',
    color: 'red',
    collapsible: true,
    defaultExpanded: false
  },
  {
    key: 'workflow_preferences',
    label: 'Workflow Preferences',
    description: 'Task management and workflow settings',
    type: 'object',
    category: 'settings',
    icon: 'GitBranch',
    color: 'orange',
    collapsible: true,
    defaultExpanded: false
  },
  {
    key: 'development_tools',
    label: 'Development Tools',
    description: 'Development environment and tool settings',
    type: 'object',
    category: 'settings',
    icon: 'Code',
    color: 'indigo',
    collapsible: true,
    defaultExpanded: false
  },
  {
    key: 'dashboard_settings',
    label: 'Dashboard Settings',
    description: 'Dashboard layout and widget configuration',
    type: 'object',
    category: 'settings',
    icon: 'LayoutDashboard',
    color: 'cyan',
    collapsible: true,
    defaultExpanded: false
  }
];

// Utility function to get field metadata
export const getFieldMetadata = (fieldKey: string): ContextFieldMetadata | null => {
  return GLOBAL_CONTEXT_FIELD_METADATA.find(meta => meta.key === fieldKey) || null;
};

// Utility function to categorize unknown fields
export const categorizeField = (key: string, value: any): ContextFieldMetadata => {
  const knownMetadataKeys = ['version', 'last_updated', 'created_at', 'updated_at', 'user_id', 'id'];

  return {
    key,
    label: key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
    type: typeof value === 'object' ? 'object' : typeof value as any,
    category: knownMetadataKeys.includes(key) ? 'metadata' : 'custom',
    icon: typeof value === 'object' ? 'Package' : 'Tag',
    color: 'gray',
    collapsible: typeof value === 'object',
    defaultExpanded: false
  };
};