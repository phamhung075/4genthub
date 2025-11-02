/**
 * Agent Management Type Definitions
 *
 * TypeScript types for the User-Specific Agent System.
 * These types match the backend Pydantic models in:
 * src/fastmcp/agent_management/interface/rest/models.py
 *
 * @module types/agentTypes
 * @version 1.0.0
 */

// ============================================================================
// Agent Template Types (Read-Only System Templates)
// ============================================================================

/**
 * Agent template from the agent-library
 * Immutable system-wide templates that users can instantiate
 */
export interface AgentTemplate {
  id: string;                              // Template UUID
  slug: string;                            // Template identifier (e.g., 'coding-agent')
  name: string;                            // Display name
  description: string;                     // Template description
  category: string;                        // Agent category
  version: string;                         // Template version
  system_prompt: string;                   // Default system prompt
  tools: string[];                         // Available tools
  capabilities: Record<string, any>;       // Agent capabilities
  rules?: string[] | null;                 // Agent rules
  output_format?: string | null;           // Output format preference
  metadata: Record<string, any>;           // Additional metadata
  created_at: string;                      // ISO 8601 timestamp
}

/**
 * Response for listing agent templates
 */
export interface AgentTemplateListResponse {
  success: boolean;
  templates: AgentTemplate[];
  count: number;
  message?: string | null;
}

// ============================================================================
// User Agent Instance Types (User's Customized Agents)
// ============================================================================

/**
 * User's agent instance with customization
 * One instance per user per template (UNIQUE constraint)
 */
export interface UserAgentInstance {
  id: string;                              // Instance UUID
  user_id: string;                         // Owner user ID
  template_id: string;                     // Source template UUID
  agent_name: string;                      // Instance name
  is_customized: boolean;                  // Whether customized from template
  is_enabled: boolean;                     // Whether agent is enabled for use (default: true)
  visibility: 'private' | 'public';        // Sharing visibility
  share_token?: string | null;             // Share token for public instances (64-char)
  usage_count: number;                     // Number of times used
  last_used_at?: string | null;            // ISO 8601 timestamp
  created_at: string;                      // ISO 8601 timestamp
  updated_at: string;                      // ISO 8601 timestamp

  // Configuration details
  system_prompt: string;                   // Active system prompt
  tools: string[];                         // Active tools
  capabilities: Record<string, any>;       // Active capabilities
  rules?: string[] | null;                 // Active rules
  output_format?: string | null;           // Active output format
}

/**
 * Response for listing user's agent instances
 */
export interface UserAgentInstanceListResponse {
  success: boolean;
  instances: UserAgentInstance[];
  count: number;
  message?: string | null;
}

// ============================================================================
// Agent Creation & Update Types
// ============================================================================

/**
 * Request to create/customize agent instance
 */
export interface CreateInstanceRequest {
  template_slug: string;                   // Template to instantiate from
  agent_name?: string | null;              // Custom name for instance
  system_prompt?: string | null;           // Custom system prompt
  tools?: string[] | null;                 // Custom tool list
  capabilities?: Record<string, any> | null; // Custom capabilities
  rules?: string[] | null;                 // Custom rules
  output_format?: string | null;           // Custom output format
  visibility?: 'private' | 'public';       // Default: 'private'
}

/**
 * Request to update agent instance
 */
export interface UpdateInstanceRequest {
  agent_name?: string | null;              // Updated name
  is_enabled?: boolean | null;             // Updated enabled status
  system_prompt?: string | null;           // Updated system prompt
  tools?: string[] | null;                 // Updated tool list
  capabilities?: Record<string, any> | null; // Updated capabilities
  rules?: string[] | null;                 // Updated rules
  output_format?: string | null;           // Updated output format
  visibility?: 'private' | 'public' | null; // Updated visibility
  share_token?: string | null;             // Share token (required for public visibility)
}

/**
 * Request to update agent configuration
 */
export interface UpdateConfigurationRequest {
  system_prompt?: string | null;           // Updated system prompt
  tools?: string[] | null;                 // Updated tool list
  capabilities?: Record<string, any> | null; // Updated capabilities
  rules?: string[] | null;                 // Updated rules
  output_format?: string | null;           // Updated output format
}

// ============================================================================
// Agent Configuration Types
// ============================================================================

/**
 * Response for agent configuration
 */
export interface AgentConfigurationResponse {
  success: boolean;
  instance_id?: string | null;             // Instance ID if exists
  template_id: string;                     // Template ID
  is_customized: boolean;                  // Whether config is customized
  configuration: Record<string, any>;      // Complete configuration
  message?: string | null;
}

// ============================================================================
// Agent Sharing Types
// ============================================================================

/**
 * Response for sharing an agent
 */
export interface ShareAgentResponse {
  success: boolean;
  instance_id: string;                     // Instance UUID
  share_token: string;                     // 64-character share token
  shareable_url: string;                   // URL for sharing
  visibility: 'public';                    // Visibility status
  message?: string | null;
}

/**
 * Request to import a shared agent
 */
export interface ImportAgentRequest {
  share_token: string;                     // 64-character share token
}

/**
 * Marketplace agent listing
 */
export interface MarketplaceAgent {
  instance_id: string;                     // Instance UUID
  agent_name: string;                      // Agent display name
  template_slug: string;                   // Template slug
  creator_display_name: string;            // Creator attribution
  share_token: string;                     // Share token for importing
  customizations_summary: string;          // Summary of customizations
  usage_count: number;                     // Usage statistics
  created_at: string;                      // ISO 8601 timestamp
}

/**
 * Response for marketplace agent list
 */
export interface MarketplaceListResponse {
  success: boolean;
  agents: MarketplaceAgent[];
  total: number;                           // Total number of agents
  page: number;                            // Current page number
  page_size: number;                       // Results per page
  message?: string | null;
}

/**
 * Response for shared agent preview
 */
export interface SharedAgentPreviewResponse {
  success: boolean;
  agent_name: string;                      // Agent display name
  template_slug: string;                   // Template slug
  creator_display_name: string;            // Creator attribution
  configuration_preview: {
    system_prompt: string;
    tools: string[];
    capabilities: Record<string, any>;
    rules?: string[] | null;
    output_format?: string | null;
  };
  customizations_summary: string;          // Summary of changes from template
  can_import: boolean;                     // Whether user can import
  message?: string | null;
}

// ============================================================================
// Usage Analytics Types
// ============================================================================

/**
 * User's agent usage statistics
 */
export interface UserUsageStats {
  total_calls: number;                     // Total agent calls
  unique_agents: number;                   // Number of unique agents used
  most_used_agent?: string | null;         // Most frequently used agent
  last_activity?: string | null;           // ISO 8601 timestamp
  usage_by_agent: Record<string, number>;  // Call count per agent
}

/**
 * Global agent popularity statistics
 */
export interface PopularAgentStats {
  slug: string;
  name: string;
  total_users: number;                     // Number of users using this agent
  total_calls: number;                     // Total calls across all users
  avg_calls_per_user: number;              // Average calls per user
}

/**
 * Response for usage analytics
 */
export interface UsageAnalyticsResponse {
  success: boolean;
  user_stats?: UserUsageStats | null;
  popular_agents?: PopularAgentStats[] | null;
  message?: string | null;
}

// ============================================================================
// Generic Response Types
// ============================================================================

/**
 * Generic success response
 */
export interface SuccessResponse {
  success: boolean;
  message: string;
  data?: Record<string, any> | null;
}

/**
 * Generic error response
 */
export interface ErrorResponse {
  success: boolean;
  error: string;
  detail?: string | null;
}

// ============================================================================
// Frontend-Specific Types (Not from backend)
// ============================================================================

/**
 * Agent filter options for UI
 */
export interface AgentFilters {
  category?: string;
  search?: string;
  visibility?: 'private' | 'public' | 'all';
  is_customized?: boolean;
  sort_by?: 'name' | 'usage_count' | 'created_at' | 'updated_at';
  sort_order?: 'asc' | 'desc';
}

/**
 * Marketplace filter options
 */
export interface MarketplaceFilters {
  category?: string;
  search?: string;
  sort?: 'recent' | 'popular';
  page?: number;
  page_size?: number;
}

/**
 * Agent configuration editor state
 */
export interface AgentConfigEditorState {
  instance_id?: string;
  template_id?: string;
  is_customized: boolean;
  current_tab: 'instructions' | 'rules' | 'capabilities' | 'output_format';
  has_unsaved_changes: boolean;
  is_saving: boolean;
  is_loading: boolean;
  error?: string | null;
}

/**
 * Agent sharing dialog state
 */
export interface AgentSharingState {
  instance_id?: string;
  is_public: boolean;
  share_token?: string;
  shareable_url?: string;
  is_sharing: boolean;
  error?: string | null;
}
