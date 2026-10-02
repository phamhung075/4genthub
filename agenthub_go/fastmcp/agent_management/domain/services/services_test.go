package services_test

import (
	"context"
	"fmt"
	"sort"
	"strings"
	"testing"

	"agenthub/fastmcp/agent_management/domain/entities"
	"agenthub/fastmcp/agent_management/domain/enums"
	"agenthub/fastmcp/agent_management/domain/internal/amtest"
	"agenthub/fastmcp/agent_management/domain/services"
	"agenthub/fastmcp/agent_management/domain/value_objects"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
)

type fakeTemplates struct {
	items []*entities.AgentTemplate
	log   *[]any
}

func (r *fakeTemplates) Save(_ context.Context, t *entities.AgentTemplate) (*entities.AgentTemplate, error) {
	*r.log = append(*r.log, []any{"t.save"})
	return t, nil
}
func (r *fakeTemplates) FindByID(_ context.Context, id value_objects.AgentTemplateId) (*entities.AgentTemplate, error) {
	for _, t := range r.items {
		if t.ID != nil && *t.ID == id {
			return t, nil
		}
	}
	return nil, nil
}
func (r *fakeTemplates) FindBySlug(_ context.Context, slug string) (*entities.AgentTemplate, error) {
	*r.log = append(*r.log, []any{"t.find_by_slug", slug})
	for _, t := range r.items {
		if t.Slug == slug {
			return t, nil
		}
	}
	return nil, nil
}
func (r *fakeTemplates) FindAll(context.Context) ([]*entities.AgentTemplate, error) {
	return r.items, nil
}
func (r *fakeTemplates) FindByCategory(context.Context, string) ([]*entities.AgentTemplate, error) {
	return nil, nil
}
func (r *fakeTemplates) ExistsBySlug(context.Context, string) (bool, error) { return false, nil }
func (r *fakeTemplates) Delete(context.Context, value_objects.AgentTemplateId) error {
	return nil
}

type fakeInstances struct {
	items []*entities.UserAgentInstance
	log   *[]any
}

func (r *fakeInstances) note(entry ...any) { *r.log = append(*r.log, entry) }

func (r *fakeInstances) Save(_ context.Context, i *entities.UserAgentInstance) (*entities.UserAgentInstance, error) {
	r.note("i.save", i.ID.String())
	for n, x := range r.items {
		if *x.ID == *i.ID {
			r.items[n] = i
			return i, nil
		}
	}
	r.items = append(r.items, i)
	return i, nil
}
func (r *fakeInstances) FindByID(_ context.Context, id value_objects.UserAgentInstanceId) (*entities.UserAgentInstance, error) {
	r.note("i.find_by_id", id.String())
	for _, x := range r.items {
		if *x.ID == id {
			return x, nil
		}
	}
	return nil, nil
}
func (r *fakeInstances) FindByUserAndTemplate(_ context.Context, u value_objects.UserId, tpl value_objects.AgentTemplateId) (*entities.UserAgentInstance, error) {
	r.note("i.find_by_user_and_template", u.String(), tpl.String())
	for _, x := range r.items {
		if *x.UserID == u && *x.TemplateID == tpl {
			return x, nil
		}
	}
	return nil, nil
}
func (r *fakeInstances) FindByUser(_ context.Context, u value_objects.UserId) ([]*entities.UserAgentInstance, error) {
	r.note("i.find_by_user", u.String())
	var out []*entities.UserAgentInstance
	for _, x := range r.items {
		if *x.UserID == u {
			out = append(out, x)
		}
	}
	return out, nil
}
func (r *fakeInstances) FindEnabledByUser(context.Context, value_objects.UserId) ([]*entities.UserAgentInstance, error) {
	return nil, nil
}
func (r *fakeInstances) FindByShareToken(_ context.Context, token string) (*entities.UserAgentInstance, error) {
	r.note("i.find_by_share_token", token)
	for _, x := range r.items {
		if x.ShareToken != nil && *x.ShareToken == token {
			return x, nil
		}
	}
	return nil, nil
}
func (r *fakeInstances) FindPublicInstances(_ context.Context, limit, offset int, order enums.InstanceOrdering) ([]*entities.UserAgentInstance, error) {
	r.note("i.find_public_instances", int64(limit), int64(offset), string(order))
	var pub []*entities.UserAgentInstance
	for _, x := range r.items {
		if x.Visibility == "public" {
			pub = append(pub, x)
		}
	}
	desc := strings.HasSuffix(string(order), "desc")
	less := func(a, b *entities.UserAgentInstance) bool {
		switch strings.Split(string(order), "_")[0] {
		case "created":
			return a.CreatedAt.Before(*b.CreatedAt)
		case "updated":
			return a.UpdatedAt.Before(*b.UpdatedAt)
		}
		return a.AgentName < b.AgentName
	}
	sort.SliceStable(pub, func(i, j int) bool {
		if desc {
			return less(pub[j], pub[i])
		}
		return less(pub[i], pub[j])
	})
	if offset > len(pub) {
		offset = len(pub)
	}
	end := min(offset+limit, len(pub))
	return pub[offset:end], nil
}
func (r *fakeInstances) ExistsByUserAndTemplate(context.Context, value_objects.UserId, value_objects.AgentTemplateId) (bool, error) {
	return false, nil
}
func (r *fakeInstances) CountByAgentNameForUser(_ context.Context, u value_objects.UserId, name string) (int, error) {
	r.note("i.count", u.String(), name)
	n := 0
	for _, x := range r.items {
		if *x.UserID == u && x.AgentName == name {
			n++
		}
	}
	return n, nil
}
func (r *fakeInstances) Delete(context.Context, value_objects.UserAgentInstanceId) error { return nil }

func uid(n int) string { return fmt.Sprintf("00000000-0000-1000-8000-%012d", n) }

func num(v any) int {
	switch n := v.(type) {
	case int64:
		return int(n)
	case float64:
		return int(n)
	}
	panic(fmt.Sprintf("not a number: %v", v))
}

func mustUser(t *testing.T, v any) *value_objects.UserId {
	if v == nil {
		return nil
	}
	id, err := value_objects.NewUserId(uid(num(v)))
	if err != nil {
		t.Fatal(err)
	}
	return &id
}

func instID(t *testing.T, v any) value_objects.UserAgentInstanceId {
	id, err := value_objects.NewUserAgentInstanceId(uid(num(v)))
	if err != nil {
		t.Fatal(err)
	}
	return id
}

func notes(v any) *string {
	if s, ok := v.(string); ok {
		return &s
	}
	return nil
}

func strs(v any) []string {
	out := []string{}
	for _, s := range amtest.Items(v) {
		out = append(out, s.(string))
	}
	return out
}

func dicts(list []*entities.UserAgentInstance) []any {
	out := []any{}
	for _, i := range list {
		out = append(out, i.ToDict())
	}
	return out
}

func instResult(i *entities.UserAgentInstance, err error) *tmentities.OrderedMap[any] {
	if err != nil {
		return amtest.ErrMap(err)
	}
	if i == nil {
		return amtest.Result(nil, nil)
	}
	return amtest.Result(i.ToDict(), nil)
}

func TestServicesParity(t *testing.T) {
	ctx := context.Background()
	for _, sc := range amtest.Items(amtest.Field(amtest.Fixture(t), "service")) {
		var log []any
		var tpls []*entities.AgentTemplate
		for _, d := range amtest.Items(amtest.Field(sc, "t")) {
			tpl, err := entities.AgentTemplateFromDict(amtest.Map(d))
			if err != nil {
				t.Fatal(err)
			}
			tpls = append(tpls, tpl)
		}
		var insts []*entities.UserAgentInstance
		for _, d := range amtest.Items(amtest.Field(sc, "i")) {
			inst, err := entities.UserAgentInstanceFromDict(amtest.Map(d))
			if err != nil {
				t.Fatal(err)
			}
			insts = append(insts, inst)
		}
		tr, ir := &fakeTemplates{tpls, &log}, &fakeInstances{insts, &log}
		isv, csv, ssv := services.NewAgentInstantiationService(tr, ir), services.NewAgentCustomizationService(ir), services.NewAgentSharingService(ir, tr)
		tok := 0
		ssv.ShareToken = func() string { tok++; return strings.Repeat(fmt.Sprintf("%04d", tok), 16) }

		script := amtest.Str(sc, "script")
		for i, r := range amtest.Items(amtest.Field(sc, "res")) {
			op := amtest.Items(amtest.Field(r, "op"))
			log = nil
			var got *tmentities.OrderedMap[any]
			switch op[0].(string) {
			case "get_or_create":
				got = instResult(isv.GetOrCreateInstance(ctx, mustUser(t, op[1]), op[2].(string)))
			case "get_by_id":
				got = instResult(isv.GetInstanceByID(ctx, instID(t, op[1])))
			case "get_for_user":
				list, err := isv.GetInstancesForUser(ctx, *mustUser(t, op[1]))
				got = amtest.Result(dicts(list), err)
			case "prompt":
				got = instResult(csv.UpdateSystemPrompt(ctx, instID(t, op[1]), *mustUser(t, op[2]), op[3].(string), notes(op[4])))
			case "rules":
				got = instResult(csv.UpdateRules(ctx, instID(t, op[1]), *mustUser(t, op[2]), strs(op[3]), notes(op[4])))
			case "caps":
				got = instResult(csv.UpdateCapabilities(ctx, instID(t, op[1]), *mustUser(t, op[2]), amtest.Map(op[3]), notes(op[4])))
			case "fmt":
				got = instResult(csv.UpdateOutputFormat(ctx, instID(t, op[1]), *mustUser(t, op[2]), amtest.Map(op[3]), notes(op[4])))
			case "full", "reset":
				cfg, err := value_objects.AgentConfigurationFromDict(amtest.Map(op[3]))
				if err != nil {
					t.Fatal(err)
				}
				if op[0] == "full" {
					got = instResult(csv.UpdateFullConfiguration(ctx, instID(t, op[1]), *mustUser(t, op[2]), cfg, notes(op[4])))
				} else {
					got = instResult(csv.ResetToTemplateDefaults(ctx, instID(t, op[1]), *mustUser(t, op[2]), cfg))
				}
			case "gen":
				token, ok, err := ssv.GenerateShareToken(ctx, instID(t, op[1]), *mustUser(t, op[2]))
				var v any = token
				if !ok {
					v = nil
				}
				got = amtest.Result(v, err)
				if err == nil && !ok {
					got = amtest.Result(nil, nil)
				}
			case "revoke":
				ok, err := ssv.RevokeShareToken(ctx, instID(t, op[1]), *mustUser(t, op[2]))
				got = amtest.Result(ok, err)
			case "import":
				got = instResult(ssv.ImportAgent(ctx, op[1].(string), *mustUser(t, op[2]), notes(op[3])))
			case "public":
				order := enums.InstanceOrdering("")
				if s, ok := op[3].(string); ok {
					order = enums.InstanceOrdering(s)
				}
				list, err := ssv.GetPublicInstances(ctx, num(op[1]), num(op[2]), order)
				got = amtest.Result(dicts(list), err)
			default:
				t.Fatalf("unknown op %v", op[0])
			}
			label := fmt.Sprintf("%s #%d %v", script, i, op)
			if g, w := amtest.Canon(t, got), amtest.Canon(t, amtest.Field(r, "out")); g != w {
				t.Errorf("%s out:\n got  %s\n want %s", label, g, w)
			}
			if g, w := amtest.Canon(t, orEmpty(log)), amtest.Canon(t, amtest.Field(r, "log")); g != w {
				t.Errorf("%s repository calls:\n got  %s\n want %s", label, g, w)
			}
		}
	}
}

func orEmpty(l []any) []any {
	if l == nil {
		return []any{}
	}
	return l
}
