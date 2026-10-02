package domain_test

import (
	"errors"
	"os"
	"regexp"
	"testing"

	"agenthub/fastmcp/task_management/domain"
	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

type obj = *entities.OrderedMap[any]

func field(v any, k string) any { x, _ := v.(obj).Get(k); return x }

func strp(v any) *string {
	if s, ok := v.(string); ok {
		return &s
	}
	return nil
}

func s(v any) string { x, _ := v.(string); return x }

func intp(v any) *int {
	if n, ok := v.(int64); ok {
		i := int(n)
		return &i
	}
	return nil
}

func strs(v any) []string {
	items, ok := v.([]any)
	if !ok {
		return nil
	}
	out := make([]string, len(items))
	for i, x := range items {
		out[i] = x.(string)
	}
	return out
}

var (
	wsIDRe = regexp.MustCompile(`"ws-[0-9a-f]{12}"`)
	tsRe   = regexp.MustCompile(`"\d{4}-\d\d-\d\dT[^"]*"`)
)

func canon(t *testing.T, v any) string {
	t.Helper()
	out, err := tmvo.PyJSONDumps(v, -1)
	if err != nil {
		t.Fatal(err)
	}
	out = wsIDRe.ReplaceAllString(out, `"ws-<id>"`)
	return tsRe.ReplaceAllStringFunc(out, func(m string) string {
		if len(m) > 6 && m[1:6] == "1999-" {
			return m
		}
		return `"<ts>"`
	})
}

// result is {"ok": v} or {"exc": type, "msg": text}.
func result(v any, err error) obj {
	m := entities.NewOrderedMap[any]()
	if err == nil {
		m.Set("ok", v)
		return m
	}
	var (
		ve *domain.ValidationError
		te *tmvo.TypeError
		ke *domain.KeyError
		vv *tmvo.ValueError
	)
	switch {
	case errors.As(err, &ve):
		m.Set("exc", "ValidationError")
	case errors.As(err, &te):
		m.Set("exc", "TypeError")
	case errors.As(err, &ke):
		m.Set("exc", "KeyError")
	case errors.As(err, &vv):
		m.Set("exc", "ValueError")
	default:
		m.Set("exc", "Error")
	}
	m.Set("msg", err.Error())
	return m
}

func dumpOf(p domain.Payload, err error) obj {
	if err != nil {
		return result(nil, err)
	}
	return result(p.ModelDump(), nil)
}

func newDelete(kind string, a []any) (domain.Payload, error) {
	switch kind {
	case "project", "project_delete":
		return nilIf(domain.NewProjectDeletePayload(s(a[0]), s(a[1])))
	case "branch", "branch_delete":
		return nilIf(domain.NewBranchDeletePayload(s(a[0]), s(a[1]), s(a[2])))
	case "task", "task_delete":
		return nilIf(domain.NewTaskDeletePayload(s(a[0]), s(a[1]), strp(a[2]), strp(a[3])))
	default:
		return nilIf(domain.NewSubtaskDeletePayload(s(a[0]), s(a[1]), strp(a[2])))
	}
}

// nilIf avoids a typed-nil Payload when the constructor failed.
func nilIf[T domain.Payload](p T, err error) (domain.Payload, error) {
	if err != nil {
		return nil, err
	}
	return p, nil
}

func newPayload(kind string, f any) domain.Payload {
	g := func(k string) any { return field(f, k) }
	switch kind {
	case "project_create":
		return domain.ProjectCreatePayload{ID: s(g("id")), Name: s(g("name")), Description: strp(g("description")), CreatedAt: strp(g("created_at")), UpdatedAt: strp(g("updated_at"))}
	case "project_update":
		return domain.ProjectUpdatePayload{ID: s(g("id")), Name: s(g("name")), Description: strp(g("description")), UpdatedAt: strp(g("updated_at"))}
	case "branch_create":
		return domain.BranchCreatePayload{ID: s(g("id")), Name: s(g("name")), GitBranchName: s(g("git_branch_name")), ProjectID: s(g("project_id")), Description: strp(g("description")), Status: strp(g("status")), CreatedAt: strp(g("created_at"))}
	case "branch_update":
		return domain.BranchUpdatePayload{ID: s(g("id")), Name: s(g("name")), GitBranchName: s(g("git_branch_name")), ProjectID: s(g("project_id")), Description: strp(g("description")), Status: strp(g("status")), UpdatedAt: strp(g("updated_at"))}
	case "task_create":
		return domain.TaskCreatePayload{ID: s(g("id")), Title: s(g("title")), Description: strp(g("description")), Status: s(g("status")), Priority: s(g("priority")), GitBranchID: s(g("git_branch_id")), ProjectID: strp(g("project_id")), Assignees: strs(g("assignees")), Labels: strs(g("labels")), CreatedAt: strp(g("created_at"))}
	case "task_update":
		return domain.TaskUpdatePayload{ID: s(g("id")), Title: s(g("title")), Description: strp(g("description")), Status: s(g("status")), Priority: s(g("priority")), GitBranchID: s(g("git_branch_id")), Assignees: strs(g("assignees")), Labels: strs(g("labels")), UpdatedAt: strp(g("updated_at"))}
	case "task_complete":
		return domain.TaskCompletePayload{ID: s(g("id")), Title: s(g("title")), CompletionSummary: strp(g("completion_summary")), TestingNotes: strp(g("testing_notes")), CompletedAt: strp(g("completed_at"))}
	case "subtask_create":
		return domain.SubtaskCreatePayload{ID: s(g("id")), Title: s(g("title")), Description: strp(g("description")), Status: s(g("status")), TaskID: s(g("task_id")), ProgressPercentage: intp(g("progress_percentage")), CreatedAt: strp(g("created_at")), UpdatedAt: strp(g("updated_at"))}
	case "subtask_update":
		return domain.SubtaskUpdatePayload{ID: s(g("id")), Title: s(g("title")), Description: strp(g("description")), Status: s(g("status")), TaskID: s(g("task_id")), ProgressPercentage: intp(g("progress_percentage")), CreatedAt: strp(g("created_at")), UpdatedAt: strp(g("updated_at"))}
	default:
		return domain.SubtaskCompletePayload{ID: s(g("id")), Title: s(g("title")), TaskID: s(g("task_id")), CompletionSummary: strp(g("completion_summary")), CreatedAt: strp(g("created_at")), UpdatedAt: strp(g("updated_at")), CompletedAt: strp(g("completed_at"))}
	}
}

func TestWebsocketProtocolParity(t *testing.T) {
	raw, err := os.ReadFile("testdata/ws_cases.json")
	if err != nil {
		t.Fatal(err)
	}
	cases, err := entities.DecodeJSON(raw)
	if err != nil {
		t.Fatal(err)
	}
	for i, c := range cases.([]any) {
		op := s(field(c, "op"))
		var got obj
		switch op {
		case "delete":
			got = dumpOf(newDelete(s(field(c, "kind")), field(c, "args").([]any)))
		case "dump":
			got = result(newPayload(s(field(c, "kind")), field(c, "fields")).ModelDump(), nil)
		case "message":
			pl := field(c, "payload")
			var payload domain.Payload
			var perr error
			if kind := s(field(pl, "kind")); len(kind) > 7 && kind[len(kind)-7:] == "_delete" {
				payload, perr = newDelete(kind, field(pl, "args").([]any))
			} else {
				payload = newPayload(kind, field(pl, "fields"))
			}
			if perr != nil {
				t.Fatalf("case %d: payload: %v", i, perr)
			}
			var overrides obj
			if o, ok := field(c, "overrides").(obj); ok {
				overrides = o
			}
			fn := map[string]func(string, domain.Payload, string, obj) (*domain.WSMessage, error){
				"delete": domain.CreateDeleteMessage, "update": domain.CreateUpdateMessage, "create": domain.CreateCreateMessage,
			}[s(field(c, "fn"))]
			msg, err := fn(s(field(c, "entity")), payload, s(field(c, "user")), overrides)
			if err != nil {
				got = result(nil, err)
			} else {
				got = result(msg.ModelDump(), nil)
			}
		case "validate_delete":
			data := map[string]any{}
			dm := field(c, "data").(obj)
			for _, k := range dm.Keys() {
				v, _ := dm.Get(k)
				data[k] = v
			}
			ok, errs := domain.ValidateDeletePayload(data)
			got = result([]any{ok, errs}, nil)
		case "legacy_task":
			snap, _ := field(c, "snapshot").(obj)
			p, err := domain.ConvertTaskDeleteLegacy(snap)
			got = dumpOf(nilIf(p, err))
		case "legacy_branch":
			a := field(c, "args").([]any)
			p, err := domain.ConvertBranchDeleteLegacy(s(a[0]), s(a[1]), s(a[2]))
			got = dumpOf(nilIf(p, err))
		case "legacy_subtask":
			a := field(c, "args").([]any)
			p, err := domain.ConvertSubtaskDeleteLegacy(s(a[0]), s(a[1]), strp(a[2]))
			got = dumpOf(nilIf(p, err))
		}
		if g, w := canon(t, got), canon(t, field(c, "out")); g != w {
			t.Fatalf("case %d (%s %v):\n got  %s\n want %s", i, op, tmvo.PyRepr(field(c, "kind")), g, w)
		}
	}
}
