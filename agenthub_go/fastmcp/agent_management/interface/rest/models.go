// Package rest ports agent_management/interface/rest (models + routes).
//
// models.go ports models.py: the pydantic request/response DTOs as Go structs whose
// field order matches the pydantic declaration order (Go's encoding/json emits struct
// fields in declaration order). Optional[...] is a pointer, dict[str, Any] is
// *entities.OrderedMap[any] (nil is Python None), datetime is time.Time.
package rest

import (
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
)

// AgentTemplateResponse mirrors models.AgentTemplateResponse.
type AgentTemplateResponse struct {
	ID           string                    `json:"id"`
	Slug         string                    `json:"slug"`
	Name         string                    `json:"name"`
	Description  string                    `json:"description"`
	Category     string                    `json:"category"`
	Version      string                    `json:"version"`
	SystemPrompt string                    `json:"system_prompt"`
	Tools        []string                  `json:"tools"`
	Capabilities *entities.OrderedMap[any] `json:"capabilities"`
	Rules        any                       `json:"rules"`
	OutputFormat any                       `json:"output_format"`
	Metadata     *entities.OrderedMap[any] `json:"metadata"`
	CreatedAt    *time.Time                `json:"created_at"`
}

// AgentTemplateListResponse mirrors models.AgentTemplateListResponse.
type AgentTemplateListResponse struct {
	Success   bool                     `json:"success"`
	Templates []*AgentTemplateResponse `json:"templates"`
	Count     int                      `json:"count"`
	Message   *string                  `json:"message,omitempty"`
}

// CreateInstanceRequest mirrors models.CreateInstanceRequest.
type CreateInstanceRequest struct {
	TemplateSlug string                    `json:"template_slug"`
	AgentName    *string                   `json:"agent_name"`
	SystemPrompt *string                   `json:"system_prompt"`
	Tools        []string                  `json:"tools"`
	Capabilities *entities.OrderedMap[any] `json:"capabilities"`
	Rules        []string                  `json:"rules"`
	OutputFormat *string                   `json:"output_format"`
	Visibility   string                    `json:"visibility"`
}

// UpdateInstanceRequest mirrors models.UpdateInstanceRequest.
type UpdateInstanceRequest struct {
	AgentName    *string                   `json:"agent_name"`
	IsEnabled    *bool                     `json:"is_enabled"`
	SystemPrompt *string                   `json:"system_prompt"`
	Tools        []string                  `json:"tools"`
	Capabilities *entities.OrderedMap[any] `json:"capabilities"`
	Rules        []string                  `json:"rules"`
	OutputFormat *string                   `json:"output_format"`
	Visibility   *string                   `json:"visibility"`
}

// UserAgentInstanceResponse mirrors models.UserAgentInstanceResponse.
type UserAgentInstanceResponse struct {
	ID                string                    `json:"id"`
	UserID            string                    `json:"user_id"`
	TemplateID        string                    `json:"template_id"`
	AgentName         string                    `json:"agent_name"`
	IsCustomized      bool                      `json:"is_customized"`
	IsEnabled         bool                      `json:"is_enabled"`
	Visibility        string                    `json:"visibility"`
	UsageCount        int                       `json:"usage_count"`
	LastUsedAt        *time.Time                `json:"last_used_at"`
	CreatedAt         *time.Time                `json:"created_at"`
	UpdatedAt         *time.Time                `json:"updated_at"`
	IsImported        bool                      `json:"is_imported"`
	OriginalCreatorID *string                   `json:"original_creator_id"`
	IsReadOnly        bool                      `json:"is_read_only"`
	SystemPrompt      string                    `json:"system_prompt"`
	Tools             []string                  `json:"tools"`
	Capabilities      *entities.OrderedMap[any] `json:"capabilities"`
	Rules             any                       `json:"rules"`
	OutputFormat      any                       `json:"output_format"`
}

// UserAgentInstanceListResponse mirrors models.UserAgentInstanceListResponse.
type UserAgentInstanceListResponse struct {
	Success   bool                         `json:"success"`
	Instances []*UserAgentInstanceResponse `json:"instances"`
	Count     int                          `json:"count"`
	Message   *string                      `json:"message,omitempty"`
}

// UserUsageStats mirrors models.UserUsageStats.
type UserUsageStats struct {
	TotalCalls    int                       `json:"total_calls"`
	UniqueAgents  int                       `json:"unique_agents"`
	MostUsedAgent *string                   `json:"most_used_agent"`
	LastActivity  *time.Time                `json:"last_activity"`
	UsageByAgent  *entities.OrderedMap[any] `json:"usage_by_agent"`
}

// PopularAgentStats mirrors models.PopularAgentStats.
type PopularAgentStats struct {
	Slug            string  `json:"slug"`
	Name            string  `json:"name"`
	TotalUsers      int     `json:"total_users"`
	TotalCalls      int     `json:"total_calls"`
	AvgCallsPerUser float64 `json:"avg_calls_per_user"`
}

// UsageAnalyticsResponse mirrors models.UsageAnalyticsResponse.
type UsageAnalyticsResponse struct {
	Success       bool                 `json:"success"`
	UserStats     *UserUsageStats      `json:"user_stats"`
	PopularAgents []*PopularAgentStats `json:"popular_agents"`
	Message       *string              `json:"message,omitempty"`
}

// AgentConfigurationResponse mirrors models.AgentConfigurationResponse.
type AgentConfigurationResponse struct {
	Success       bool                      `json:"success"`
	InstanceID    *string                   `json:"instance_id"`
	TemplateID    string                    `json:"template_id"`
	IsCustomized  bool                      `json:"is_customized"`
	Configuration *entities.OrderedMap[any] `json:"configuration"`
	Message       *string                   `json:"message,omitempty"`
}

// UpdateConfigurationRequest mirrors models.UpdateConfigurationRequest.
type UpdateConfigurationRequest struct {
	SystemPrompt *string                   `json:"system_prompt"`
	Tools        []string                  `json:"tools"`
	Capabilities *entities.OrderedMap[any] `json:"capabilities"`
	Rules        []string                  `json:"rules"`
	OutputFormat *string                   `json:"output_format"`
}

// ShareAgentResponse mirrors models.ShareAgentResponse.
type ShareAgentResponse struct {
	Success      bool    `json:"success"`
	InstanceID   string  `json:"instance_id"`
	ShareToken   string  `json:"share_token"`
	ShareableURL string  `json:"shareable_url"`
	Visibility   string  `json:"visibility"`
	Message      *string `json:"message,omitempty"`
}

// ImportAgentRequest mirrors models.ImportAgentRequest.
type ImportAgentRequest struct {
	ShareToken string `json:"share_token"`
}

// MarketplaceAgentResponse mirrors models.MarketplaceAgentResponse.
type MarketplaceAgentResponse struct {
	InstanceID            string     `json:"instance_id"`
	AgentName             string     `json:"agent_name"`
	TemplateSlug          string     `json:"template_slug"`
	CreatorDisplayName    string     `json:"creator_display_name"`
	ShareToken            string     `json:"share_token"`
	CustomizationsSummary string     `json:"customizations_summary"`
	UsageCount            int        `json:"usage_count"`
	CreatedAt             *time.Time `json:"created_at"`
}

// MarketplaceListResponse mirrors models.MarketplaceListResponse.
type MarketplaceListResponse struct {
	Success  bool                        `json:"success"`
	Agents   []*MarketplaceAgentResponse `json:"agents"`
	Total    int                         `json:"total"`
	Page     int                         `json:"page"`
	PageSize int                         `json:"page_size"`
	Message  *string                     `json:"message,omitempty"`
}

// SharedAgentPreviewResponse mirrors models.SharedAgentPreviewResponse.
type SharedAgentPreviewResponse struct {
	Success               bool                      `json:"success"`
	AgentName             string                    `json:"agent_name"`
	TemplateSlug          string                    `json:"template_slug"`
	CreatorDisplayName    string                    `json:"creator_display_name"`
	ConfigurationPreview  *entities.OrderedMap[any] `json:"configuration_preview"`
	CustomizationsSummary string                    `json:"customizations_summary"`
	CanImport             bool                      `json:"can_import"`
	Message               *string                   `json:"message,omitempty"`
}

// SuccessResponse mirrors models.SuccessResponse.
type SuccessResponse struct {
	Success bool                      `json:"success"`
	Message string                    `json:"message"`
	Data    *entities.OrderedMap[any] `json:"data,omitempty"`
}

// ErrorResponse mirrors models.ErrorResponse.
type ErrorResponse struct {
	Success bool    `json:"success"`
	Error   string  `json:"error"`
	Detail  *string `json:"detail,omitempty"`
}
