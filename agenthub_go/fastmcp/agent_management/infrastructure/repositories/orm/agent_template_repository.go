// ORM Agent Template Repository (Python
// agent_management/infrastructure/repositories/orm/agent_template_repository.py): template
// CRUD over agent_templates. find_* / exists / delete swallow errors and return the Python
// default; save re-raises.

package orm

import (
	"context"
	"time"

	"agenthub/fastmcp/agent_management/domain/entities"
	domainrepo "agenthub/fastmcp/agent_management/domain/repositories"
	amvo "agenthub/fastmcp/agent_management/domain/value_objects"
	db "agenthub/fastmcp/agent_management/infrastructure/database"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
	baserepo "agenthub/fastmcp/task_management/infrastructure/repositories"
)

// agentTemplateRepoSelect lists agent_templates' columns (uuid cast to text).
const agentTemplateRepoSelect = `"id"::text, "slug", "name", "description", "category", "version", ` +
	`"system_prompt", "tools", "capabilities", "rules", "output_format", "metadata", "created_at", "updated_at"`

// ORMAgentTemplateRepository is Python's ORMAgentTemplateRepository.
type ORMAgentTemplateRepository struct {
	*baserepo.ORMRepository[db.AgentTemplateORM]
}

var _ domainrepo.AgentTemplateRepository = (*ORMAgentTemplateRepository)(nil)

// NewORMAgentTemplateRepository builds the repository over agent_templates.
func NewORMAgentTemplateRepository(sessions *database.SessionManager) (*ORMAgentTemplateRepository, error) {
	base, err := baserepo.NewORMRepository[db.AgentTemplateORM]("agent_templates", sessions)
	if err != nil {
		return nil, err
	}
	return &ORMAgentTemplateRepository{ORMRepository: base}, nil
}

// agentTemplateRepoParseJSON is json.loads for a text column.
func agentTemplateRepoParseJSON(s string) (any, error) {
	return tmentities.DecodeJSON([]byte(s))
}

// agentTemplateModelToEntity is _model_to_entity.
func agentTemplateModelToEntity(row *db.AgentTemplateORM) (*entities.AgentTemplate, error) {
	tools, err := agentTemplateRepoParseJSON(row.Tools)
	if err != nil {
		return nil, err
	}
	capabilities, err := agentTemplateRepoParseJSON(row.Capabilities)
	if err != nil {
		return nil, err
	}
	var rules, outputFormat any
	if row.Rules != nil && *row.Rules != "" {
		if rules, err = agentTemplateRepoParseJSON(*row.Rules); err != nil {
			return nil, err
		}
	}
	if row.OutputFormat != nil && *row.OutputFormat != "" {
		if outputFormat, err = agentTemplateRepoParseJSON(*row.OutputFormat); err != nil {
			return nil, err
		}
	}
	var metadata any
	if row.MetadataJSON != nil && *row.MetadataJSON != "" {
		if metadata, err = agentTemplateRepoParseJSON(*row.MetadataJSON); err != nil {
			return nil, err
		}
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
	id, err := amvo.NewAgentTemplateId(row.ID)
	if err != nil {
		return nil, err
	}
	t := entities.DefaultAgentTemplate()
	t.ID, t.Slug, t.Name, t.Description, t.Category, t.Version = &id, row.Slug, row.Name, row.Description, row.Category, row.Version
	t.DefaultConfiguration = &cfg
	if m, ok := metadata.(*tmentities.OrderedMap[any]); ok && m.Len() > 0 {
		t.Metadata = m
	}
	c, u := row.CreatedAt, row.UpdatedAt
	t.CreatedAt, t.UpdatedAt = &c, &u
	return entities.NewAgentTemplate(t)
}

// agentTemplateRepoModelDict is _entity_to_model_dict.
type agentTemplateRepoModelDict struct {
	ID           string
	Slug         string
	Name         string
	Description  string
	Category     string
	Version      string
	SystemPrompt string
	Tools        string
	Capabilities string
	Rules        *string
	OutputFormat *string
	MetadataJSON *string
	CreatedAt    time.Time
	UpdatedAt    time.Time
}

func agentTemplateToModelDict(template *entities.AgentTemplate) (*agentTemplateRepoModelDict, error) {
	cfg := template.DefaultConfiguration
	if cfg == nil {
		return nil, tmvo.TypeErrorf("'NoneType' object has no attribute 'system_prompt'")
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
	if template.Metadata != nil && template.Metadata.Len() > 0 {
		s, err := tmvo.PyJSONDumps(template.Metadata, -1)
		if err != nil {
			return nil, err
		}
		metadataJSON = &s
	}
	id := "None"
	if template.ID != nil {
		id = template.ID.String()
	}
	createdAt, updatedAt := time.Now().UTC(), time.Now().UTC()
	if template.CreatedAt != nil {
		createdAt = *template.CreatedAt
	}
	if template.UpdatedAt != nil {
		updatedAt = *template.UpdatedAt
	}
	return &agentTemplateRepoModelDict{
		ID: id, Slug: template.Slug, Name: template.Name, Description: template.Description,
		Category: template.Category, Version: template.Version, SystemPrompt: cfg.SystemPrompt,
		Tools: tools, Capabilities: capabilities, Rules: rules, OutputFormat: outputFormat,
		MetadataJSON: metadataJSON, CreatedAt: createdAt, UpdatedAt: updatedAt,
	}, nil
}

// Save is save.
func (r *ORMAgentTemplateRepository) Save(ctx context.Context, template *entities.AgentTemplate) (*entities.AgentTemplate, error) {
	model, err := agentTemplateToModelDict(template)
	if err != nil {
		return nil, err
	}
	var out *entities.AgentTemplate
	err = r.Transaction(ctx, func(ctx context.Context) error {
		existing, err := r.ORMRepository.GetByID(ctx, model.ID)
		if err != nil {
			return err
		}
		var row *db.AgentTemplateORM
		if existing != nil {
			row, err = r.ORMRepository.Update(ctx, model.ID, baserepo.NewKwargs(
				"slug", model.Slug,
				"name", model.Name,
				"description", model.Description,
				"category", model.Category,
				"version", model.Version,
				"system_prompt", model.SystemPrompt,
				"tools", model.Tools,
				"capabilities", model.Capabilities,
				"rules", model.Rules,
				"output_format", model.OutputFormat,
				"metadata_json", model.MetadataJSON,
				"updated_at", time.Now().UTC(),
			))
		} else {
			row, err = r.ORMRepository.Create(ctx, baserepo.NewKwargs(
				"id", model.ID,
				"slug", model.Slug,
				"name", model.Name,
				"description", model.Description,
				"category", model.Category,
				"version", model.Version,
				"system_prompt", model.SystemPrompt,
				"tools", model.Tools,
				"capabilities", model.Capabilities,
				"rules", model.Rules,
				"output_format", model.OutputFormat,
				"metadata_json", model.MetadataJSON,
				"created_at", model.CreatedAt,
				"updated_at", model.UpdatedAt,
			))
		}
		if err != nil {
			return err
		}
		out, err = agentTemplateModelToEntity(row)
		return err
	})
	return out, err
}

// FindByID is find_by_id; errors and conversion failures return nil.
func (r *ORMAgentTemplateRepository) FindByID(ctx context.Context, templateID amvo.AgentTemplateId) (*entities.AgentTemplate, error) {
	row, err := r.ORMRepository.GetByID(ctx, templateID.String())
	if err != nil || row == nil {
		return nil, nil
	}
	e, err := agentTemplateModelToEntity(row)
	if err != nil {
		return nil, nil
	}
	return e, nil
}

// FindBySlug is find_by_slug.
func (r *ORMAgentTemplateRepository) FindBySlug(ctx context.Context, slug string) (*entities.AgentTemplate, error) {
	row, err := r.ORMRepository.FindOneBy(ctx, baserepo.NewKwargs("slug", slug))
	if err != nil || row == nil {
		return nil, nil
	}
	e, err := agentTemplateModelToEntity(row)
	if err != nil {
		return nil, nil
	}
	return e, nil
}

// FindAll is find_all, ordered by category then name.
func (r *ORMAgentTemplateRepository) FindAll(ctx context.Context) ([]*entities.AgentTemplate, error) {
	return r.agentTemplateQuery(ctx, "SELECT "+agentTemplateRepoSelect+" FROM agent_templates ORDER BY category, name")
}

// FindByCategory is find_by_category, ordered by name.
func (r *ORMAgentTemplateRepository) FindByCategory(ctx context.Context, category string) ([]*entities.AgentTemplate, error) {
	return r.agentTemplateQuery(ctx, "SELECT "+agentTemplateRepoSelect+" FROM agent_templates WHERE category = $1 ORDER BY name", category)
}

// agentTemplateQuery scans and converts the rows of a query; errors return [].
func (r *ORMAgentTemplateRepository) agentTemplateQuery(ctx context.Context, query string, args ...any) ([]*entities.AgentTemplate, error) {
	out := []*entities.AgentTemplate{}
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		rows, err := s.QueryContext(ctx, query, args...)
		if err != nil {
			return err
		}
		defer rows.Close()
		for rows.Next() {
			row := &db.AgentTemplateORM{}
			if err := rows.Scan(&row.ID, &row.Slug, &row.Name, &row.Description, &row.Category, &row.Version,
				&row.SystemPrompt, &row.Tools, &row.Capabilities, &row.Rules, &row.OutputFormat,
				&row.MetadataJSON, &row.CreatedAt, &row.UpdatedAt); err != nil {
				return err
			}
			e, err := agentTemplateModelToEntity(row)
			if err != nil {
				return err
			}
			out = append(out, e)
		}
		return rows.Err()
	})
	if err != nil {
		return []*entities.AgentTemplate{}, nil
	}
	return out, nil
}

// ExistsBySlug is exists_by_slug.
func (r *ORMAgentTemplateRepository) ExistsBySlug(ctx context.Context, slug string) (bool, error) {
	n, err := r.ORMRepository.Count(ctx, baserepo.NewKwargs("slug", slug))
	if err != nil {
		return false, nil
	}
	return n > 0, nil
}

// Delete is delete; the Python bool result is dropped by the interface, errors are swallowed.
func (r *ORMAgentTemplateRepository) Delete(ctx context.Context, templateID amvo.AgentTemplateId) error {
	_, err := r.ORMRepository.Delete(ctx, templateID.String())
	if err != nil {
		return nil
	}
	return nil
}
