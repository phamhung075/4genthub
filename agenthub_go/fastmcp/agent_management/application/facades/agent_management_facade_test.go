package facades

import (
	"context"
	"testing"

	amentities "agenthub/fastmcp/agent_management/domain/entities"
	"agenthub/fastmcp/agent_management/domain/enums"
	amvo "agenthub/fastmcp/agent_management/domain/value_objects"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

type fakeTemplateRepo struct {
	templates []*amentities.AgentTemplate
}

func (r *fakeTemplateRepo) Save(_ context.Context, t *amentities.AgentTemplate) (*amentities.AgentTemplate, error) {
	return t, nil
}
func (r *fakeTemplateRepo) FindByID(_ context.Context, id amvo.AgentTemplateId) (*amentities.AgentTemplate, error) {
	for _, t := range r.templates {
		if t.ID != nil && t.ID.String() == id.String() {
			return t, nil
		}
	}
	return nil, nil
}
func (r *fakeTemplateRepo) FindBySlug(_ context.Context, slug string) (*amentities.AgentTemplate, error) {
	for _, t := range r.templates {
		if t.Slug == slug {
			return t, nil
		}
	}
	return nil, nil
}
func (r *fakeTemplateRepo) FindAll(context.Context) ([]*amentities.AgentTemplate, error) {
	return r.templates, nil
}
func (r *fakeTemplateRepo) FindByCategory(context.Context, string) ([]*amentities.AgentTemplate, error) {
	return nil, nil
}
func (r *fakeTemplateRepo) ExistsBySlug(_ context.Context, slug string) (bool, error) {
	for _, t := range r.templates {
		if t.Slug == slug {
			return true, nil
		}
	}
	return false, nil
}
func (r *fakeTemplateRepo) Delete(context.Context, amvo.AgentTemplateId) error { return nil }

type fakeInstanceRepo struct {
	instances []*amentities.UserAgentInstance
	orphaned  map[string]bool
}

func (r *fakeInstanceRepo) Save(_ context.Context, i *amentities.UserAgentInstance) (*amentities.UserAgentInstance, error) {
	for idx, existing := range r.instances {
		if existing.ID != nil && i.ID != nil && existing.ID.String() == i.ID.String() {
			r.instances[idx] = i
			return i, nil
		}
	}
	r.instances = append(r.instances, i)
	return i, nil
}
func (r *fakeInstanceRepo) FindByID(_ context.Context, id amvo.UserAgentInstanceId) (*amentities.UserAgentInstance, error) {
	for _, i := range r.instances {
		if i.ID != nil && i.ID.String() == id.String() {
			return i, nil
		}
	}
	return nil, nil
}
func (r *fakeInstanceRepo) FindByUserAndTemplate(_ context.Context, userID amvo.UserId, templateID amvo.AgentTemplateId) (*amentities.UserAgentInstance, error) {
	for _, i := range r.instances {
		if i.UserID.Value == userID.Value && i.TemplateID != nil && i.TemplateID.String() == templateID.String() {
			return i, nil
		}
	}
	return nil, nil
}
func (r *fakeInstanceRepo) FindByUser(_ context.Context, userID amvo.UserId) ([]*amentities.UserAgentInstance, error) {
	out := []*amentities.UserAgentInstance{}
	for _, i := range r.instances {
		if i.UserID.Value == userID.Value {
			out = append(out, i)
		}
	}
	return out, nil
}
func (r *fakeInstanceRepo) FindEnabledByUser(ctx context.Context, userID amvo.UserId) ([]*amentities.UserAgentInstance, error) {
	return r.FindByUser(ctx, userID)
}
func (r *fakeInstanceRepo) FindByShareToken(_ context.Context, token string) (*amentities.UserAgentInstance, error) {
	for _, i := range r.instances {
		if i.ShareToken != nil && *i.ShareToken == token {
			return i, nil
		}
	}
	return nil, nil
}
func (r *fakeInstanceRepo) FindPublicInstances(context.Context, int, int, enums.InstanceOrdering) ([]*amentities.UserAgentInstance, error) {
	return nil, nil
}
func (r *fakeInstanceRepo) ExistsByUserAndTemplate(context.Context, amvo.UserId, amvo.AgentTemplateId) (bool, error) {
	return false, nil
}
func (r *fakeInstanceRepo) CountByAgentNameForUser(context.Context, amvo.UserId, string) (int, error) {
	return 0, nil
}
func (r *fakeInstanceRepo) Delete(_ context.Context, id amvo.UserAgentInstanceId) error {
	for idx, i := range r.instances {
		if i.ID != nil && i.ID.String() == id.String() {
			r.instances = append(r.instances[:idx], r.instances[idx+1:]...)
			return nil
		}
	}
	return nil
}

// Extra methods beyond the domain interface, mirroring the ORM repository.
func (r *fakeInstanceRepo) FindByUserAndTemplateSlug(ctx context.Context, userID amvo.UserId, slug string) (*amentities.UserAgentInstance, error) {
	for _, i := range r.instances {
		if i.UserID.Value == userID.Value {
			return i, nil
		}
	}
	return nil, nil
}
func (r *fakeInstanceRepo) IsOrphaned(_ context.Context, id amvo.UserAgentInstanceId) (bool, error) {
	return r.orphaned[id.String()], nil
}

const testUserID = "11111111-1111-4111-8111-111111111111"

func newTestFacade(t *testing.T) (*AgentManagementFacade, *fakeInstanceRepo) {
	t.Helper()
	templateID := amvo.GenerateNewAgentTemplateId()
	config, err := amvo.NewAgentConfiguration("You are the coding agent.", []string{"read", "write"}, tmentities.NewOrderedMap[any](), []string{"be kind"}, nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	template := amentities.DefaultAgentTemplate()
	template.ID = &templateID
	template.Slug = "coding-agent"
	template.Name = "Coding Agent"
	template.Description = "Writes code"
	template.Category = "development"
	template.Version = "2.0.0"
	template.DefaultConfiguration = &config
	template.Metadata = tmentities.NewOrderedMap[any]()
	template.Metadata.Set("source", "agent-library")
	if _, err := amentities.NewAgentTemplate(template); err != nil {
		t.Fatal(err)
	}
	templates := &fakeTemplateRepo{templates: []*amentities.AgentTemplate{&template}}
	instances := &fakeInstanceRepo{orphaned: map[string]bool{}}
	return NewAgentManagementFacade(templates, instances, nil, nil), instances
}

func TestGetAgentForCallResponseShape(t *testing.T) {
	facade, instances := newTestFacade(t)
	userID, err := amvo.NewUserId(testUserID)
	if err != nil {
		t.Fatal(err)
	}
	resp, err := facade.GetAgentForCall(context.Background(), &userID, "coding-agent")
	if err != nil {
		t.Fatal(err)
	}
	wantKeys := []string{"name", "slug", "description", "system_prompt", "tools", "capabilities", "rules",
		"output_format", "category", "version", "is_customized", "is_orphaned", "instance_id", "template_id", "metadata"}
	keys := resp.Keys()
	if len(keys) != len(wantKeys) {
		t.Fatalf("keys = %v", keys)
	}
	for i, k := range wantKeys {
		if keys[i] != k {
			t.Fatalf("key[%d] = %q, want %q", i, keys[i], k)
		}
	}
	if v, _ := resp.Get("name"); v != "Coding Agent" {
		t.Errorf("name = %v", v)
	}
	if v, _ := resp.Get("is_customized"); v != false {
		t.Errorf("is_customized = %v", v)
	}
	tools, _ := resp.Get("tools")
	if list, ok := tools.([]any); !ok || len(list) != 2 || list[0] != "read" {
		t.Errorf("tools = %#v", tools)
	}
	meta, _ := resp.Get("metadata")
	mm, ok := meta.(*tmentities.OrderedMap[any])
	if !ok {
		t.Fatalf("metadata type = %T", meta)
	}
	if v, _ := mm.Get("source"); v != "agent-library" {
		t.Errorf("metadata.source = %v", v)
	}
	if v, ok := mm.Get("last_used"); !ok || v == nil {
		t.Errorf("last_used = %v", v)
	}
	if v, _ := mm.Get("orphaned_warning"); v != nil {
		t.Errorf("orphaned_warning = %v", v)
	}
	if len(instances.instances) != 1 {
		t.Fatalf("instances saved = %d", len(instances.instances))
	}
	if instances.instances[0].UsageCount != 1 {
		t.Errorf("usage_count = %d, want 1", instances.instances[0].UsageCount)
	}
}

func TestGetAgentForCallUnknownSlug(t *testing.T) {
	facade, _ := newTestFacade(t)
	userID, _ := amvo.NewUserId(testUserID)
	_, err := facade.GetAgentForCall(context.Background(), &userID, "nope")
	if err == nil {
		t.Fatal("expected error")
	}
	verr, ok := err.(*tmvo.ValueError)
	if !ok || verr.Msg != "Agent template not found: nope" {
		t.Fatalf("err = %v", err)
	}
}

func TestGetSharedAgentPreviewInvalidToken(t *testing.T) {
	facade, _ := newTestFacade(t)
	_, err := facade.GetSharedAgentPreview(context.Background(), "short")
	if err == nil || err.Error() != "Invalid share token" {
		t.Fatalf("err = %v", err)
	}
}
