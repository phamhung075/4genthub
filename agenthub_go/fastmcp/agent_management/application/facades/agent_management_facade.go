// Package facades ports agent_management/application/facades.
package facades

import (
	"context"
	"time"
	"unicode/utf8"

	amentities "agenthub/fastmcp/agent_management/domain/entities"
	"agenthub/fastmcp/agent_management/domain/enums"
	"agenthub/fastmcp/agent_management/domain/repositories"
	"agenthub/fastmcp/agent_management/domain/services"
	amvo "agenthub/fastmcp/agent_management/domain/value_objects"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// ImportHistoryRecorder records an import into agent_import_history. Python writes the
// AgentImportHistoryORM row through the repository's db session; the Go application layer
// cannot reach the database package, so a minimal optional interface is declared here.
type ImportHistoryRecorder interface {
	RecordAgentImportHistory(ctx context.Context, importerUserID, sourceInstanceID, importedInstanceID, shareToken string) error
}

// orphanChecker is the extra method Python calls on ORMUserAgentInstanceRepository that
// is not part of the domain repository interface.
type orphanChecker interface {
	IsOrphaned(ctx context.Context, instanceID amvo.UserAgentInstanceId) (bool, error)
}

// slugFinder is the extra lookup method Python's repository exposes beyond the domain
// interface.
type slugFinder interface {
	FindByUserAndTemplateSlug(ctx context.Context, userID amvo.UserId, templateSlug string) (*amentities.UserAgentInstance, error)
}

// AgentManagementFacade orchestrates agent instantiation, customization and sharing.
type AgentManagementFacade struct {
	templateRepo         repositories.AgentTemplateRepository
	instanceRepo         repositories.UserAgentInstanceRepository
	instantiationService *services.AgentInstantiationService
	sharingService       *services.AgentSharingService
	// HistoryRecorder, when set, receives agent_import_history rows (Python always
	// writes them; leave nil to skip when no session is available).
	HistoryRecorder ImportHistoryRecorder
}

// NewAgentManagementFacade wires the repositories and domain services. Nil
// instantiation/sharing services are built from the repositories, mirroring the Python
// defaults.
func NewAgentManagementFacade(templateRepo repositories.AgentTemplateRepository, instanceRepo repositories.UserAgentInstanceRepository, instantiationService *services.AgentInstantiationService, sharingService *services.AgentSharingService) *AgentManagementFacade {
	if instantiationService == nil {
		instantiationService = services.NewAgentInstantiationService(templateRepo, instanceRepo)
	}
	if sharingService == nil {
		sharingService = services.NewAgentSharingService(instanceRepo, templateRepo)
	}
	return &AgentManagementFacade{
		templateRepo:         templateRepo,
		instanceRepo:         instanceRepo,
		instantiationService: instantiationService,
		sharingService:       sharingService,
	}
}

// GetOrCreateInstance delegates to the instantiation service, raising the Python
// "Agent template not found" error when the service returns nothing.
func (f *AgentManagementFacade) GetOrCreateInstance(ctx context.Context, userID *amvo.UserId, agentSlug string) (*amentities.UserAgentInstance, error) {
	instance, err := f.instantiationService.GetOrCreateInstance(ctx, userID, agentSlug)
	if err != nil {
		return nil, err
	}
	if instance == nil {
		return nil, tmvo.ValueErrorf("Agent template not found: %s", agentSlug)
	}
	return instance, nil
}

// BulkCreateInstances creates instances for the given slugs (nil means every template),
// skipping templates the user already has and swallowing per-slug failures.
func (f *AgentManagementFacade) BulkCreateInstances(ctx context.Context, userID *amvo.UserId, templateSlugs []string) ([]*amentities.UserAgentInstance, error) {
	allTemplates, err := f.templateRepo.FindAll(ctx)
	if err != nil {
		return nil, err
	}
	slugs := templateSlugs
	if slugs == nil {
		slugs = make([]string, 0, len(allTemplates))
		for _, t := range allTemplates {
			slugs = append(slugs, t.Slug)
		}
	}
	templateIDToSlug := map[string]string{}
	for _, t := range allTemplates {
		if t.ID != nil {
			templateIDToSlug[t.ID.String()] = t.Slug
		}
	}
	existingInstances, err := f.instanceRepo.FindByUser(ctx, *userID)
	if err != nil {
		return nil, err
	}
	existingSlugs := map[string]bool{}
	for _, inst := range existingInstances {
		if inst.TemplateID == nil {
			continue
		}
		if slug, ok := templateIDToSlug[inst.TemplateID.String()]; ok {
			existingSlugs[slug] = true
		}
	}
	created := []*amentities.UserAgentInstance{}
	for _, slug := range slugs {
		if existingSlugs[slug] {
			continue
		}
		instance, err := f.instantiationService.GetOrCreateInstance(ctx, userID, slug)
		if err != nil {
			continue
		}
		if instance != nil {
			created = append(created, instance)
		}
	}
	return created, nil
}

// GetAgentForCall returns the response dict for the call_agent MCP tool, tracking usage
// first and preserving the Python dict key order.
func (f *AgentManagementFacade) GetAgentForCall(ctx context.Context, userID *amvo.UserId, agentSlug string) (*tmentities.OrderedMap[any], error) {
	instance, err := f.GetOrCreateInstance(ctx, userID, agentSlug)
	if err != nil {
		return nil, err
	}
	instance.TrackUsage()
	if _, err := f.instanceRepo.Save(ctx, instance); err != nil {
		return nil, err
	}
	template, err := f.templateRepo.FindBySlug(ctx, agentSlug)
	if err != nil {
		return nil, err
	}
	if template == nil {
		return nil, tmvo.ValueErrorf("Agent template not found: %s", agentSlug)
	}
	config := instance.Configuration
	isOrphaned := false
	if oc, ok := f.instanceRepo.(orphanChecker); ok {
		if instance.ID == nil {
			return nil, tmvo.TypeErrorf("instance has no id")
		}
		isOrphaned, err = oc.IsOrphaned(ctx, *instance.ID)
		if err != nil {
			return nil, err
		}
	}

	name := instance.AgentName
	if name == "" {
		name = template.Name
	}
	capabilities := config.Capabilities
	if capabilities == nil {
		capabilities = tmentities.NewOrderedMap[any]()
	}
	resp := tmentities.NewOrderedMap[any]()
	resp.Set("name", name)
	resp.Set("slug", template.Slug)
	resp.Set("description", template.Description)
	resp.Set("system_prompt", config.SystemPrompt)
	resp.Set("tools", facadeStringList(config.Tools))
	resp.Set("capabilities", capabilities)
	resp.Set("rules", facadeStringList(config.Rules))
	resp.Set("output_format", facadeAnyOrNil(config.OutputFormat))
	resp.Set("category", template.Category)
	resp.Set("version", template.Version)
	resp.Set("is_customized", instance.IsCustomized)
	resp.Set("is_orphaned", isOrphaned)

	instanceID := ""
	if instance.ID != nil {
		instanceID = instance.ID.String()
	}
	templateID := ""
	if template.ID != nil {
		templateID = template.ID.String()
	}
	resp.Set("instance_id", instanceID)
	resp.Set("template_id", templateID)

	metadata := tmentities.NewOrderedMap[any]()
	if template.Metadata != nil {
		for _, k := range template.Metadata.Keys() {
			v, _ := template.Metadata.Get(k)
			metadata.Set(k, v)
		}
	}
	metadata.Set("created_at", facadeIsoOrNil(instance.CreatedAt))
	var lastUsed any
	if instance.LastUsedAt != nil {
		lastUsed = tmvo.IsoFormat(*instance.LastUsedAt)
	}
	metadata.Set("last_used", lastUsed)
	var customizations any = tmentities.NewOrderedMap[any]()
	if instance.Metadata != nil {
		if v, ok := instance.Metadata.Get("customizations"); ok {
			customizations = v
		}
	}
	metadata.Set("customizations", customizations)
	var orphanedWarning any
	if isOrphaned {
		orphanedWarning = "Agent not supported by owner anymore, you are in last version"
	}
	metadata.Set("orphaned_warning", orphanedWarning)
	resp.Set("metadata", metadata)
	return resp, nil
}

// GetUserInstances returns every instance the user owns.
func (f *AgentManagementFacade) GetUserInstances(ctx context.Context, userID *amvo.UserId) ([]*amentities.UserAgentInstance, error) {
	return f.instanceRepo.FindByUser(ctx, *userID)
}

// GetTemplateBySlug returns the template with the slug, or nil.
func (f *AgentManagementFacade) GetTemplateBySlug(ctx context.Context, agentSlug string) (*amentities.AgentTemplate, error) {
	return f.templateRepo.FindBySlug(ctx, agentSlug)
}

// GetTemplateByID parses the id (Python AgentTemplateId.from_string) and looks it up.
func (f *AgentManagementFacade) GetTemplateByID(ctx context.Context, templateID string) (*amentities.AgentTemplate, error) {
	id, err := amvo.NewAgentTemplateId(templateID)
	if err != nil {
		return nil, err
	}
	return f.templateRepo.FindByID(ctx, id)
}

// ListAvailableTemplates returns every template.
func (f *AgentManagementFacade) ListAvailableTemplates(ctx context.Context) ([]*amentities.AgentTemplate, error) {
	return f.templateRepo.FindAll(ctx)
}

// UpdateInstance updates a user's instance. Pointer arguments are Python's None
// sentinels; a non-nil pointer means the value was provided.
func (f *AgentManagementFacade) UpdateInstance(
	ctx context.Context,
	userID *amvo.UserId,
	instanceID string,
	agentName *string,
	isEnabled *bool,
	systemPrompt *string,
	tools *[]string,
	capabilities *tmentities.OrderedMap[any],
	rules *[]string,
	outputFormat *string,
	visibility *string,
) (*amentities.UserAgentInstance, error) {
	instanceUUID, err := amvo.NewUserAgentInstanceId(instanceID)
	if err != nil {
		return nil, err
	}
	instance, err := f.instanceRepo.FindByID(ctx, instanceUUID)
	if err != nil {
		return nil, err
	}
	if instance == nil {
		return nil, tmvo.ValueErrorf("Instance not found: %s", instanceID)
	}
	if instance.UserID == nil || instance.UserID.Value != userID.Value {
		return nil, tmvo.ValueErrorf("Instance %s does not belong to user %s", instanceID, userID.Value)
	}
	if instance.OriginalCreatorID != nil {
		if instance.OriginalCreatorID.Value != userID.Value {
			return nil, tmvo.ValueErrorf("Cannot edit imported agent. Only the original creator (user %s) can update this agent.", instance.OriginalCreatorID.Value)
		}
	}
	if agentName != nil {
		instance.AgentName = *agentName
	}
	if isEnabled != nil {
		instance.IsEnabled = *isEnabled
	}
	if facadeAnyTruthy(systemPrompt, tools, capabilities, rules, outputFormat) {
		current := instance.Configuration
		newConfigDict := tmentities.NewOrderedMap[any]()
		prompt := current.SystemPrompt
		if systemPrompt != nil {
			prompt = *systemPrompt
		}
		newConfigDict.Set("system_prompt", prompt)
		useTools := current.Tools
		if tools != nil {
			useTools = *tools
		}
		newConfigDict.Set("tools", facadeStringList(useTools))
		caps := current.Capabilities
		if capabilities != nil {
			caps = capabilities
		}
		newConfigDict.Set("capabilities", caps)
		useRules := current.Rules
		if rules != nil {
			useRules = *rules
		}
		newConfigDict.Set("rules", facadeStringList(useRules))
		if outputFormat != nil {
			newConfigDict.Set("output_format", *outputFormat)
		} else {
			newConfigDict.Set("output_format", current.OutputFormat)
		}
		newConfig, err := amvo.AgentConfigurationFromDict(newConfigDict)
		if err != nil {
			return nil, err
		}
		notes := "Updated via REST API"
		if err := instance.CustomizeConfiguration(newConfig, &notes); err != nil {
			return nil, err
		}
	}
	if visibility != nil {
		v := *visibility
		if v != "private" && v != "public" {
			return nil, tmvo.ValueErrorf("Invalid visibility: %s. Must be 'private' or 'public'", v)
		}
		hasToken := instance.ShareToken != nil && *instance.ShareToken != ""
		if v == "public" && !hasToken {
			token, ok, err := f.sharingService.GenerateShareToken(ctx, instanceUUID, *userID)
			if err != nil {
				return nil, err
			}
			if !ok || token == "" {
				return nil, tmvo.ValueErrorf("Failed to generate share token for instance %s", instanceID)
			}
			instance, err = f.instanceRepo.FindByID(ctx, instanceUUID)
			if err != nil {
				return nil, err
			}
		} else if v == "private" && hasToken {
			success, err := f.sharingService.RevokeShareToken(ctx, instanceUUID, *userID)
			if err != nil {
				return nil, err
			}
			if !success {
				return nil, tmvo.ValueErrorf("Failed to revoke share token for instance %s", instanceID)
			}
			instance, err = f.instanceRepo.FindByID(ctx, instanceUUID)
			if err != nil {
				return nil, err
			}
		}
	}
	return f.instanceRepo.Save(ctx, instance)
}

// DeleteInstance deletes an instance the user owns.
func (f *AgentManagementFacade) DeleteInstance(ctx context.Context, userID *amvo.UserId, instanceID string) (bool, error) {
	instanceUUID, err := amvo.NewUserAgentInstanceId(instanceID)
	if err != nil {
		return false, err
	}
	instance, err := f.instanceRepo.FindByID(ctx, instanceUUID)
	if err != nil {
		return false, err
	}
	if instance == nil {
		return false, tmvo.ValueErrorf("Instance not found: %s", instanceID)
	}
	if instance.UserID == nil || instance.UserID.Value != userID.Value {
		return false, tmvo.ValueErrorf("Instance %s does not belong to user %s", instanceID, userID.Value)
	}
	if err := f.instanceRepo.Delete(ctx, instanceUUID); err != nil {
		return false, err
	}
	return true, nil
}

// UpdateConfiguration updates (or creates) the instance for the agent slug.
func (f *AgentManagementFacade) UpdateConfiguration(
	ctx context.Context,
	userID *amvo.UserId,
	agentSlug string,
	systemPrompt *string,
	tools *[]string,
	capabilities *tmentities.OrderedMap[any],
	rules *[]string,
	outputFormat *string,
) (*amentities.UserAgentInstance, error) {
	instance, err := f.GetOrCreateInstance(ctx, userID, agentSlug)
	if err != nil {
		return nil, err
	}
	if facadeAnyTruthy(systemPrompt, tools, capabilities, rules, outputFormat) {
		current := instance.Configuration
		newConfigDict := tmentities.NewOrderedMap[any]()
		prompt := current.SystemPrompt
		if systemPrompt != nil {
			prompt = *systemPrompt
		}
		newConfigDict.Set("system_prompt", prompt)
		useTools := current.Tools
		if tools != nil {
			useTools = *tools
		}
		newConfigDict.Set("tools", facadeStringList(useTools))
		caps := current.Capabilities
		if capabilities != nil {
			caps = capabilities
		}
		newConfigDict.Set("capabilities", caps)
		useRules := current.Rules
		if rules != nil {
			useRules = *rules
		}
		newConfigDict.Set("rules", facadeStringList(useRules))
		if outputFormat != nil {
			newConfigDict.Set("output_format", *outputFormat)
		} else {
			newConfigDict.Set("output_format", current.OutputFormat)
		}
		newConfig, err := amvo.AgentConfigurationFromDict(newConfigDict)
		if err != nil {
			return nil, err
		}
		notes := "Updated configuration via REST API"
		if err := instance.CustomizeConfiguration(newConfig, &notes); err != nil {
			return nil, err
		}
		return f.instanceRepo.Save(ctx, instance)
	}
	return instance, nil
}

// ResetConfiguration restores the template default configuration.
func (f *AgentManagementFacade) ResetConfiguration(ctx context.Context, userID *amvo.UserId, agentSlug string) (*amentities.UserAgentInstance, error) {
	template, err := f.templateRepo.FindBySlug(ctx, agentSlug)
	if err != nil {
		return nil, err
	}
	if template == nil {
		return nil, tmvo.ValueErrorf("Agent template not found: %s", agentSlug)
	}
	sf, ok := f.instanceRepo.(slugFinder)
	if !ok {
		return nil, tmvo.TypeErrorf("repository does not support find_by_user_and_template_slug")
	}
	instance, err := sf.FindByUserAndTemplateSlug(ctx, *userID, agentSlug)
	if err != nil {
		return nil, err
	}
	if instance == nil {
		return nil, tmvo.ValueErrorf("No instance found for user %s and agent %s", userID.Value, agentSlug)
	}
	if template.DefaultConfiguration == nil {
		return nil, tmvo.ValueErrorf("Agent template has no default configuration")
	}
	notes := "Reset to default template configuration"
	if err := instance.CustomizeConfiguration(*template.DefaultConfiguration, &notes); err != nil {
		return nil, err
	}
	instance.IsCustomized = false
	return f.instanceRepo.Save(ctx, instance)
}

// ShareAgent makes the owner's instance public and returns the share token.
func (f *AgentManagementFacade) ShareAgent(ctx context.Context, userID *amvo.UserId, instanceID string) (*string, error) {
	instanceUUID, err := amvo.NewUserAgentInstanceId(instanceID)
	if err != nil {
		return nil, err
	}
	shareToken, ok, err := f.sharingService.GenerateShareToken(ctx, instanceUUID, *userID)
	if err != nil {
		return nil, err
	}
	if !ok || shareToken == "" {
		return nil, tmvo.ValueErrorf("Failed to share instance %s. Instance not found or unauthorized.", instanceID)
	}
	return &shareToken, nil
}

// UnshareAgent revokes the share token and makes the instance private again.
func (f *AgentManagementFacade) UnshareAgent(ctx context.Context, userID *amvo.UserId, instanceID string) (bool, error) {
	instanceUUID, err := amvo.NewUserAgentInstanceId(instanceID)
	if err != nil {
		return false, err
	}
	result, err := f.sharingService.RevokeShareToken(ctx, instanceUUID, *userID)
	if err != nil {
		return false, err
	}
	if !result {
		return false, tmvo.ValueErrorf("Failed to unshare instance %s. Instance not found or unauthorized.", instanceID)
	}
	return result, nil
}

// ImportAgent imports a shared agent and records the import history when a recorder is
// configured.
func (f *AgentManagementFacade) ImportAgent(ctx context.Context, shareToken string, importerUserID *amvo.UserId, creatorEmail *string) (*amentities.UserAgentInstance, error) {
	sourceInstance, err := f.instanceRepo.FindByShareToken(ctx, shareToken)
	if err != nil {
		return nil, err
	}
	importedInstance, err := f.sharingService.ImportAgent(ctx, shareToken, *importerUserID, creatorEmail)
	if err != nil {
		return nil, err
	}
	if importedInstance == nil {
		return nil, tmvo.ValueErrorf("Failed to import agent. Invalid token, instance not public, or user already has this template.")
	}
	if sourceInstance != nil && f.HistoryRecorder != nil {
		if err := f.HistoryRecorder.RecordAgentImportHistory(ctx, importerUserID.Value, sourceInstance.ID.String(), importedInstance.ID.String(), shareToken); err != nil {
			return nil, err
		}
	}
	return importedInstance, nil
}

// GetMarketplaceAgents returns the public instances, ordered by the domain service.
func (f *AgentManagementFacade) GetMarketplaceAgents(ctx context.Context, limit, offset int, orderBy enums.InstanceOrdering) ([]*amentities.UserAgentInstance, error) {
	return f.sharingService.GetPublicInstances(ctx, limit, offset, orderBy)
}

// GetSharedAgentPreview returns the public instance for the token, or nil.
func (f *AgentManagementFacade) GetSharedAgentPreview(ctx context.Context, shareToken string) (*amentities.UserAgentInstance, error) {
	if shareToken == "" || utf8.RuneCountInString(shareToken) != 64 {
		return nil, tmvo.ValueErrorf("Invalid share token")
	}
	instance, err := f.instanceRepo.FindByShareToken(ctx, shareToken)
	if err != nil {
		return nil, err
	}
	if instance == nil || !instance.IsPublic() {
		return nil, nil
	}
	return instance, nil
}

// facadeStringList is Python list[tuple[str, ...]] -> JSON array.
func facadeStringList(items []string) []any {
	out := make([]any, len(items))
	for i, s := range items {
		out[i] = s
	}
	return out
}

func facadeIsoOrNil(t *time.Time) any {
	if t == nil {
		return nil
	}
	return tmvo.IsoFormat(*t)
}

func facadeAnyOrNil(m *tmentities.OrderedMap[any]) any {
	if m == nil {
		return nil
	}
	return m
}

// facadeAnyTruthy is Python any([...]) over the optional config arguments.
func facadeAnyTruthy(values ...any) bool {
	for _, v := range values {
		if facadeTruthy(v) {
			return true
		}
	}
	return false
}

func facadeTruthy(v any) bool {
	switch x := v.(type) {
	case nil:
		return false
	case *string:
		return x != nil && tmvo.PyTruthy(*x)
	case *bool:
		return x != nil && *x
	case *[]string:
		return x != nil && len(*x) > 0
	case *tmentities.OrderedMap[any]:
		return x != nil && x.Len() > 0
	}
	return tmvo.PyTruthy(v)
}
