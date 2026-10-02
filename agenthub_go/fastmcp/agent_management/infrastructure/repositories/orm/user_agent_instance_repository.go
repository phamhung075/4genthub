// ORM User Agent Instance Repository (Python
// agent_management/infrastructure/repositories/orm/user_agent_instance_repository.py):
// per-user agent instance CRUD, sharing and marketplace queries. find_* / exists / delete
// swallow errors and return the Python default; save re-raises.

package orm

import (
	"context"
	"fmt"
	"time"

	"agenthub/fastmcp/agent_management/domain/entities"
	"agenthub/fastmcp/agent_management/domain/enums"
	domainrepo "agenthub/fastmcp/agent_management/domain/repositories"
	amvo "agenthub/fastmcp/agent_management/domain/value_objects"
	db "agenthub/fastmcp/agent_management/infrastructure/database"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
	baserepo "agenthub/fastmcp/task_management/infrastructure/repositories"
)

// userAgentInstanceRepoSelect lists user_agent_instances' columns (uuid cast to text).
const userAgentInstanceRepoSelect = `"id"::text, "user_id"::text, "template_id"::text, "agent_name", ` +
	`"is_customized", "is_enabled", "customization_notes", "system_prompt", "tools", "capabilities", ` +
	`"rules", "output_format", "metadata", "visibility", "share_token", "share_created_at", ` +
	`"original_creator_id"::text, "imported_at", "created_at", "updated_at", "last_used_at", "usage_count"`

// ORMUserAgentInstanceRepository is Python's ORMUserAgentInstanceRepository.
type ORMUserAgentInstanceRepository struct {
	*baserepo.ORMRepository[db.UserAgentInstanceORM]
}

var _ domainrepo.UserAgentInstanceRepository = (*ORMUserAgentInstanceRepository)(nil)

// NewORMUserAgentInstanceRepository builds the repository over user_agent_instances.
func NewORMUserAgentInstanceRepository(sessions *database.SessionManager) (*ORMUserAgentInstanceRepository, error) {
	base, err := baserepo.NewORMRepository[db.UserAgentInstanceORM]("user_agent_instances", sessions)
	if err != nil {
		return nil, err
	}
	return &ORMUserAgentInstanceRepository{ORMRepository: base}, nil
}

// userAgentInstanceUUID passes a uuid column value as an untyped nil or a plain string.
func userAgentInstanceUUID(p *string) any {
	if p == nil {
		return nil
	}
	return *p
}

// userAgentInstanceSafeJSON is safe_json_parse(value, default).
func userAgentInstanceSafeJSON(value *string, def any) (any, error) {
	if value == nil || tmvo.PyStrip(*value) == "" {
		return def, nil
	}
	return tmentities.DecodeJSON([]byte(*value))
}

// userAgentInstanceModelToEntity is _model_to_entity.
func userAgentInstanceModelToEntity(row *db.UserAgentInstanceORM) (*entities.UserAgentInstance, error) {
	tools, err := userAgentInstanceSafeJSON(&row.Tools, []any{})
	if err != nil {
		return nil, err
	}
	capabilities, err := userAgentInstanceSafeJSON(&row.Capabilities, tmentities.NewOrderedMap[any]())
	if err != nil {
		return nil, err
	}
	rules, err := userAgentInstanceSafeJSON(row.Rules, nil)
	if err != nil {
		return nil, err
	}
	outputFormat, err := userAgentInstanceSafeJSON(row.OutputFormat, nil)
	if err != nil {
		return nil, err
	}
	metadata, err := userAgentInstanceSafeJSON(row.MetadataJSON, tmentities.NewOrderedMap[any]())
	if err != nil {
		return nil, err
	}
	cfgDict := tmentities.NewOrderedMap[any]()
	cfgDict.Set("system_prompt", row.SystemPrompt)
	cfgDict.Set("tools", tools)
	cfgDict.Set("capabilities", capabilities)
	if rules != nil {
		// Python passes rules=None to the constructor; the Go value object holds no None, so it is left unset (empty)
		cfgDict.Set("rules", rules)
	}
	cfgDict.Set("output_format", outputFormat)
	cfgDict.Set("metadata", metadata)
	cfg, err := amvo.AgentConfigurationFromDict(cfgDict)
	if err != nil {
		return nil, err
	}
	id, err := amvo.NewUserAgentInstanceId(row.ID)
	if err != nil {
		return nil, err
	}
	userID, err := amvo.NewUserId(row.UserID)
	if err != nil {
		return nil, err
	}
	templateID, err := amvo.NewAgentTemplateId(row.TemplateID)
	if err != nil {
		return nil, err
	}
	var originalCreatorID *amvo.UserId
	if row.OriginalCreatorID != nil && *row.OriginalCreatorID != "" {
		oc, err := amvo.NewUserId(*row.OriginalCreatorID)
		if err != nil {
			return nil, err
		}
		originalCreatorID = &oc
	}
	u := entities.DefaultUserAgentInstance()
	u.ID, u.UserID, u.TemplateID = &id, &userID, &templateID
	u.AgentName = row.AgentName
	u.IsCustomized = row.IsCustomized
	u.IsEnabled = row.IsEnabled
	u.Configuration = &cfg
	u.Visibility = row.Visibility
	u.ShareToken = row.ShareToken
	u.OriginalCreatorID = originalCreatorID
	u.UsageCount = int(row.UsageCount)
	u.LastUsedAt = row.LastUsedAt
	c, up := row.CreatedAt, row.UpdatedAt
	u.CreatedAt, u.UpdatedAt = &c, &up
	return entities.NewUserAgentInstance(u)
}

// userAgentInstanceModelDict is _entity_to_model_dict.
type userAgentInstanceModelDict struct {
	ID                 string
	UserID             string
	TemplateID         string
	AgentName          string
	IsCustomized       bool
	IsEnabled          bool
	CustomizationNotes *string
	SystemPrompt       string
	Tools              string
	Capabilities       string
	Rules              *string
	OutputFormat       *string
	MetadataJSON       *string
	Visibility         string
	ShareToken         *string
	ShareCreatedAt     *time.Time
	OriginalCreatorID  *string
	ImportedAt         *time.Time
	UsageCount         int
	LastUsedAt         *time.Time
	CreatedAt          time.Time
	UpdatedAt          time.Time
}

func userAgentInstanceToModelDict(instance *entities.UserAgentInstance) (*userAgentInstanceModelDict, error) {
	cfg := instance.Configuration
	if cfg == nil {
		return nil, tmvo.TypeErrorf("'NoneType' object has no attribute 'system_prompt'")
	}
	var customizationNotes *string
	if instance.Metadata != nil && instance.Metadata.Has("last_customization") {
		last, _ := instance.Metadata.Get("last_customization")
		m, ok := last.(*tmentities.OrderedMap[any])
		if !ok {
			return nil, tmvo.TypeErrorf("'%s' object has no attribute 'get'", tmvo.PyRepr(last))
		}
		if v, ok := m.Get("notes"); ok && v != nil {
			s, isStr := v.(string)
			if !isStr {
				return nil, tmvo.TypeErrorf("customization_notes must be a string, got %s", tmvo.PyRepr(v))
			}
			customizationNotes = &s
		}
	}
	tools, err := tmvo.PyJSONDumps(cfg.Tools, -1)
	if err != nil {
		return nil, err
	}
	capabilities, err := tmvo.PyJSONDumps(cfg.Capabilities, -1)
	if err != nil {
		return nil, err
	}
	var rules *string
	if len(cfg.Rules) > 0 {
		s, err := tmvo.PyJSONDumps(cfg.Rules, -1)
		if err != nil {
			return nil, err
		}
		rules = &s
	}
	var outputFormat *string
	if tmvo.PyTruthy(cfg.OutputFormat) {
		s, err := tmvo.PyJSONDumps(cfg.OutputFormat, -1)
		if err != nil {
			return nil, err
		}
		outputFormat = &s
	}
	var metadataJSON *string
	if tmvo.PyTruthy(cfg.Metadata) {
		s, err := tmvo.PyJSONDumps(cfg.Metadata, -1)
		if err != nil {
			return nil, err
		}
		metadataJSON = &s
	}
	id, userID, templateID := "None", "None", "None"
	if instance.ID != nil {
		id = instance.ID.String()
	}
	if instance.UserID != nil {
		userID = instance.UserID.String()
	}
	if instance.TemplateID != nil {
		templateID = instance.TemplateID.String()
	}
	var originalCreatorID *string
	if instance.OriginalCreatorID != nil {
		s := instance.OriginalCreatorID.String()
		originalCreatorID = &s
	}
	createdAt, updatedAt := time.Now().UTC(), time.Now().UTC()
	if instance.CreatedAt != nil {
		createdAt = *instance.CreatedAt
	}
	if instance.UpdatedAt != nil {
		updatedAt = *instance.UpdatedAt
	}
	return &userAgentInstanceModelDict{
		ID: id, UserID: userID, TemplateID: templateID, AgentName: instance.AgentName,
		IsCustomized: instance.IsCustomized, IsEnabled: instance.IsEnabled,
		CustomizationNotes: customizationNotes, SystemPrompt: cfg.SystemPrompt,
		Tools: tools, Capabilities: capabilities, Rules: rules, OutputFormat: outputFormat,
		MetadataJSON: metadataJSON, Visibility: instance.Visibility, ShareToken: instance.ShareToken,
		ShareCreatedAt: nil, OriginalCreatorID: originalCreatorID, ImportedAt: nil,
		UsageCount: instance.UsageCount, LastUsedAt: instance.LastUsedAt,
		CreatedAt: createdAt, UpdatedAt: updatedAt,
	}, nil
}

// Save is save.
func (r *ORMUserAgentInstanceRepository) Save(ctx context.Context, instance *entities.UserAgentInstance) (*entities.UserAgentInstance, error) {
	model, err := userAgentInstanceToModelDict(instance)
	if err != nil {
		return nil, err
	}
	var out *entities.UserAgentInstance
	err = r.Transaction(ctx, func(ctx context.Context) error {
		existing, err := r.ORMRepository.GetByID(ctx, model.ID)
		if err != nil {
			return err
		}
		var row *db.UserAgentInstanceORM
		if existing != nil {
			row, err = r.ORMRepository.Update(ctx, model.ID, baserepo.NewKwargs(
				"agent_name", model.AgentName,
				"is_customized", model.IsCustomized,
				"is_enabled", model.IsEnabled,
				"customization_notes", model.CustomizationNotes,
				"system_prompt", model.SystemPrompt,
				"tools", model.Tools,
				"capabilities", model.Capabilities,
				"rules", model.Rules,
				"output_format", model.OutputFormat,
				"metadata_json", model.MetadataJSON,
				"visibility", model.Visibility,
				"share_token", model.ShareToken,
				"share_created_at", model.ShareCreatedAt,
				"usage_count", model.UsageCount,
				"last_used_at", model.LastUsedAt,
				"updated_at", time.Now().UTC(),
			))
		} else {
			row, err = r.ORMRepository.Create(ctx, baserepo.NewKwargs(
				"id", model.ID,
				"user_id", model.UserID,
				"template_id", model.TemplateID,
				"agent_name", model.AgentName,
				"is_customized", model.IsCustomized,
				"is_enabled", model.IsEnabled,
				"customization_notes", model.CustomizationNotes,
				"system_prompt", model.SystemPrompt,
				"tools", model.Tools,
				"capabilities", model.Capabilities,
				"rules", model.Rules,
				"output_format", model.OutputFormat,
				"metadata_json", model.MetadataJSON,
				"visibility", model.Visibility,
				"share_token", model.ShareToken,
				"share_created_at", model.ShareCreatedAt,
				"original_creator_id", userAgentInstanceUUID(model.OriginalCreatorID),
				"imported_at", model.ImportedAt,
				"usage_count", model.UsageCount,
				"last_used_at", model.LastUsedAt,
				"created_at", model.CreatedAt,
				"updated_at", model.UpdatedAt,
			))
		}
		if err != nil {
			return err
		}
		out, err = userAgentInstanceModelToEntity(row)
		return err
	})
	return out, err
}

// FindByID is find_by_id; errors and conversion failures return nil.
func (r *ORMUserAgentInstanceRepository) FindByID(ctx context.Context, instanceID amvo.UserAgentInstanceId) (*entities.UserAgentInstance, error) {
	row, err := r.ORMRepository.GetByID(ctx, instanceID.String())
	if err != nil || row == nil {
		return nil, nil
	}
	e, err := userAgentInstanceModelToEntity(row)
	if err != nil {
		return nil, nil
	}
	return e, nil
}

// FindByUserAndTemplate is find_by_user_and_template.
func (r *ORMUserAgentInstanceRepository) FindByUserAndTemplate(ctx context.Context, userID amvo.UserId, templateID amvo.AgentTemplateId) (*entities.UserAgentInstance, error) {
	row, err := r.ORMRepository.FindOneBy(ctx, baserepo.NewKwargs("user_id", userID.String(), "template_id", templateID.String()))
	if err != nil || row == nil {
		return nil, nil
	}
	e, err := userAgentInstanceModelToEntity(row)
	if err != nil {
		return nil, nil
	}
	return e, nil
}

// FindByUserAndTemplateSlug is find_by_user_and_template_slug (not part of the interface).
func (r *ORMUserAgentInstanceRepository) FindByUserAndTemplateSlug(ctx context.Context, userID amvo.UserId, templateSlug string) (*entities.UserAgentInstance, error) {
	var templateID string
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx, `SELECT "id"::text FROM agent_templates WHERE slug = $1 LIMIT 1`, templateSlug).Scan(&templateID)
	})
	if err != nil {
		return nil, nil
	}
	row, err := r.ORMRepository.FindOneBy(ctx, baserepo.NewKwargs("user_id", userID.String(), "template_id", templateID))
	if err != nil || row == nil {
		return nil, nil
	}
	e, err := userAgentInstanceModelToEntity(row)
	if err != nil {
		return nil, nil
	}
	return e, nil
}

// ExistsByUserAndTemplate is exists_by_user_and_template.
func (r *ORMUserAgentInstanceRepository) ExistsByUserAndTemplate(ctx context.Context, userID amvo.UserId, templateID amvo.AgentTemplateId) (bool, error) {
	n, err := r.ORMRepository.Count(ctx, baserepo.NewKwargs("user_id", userID.String(), "template_id", templateID.String()))
	if err != nil {
		return false, nil
	}
	return n > 0, nil
}

// FindByUser is find_by_user, ordered by agent_name.
func (r *ORMUserAgentInstanceRepository) FindByUser(ctx context.Context, userID amvo.UserId) ([]*entities.UserAgentInstance, error) {
	return r.userAgentInstanceQuery(ctx, "SELECT "+userAgentInstanceRepoSelect+" FROM user_agent_instances WHERE user_id = $1 ORDER BY agent_name", userID.String())
}

// FindEnabledByUser is find_enabled_by_user, ordered by agent_name.
func (r *ORMUserAgentInstanceRepository) FindEnabledByUser(ctx context.Context, userID amvo.UserId) ([]*entities.UserAgentInstance, error) {
	return r.userAgentInstanceQuery(ctx, "SELECT "+userAgentInstanceRepoSelect+" FROM user_agent_instances WHERE user_id = $1 AND is_enabled ORDER BY agent_name", userID.String())
}

// FindByShareToken is find_by_share_token.
func (r *ORMUserAgentInstanceRepository) FindByShareToken(ctx context.Context, shareToken string) (*entities.UserAgentInstance, error) {
	row, err := r.ORMRepository.FindOneBy(ctx, baserepo.NewKwargs("share_token", shareToken))
	if err != nil || row == nil {
		return nil, nil
	}
	e, err := userAgentInstanceModelToEntity(row)
	if err != nil {
		return nil, nil
	}
	return e, nil
}

// FindPublicInstances is find_public_instances: public rows with a share token, excluding
// orphaned imports.
func (r *ORMUserAgentInstanceRepository) FindPublicInstances(ctx context.Context, limit, offset int, orderBy enums.InstanceOrdering) ([]*entities.UserAgentInstance, error) {
	order := "created_at DESC"
	switch orderBy {
	case enums.InstanceOrderingCreatedAsc:
		order = "created_at ASC"
	case enums.InstanceOrderingUpdatedDesc:
		order = "updated_at DESC"
	case enums.InstanceOrderingUpdatedAsc:
		order = "updated_at ASC"
	case enums.InstanceOrderingNameAsc:
		order = "agent_name ASC"
	case enums.InstanceOrderingNameDesc:
		order = "agent_name DESC"
	}
	query := fmt.Sprintf("SELECT %s FROM user_agent_instances AS uai WHERE uai.visibility = 'public' "+
		"AND uai.share_token IS NOT NULL AND (uai.original_creator_id IS NULL OR EXISTS "+
		"(SELECT 1 FROM user_agent_instances AS orig WHERE orig.user_id = uai.original_creator_id)) "+
		"ORDER BY %s OFFSET $1 LIMIT $2", userAgentInstanceRepoSelect, order)
	return r.userAgentInstanceQuery(ctx, query, offset, limit)
}

// userAgentInstanceQuery scans and converts the rows of a query; errors return [].
func (r *ORMUserAgentInstanceRepository) userAgentInstanceQuery(ctx context.Context, query string, args ...any) ([]*entities.UserAgentInstance, error) {
	out := []*entities.UserAgentInstance{}
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		rows, err := s.QueryContext(ctx, query, args...)
		if err != nil {
			return err
		}
		defer rows.Close()
		for rows.Next() {
			row := &db.UserAgentInstanceORM{}
			if err := rows.Scan(&row.ID, &row.UserID, &row.TemplateID, &row.AgentName, &row.IsCustomized,
				&row.IsEnabled, &row.CustomizationNotes, &row.SystemPrompt, &row.Tools, &row.Capabilities,
				&row.Rules, &row.OutputFormat, &row.MetadataJSON, &row.Visibility, &row.ShareToken,
				&row.ShareCreatedAt, &row.OriginalCreatorID, &row.ImportedAt, &row.CreatedAt, &row.UpdatedAt,
				&row.LastUsedAt, &row.UsageCount); err != nil {
				return err
			}
			e, err := userAgentInstanceModelToEntity(row)
			if err != nil {
				return err
			}
			out = append(out, e)
		}
		return rows.Err()
	})
	if err != nil {
		return []*entities.UserAgentInstance{}, nil
	}
	return out, nil
}

// IsOrphaned is is_orphaned (not part of the interface).
func (r *ORMUserAgentInstanceRepository) IsOrphaned(ctx context.Context, instanceID amvo.UserAgentInstanceId) (bool, error) {
	row, err := r.ORMRepository.GetByID(ctx, instanceID.String())
	if err != nil || row == nil {
		return false, nil
	}
	if row.OriginalCreatorID == nil || *row.OriginalCreatorID == "" {
		return false, nil
	}
	rows, err := r.ORMRepository.FindBy(ctx, baserepo.NewKwargs("user_id", *row.OriginalCreatorID))
	if err != nil {
		return false, nil
	}
	return len(rows) == 0, nil
}

// CountByAgentNameForUser is count_by_agent_name_for_user.
func (r *ORMUserAgentInstanceRepository) CountByAgentNameForUser(ctx context.Context, userID amvo.UserId, agentName string) (int, error) {
	n, err := r.ORMRepository.Count(ctx, baserepo.NewKwargs("user_id", userID.String(), "agent_name", agentName))
	if err != nil {
		return 0, nil
	}
	return n, nil
}

// Delete is delete; the Python bool result is dropped by the interface, errors are swallowed.
func (r *ORMUserAgentInstanceRepository) Delete(ctx context.Context, instanceID amvo.UserAgentInstanceId) error {
	_, err := r.ORMRepository.Delete(ctx, instanceID.String())
	if err != nil {
		return nil
	}
	return nil
}
