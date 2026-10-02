package entities_test

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"agenthub/fastmcp/agent_management/domain/entities"
	"agenthub/fastmcp/agent_management/domain/internal/amtest"
	"agenthub/fastmcp/agent_management/domain/value_objects"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
)

func uuid(n int) string { return fmt.Sprintf("00000000-0000-1000-8000-%012d", n) }

func compare(t *testing.T, label string, got, want any) {
	t.Helper()
	if g, w := amtest.Canon(t, got), amtest.Canon(t, want); g != w {
		t.Errorf("%s:\n got  %s\n want %s", label, g, w)
	}
}

func TestAgentTemplateFromDictParity(t *testing.T) {
	for _, c := range amtest.Items(amtest.Field(amtest.Fixture(t), "template")) {
		name := amtest.Str(c, "name")
		tpl, err := entities.AgentTemplateFromDict(amtest.Map(amtest.Field(c, "in")))
		var got any
		if err != nil {
			got = amtest.ErrMap(err)
		} else {
			cfg, cerr := tpl.GetConfigurationCopy()
			if cerr != nil {
				t.Fatal(cerr)
			}
			got = amtest.Result(amtest.Obj("dict", tpl.ToDict(), "repr", tpl.String(),
				"match", []any{tpl.MatchesSlug("CODING-AGENT"), tpl.MatchesSlug("x")},
				"copy", cfg.ToDict(), "entity_id", tpl.GetEntityID()), nil)
		}
		compare(t, "template "+name, got, amtest.Field(c, "out"))
	}
}

func TestAgentTemplateFromYAMLParity(t *testing.T) {
	dir := t.TempDir()
	for _, c := range amtest.Items(amtest.Field(amtest.Fixture(t), "yaml")) {
		name := amtest.Str(c, "name")
		path := filepath.Join(dir, name+".yaml")
		if name == "missing" {
			_, err := entities.FromYAML(path, nil)
			if !errors.Is(err, os.ErrNotExist) {
				t.Errorf("missing: want FileNotFoundError, got %v", err)
			}
			continue
		}
		if err := os.WriteFile(path, []byte(amtest.Str(c, "text")), 0o644); err != nil {
			t.Fatal(err)
		}
		id, _ := value_objects.NewAgentTemplateId(uuid(7))
		tpl, err := entities.FromYAML(path, &id)
		want := amtest.Field(c, "out")
		var got *tmentities.OrderedMap[any]
		if err != nil {
			got = amtest.ErrMap(err)
			if m := amtest.Str(got, "msg"); m != "" {
				got.Set("msg", strings.ReplaceAll(m, dir, "<dir>"))
			}
			// The YAML parser's own error text differs between PyYAML and yaml.v3.
			if name == "badyaml" || name == "multi" {
				prefix := "Invalid YAML in <dir>/" + name + ".yaml: "
				if !strings.HasPrefix(amtest.Str(got, "msg"), prefix) || !strings.HasPrefix(amtest.Str(want, "msg"), prefix) {
					t.Errorf("%s: got %q want %q", name, amtest.Str(got, "msg"), amtest.Str(want, "msg"))
				}
				continue
			}
		} else {
			d := tpl.ToDict()
			meta, _ := d.Get("metadata")
			amtest.Map(meta).Set("source_file", "<path>")
			got = amtest.Result(d, nil)
		}
		compare(t, "yaml "+name, got, want)
	}
}

func TestUserAgentInstanceParity(t *testing.T) {
	for _, c := range amtest.Items(amtest.Field(amtest.Fixture(t), "instance")) {
		label := amtest.Str(c, "name")
		ops := amtest.Items(amtest.Field(c, "ops"))
		inst, err := entities.UserAgentInstanceFromDict(amtest.Map(amtest.Field(c, "in")))
		if init := amtest.Field(c, "init"); init != nil {
			compare(t, "instance "+label+" init", amtest.ErrMap(err), init)
			if err == nil {
				t.Errorf("instance %s: want init error %v", label, amtest.Str(init, "msg"))
			}
			continue
		}
		if err != nil {
			t.Fatalf("instance %s: %v", label, err)
		}
		steps := amtest.Items(amtest.Field(c, "steps"))
		step := func(r any, withR bool) any {
			if !withR {
				return amtest.Obj("dict", inst.ToDict(), "repr", inst.String())
			}
			return amtest.Obj("dict", inst.ToDict(), "repr", inst.String(), "r", r)
		}
		compare(t, fmt.Sprintf("instance %s %v step 0", label, ops), step(nil, false), steps[0])
		for i, o := range ops {
			op := amtest.Items(o)
			var r any
			switch op[0].(string) {
			case "customize":
				cfgDict := amtest.Obj("system_prompt", "changed", "tools", []any{"t"})
				cfg, cerr := value_objects.AgentConfigurationFromDict(cfgDict)
				if cerr != nil {
					t.Fatal(cerr)
				}
				var notes *string
				if s, ok := op[1].(string); ok {
					notes = &s
				}
				r = amtest.Result(nil, inst.CustomizeConfiguration(cfg, notes))
			case "track":
				inst.TrackUsage()
			case "gen":
				r = amtest.Result(nil, inst.GenerateShareToken(op[1].(string)))
			case "revoke":
				inst.RevokeShareToken()
			case "name":
				var email *string
				if s, ok := op[1].(string); ok {
					email = &s
				}
				r = inst.GetCreatorDisplayName(email)
			case "pub":
				r = inst.IsPublic()
			case "imp":
				r = inst.IsImported()
			}
			compare(t, fmt.Sprintf("instance %s %v step %d", label, ops, i+1), step(r, true), steps[i+1])
		}
	}
}
