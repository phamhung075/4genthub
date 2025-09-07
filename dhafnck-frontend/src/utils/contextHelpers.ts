// Utility functions for handling context data structures

export interface ContextProgress {
  current_session_summary?: string;
  completion_percentage?: number;
  next_steps?: string[];
  completed_actions?: string[];
}

export interface ContextMetadata {
  status?: string;
  [key: string]: any;
}

// New context structures based on CONTEXT_DATA_MODELS.md
export interface GlobalContextData {
  organization_standards?: Record<string, any>;
  compliance_requirements?: Record<string, any>;
  shared_resources?: Record<string, any>;
  reusable_patterns?: Record<string, any>;
  global_preferences?: Record<string, any>;
  [key: string]: any;
}

export interface ProjectContextData {
  project_info?: Record<string, any>;
  team_preferences?: Record<string, any>;
  technology_stack?: Record<string, any>;
  project_workflow?: Record<string, any>;
  local_standards?: Record<string, any>;
  project_settings?: Record<string, any>;
  technical_specifications?: Record<string, any>;
  [key: string]: any;
}

export interface BranchContextData {
  branch_info?: Record<string, any>;
  branch_workflow?: Record<string, any>;
  feature_flags?: Record<string, any>;
  discovered_patterns?: Record<string, any>;
  branch_decisions?: Record<string, any>;
  branch_settings?: Record<string, any>;
  active_patterns?: Record<string, any>;
  local_overrides?: Record<string, any>;
  delegation_rules?: Record<string, any>;
  [key: string]: any;
}

export interface TaskContextData {
  task_data?: Record<string, any>;
  execution_context?: Record<string, any>;
  discovered_patterns?: Record<string, any>;
  implementation_notes?: Record<string, any>;
  test_results?: Record<string, any>;
  blockers?: Record<string, any>;
  local_decisions?: Record<string, any>;
  delegation_queue?: Record<string, any>;
  local_overrides?: Record<string, any>;
  delegation_triggers?: Record<string, any>;
  [key: string]: any;
}

export interface ContextData {
  progress?: ContextProgress;
  metadata?: ContextMetadata;
  // Support all context level structures - Global Context
  organization_standards?: Record<string, any>;
  compliance_requirements?: Record<string, any>;
  shared_resources?: Record<string, any>;
  reusable_patterns?: Record<string, any>;
  global_preferences?: Record<string, any>;
  // Project Context
  project_info?: Record<string, any>;
  team_preferences?: Record<string, any>;
  technology_stack?: Record<string, any>;
  project_workflow?: Record<string, any>;
  local_standards?: Record<string, any>;
  project_settings?: Record<string, any>;
  technical_specifications?: Record<string, any>;
  // Branch Context
  branch_info?: Record<string, any>;
  branch_workflow?: Record<string, any>;
  feature_flags?: Record<string, any>;
  discovered_patterns?: Record<string, any>;
  branch_decisions?: Record<string, any>;
  branch_settings?: Record<string, any>;
  active_patterns?: Record<string, any>;
  local_overrides?: Record<string, any>;
  delegation_rules?: Record<string, any>;
  // Task Context
  task_data?: Record<string, any>;
  execution_context?: Record<string, any>;
  implementation_notes?: Record<string, any>;
  test_results?: Record<string, any>;
  blockers?: Record<string, any>;
  local_decisions?: Record<string, any>;
  delegation_queue?: Record<string, any>;
  delegation_triggers?: Record<string, any>;
  [key: string]: any;
}

/**
 * Extract completion summary from context data
 */
export function getCompletionSummary(contextData?: ContextData): string | null {
  if (!contextData?.progress) return null;
  return contextData.progress.current_session_summary || null;
}

/**
 * Check if context data is using legacy format (always false now)
 */
export function isLegacyFormat(contextData?: ContextData): boolean {
  return false; // No legacy support
}

/**
 * Get completion percentage from context data
 */
export function getCompletionPercentage(contextData?: ContextData): number | null {
  return contextData?.progress?.completion_percentage ?? null;
}

/**
 * Get task status from metadata
 */
export function getTaskStatus(contextData?: ContextData): string | null {
  return contextData?.metadata?.status ?? null;
}

/**
 * Get testing notes and next steps as an array
 */
export function getTestingNotes(contextData?: ContextData): string[] {
  if (!contextData?.progress?.next_steps) return [];
  
  return Array.isArray(contextData.progress.next_steps) 
    ? contextData.progress.next_steps 
    : [];
}

/**
 * Check if context data has meaningful completion information
 */
export function hasCompletionInfo(contextData?: ContextData): boolean {
  return !!(
    getCompletionSummary(contextData) ||
    getTaskStatus(contextData) ||
    getTestingNotes(contextData).length > 0
  );
}

/**
 * Format context data for display with proper labels
 */
export function formatContextDisplay(contextData?: ContextData) {
  const completionSummary = getCompletionSummary(contextData);
  const isLegacy = isLegacyFormat(contextData);
  const completionPercentage = getCompletionPercentage(contextData);
  const taskStatus = getTaskStatus(contextData);
  const testingNotes = getTestingNotes(contextData);
  
  return {
    completionSummary,
    isLegacy,
    completionPercentage,
    taskStatus,
    testingNotes,
    hasInfo: hasCompletionInfo(contextData)
  };
}

/**
 * Get context level based on available fields
 */
export function getContextLevel(contextData?: ContextData): string | null {
  if (!contextData) return null;
  
  if (contextData.organization_standards || contextData.compliance_requirements || 
      contextData.shared_resources || contextData.reusable_patterns || 
      contextData.global_preferences) {
    return 'global';
  }
  
  if (contextData.project_info || contextData.team_preferences || 
      contextData.technology_stack || contextData.project_workflow || 
      contextData.local_standards) {
    return 'project';
  }
  
  if (contextData.branch_info || contextData.branch_workflow || 
      contextData.feature_flags || contextData.branch_decisions || 
      contextData.active_patterns || contextData.delegation_rules) {
    return 'branch';
  }
  
  if (contextData.task_data || contextData.execution_context || 
      contextData.implementation_notes || contextData.test_results || 
      contextData.blockers || contextData.local_decisions || 
      contextData.delegation_queue || contextData.delegation_triggers) {
    return 'task';
  }
  
  return null;
}

/**
 * Get formatted context fields based on context level
 */
export function getContextFields(contextData?: ContextData): Record<string, any> {
  if (!contextData) return {};
  
  const level = getContextLevel(contextData);
  const fields: Record<string, any> = {};
  
  switch (level) {
    case 'global':
      if (contextData.organization_standards) fields['Organization Standards'] = contextData.organization_standards;
      if (contextData.compliance_requirements) fields['Compliance Requirements'] = contextData.compliance_requirements;
      if (contextData.shared_resources) fields['Shared Resources'] = contextData.shared_resources;
      if (contextData.reusable_patterns) fields['Reusable Patterns'] = contextData.reusable_patterns;
      if (contextData.global_preferences) fields['Global Preferences'] = contextData.global_preferences;
      break;
      
    case 'project':
      if (contextData.project_info) fields['Project Info'] = contextData.project_info;
      if (contextData.team_preferences) fields['Team Preferences'] = contextData.team_preferences;
      if (contextData.technology_stack) fields['Technology Stack'] = contextData.technology_stack;
      if (contextData.project_workflow) fields['Project Workflow'] = contextData.project_workflow;
      if (contextData.local_standards) fields['Local Standards'] = contextData.local_standards;
      if (contextData.project_settings) fields['Project Settings'] = contextData.project_settings;
      if (contextData.technical_specifications) fields['Technical Specifications'] = contextData.technical_specifications;
      break;
      
    case 'branch':
      if (contextData.branch_info) fields['Branch Info'] = contextData.branch_info;
      if (contextData.branch_workflow) fields['Branch Workflow'] = contextData.branch_workflow;
      if (contextData.feature_flags) fields['Feature Flags'] = contextData.feature_flags;
      if (contextData.discovered_patterns) fields['Discovered Patterns'] = contextData.discovered_patterns;
      if (contextData.branch_decisions) fields['Branch Decisions'] = contextData.branch_decisions;
      if (contextData.branch_settings) fields['Branch Settings'] = contextData.branch_settings;
      if (contextData.active_patterns) fields['Active Patterns'] = contextData.active_patterns;
      if (contextData.local_overrides) fields['Local Overrides'] = contextData.local_overrides;
      if (contextData.delegation_rules) fields['Delegation Rules'] = contextData.delegation_rules;
      break;
      
    case 'task':
      if (contextData.task_data) fields['Task Data'] = contextData.task_data;
      if (contextData.execution_context) fields['Execution Context'] = contextData.execution_context;
      if (contextData.discovered_patterns) fields['Discovered Patterns'] = contextData.discovered_patterns;
      if (contextData.implementation_notes) fields['Implementation Notes'] = contextData.implementation_notes;
      if (contextData.test_results) fields['Test Results'] = contextData.test_results;
      if (contextData.blockers) fields['Blockers'] = contextData.blockers;
      if (contextData.local_decisions) fields['Local Decisions'] = contextData.local_decisions;
      if (contextData.delegation_queue) fields['Delegation Queue'] = contextData.delegation_queue;
      if (contextData.local_overrides) fields['Local Overrides'] = contextData.local_overrides;
      if (contextData.delegation_triggers) fields['Delegation Triggers'] = contextData.delegation_triggers;
      break;
  }
  
  return fields;
}