// agent_management_routes.go ports agent_management/interface/rest/agent_management_routes.py.
//
// The FastAPI APIRouter/Depends/status plumbing has no Go meaning; what is ported is the
// handler logic: the facade calls, response construction, validation branches, error text
// and HTTP status codes (as *auth.HTTPException).
package rest

import (
	"context"
	"crypto/sha1"
	"errors"
	"fmt"
	"time"

	"agenthub/fastmcp/agent_management/domain/entities"
	"agenthub/fastmcp/agent_management/domain/value_objects"
	"agenthub/fastmcp/auth"
	authdomain "agenthub/fastmcp/auth/domain/entities"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// Facade is the minimal AgentManagementFacade surface used by these routes. The real Go
// facade is not ported yet; this interface declares the needed methods (ctx first, like
// the repository interfaces). UpdateConfiguration/UpdateInstance pass the request's
// optional fields explicitly (nil pointer = Python None).
type Facade interface {
	ListAvailableTemplates(ctx context.Context) ([]*entities.AgentTemplate, error)
	GetTemplateBySlug(ctx context.Context, agentSlug string) (*entities.AgentTemplate, error)
	GetTemplateByID(ctx context.Context, templateID string) (*entities.AgentTemplate, error)
	GetUserInstances(ctx context.Context, userID value_objects.UserId) ([]*entities.UserAgentInstance, error)
	GetOrCreateInstance(ctx context.Context, userID value_objects.UserId, agentSlug string) (*entities.UserAgentInstance, error)
	BulkCreateInstances(ctx context.Context, userID value_objects.UserId, templateSlugs []string) ([]*entities.UserAgentInstance, error)
	UpdateInstance(ctx context.Context, userID value_objects.UserId, instanceID string, agentName *string, isEnabled *bool, systemPrompt *string, tools []string, capabilities *tmentities.OrderedMap[any], rules []string, outputFormat *string, visibility *string) (*entities.UserAgentInstance, error)
	DeleteInstance(ctx context.Context, userID value_objects.UserId, instanceID string) (bool, error)
	UpdateConfiguration(ctx context.Context, userID value_objects.UserId, agentSlug string, systemPrompt *string, tools []string, capabilities *tmentities.OrderedMap[any], rules []string, outputFormat *string) (*entities.UserAgentInstance, error)
	ResetConfiguration(ctx context.Context, userID value_objects.UserId, agentSlug string) (*entities.UserAgentInstance, error)
	ShareAgent(ctx context.Context, userID value_objects.UserId, instanceID string) (*string, error)
	UnshareAgent(ctx context.Context, userID value_objects.UserId, instanceID string) (bool, error)
	ImportAgent(ctx context.Context, shareToken string, importerUserID value_objects.UserId, creatorEmail string) (*entities.UserAgentInstance, error)
	GetMarketplaceAgents(ctx context.Context, limit, offset int) ([]*entities.UserAgentInstance, error)
	GetSharedAgentPreview(ctx context.Context, shareToken string) (*entities.UserAgentInstance, error)
}

func httpErr(status int, detail string) *auth.HTTPException {
	return &auth.HTTPException{StatusCode: status, Detail: detail}
}

func valueErr(err error) (*tmvo.ValueError, bool) {
	var ve *tmvo.ValueError
	if errors.As(err, &ve) {
		return ve, true
	}
	return nil, false
}

func currentID(u *authdomain.User) string {
	if u.ID == nil {
		return ""
	}
	return *u.ID
}

func emptyDict(m *tmentities.OrderedMap[any]) *tmentities.OrderedMap[any] {
	if m == nil {
		return tmentities.NewOrderedMap[any]()
	}
	return m
}

func stringsOrNil(rules []string) any {
	if len(rules) == 0 {
		return nil
	}
	return append([]string{}, rules...)
}

func creatorID(inst *entities.UserAgentInstance) *string {
	if inst.OriginalCreatorID == nil {
		return nil
	}
	s := inst.OriginalCreatorID.Value
	return &s
}

func instanceResponse(inst *entities.UserAgentInstance) *UserAgentInstanceResponse {
	return &UserAgentInstanceResponse{
		ID:                inst.ID.Value,
		UserID:            inst.UserID.Value,
		TemplateID:        inst.TemplateID.Value,
		AgentName:         inst.AgentName,
		IsCustomized:      inst.IsCustomized,
		IsEnabled:         inst.IsEnabled,
		Visibility:        inst.Visibility,
		UsageCount:        inst.UsageCount,
		LastUsedAt:        inst.LastUsedAt,
		CreatedAt:         inst.CreatedAt,
		UpdatedAt:         inst.UpdatedAt,
		IsImported:        inst.OriginalCreatorID != nil,
		OriginalCreatorID: creatorID(inst),
		IsReadOnly:        inst.OriginalCreatorID != nil && inst.OriginalCreatorID.Value != inst.UserID.Value,
		SystemPrompt:      inst.Configuration.SystemPrompt,
		Tools:             append([]string{}, inst.Configuration.Tools...),
		Capabilities:      emptyDict(inst.Configuration.Capabilities),
		Rules:             stringsOrNil(inst.Configuration.Rules),
		OutputFormat:      inst.Configuration.OutputFormat,
	}
}

func templateResponse(t *entities.AgentTemplate) *AgentTemplateResponse {
	return &AgentTemplateResponse{
		ID:           t.ID.Value,
		Slug:         t.Slug,
		Name:         t.Name,
		Description:  t.Description,
		Category:     t.Category,
		Version:      t.Version,
		SystemPrompt: t.DefaultConfiguration.SystemPrompt,
		Tools:        append([]string{}, t.DefaultConfiguration.Tools...),
		Capabilities: emptyDict(t.DefaultConfiguration.Capabilities),
		Rules:        stringsOrNil(t.DefaultConfiguration.Rules),
		OutputFormat: t.DefaultConfiguration.OutputFormat,
		Metadata:     t.Metadata,
		CreatedAt:    t.CreatedAt,
	}
}

// ListTemplates is list_templates GET /templates.
func ListTemplates(ctx context.Context, currentUser *authdomain.User, facade Facade) (*AgentTemplateListResponse, error) {
	templates, err := facade.ListAvailableTemplates(ctx)
	if err != nil {
		return nil, httpErr(500, fmt.Sprintf("Failed to list templates: %s", err.Error()))
	}
	responses := make([]*AgentTemplateResponse, 0, len(templates))
	for _, t := range templates {
		responses = append(responses, templateResponse(t))
	}
	return &AgentTemplateListResponse{Success: true, Templates: responses, Count: len(responses)}, nil
}

// GetTemplate is get_template GET /templates/{slug}.
func GetTemplate(ctx context.Context, slug string, currentUser *authdomain.User, facade Facade) (*AgentTemplateResponse, error) {
	template, err := facade.GetTemplateBySlug(ctx, slug)
	if err != nil {
		return nil, httpErr(500, fmt.Sprintf("Failed to get template: %s", err.Error()))
	}
	if template == nil {
		return nil, httpErr(404, fmt.Sprintf("Template '%s' not found", slug))
	}
	return templateResponse(template), nil
}

// ListUserInstances is list_user_instances GET /instances.
func ListUserInstances(ctx context.Context, currentUser *authdomain.User, facade Facade) (*UserAgentInstanceListResponse, error) {
	userID, err := value_objects.NewUserId(currentID(currentUser))
	if err != nil {
		return nil, httpErr(500, fmt.Sprintf("Failed to list instances: %s", err.Error()))
	}
	instances, err := facade.GetUserInstances(ctx, userID)
	if err != nil {
		return nil, httpErr(500, fmt.Sprintf("Failed to list instances: %s", err.Error()))
	}
	responses := make([]*UserAgentInstanceResponse, 0, len(instances))
	for _, inst := range instances {
		responses = append(responses, instanceResponse(inst))
	}
	return &UserAgentInstanceListResponse{Success: true, Instances: responses, Count: len(responses)}, nil
}

// GetInstance is get_instance GET /instances/{instance_id}.
func GetInstance(ctx context.Context, instanceID string, currentUser *authdomain.User, facade Facade) (*UserAgentInstanceResponse, error) {
	userID, err := value_objects.NewUserId(currentID(currentUser))
	if err != nil {
		return nil, httpErr(500, fmt.Sprintf("Failed to get instance: %s", err.Error()))
	}
	instances, err := facade.GetUserInstances(ctx, userID)
	if err != nil {
		return nil, httpErr(500, fmt.Sprintf("Failed to get instance: %s", err.Error()))
	}
	for _, inst := range instances {
		if inst.ID.Value == instanceID {
			return instanceResponse(inst), nil
		}
	}
	return nil, httpErr(404, fmt.Sprintf("Instance '%s' not found or access denied", instanceID))
}

// CreateInstance is create_instance POST /instances.
func CreateInstance(ctx context.Context, request CreateInstanceRequest, currentUser *authdomain.User, facade Facade) (*UserAgentInstanceResponse, error) {
	userID, err := value_objects.NewUserId(currentID(currentUser))
	if err != nil {
		return nil, httpErr(500, fmt.Sprintf("Failed to create instance: %s", err.Error()))
	}
	instance, err := facade.GetOrCreateInstance(ctx, userID, request.TemplateSlug)
	if err != nil {
		if ve, ok := valueErr(err); ok {
			return nil, httpErr(404, ve.Msg)
		}
		return nil, httpErr(500, fmt.Sprintf("Failed to create instance: %s", err.Error()))
	}
	// Customizations requested -> TODO not implemented in the facade (Python logs only).
	return instanceResponse(instance), nil
}

// BulkCreateInstances is bulk_create_instances POST /instances/bulk-create.
func BulkCreateInstances(ctx context.Context, currentUser *authdomain.User, facade Facade) ([]*UserAgentInstanceResponse, error) {
	userID, err := value_objects.NewUserId(currentID(currentUser))
	if err != nil {
		return nil, httpErr(500, fmt.Sprintf("Failed to bulk create instances: %s", err.Error()))
	}
	created, err := facade.BulkCreateInstances(ctx, userID, nil)
	if err != nil {
		return nil, httpErr(500, fmt.Sprintf("Failed to bulk create instances: %s", err.Error()))
	}
	responses := make([]*UserAgentInstanceResponse, 0, len(created))
	for _, inst := range created {
		responses = append(responses, instanceResponse(inst))
	}
	return responses, nil
}

// UpdateInstance is update_instance PUT /instances/{instance_id}.
func UpdateInstance(ctx context.Context, instanceID string, request UpdateInstanceRequest, currentUser *authdomain.User, facade Facade) (*UserAgentInstanceResponse, error) {
	userID, userIDErr := value_objects.NewUserId(currentID(currentUser))
	if userIDErr != nil {
		// Python converts a non-UUID current_user.id to uuid5(nil_namespace, id).
		converted, convErr := value_objects.NewUserId(uuid5Nil(currentID(currentUser)))
		if convErr != nil {
			return nil, httpErr(500, fmt.Sprintf("Failed to update instance: %s", convErr.Error()))
		}
		userID = converted
	}
	updated, err := facade.UpdateInstance(ctx, userID, instanceID, request.AgentName, request.IsEnabled, request.SystemPrompt, request.Tools, request.Capabilities, request.Rules, request.OutputFormat, request.Visibility)
	if err != nil {
		if ve, ok := valueErr(err); ok {
			msg := ve.Msg
			if contains(msg, "Cannot edit imported agent") || contains(msg, "original creator") {
				return nil, httpErr(403, msg)
			}
			return nil, httpErr(400, msg)
		}
		return nil, httpErr(500, fmt.Sprintf("Failed to update instance: %s", err.Error()))
	}
	return instanceResponse(updated), nil
}

// DeleteInstance is delete_instance DELETE /instances/{instance_id}.
func DeleteInstance(ctx context.Context, instanceID string, currentUser *authdomain.User, facade Facade) (*SuccessResponse, error) {
	userID, err := value_objects.NewUserId(currentID(currentUser))
	if err != nil {
		return nil, httpErr(500, fmt.Sprintf("Failed to delete instance: %s", err.Error()))
	}
	success, err := facade.DeleteInstance(ctx, userID, instanceID)
	if err != nil {
		if ve, ok := valueErr(err); ok {
			return nil, httpErr(400, ve.Msg)
		}
		return nil, httpErr(500, fmt.Sprintf("Failed to delete instance: %s", err.Error()))
	}
	if !success {
		return nil, httpErr(500, "Failed to delete instance")
	}
	return &SuccessResponse{Success: true, Message: fmt.Sprintf("Instance %s deleted successfully", instanceID)}, nil
}

// GetUserUsageStats is get_user_usage_stats GET /analytics/usage.
func GetUserUsageStats(ctx context.Context, currentUser *authdomain.User, facade Facade) (*UsageAnalyticsResponse, error) {
	userID, err := value_objects.NewUserId(currentID(currentUser))
	if err != nil {
		return nil, httpErr(500, fmt.Sprintf("Failed to get usage statistics: %s", err.Error()))
	}
	instances, err := facade.GetUserInstances(ctx, userID)
	if err != nil {
		return nil, httpErr(500, fmt.Sprintf("Failed to get usage statistics: %s", err.Error()))
	}
	totalCalls := 0
	usageByAgent := tmentities.NewOrderedMap[any]()
	var mostUsed *entities.UserAgentInstance
	var lastActivity *time.Time
	for _, inst := range instances {
		totalCalls += inst.UsageCount
		usageByAgent.Set(inst.AgentName, inst.UsageCount)
		if mostUsed == nil || inst.UsageCount > mostUsed.UsageCount {
			mostUsed = inst
		}
		if inst.LastUsedAt != nil && (lastActivity == nil || inst.LastUsedAt.After(*lastActivity)) {
			lastActivity = inst.LastUsedAt
		}
	}
	var mostUsedName *string
	if mostUsed != nil && mostUsed.UsageCount > 0 {
		name := mostUsed.AgentName
		mostUsedName = &name
	}
	stats := &UserUsageStats{
		TotalCalls:    totalCalls,
		UniqueAgents:  len(instances),
		MostUsedAgent: mostUsedName,
		LastActivity:  lastActivity,
		UsageByAgent:  usageByAgent,
	}
	return &UsageAnalyticsResponse{Success: true, UserStats: stats}, nil
}

// GetPopularAgents is get_popular_agents GET /analytics/popular (not implemented in Python).
func GetPopularAgents(ctx context.Context, currentUser *authdomain.User, facade Facade, limit int) (*UsageAnalyticsResponse, error) {
	msg := "Global analytics not yet implemented"
	return &UsageAnalyticsResponse{Success: true, PopularAgents: []*PopularAgentStats{}, Message: &msg}, nil
}

func configDict(inst *entities.UserAgentInstance) *tmentities.OrderedMap[any] {
	c := tmentities.NewOrderedMap[any]()
	c.Set("system_prompt", inst.Configuration.SystemPrompt)
	c.Set("tools", append([]string{}, inst.Configuration.Tools...))
	c.Set("capabilities", emptyDict(inst.Configuration.Capabilities))
	c.Set("rules", stringsOrNil(inst.Configuration.Rules))
	c.Set("output_format", inst.Configuration.OutputFormat)
	return c
}

// GetConfiguration is get_configuration GET /configuration/{slug}.
func GetConfiguration(ctx context.Context, slug string, currentUser *authdomain.User, facade Facade) (*AgentConfigurationResponse, error) {
	userID, err := value_objects.NewUserId(currentID(currentUser))
	if err != nil {
		return nil, httpErr(500, fmt.Sprintf("Failed to get configuration: %s", err.Error()))
	}
	instance, err := facade.GetOrCreateInstance(ctx, userID, slug)
	if err != nil {
		if ve, ok := valueErr(err); ok {
			return nil, httpErr(404, ve.Msg)
		}
		return nil, httpErr(500, fmt.Sprintf("Failed to get configuration: %s", err.Error()))
	}
	id := instance.ID.Value
	return &AgentConfigurationResponse{
		Success:       true,
		InstanceID:    &id,
		TemplateID:    instance.TemplateID.Value,
		IsCustomized:  instance.IsCustomized,
		Configuration: configDict(instance),
	}, nil
}

// UpdateConfiguration is update_configuration PUT /configuration/{slug}.
func UpdateConfiguration(ctx context.Context, slug string, request UpdateConfigurationRequest, currentUser *authdomain.User, facade Facade) (*AgentConfigurationResponse, error) {
	userID, err := value_objects.NewUserId(currentID(currentUser))
	if err != nil {
		return nil, httpErr(500, fmt.Sprintf("Failed to update configuration: %s", err.Error()))
	}
	updated, err := facade.UpdateConfiguration(ctx, userID, slug, request.SystemPrompt, request.Tools, request.Capabilities, request.Rules, request.OutputFormat)
	if err != nil {
		if ve, ok := valueErr(err); ok {
			return nil, httpErr(400, ve.Msg)
		}
		return nil, httpErr(500, fmt.Sprintf("Failed to update configuration: %s", err.Error()))
	}
	template, err := facade.GetTemplateBySlug(ctx, slug)
	if err != nil {
		return nil, httpErr(500, fmt.Sprintf("Failed to update configuration: %s", err.Error()))
	}
	if template == nil {
		return nil, httpErr(404, fmt.Sprintf("Agent template not found: %s", slug))
	}
	msg := fmt.Sprintf("Configuration updated for %s", slug)
	return &AgentConfigurationResponse{
		Success:       true,
		InstanceID:    optionalInstanceID(updated),
		TemplateID:    template.ID.Value,
		IsCustomized:  updated.IsCustomized,
		Configuration: configDict(updated),
		Message:       &msg,
	}, nil
}

// ResetConfiguration is reset_configuration POST /configuration/{slug}/reset.
func ResetConfiguration(ctx context.Context, slug string, currentUser *authdomain.User, facade Facade) (*AgentConfigurationResponse, error) {
	userID, err := value_objects.NewUserId(currentID(currentUser))
	if err != nil {
		return nil, httpErr(500, fmt.Sprintf("Failed to reset configuration: %s", err.Error()))
	}
	reset, err := facade.ResetConfiguration(ctx, userID, slug)
	if err != nil {
		if ve, ok := valueErr(err); ok {
			return nil, httpErr(400, ve.Msg)
		}
		return nil, httpErr(500, fmt.Sprintf("Failed to reset configuration: %s", err.Error()))
	}
	template, err := facade.GetTemplateBySlug(ctx, slug)
	if err != nil {
		return nil, httpErr(500, fmt.Sprintf("Failed to reset configuration: %s", err.Error()))
	}
	if template == nil {
		return nil, httpErr(404, fmt.Sprintf("Agent template not found: %s", slug))
	}
	msg := fmt.Sprintf("Configuration reset to default for %s", slug)
	return &AgentConfigurationResponse{
		Success:       true,
		InstanceID:    optionalInstanceID(reset),
		TemplateID:    template.ID.Value,
		IsCustomized:  reset.IsCustomized,
		Configuration: configDict(reset),
		Message:       &msg,
	}, nil
}

func optionalInstanceID(inst *entities.UserAgentInstance) *string {
	if inst.ID == nil {
		return nil
	}
	id := inst.ID.Value
	return &id
}

// ShareAgent is share_agent POST /instances/{instance_id}/share.
func ShareAgent(ctx context.Context, instanceID string, currentUser *authdomain.User, facade Facade) (*ShareAgentResponse, error) {
	userID, err := value_objects.NewUserId(currentID(currentUser))
	if err != nil {
		return nil, httpErr(500, fmt.Sprintf("Failed to share agent: %s", err.Error()))
	}
	token, err := facade.ShareAgent(ctx, userID, instanceID)
	if err != nil {
		if ve, ok := valueErr(err); ok {
			return nil, httpErr(404, ve.Msg)
		}
		return nil, httpErr(500, fmt.Sprintf("Failed to share agent: %s", err.Error()))
	}
	tok := ""
	if token != nil {
		tok = *token
	}
	msg := "Agent shared successfully"
	return &ShareAgentResponse{
		Success:      true,
		InstanceID:   instanceID,
		ShareToken:   tok,
		ShareableURL: fmt.Sprintf("/api/v2/agent-management/marketplace/%s", tok),
		Visibility:   "public",
		Message:      &msg,
	}, nil
}

// UnshareAgent is unshare_agent POST /instances/{instance_id}/unshare.
func UnshareAgent(ctx context.Context, instanceID string, currentUser *authdomain.User, facade Facade) (*SuccessResponse, error) {
	userID, err := value_objects.NewUserId(currentID(currentUser))
	if err != nil {
		return nil, httpErr(500, fmt.Sprintf("Failed to unshare agent: %s", err.Error()))
	}
	_, err = facade.UnshareAgent(ctx, userID, instanceID)
	if err != nil {
		if ve, ok := valueErr(err); ok {
			return nil, httpErr(404, ve.Msg)
		}
		return nil, httpErr(500, fmt.Sprintf("Failed to unshare agent: %s", err.Error()))
	}
	return &SuccessResponse{Success: true, Message: "Agent unshared successfully. It is now private."}, nil
}

// ImportAgent is import_agent POST /import.
func ImportAgent(ctx context.Context, request ImportAgentRequest, currentUser *authdomain.User, facade Facade) (*UserAgentInstanceResponse, error) {
	userID, userIDErr := value_objects.NewUserId(currentID(currentUser))
	if userIDErr != nil {
		converted, convErr := value_objects.NewUserId(uuid5Nil(currentID(currentUser)))
		if convErr != nil {
			return nil, httpErr(500, fmt.Sprintf("Failed to import agent: %s", convErr.Error()))
		}
		userID = converted
	}
	imported, err := facade.ImportAgent(ctx, request.ShareToken, userID, currentUser.Email)
	if err != nil {
		if ve, ok := valueErr(err); ok {
			return nil, httpErr(400, ve.Msg)
		}
		return nil, httpErr(500, fmt.Sprintf("Failed to import agent: %s", err.Error()))
	}
	resp := instanceResponse(imported)
	resp.IsImported = true
	resp.IsReadOnly = imported.OriginalCreatorID != nil && imported.OriginalCreatorID.Value != userID.Value
	return resp, nil
}

// BrowseMarketplace is browse_marketplace GET /marketplace.
func BrowseMarketplace(ctx context.Context, category, search, sortBy *string, page, pageSize int, facade Facade) (*MarketplaceListResponse, error) {
	if page < 1 {
		return nil, httpErr(400, "Page number must be >= 1")
	}
	if pageSize < 1 || pageSize > 100 {
		return nil, httpErr(400, "Page size must be between 1 and 100")
	}
	instances, err := facade.GetMarketplaceAgents(ctx, pageSize, (page-1)*pageSize)
	if err != nil {
		return nil, httpErr(500, fmt.Sprintf("Failed to browse marketplace: %s", err.Error()))
	}
	agents := make([]*MarketplaceAgentResponse, 0, len(instances))
	for _, inst := range instances {
		template, err := facade.GetTemplateByID(ctx, inst.TemplateID.Value)
		if err != nil {
			return nil, httpErr(500, fmt.Sprintf("Failed to browse marketplace: %s", err.Error()))
		}
		slug := "unknown"
		if template != nil {
			slug = template.Slug
		}
		summary := "Default template"
		if inst.IsCustomized {
			summary = "Custom configuration"
		}
		shareToken := ""
		if inst.ShareToken != nil {
			shareToken = *inst.ShareToken
		}
		agents = append(agents, &MarketplaceAgentResponse{
			InstanceID:            inst.ID.Value,
			AgentName:             inst.AgentName,
			TemplateSlug:          slug,
			CreatorDisplayName:    inst.GetCreatorDisplayName(nil),
			ShareToken:            shareToken,
			CustomizationsSummary: summary,
			UsageCount:            inst.UsageCount,
			CreatedAt:             inst.CreatedAt,
		})
	}
	msg := fmt.Sprintf("Found %d public agents", len(agents))
	return &MarketplaceListResponse{Success: true, Agents: agents, Total: len(agents), Page: page, PageSize: pageSize, Message: &msg}, nil
}

// PreviewSharedAgent is preview_shared_agent GET /marketplace/{share_token}.
func PreviewSharedAgent(ctx context.Context, shareToken string, facade Facade) (*SharedAgentPreviewResponse, error) {
	instance, err := facade.GetSharedAgentPreview(ctx, shareToken)
	if err != nil {
		if ve, ok := valueErr(err); ok {
			return nil, httpErr(400, ve.Msg)
		}
		return nil, httpErr(500, fmt.Sprintf("Failed to preview shared agent: %s", err.Error()))
	}
	if instance == nil {
		return nil, httpErr(404, "Shared agent not found or is no longer public")
	}
	template, err := facade.GetTemplateByID(ctx, instance.TemplateID.Value)
	if err != nil {
		return nil, httpErr(500, fmt.Sprintf("Failed to preview shared agent: %s", err.Error()))
	}
	slug := "unknown"
	if template != nil {
		slug = template.Slug
	}
	preview := tmentities.NewOrderedMap[any]()
	preview.Set("system_prompt", instance.Configuration.SystemPrompt)
	preview.Set("tools", append([]string{}, instance.Configuration.Tools...))
	preview.Set("capabilities", emptyDict(instance.Configuration.Capabilities))
	rules := any([]string{})
	if len(instance.Configuration.Rules) > 0 {
		rules = append([]string{}, instance.Configuration.Rules...)
	}
	preview.Set("rules", rules)
	preview.Set("output_format", instance.Configuration.OutputFormat)
	summary := "Default template configuration"
	if instance.IsCustomized {
		summary = "Custom configuration"
	}
	msg := "Agent preview loaded successfully"
	return &SharedAgentPreviewResponse{
		Success:               true,
		AgentName:             instance.AgentName,
		TemplateSlug:          slug,
		CreatorDisplayName:    instance.GetCreatorDisplayName(nil),
		ConfigurationPreview:  preview,
		CustomizationsSummary: summary,
		CanImport:             true,
		Message:               &msg,
	}, nil
}

func contains(s, sub string) bool {
	for i := 0; i+len(sub) <= len(s); i++ {
		if s[i:i+len(sub)] == sub {
			return true
		}
	}
	return false
}

// uuid5Nil is uuid.uuid5(uuid.UUID(int=0), name) used for non-UUID development user ids.
func uuid5Nil(name string) string {
	var ns [16]byte
	h := sha1.New()
	h.Write(ns[:])
	h.Write([]byte(name))
	sum := h.Sum(nil)
	var u [16]byte
	copy(u[:], sum[:16])
	u[6] = (u[6] & 0x0f) | 0x50
	u[8] = (u[8] & 0x3f) | 0x80
	return fmt.Sprintf("%x-%x-%x-%x-%x", u[0:4], u[4:6], u[6:8], u[8:10], u[10:16])
}
