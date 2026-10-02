package repositories

// ORM Agent Repository (Python infrastructure/repositories/orm/agent_repository.py):
// agent persistence over database/sql + pgx. The EventPublishingMixin side effects and
// logging are dropped. The Python class inherits its CRUD methods from BaseORMRepository,
// which does NOT apply user isolation, so the unscoped ORMRepository methods are used here;
// only set_user_id / apply_user_filter are user-scoped.

import (
	"context"
	"encoding/json"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/entities/base"
	"agenthub/fastmcp/task_management/domain/exceptions"
	domainrepos "agenthub/fastmcp/task_management/domain/repositories"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// ORMAgentRepository is Python's ORMAgentRepository.
type ORMAgentRepository struct {
	*UserScopedORMRepository[database.Agent]
	EventPublishingMixin

	// ProjectID is the project context passed to the constructor (may be nil).
	ProjectID *string
}

// Assert the domain interface is implemented.
var _ domainrepos.AgentRepository = (*ORMAgentRepository)(nil)

// agentRepoUUIDPattern is the UUID regex used by the auto-registration fallback name.
var agentRepoUUIDPattern = regexp.MustCompile(`(?i)^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$`)

// NewORMAgentRepository builds the repository for the agents table. userID nil means
// system mode; non-UUID user ids become uuid5(NAMESPACE_DNS, user_id) like Python.
func NewORMAgentRepository(sessions *database.SessionManager, userID *string, projectID *string) (*ORMAgentRepository, error) {
	normalized := userID
	if userID != nil {
		v := *userID
		if _, ok := tmvo.PyParseUUID(v); !ok {
			v = database.Uuid5(database.UserIDNamespace, v)
		}
		normalized = &v
	}
	baseRepo, err := NewUserScopedORMRepository[database.Agent]("agents", sessions, normalized)
	if err != nil {
		return nil, err
	}
	return &ORMAgentRepository{
		UserScopedORMRepository: baseRepo,
		EventPublishingMixin:    NewEventPublishingMixin(),
		ProjectID:               projectID,
	}, nil
}

// WithUser returns a new instance scoped to userID (with_user).
func (r *ORMAgentRepository) WithUser(userID string) (*ORMAgentRepository, error) {
	return NewORMAgentRepository(r.Sessions, &userID, r.ProjectID)
}

// ---- normalisation helpers ------------------------------------------------------

// agentRepoCapability maps a capability string to its enum member (invalid -> false).
func agentRepoCapability(s string) (entities.AgentCapability, bool) {
	for _, c := range entities.AgentCapabilityValues {
		if string(c) == s {
			return c, true
		}
	}
	return "", false
}

// agentRepoStatus maps a status string to its enum member (invalid -> false).
func agentRepoStatus(s string) (entities.AgentStatus, bool) {
	switch entities.AgentStatus(s) {
	case entities.AgentStatusAvailable, entities.AgentStatusBusy, entities.AgentStatusOffline, entities.AgentStatusPaused:
		return entities.AgentStatus(s), true
	}
	return "", false
}

// agentRepoDecodeJSON decodes a JSON column; nil/empty or malformed yields nil.
func agentRepoDecodeJSON(raw json.RawMessage) any {
	if len(raw) == 0 {
		return nil
	}
	decoded, err := entities.DecodeJSON(raw)
	if err != nil {
		return nil
	}
	return decoded
}

// agentRepoMetadataMap is `agent.model_metadata or {}`.
func agentRepoMetadataMap(raw json.RawMessage) *entities.OrderedMap[any] {
	if m, ok := agentRepoDecodeJSON(raw).(*entities.OrderedMap[any]); ok {
		return m
	}
	return entities.NewOrderedMap[any]()
}

// agentRepoMetadataValue is metadata.get(key, default).
func agentRepoMetadataValue(metadata *entities.OrderedMap[any], key string, def any) any {
	if metadata == nil {
		return def
	}
	if v, ok := metadata.Get(key); ok {
		return v
	}
	return def
}

// agentRepoStringSet normalises assigned_trees data to a set of strings.
func agentRepoStringSet(raw any) map[string]struct{} {
	out := map[string]struct{}{}
	switch v := raw.(type) {
	case nil:
		return out
	case string:
		out[v] = struct{}{}
	case []any:
		for _, item := range v {
			out[agentRepoToString(item)] = struct{}{}
		}
	case []string:
		for _, item := range v {
			out[item] = struct{}{}
		}
	case *entities.OrderedMap[any]:
		for _, k := range v.Keys() {
			out[k] = struct{}{}
		}
	}
	return out
}

// agentRepoStringSetIfList is `set(raw) if isinstance(raw, list) else set()`.
func agentRepoStringSetIfList(raw any) map[string]struct{} {
	out := map[string]struct{}{}
	switch v := raw.(type) {
	case []any:
		for _, item := range v {
			out[agentRepoToString(item)] = struct{}{}
		}
	case []string:
		for _, item := range v {
			out[item] = struct{}{}
		}
	}
	return out
}

// agentRepoStringList normalises assigned_trees data to a list of strings.
func agentRepoStringList(raw any) []string {
	out := []string{}
	switch v := raw.(type) {
	case nil:
		return out
	case string:
		return []string{v}
	case []any:
		for _, item := range v {
			out = append(out, agentRepoToString(item))
		}
		return out
	case []string:
		return append(out, v...)
	case *entities.OrderedMap[any]:
		return append(out, v.Keys()...)
	}
	return out
}

func agentRepoToString(v any) string {
	if s, ok := v.(string); ok {
		return s
	}
	return tmvo.PyStr(v)
}

func agentRepoSortedKeys(m map[string]struct{}) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	// Python set iteration order is unspecified; a stable order keeps Go output deterministic.
	sort.Strings(out)
	return out
}

func agentRepoFirstSorted(m map[string]struct{}) (string, bool) {
	if len(m) == 0 {
		return "", false
	}
	return agentRepoSortedKeys(m)[0], true
}

// agentRepoOrderedToMap converts a Python-dict result to the map[string]any the domain
// interface requires (the nested values keep their ObservableMap order).
func agentRepoOrderedToMap(m *entities.OrderedMap[any]) map[string]any {
	out := map[string]any{}
	if m == nil {
		return out
	}
	for _, k := range m.Keys() {
		v, _ := m.Get(k)
		out[k] = v
	}
	return out
}

// ---- domain <-> row conversion --------------------------------------------------

// agentRepoModelToEntity is _model_to_entity.
func (r *ORMAgentRepository) agentRepoModelToEntity(row *database.Agent) (*entities.Agent, error) {
	entity, err := r.agentRepoModelToEntityInner(row)
	if err != nil {
		return nil, exceptions.NewDatabaseException(
			"Failed to convert agent model to entity: "+err.Error(), "model_to_entity", "agents")
	}
	return entity, nil
}

func (r *ORMAgentRepository) agentRepoModelToEntityInner(row *database.Agent) (*entities.Agent, error) {
	id, err := tmvo.NewAgentId(row.ID)
	if err != nil {
		return nil, err
	}
	capabilities := map[entities.AgentCapability]struct{}{}
	if list, ok := agentRepoDecodeJSON(row.Capabilities).([]any); ok {
		for _, item := range list {
			s, ok := item.(string)
			if !ok {
				continue
			}
			if c, ok := agentRepoCapability(s); ok {
				capabilities[c] = struct{}{}
			}
		}
	}
	status := entities.AgentStatusAvailable
	if row.Status != "" {
		if s, ok := agentRepoStatus(row.Status); ok {
			status = s
		}
	}
	metadata := agentRepoMetadataMap(row.Metadata)
	assignedTrees := agentRepoStringSet(agentRepoMetadataValue(metadata, "assigned_trees", []any{}))
	assignedProjects := agentRepoStringSetIfList(agentRepoMetadataValue(metadata, "assigned_projects", []any{}))
	activeTasks := agentRepoStringSetIfList(agentRepoMetadataValue(metadata, "active_tasks", []any{}))

	one := 1
	success := 100.0
	created, updated := row.CreatedAt, row.UpdatedAt
	return entities.NewAgent(entities.Agent{
		ID:                  &id,
		Name:                row.Name,
		Description:         row.Description,
		Capabilities:        capabilities,
		Specializations:     []string{},
		PreferredLanguages:  []string{},
		PreferredFrameworks: []string{},
		Status:              status,
		MaxConcurrentTasks:  &one,
		CurrentWorkload:     0,
		WorkHours:           nil,
		Timezone:            "UTC",
		PriorityPreference:  "medium",
		CompletedTasks:      0,
		AverageTaskDuration: nil,
		SuccessRate:         &success,
		AssignedProjects:    assignedProjects,
		AssignedTrees:       assignedTrees,
		ActiveTasks:         activeTasks,
		BaseTimestampEntity: base.BaseTimestampEntity{CreatedAt: &created, UpdatedAt: &updated},
	})
}

// agentRepoEntityToModelDict is _entity_to_model_dict.
func (r *ORMAgentRepository) agentRepoEntityToModelDict(agent *entities.Agent) Kwargs {
	id := ""
	if agent.ID != nil {
		id = agent.ID.String()
	}
	capabilities := []string{}
	for _, c := range entities.AgentCapabilityValues {
		if _, ok := agent.Capabilities[c]; ok {
			capabilities = append(capabilities, string(c))
		}
	}
	availability := 0.0
	if agent.IsAvailable() {
		availability = 1.0
	}
	var lastActive any
	if agent.Status == entities.AgentStatusAvailable {
		lastActive = time.Now().UTC()
	}
	var workHours any
	if agent.WorkHours != nil {
		workHours = agent.WorkHours
	}
	var averageDuration any
	if agent.AverageTaskDuration != nil {
		averageDuration = *agent.AverageTaskDuration
	}
	metadata := entities.NewOrderedMap[any]()
	metadata.Set("specializations", agent.Specializations)
	metadata.Set("preferred_languages", agent.PreferredLanguages)
	metadata.Set("preferred_frameworks", agent.PreferredFrameworks)
	metadata.Set("max_concurrent_tasks", *agent.MaxConcurrentTasks)
	metadata.Set("current_workload", agent.CurrentWorkload)
	metadata.Set("work_hours", workHours)
	metadata.Set("timezone", agent.Timezone)
	metadata.Set("priority_preference", agent.PriorityPreference)
	metadata.Set("completed_tasks", agent.CompletedTasks)
	metadata.Set("average_task_duration", averageDuration)
	metadata.Set("success_rate", *agent.SuccessRate)
	metadata.Set("assigned_projects", agentRepoSortedKeys(agent.AssignedProjects))
	metadata.Set("assigned_trees", agentRepoSortedKeys(agent.AssignedTrees))
	metadata.Set("active_tasks", agentRepoSortedKeys(agent.ActiveTasks))
	return NewKwargs(
		"id", id,
		"name", agent.Name,
		"description", agent.Description,
		"capabilities", capabilities,
		"status", string(agent.Status),
		"availability_score", availability,
		"last_active_at", lastActive,
		"created_at", agent.CreatedAt,
		"updated_at", agent.UpdatedAt,
		"model_metadata", metadata,
	)
}

// agentRepoAgentData builds the per-agent dict shared by get_agent / list_agents.
func agentRepoAgentData(row *database.Agent, includeMetadata bool) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	out.Set("id", row.ID)
	out.Set("name", row.Name)
	out.Set("description", row.Description)
	out.Set("capabilities", agentRepoDecodedList(row.Capabilities))
	out.Set("status", row.Status)
	out.Set("availability_score", row.AvailabilityScore)
	if includeMetadata {
		out.Set("model_metadata", agentRepoMetadataMap(row.Metadata))
	}
	out.Set("assignments", agentRepoAssignmentsList(row))
	out.Set("created_at", tmvo.IsoFormatNaive(row.CreatedAt))
	out.Set("updated_at", tmvo.IsoFormatNaive(row.UpdatedAt))
	return out
}

// agentRepoDecodedList is `agent.capabilities or []`.
func agentRepoDecodedList(raw json.RawMessage) []any {
	if list, ok := agentRepoDecodeJSON(raw).([]any); ok {
		return list
	}
	return []any{}
}

// agentRepoAssignmentsList is _normalize_assigned_trees_to_list(metadata.get(...)).
func agentRepoAssignmentsList(row *database.Agent) []string {
	return agentRepoStringList(agentRepoMetadataValue(agentRepoMetadataMap(row.Metadata), "assigned_trees", []any{}))
}

// ---- interface methods ----------------------------------------------------------

// RegisterAgent registers a new agent (register_agent).
func (r *ORMAgentRepository) RegisterAgent(ctx context.Context, agent *entities.Agent) (*entities.Agent, error) {
	projectID, _ := agentRepoFirstSorted(agent.AssignedProjects)

	id := ""
	if agent.ID != nil {
		id = agent.ID.String()
	}

	exists, err := r.ORMRepository.Exists(ctx, NewKwargs("id", id))
	if err != nil {
		return nil, r.agentRepoRegisterError(err, projectID)
	}
	if exists {
		existing, err := r.ORMRepository.GetByID(ctx, id)
		if err != nil {
			return nil, r.agentRepoRegisterError(err, projectID)
		}
		if existing != nil {
			return nil, exceptions.NewValidationException(
				"Agent with ID '"+id+"' already exists. "+
					"Existing agent name: '"+existing.Name+"'. "+
					"Use 'manage_agent' with action='get' to view details, "+
					"or action='update' to modify the existing agent.",
				"id", id)
		}
		return nil, exceptions.NewValidationException(
			"Agent with ID '"+id+"' already exists. Use the existing agent or choose a different ID.",
			"id", id)
	}

	existingByName, err := r.FindByName(ctx, agent.Name)
	if err != nil {
		return nil, r.agentRepoRegisterError(err, projectID)
	}
	if existingByName != nil && existingByName.ID != id {
		return nil, exceptions.NewValidationException(
			"An agent with name '"+agent.Name+"' already exists (ID: "+existingByName.ID+"). "+
				"Consider using the existing agent or choosing a different name.",
			"name", agent.Name)
	}

	modelDict := r.agentRepoEntityToModelDict(agent)
	if agent.Description != "" {
		if metadata, ok := modelDict.Get("model_metadata"); ok {
			if m, ok := metadata.(*entities.OrderedMap[any]); ok {
				m.Set("call_agent", agent.Description)
			}
		}
	}
	modelDict, err = r.SetUserID(modelDict)
	if err != nil {
		return nil, r.agentRepoRegisterError(err, projectID)
	}
	row, err := r.ORMRepository.Create(ctx, modelDict)
	if err != nil {
		lower := strings.ToLower(err.Error())
		if strings.Contains(lower, "unique constraint") || strings.Contains(lower, "duplicate key") ||
			strings.Contains(lower, "already exists") {
			return nil, exceptions.NewValidationException(
				"Agent '"+agent.Name+"' (ID: "+id+") could not be created due to a duplicate key. "+
					"Another process may have created it simultaneously. Please try again or use the existing agent.",
				"id", id)
		}
		return nil, r.agentRepoRegisterError(err, projectID)
	}
	entity, err := r.agentRepoModelToEntity(row)
	if err != nil {
		return nil, r.agentRepoRegisterError(err, projectID)
	}
	r.PublishEntityEvents(entity)
	return entity, nil
}

// agentRepoRegisterError mirrors register_agent's outer except clause.
func (r *ORMAgentRepository) agentRepoRegisterError(err error, projectID string) error {
	message := "Failed to register agent: " + err.Error()
	if strings.Contains(strings.ToLower(err.Error()), "foreign key") {
		message = "Failed to register agent: Project '" + projectID + "' does not exist"
	}
	return exceptions.NewDatabaseException(message, "register_agent", "agents")
}

// UnregisterAgent removes an agent (unregister_agent).
func (r *ORMAgentRepository) UnregisterAgent(ctx context.Context, projectID, agentID string) (map[string]any, error) {
	row, err := r.ORMRepository.GetByID(ctx, agentID)
	if err != nil {
		return nil, exceptions.NewDatabaseException("Failed to unregister agent: "+err.Error(), "unregister_agent", "agents")
	}
	if row == nil {
		return nil, exceptions.NewResourceNotFoundException("agent", agentID, "Agent "+agentID+" not found")
	}
	agentData := entities.NewOrderedMap[any]()
	agentData.Set("id", row.ID)
	agentData.Set("name", row.Name)
	agentData.Set("description", row.Description)
	agentData.Set("capabilities", agentRepoDecodedList(row.Capabilities))
	agentData.Set("status", row.Status)
	agentData.Set("model_metadata", agentRepoMetadataMap(row.Metadata))

	deleted, err := r.ORMRepository.Delete(ctx, agentID)
	if err != nil {
		return nil, exceptions.NewDatabaseException("Failed to unregister agent: "+err.Error(), "unregister_agent", "agents")
	}
	if !deleted {
		return nil, exceptions.NewDatabaseException("Failed to delete agent "+agentID, "unregister_agent", "agents")
	}
	return map[string]any{
		"agent_data":          agentData,
		"removed_assignments": []string{},
	}, nil
}

// AssignAgentToTree assigns an agent to a task tree, auto-registering it (assign_agent_to_tree).
func (r *ORMAgentRepository) AssignAgentToTree(ctx context.Context, projectID, agentID, gitBranchID string) (map[string]any, error) {
	actualAgentID := agentID
	var agentName *string
	if strings.Contains(agentID, ":") {
		parts := strings.SplitN(agentID, ":", 2)
		actualAgentID = parts[0]
		name := parts[1]
		agentName = &name
	}

	row, err := r.ORMRepository.GetByID(ctx, actualAgentID)
	if err != nil {
		return nil, exceptions.NewDatabaseException("Failed to assign agent to tree: "+err.Error(), "assign_agent_to_tree", "agents")
	}
	autoRegistered := false
	if row == nil {
		row, autoRegistered, err = r.agentRepoAutoRegister(ctx, projectID, actualAgentID, agentName)
		if err != nil {
			if _, ok := err.(*exceptions.ResourceNotFoundException); ok {
				return nil, err
			}
			return nil, exceptions.NewDatabaseException("Failed to assign agent to tree: "+err.Error(), "assign_agent_to_tree", "agents")
		}
	}

	entity, err := r.agentRepoModelToEntity(row)
	if err != nil {
		return nil, exceptions.NewDatabaseException("Failed to assign agent to tree: "+err.Error(), "assign_agent_to_tree", "agents")
	}
	if _, ok := entity.AssignedTrees[gitBranchID]; ok {
		return map[string]any{
			"success":         true,
			"message":         "Agent " + actualAgentID + " already assigned to tree " + gitBranchID,
			"auto_registered": autoRegistered,
		}, nil
	}
	if err := entity.AssignToTree(gitBranchID); err != nil {
		return nil, exceptions.NewDatabaseException("Failed to assign agent to tree: "+err.Error(), "assign_agent_to_tree", "agents")
	}
	modelDict := r.agentRepoEntityToModelDict(entity)
	metadata, _ := modelDict.Get("model_metadata")
	if _, err := r.ORMRepository.Update(ctx, actualAgentID, NewKwargs(
		"model_metadata", metadata,
		"updated_at", entity.UpdatedAt,
	)); err != nil {
		return nil, exceptions.NewDatabaseException("Failed to assign agent to tree: "+err.Error(), "assign_agent_to_tree", "agents")
	}
	r.PublishEntityEvents(entity)
	return map[string]any{
		"success":         true,
		"message":         "Agent " + actualAgentID + " assigned to tree " + gitBranchID,
		"auto_registered": autoRegistered,
	}, nil
}

// agentRepoAutoRegister mirrors the auto-registration branch of assign_agent_to_tree. Every
// failure surfaces as ResourceNotFoundException with the "auto-registration failed" text,
// because Python's outer except catches (and re-wraps) the inner ones too.
func (r *ORMAgentRepository) agentRepoAutoRegister(ctx context.Context, projectID, actualAgentID string, agentName *string) (*database.Agent, bool, error) {
	fail := func(inner error) (*database.Agent, bool, error) {
		return nil, false, exceptions.NewResourceNotFoundException("agent", actualAgentID,
			"Agent "+actualAgentID+" not found and auto-registration failed: "+inner.Error())
	}

	exists, err := r.ORMRepository.Exists(ctx, NewKwargs("id", actualAgentID))
	if err != nil {
		return fail(err)
	}
	if exists {
		row, err := r.ORMRepository.GetByID(ctx, actualAgentID)
		if err != nil {
			return fail(err)
		}
		if row != nil {
			return row, false, nil
		}
		return fail(exceptions.NewResourceNotFoundException("agent", actualAgentID,
			"Agent "+actualAgentID+" exists but couldn't be retrieved"))
	}

	name := ""
	if agentName != nil {
		name = *agentName
	} else if agentRepoUUIDPattern.MatchString(actualAgentID) {
		name = "agent_" + actualAgentID[:8]
	} else {
		name = strings.TrimLeft(actualAgentID, "@")
	}

	id := tmvo.AgentId{EntityId: tmvo.EntityId{Value: actualAgentID}}
	entity, err := entities.NewAgent(entities.Agent{
		ID:          &id,
		Name:        name,
		Description: "Auto-registered agent " + name + " for project " + projectID,
	})
	if err != nil {
		return fail(err)
	}
	modelDict := r.agentRepoEntityToModelDict(entity)
	if metadata, ok := modelDict.Get("model_metadata"); ok {
		if m, ok := metadata.(*entities.OrderedMap[any]); ok {
			m.Set("call_agent", "@"+name)
		}
	}
	modelDict, err = r.SetUserID(modelDict)
	if err != nil {
		return fail(err)
	}
	row, err := r.ORMRepository.Create(ctx, modelDict)
	if err != nil {
		if strings.Contains(err.Error(), "UNIQUE constraint") ||
			strings.Contains(strings.ToLower(err.Error()), "duplicate key") {
			row, err = r.ORMRepository.GetByID(ctx, actualAgentID)
			if err != nil {
				return fail(err)
			}
			if row != nil {
				return row, false, nil
			}
			return fail(exceptions.NewResourceNotFoundException("agent", actualAgentID,
				"Agent "+actualAgentID+" creation failed but agent not found"))
		}
		return fail(err)
	}
	return row, true, nil
}

// UnassignAgentFromTree unassigns an agent from tree(s) (unassign_agent_from_tree).
func (r *ORMAgentRepository) UnassignAgentFromTree(ctx context.Context, projectID, agentID string, gitBranchID *string) (map[string]any, error) {
	row, err := r.ORMRepository.GetByID(ctx, agentID)
	if err != nil {
		return nil, exceptions.NewDatabaseException("Failed to unassign agent from tree: "+err.Error(), "unassign_agent_from_tree", "agents")
	}
	if row == nil {
		return nil, exceptions.NewResourceNotFoundException("agent", agentID, "Agent "+agentID+" not found")
	}
	entity, err := r.agentRepoModelToEntity(row)
	if err != nil {
		return nil, exceptions.NewDatabaseException("Failed to unassign agent from tree: "+err.Error(), "unassign_agent_from_tree", "agents")
	}
	var removed []string
	if gitBranchID != nil {
		if _, ok := entity.AssignedTrees[*gitBranchID]; ok {
			if err := entity.UnassignFromTree(*gitBranchID); err != nil {
				return nil, exceptions.NewDatabaseException("Failed to unassign agent from tree: "+err.Error(), "unassign_agent_from_tree", "agents")
			}
			removed = []string{*gitBranchID}
		} else {
			removed = []string{}
		}
	} else {
		removed = agentRepoSortedKeys(entity.AssignedTrees)
		if err := entity.UnassignFromAllTrees(); err != nil {
			return nil, exceptions.NewDatabaseException("Failed to unassign agent from tree: "+err.Error(), "unassign_agent_from_tree", "agents")
		}
	}
	modelDict := r.agentRepoEntityToModelDict(entity)
	metadata, _ := modelDict.Get("model_metadata")
	if _, err := r.ORMRepository.Update(ctx, agentID, NewKwargs(
		"model_metadata", metadata,
		"updated_at", entity.UpdatedAt,
	)); err != nil {
		return nil, exceptions.NewDatabaseException("Failed to unassign agent from tree: "+err.Error(), "unassign_agent_from_tree", "agents")
	}
	return map[string]any{
		"removed_assignments":   removed,
		"remaining_assignments": agentRepoSortedKeys(entity.AssignedTrees),
	}, nil
}

// GetAgent returns the agent details dict (get_agent).
func (r *ORMAgentRepository) GetAgent(ctx context.Context, projectID, agentID string) (map[string]any, error) {
	row, err := r.ORMRepository.GetByID(ctx, agentID)
	if err != nil {
		return nil, exceptions.NewDatabaseException("Failed to get agent: "+err.Error(), "get_agent", "agents")
	}
	if row == nil {
		return nil, exceptions.NewResourceNotFoundException("agent", agentID, "Agent "+agentID+" not found")
	}
	return agentRepoOrderedToMap(agentRepoAgentData(row, true)), nil
}

// ListAgents lists every agent (list_agents).
func (r *ORMAgentRepository) ListAgents(ctx context.Context, projectID string) (map[string]any, error) {
	rows, err := r.ORMRepository.GetAll(ctx, nil, nil)
	if err != nil {
		return nil, exceptions.NewDatabaseException("Failed to list agents: "+err.Error(), "list_agents", "agents")
	}
	agentList := make([]*entities.OrderedMap[any], 0, len(rows))
	for _, row := range rows {
		agentList = append(agentList, agentRepoAgentData(row, true))
	}
	return map[string]any{"agents": agentList, "total_agents": len(agentList)}, nil
}

// UpdateAgent updates an agent (update_agent).
func (r *ORMAgentRepository) UpdateAgent(ctx context.Context, agent *entities.Agent) (*entities.Agent, error) {
	id := ""
	if agent.ID != nil {
		id = agent.ID.String()
	}
	existing, err := r.ORMRepository.GetByID(ctx, id)
	if err != nil {
		return nil, exceptions.NewDatabaseException("Failed to update agent: "+err.Error(), "update_agent", "agents")
	}
	if existing == nil {
		return nil, exceptions.NewResourceNotFoundException("agent", id, "Agent "+id+" not found")
	}
	modelDict := r.agentRepoEntityToModelDict(agent)
	updated, err := r.ORMRepository.Update(ctx, id, modelDict)
	if err != nil {
		return nil, exceptions.NewDatabaseException("Failed to update agent: "+err.Error(), "update_agent", "agents")
	}
	if updated == nil {
		return nil, nil
	}
	entity, err := r.agentRepoModelToEntity(updated)
	if err != nil {
		return nil, exceptions.NewDatabaseException("Failed to update agent: "+err.Error(), "update_agent", "agents")
	}
	return entity, nil
}

// RebalanceAgents analyses agent assignments (rebalance_agents).
func (r *ORMAgentRepository) RebalanceAgents(ctx context.Context, projectID string) (map[string]any, error) {
	rows, err := r.ORMRepository.GetAll(ctx, nil, nil)
	if err != nil {
		return nil, exceptions.NewDatabaseException("Failed to rebalance agents: "+err.Error(), "rebalance_agents", "agents")
	}
	result := entities.NewOrderedMap[any]()
	if len(rows) == 0 {
		result.Set("changes_made", false)
		result.Set("message", "No agents found in project")
		return map[string]any{"rebalance_result": result}, nil
	}
	changes := []string{}
	for _, row := range rows {
		assignments := agentRepoAssignmentsList(row)
		if len(assignments) > 0 {
			changes = append(changes, "Agent '"+row.Name+"' has "+strconv.Itoa(len(assignments))+" assignments")
		}
	}
	result.Set("changes_made", len(changes) > 0)
	result.Set("changes", changes)
	result.Set("message", "Analyzed "+strconv.Itoa(len(rows))+" agents")
	return map[string]any{"rebalance_result": result}, nil
}

// GetAvailableAgents returns the agents with available status (get_available_agents).
func (r *ORMAgentRepository) GetAvailableAgents(ctx context.Context) ([]*entities.OrderedMap[any], error) {
	rows, err := r.ORMRepository.FindBy(ctx, NewKwargs("status", string(entities.AgentStatusAvailable)))
	if err != nil {
		return nil, exceptions.NewDatabaseException("Failed to get available agents: "+err.Error(), "get_available_agents", "agents")
	}
	out := make([]*entities.OrderedMap[any], 0, len(rows))
	for _, row := range rows {
		out = append(out, agentRepoAgentData(row, false))
	}
	return out, nil
}

// FindByName finds an agent by name, with or without @ prefix (find_by_name). Errors are
// swallowed like the Python except clause.
func (r *ORMAgentRepository) FindByName(ctx context.Context, name string) (*database.Agent, error) {
	cleanName := strings.TrimLeft(name, "@")
	row, err := r.ORMRepository.FindOneBy(ctx, NewKwargs("name", cleanName))
	if err == nil && row != nil {
		return row, nil
	}
	row, err = r.ORMRepository.FindOneBy(ctx, NewKwargs("name", "@"+cleanName))
	if err != nil {
		return nil, nil
	}
	return row, nil
}

// SearchAgents searches agents by name within the user's scope (search_agents).
func (r *ORMAgentRepository) SearchAgents(ctx context.Context, projectID, query string) ([]*entities.OrderedMap[any], error) {
	var out []*entities.OrderedMap[any]
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		pattern := "%" + query + "%"
		q := "SELECT " + r.ORMRepository.selectList() + " FROM " + quoteIdent(r.Table.Name) +
			" WHERE " + quoteIdent("name") + " ILIKE $1"
		args := []any{pattern}
		if r.UserID != nil {
			args = append(args, *r.UserID)
			q += " AND " + quoteIdent("user_id") + " = $2"
		}
		rows, err := s.QueryContext(ctx, q, args...)
		if err != nil {
			return err
		}
		defer rows.Close()
		for rows.Next() {
			row := r.ORMRepository.newRow()
			if err := rows.Scan(r.ORMRepository.scanDest(row)...); err != nil {
				return err
			}
			out = append(out, agentRepoAgentData(row, false))
		}
		return rows.Err()
	})
	if err != nil {
		return nil, exceptions.NewDatabaseException("Failed to search agents: "+err.Error(), "search_agents", "agents")
	}
	return out, nil
}
