package repositories

// ORM Template Repository (Python infrastructure/repositories/orm/template_repository.py):
// template persistence with filtering, analytics and usage tracking.
//
// Python's ORMTemplateRepository subclasses BaseTimestampRepository and declares itself a
// TemplateRepositoryInterface, but several of its methods do not match that ABC: save
// returns bool (not the template), list_templates takes status/priority (ignored) and
// returns a bare list (no total). This port keeps the Python signatures and behaviour;
// every public method swallows errors exactly like Python (returning false / nil / [] / {}).

import (
	"context"
	"fmt"
	"sort"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// ORMTemplateRepository is ORMTemplateRepository().
type ORMTemplateRepository struct {
	*ORMRepository[database.Template]
}

// NewORMTemplateRepository builds the repository (Python's constructor takes no arguments;
// Go needs the session manager).
func NewORMTemplateRepository(sessions *database.SessionManager) (*ORMTemplateRepository, error) {
	base, err := NewORMRepository[database.Template]("templates", sessions)
	if err != nil {
		return nil, err
	}
	return &ORMTemplateRepository{ORMRepository: base}, nil
}

// templateRepoModelDict is _entity_to_model_dict's dict.
type templateRepoModelDict struct {
	ID         string
	Name       string
	Type       string
	Content    *entities.OrderedMap[any]
	Category   string
	Tags       []string
	UsageCount int
	CreatedAt  time.Time
	UpdatedAt  time.Time
	CreatedBy  string
}

// templateRepoEnum mirrors an enum class call (Python accepts only declared members).
func templateRepoEnum[T ~string](name, v string, all []T) (T, error) {
	for _, e := range all {
		if string(e) == v {
			return e, nil
		}
	}
	var zero T
	return zero, value_objects.ValueErrorf("%s is not a valid %s", value_objects.PyRepr(v), name)
}

// templateRepoNoneAttr is the AttributeError text for `.value` on a None enum.
func templateRepoNoneAttr(attr string) error {
	return value_objects.TypeErrorf("'NoneType' object has no attribute '%s'", attr)
}

// templateRepoContent decodes the JSON content column; Python treats any non-dict as {}.
func templateRepoContent(raw []byte) *entities.OrderedMap[any] {
	if len(raw) == 0 {
		return entities.NewOrderedMap[any]()
	}
	v, err := entities.DecodeJSON(raw)
	if err != nil {
		return entities.NewOrderedMap[any]()
	}
	if m, ok := v.(*entities.OrderedMap[any]); ok {
		return m
	}
	return entities.NewOrderedMap[any]()
}

func templateRepoString(m *entities.OrderedMap[any], key, def string) string {
	v, ok := m.Get(key)
	if !ok {
		return def
	}
	if s, ok := v.(string); ok {
		return s
	}
	return def
}

func templateRepoStringList(m *entities.OrderedMap[any], key string) []string {
	v, ok := m.Get(key)
	if !ok {
		return []string{}
	}
	switch l := v.(type) {
	case []string:
		return append([]string{}, l...)
	case []any:
		out := []string{}
		for _, e := range l {
			if s, ok := e.(string); ok {
				out = append(out, s)
			}
		}
		return out
	}
	return []string{}
}

func templateRepoMap(m *entities.OrderedMap[any], key string) map[string]any {
	v, ok := m.Get(key)
	if !ok {
		return map[string]any{}
	}
	switch d := v.(type) {
	case map[string]any:
		return d
	case *entities.OrderedMap[any]:
		out := map[string]any{}
		for _, k := range d.Keys() {
			val, _ := d.Get(k)
			out[k] = val
		}
		return out
	}
	return map[string]any{}
}

func templateRepoInt(v any) (int, bool) {
	switch n := v.(type) {
	case int:
		return n, true
	case int64:
		return int(n), true
	case float64:
		if n == float64(int(n)) {
			return int(n), true
		}
	}
	return 0, false
}

// Save is save: it returns true on success and false on any error (Python swallows the
// exception and logs it).
func (r *ORMTemplateRepository) Save(ctx context.Context, template *entities.Template) (bool, error) {
	if err := r.save(ctx, template); err != nil {
		return false, nil
	}
	return true, nil
}

func (r *ORMTemplateRepository) save(ctx context.Context, template *entities.Template) error {
	id := "None" // str(None)
	if template.ID != nil {
		id = template.ID.Value
	}
	modelDict, err := r.entityToModelDict(template)
	if err != nil {
		return err
	}
	return r.Transaction(ctx, func(ctx context.Context) error {
		existing, err := r.ORMRepository.GetByID(ctx, id)
		if err != nil {
			return err
		}
		if existing != nil {
			// Preserve usage_count; touch() refreshes updated_at.
			_, err = r.ORMRepository.Update(ctx, id, NewKwargs(
				"name", modelDict.Name,
				"type", modelDict.Type,
				"content", modelDict.Content,
				"category", modelDict.Category,
				"tags", modelDict.Tags,
				"created_by", modelDict.CreatedBy,
				"updated_at", Now(),
			))
			return err
		}
		_, err = r.ORMRepository.Create(ctx, NewKwargs(
			"id", modelDict.ID,
			"name", modelDict.Name,
			"type", modelDict.Type,
			"content", modelDict.Content,
			"category", modelDict.Category,
			"tags", modelDict.Tags,
			"usage_count", modelDict.UsageCount,
			"created_at", modelDict.CreatedAt,
			"updated_at", modelDict.UpdatedAt,
			"created_by", modelDict.CreatedBy,
		))
		return err
	})
}

// GetByID is get_by_id; it returns nil when absent or when conversion fails.
func (r *ORMTemplateRepository) GetByID(ctx context.Context, templateID value_objects.TemplateId) (*entities.Template, error) {
	row, err := r.ORMRepository.GetByID(ctx, templateID.Value)
	if err != nil || row == nil {
		return nil, nil
	}
	t, err := r.modelToEntity(row)
	if err != nil {
		return nil, nil
	}
	return t, nil
}

// ListTemplates is list_templates. status and priority are accepted but never applied
// (Python ignores them); template_type and category filter, ordering is usage_count DESC
// then name.
func (r *ORMTemplateRepository) ListTemplates(
	ctx context.Context,
	templateType *value_objects.TemplateType,
	category *value_objects.TemplateCategory,
	status *value_objects.TemplateStatus,
	priority *value_objects.TemplatePriority,
	limit, offset *int,
) ([]*entities.Template, error) {
	_ = status
	_ = priority
	out := []*entities.Template{}
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		var conds []string
		var args []any
		if templateType != nil {
			args = append(args, string(*templateType))
			conds = append(conds, fmt.Sprintf("%s = $%d", quoteIdent("type"), len(args)))
		}
		if category != nil {
			args = append(args, string(*category))
			conds = append(conds, fmt.Sprintf("%s = $%d", quoteIdent("category"), len(args)))
		}
		suffix := ""
		if len(conds) > 0 {
			suffix += " WHERE " + strings.Join(conds, " AND ")
		}
		suffix += " ORDER BY " + quoteIdent("usage_count") + " DESC, " + quoteIdent("name")
		if limit != nil && *limit != 0 {
			suffix += fmt.Sprintf(" LIMIT %d", *limit)
		}
		if offset != nil && *offset != 0 {
			suffix += fmt.Sprintf(" OFFSET %d", *offset)
		}
		rows, err := r.selectRows(ctx, s, suffix, args...)
		if err != nil {
			return err
		}
		for _, row := range rows {
			t, err := r.modelToEntity(row)
			if err != nil {
				return err
			}
			out = append(out, t)
		}
		return nil
	})
	if err != nil {
		return []*entities.Template{}, nil
	}
	return out, nil
}

// Delete is delete; it returns false when absent or on error.
func (r *ORMTemplateRepository) Delete(ctx context.Context, templateID value_objects.TemplateId) (bool, error) {
	deleted, err := r.ORMRepository.Delete(ctx, templateID.Value)
	if err != nil {
		return false, nil
	}
	return deleted, nil
}

// GetTemplatesByType is get_templates_by_type.
func (r *ORMTemplateRepository) GetTemplatesByType(ctx context.Context, templateType value_objects.TemplateType) ([]*entities.Template, error) {
	return r.ListTemplates(ctx, &templateType, nil, nil, nil, nil, nil)
}

// GetTemplatesByCategory is get_templates_by_category.
func (r *ORMTemplateRepository) GetTemplatesByCategory(ctx context.Context, category value_objects.TemplateCategory) ([]*entities.Template, error) {
	return r.ListTemplates(ctx, nil, &category, nil, nil, nil, nil)
}

// SearchTemplatesByTags is search_templates_by_tags. Python emits MySQL JSON_SEARCH text()
// conditions, which fail on PostgreSQL; the exception is swallowed and [] returned.
func (r *ORMTemplateRepository) SearchTemplatesByTags(ctx context.Context, tags []string) ([]*entities.Template, error) {
	if len(tags) == 0 {
		return []*entities.Template{}, nil
	}
	out := []*entities.Template{}
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		conds := make([]string, 0, len(tags))
		for _, tag := range tags {
			conds = append(conds, fmt.Sprintf("JSON_SEARCH(tags, 'one', '%s') IS NOT NULL", tag))
		}
		q := "SELECT " + r.selectList() + " FROM " + quoteIdent(r.Table.Name) +
			" WHERE " + strings.Join(conds, " OR ") +
			" ORDER BY " + quoteIdent("usage_count") + " DESC"
		rows, err := s.QueryContext(ctx, q)
		if err != nil {
			return err
		}
		defer rows.Close()
		for rows.Next() {
			row := r.newRow()
			if err := rows.Scan(r.scanDest(row)...); err != nil {
				return err
			}
			t, err := r.modelToEntity(row)
			if err != nil {
				return err
			}
			out = append(out, t)
		}
		return rows.Err()
	})
	if err != nil {
		return []*entities.Template{}, nil
	}
	return out, nil
}

// IncrementUsageCount is increment_usage_count.
func (r *ORMTemplateRepository) IncrementUsageCount(ctx context.Context, templateID value_objects.TemplateId) (bool, error) {
	row, err := r.ORMRepository.GetByID(ctx, templateID.Value)
	if err != nil || row == nil {
		return false, nil
	}
	if _, err := r.ORMRepository.Update(ctx, templateID.Value, NewKwargs("usage_count", row.UsageCount+1, "updated_at", Now())); err != nil {
		return false, nil
	}
	return true, nil
}

// SaveUsage is save_usage: it only increments the usage count.
func (r *ORMTemplateRepository) SaveUsage(ctx context.Context, usage entities.TemplateUsage) (bool, error) {
	return r.IncrementUsageCount(ctx, usage.TemplateID)
}

// GetUsageStats is get_usage_stats; the datetimes are returned as-is (not formatted).
func (r *ORMTemplateRepository) GetUsageStats(ctx context.Context, templateID value_objects.TemplateId) (*entities.OrderedMap[any], error) {
	row, err := r.ORMRepository.GetByID(ctx, templateID.Value)
	if err != nil || row == nil {
		return entities.NewOrderedMap[any](), nil
	}
	out := entities.NewOrderedMap[any]()
	out.Set("template_id", templateID.Value)
	out.Set("total_usage", row.UsageCount)
	out.Set("last_used", row.UpdatedAt)
	out.Set("created_at", row.CreatedAt)
	return out, nil
}

// GetAnalytics is get_analytics. Python's ORM method takes no template id.
func (r *ORMTemplateRepository) GetAnalytics(ctx context.Context) (*entities.OrderedMap[any], error) {
	out := entities.NewOrderedMap[any]()
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		var total int64
		if err := s.QueryRowContext(ctx, "SELECT count(*) FROM "+quoteIdent(r.Table.Name)).Scan(&total); err != nil {
			return err
		}
		typeStats, err := r.groupCount(ctx, s, "type")
		if err != nil {
			return err
		}
		categoryStats, err := r.groupCount(ctx, s, "category")
		if err != nil {
			return err
		}
		mostUsed := []*entities.OrderedMap[any]{}
		rows, err := s.QueryContext(ctx,
			"SELECT "+quoteIdent("id")+"::text, "+quoteIdent("name")+", "+quoteIdent("usage_count")+
				" FROM "+quoteIdent(r.Table.Name)+" ORDER BY "+quoteIdent("usage_count")+" DESC LIMIT 10")
		if err != nil {
			return err
		}
		defer rows.Close()
		for rows.Next() {
			var id, name string
			var usage int64
			if err := rows.Scan(&id, &name, &usage); err != nil {
				return err
			}
			item := entities.NewOrderedMap[any]()
			item.Set("id", id)
			item.Set("name", name)
			item.Set("usage_count", usage)
			mostUsed = append(mostUsed, item)
		}
		if err := rows.Err(); err != nil {
			return err
		}
		out.Set("total_templates", total)
		out.Set("templates_by_type", typeStats)
		out.Set("templates_by_category", categoryStats)
		out.Set("most_used_templates", mostUsed)
		out.Set("generated_at", value_objects.IsoFormat(time.Now().UTC()))
		return nil
	})
	if err != nil {
		return entities.NewOrderedMap[any](), nil
	}
	return out, nil
}

func (r *ORMTemplateRepository) groupCount(ctx context.Context, s database.DBTX, column string) (*entities.OrderedMap[any], error) {
	out := entities.NewOrderedMap[any]()
	rows, err := s.QueryContext(ctx,
		"SELECT "+quoteIdent(column)+", count(*) FROM "+quoteIdent(r.Table.Name)+" GROUP BY "+quoteIdent(column))
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	for rows.Next() {
		var key string
		var count int64
		if err := rows.Scan(&key, &count); err != nil {
			return nil, err
		}
		out.Set(key, count)
	}
	return out, rows.Err()
}

// extractTags is _extract_tags_from_template. Python returns list(set(...)), so the order
// is unspecified; metadata keys are visited in sorted order for determinism.
func (r *ORMTemplateRepository) extractTags(template *entities.Template) ([]string, error) {
	if template.TemplateType == nil || template.Category == nil || template.Status == nil || template.Priority == nil {
		return nil, templateRepoNoneAttr("value")
	}
	if template.Metadata == nil {
		return nil, templateRepoNoneAttr("keys")
	}
	tags := []string{
		string(*template.TemplateType),
		string(*template.Category),
		string(*template.Status),
		string(*template.Priority),
	}
	tags = append(tags, template.CompatibleAgents...)
	keys := make([]string, 0, len(template.Metadata))
	for k := range template.Metadata {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	tags = append(tags, keys...)

	seen := map[string]bool{}
	out := []string{}
	for _, tag := range tags {
		if tag == "" || seen[tag] {
			continue
		}
		seen[tag] = true
		out = append(out, tag)
	}
	return out, nil
}

// entityToModelDict is _entity_to_model_dict.
func (r *ORMTemplateRepository) entityToModelDict(template *entities.Template) (*templateRepoModelDict, error) {
	if template.TemplateType == nil || template.Category == nil || template.Status == nil || template.Priority == nil {
		return nil, templateRepoNoneAttr("value")
	}
	tags, err := r.extractTags(template)
	if err != nil {
		return nil, err
	}
	content := entities.NewOrderedMap[any]()
	content.Set("description", template.Description)
	content.Set("content", template.Content)
	content.Set("status", string(*template.Status))
	content.Set("priority", string(*template.Priority))
	content.Set("compatible_agents", template.CompatibleAgents)
	content.Set("file_patterns", template.FilePatterns)
	content.Set("variables", template.Variables)
	content.Set("metadata", template.Metadata)
	version := 0
	if template.Version != nil {
		version = *template.Version
	}
	content.Set("version", version)
	isActive := false
	if template.IsActive != nil {
		isActive = *template.IsActive
	}
	content.Set("is_active", isActive)

	id := "None"
	if template.ID != nil {
		id = template.ID.Value
	}
	createdAt, updatedAt := time.Time{}, time.Time{}
	if template.CreatedAt != nil {
		createdAt = *template.CreatedAt
	}
	if template.UpdatedAt != nil {
		updatedAt = *template.UpdatedAt
	}
	return &templateRepoModelDict{
		ID: id, Name: template.Name, Type: string(*template.TemplateType),
		Content: content, Category: string(*template.Category), Tags: tags,
		UsageCount: 0, CreatedAt: createdAt, UpdatedAt: updatedAt, CreatedBy: "system",
	}, nil
}

// modelToEntity is _model_to_entity.
func (r *ORMTemplateRepository) modelToEntity(row *database.Template) (*entities.Template, error) {
	content := templateRepoContent(row.Content)
	tid, err := value_objects.NewTemplateId(row.ID)
	if err != nil {
		return nil, err
	}
	tt, err := templateRepoEnum("TemplateType", row.Type, value_objects.TemplateTypeValues)
	if err != nil {
		return nil, err
	}
	cat, err := templateRepoEnum("TemplateCategory", row.Category, value_objects.TemplateCategoryValues)
	if err != nil {
		return nil, err
	}
	st, err := templateRepoEnum("TemplateStatus", templateRepoString(content, "status", "active"), value_objects.TemplateStatusValues)
	if err != nil {
		return nil, err
	}
	pr, err := templateRepoEnum("TemplatePriority", templateRepoString(content, "priority", "medium"), value_objects.TemplatePriorityValues)
	if err != nil {
		return nil, err
	}
	t := entities.Template{
		ID: &tid, Name: row.Name,
		Description:  templateRepoString(content, "description", ""),
		Content:      templateRepoString(content, "content", ""),
		TemplateType: &tt, Category: &cat, Status: &st, Priority: &pr,
		CompatibleAgents: templateRepoStringList(content, "compatible_agents"),
		FilePatterns:     templateRepoStringList(content, "file_patterns"),
		Variables:        templateRepoStringList(content, "variables"),
		Metadata:         templateRepoMap(content, "metadata"),
	}
	if v, ok := content.Get("version"); ok {
		if n, ok := templateRepoInt(v); ok {
			t.Version = &n
		}
	}
	if v, ok := content.Get("is_active"); ok {
		if b, ok := v.(bool); ok {
			t.IsActive = &b
		}
	}
	c, u := row.CreatedAt, row.UpdatedAt
	t.CreatedAt, t.UpdatedAt = &c, &u
	return entities.NewTemplate(t)
}
