package entities_test

import (
	"sort"
	"testing"

	"agenthub/fastmcp/ai_task_planning/domain/entities"
	"agenthub/fastmcp/ai_task_planning/domain/internal/atptest"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
)

func compare(t *testing.T, label string, got, want any) {
	t.Helper()
	if g, w := atptest.Canon(t, got), atptest.Canon(t, want); g != w {
		t.Errorf("%s:\n got  %s\n want %s", label, g, w)
	}
}

func TestPlanningRequestParity(t *testing.T) {
	for _, c := range atptest.Items(atptest.Field(atptest.Fixture(t), "request")) {
		name := atptest.Str(c, "name")
		var got any
		p, err := entities.PlanningRequestFromDict(atptest.Map(atptest.Field(c, "in")))
		if err != nil {
			got = atptest.ErrMap(err)
		} else {
			for _, a := range atptest.Items(atptest.Field(c, "adds")) {
				row := atptest.Items(a)
				p.AddRequirement(row[0].(string), row[1].(string), atptest.Strs(row[2]))
			}
			for _, r := range atptest.Items(atptest.Field(c, "refs")) {
				row := atptest.Items(r)
				p.AddCodeReference(row[0].(string), atptest.Strs(row[1]))
			}
			got = atptest.Result(atptest.Obj("dict", p.ToDict(), "cx", string(p.EstimateOverallComplexity())), nil)
		}
		compare(t, name, got, atptest.Field(c, "out"))
	}
}

func buildTask(t *testing.T, s any) *entities.PlannedTask {
	t.Helper()
	task := entities.NewPlannedTask(atptest.Str(s, "id"), atptest.Str(s, "title"), atptest.Str(s, "description"),
		entities.TaskType(atptest.Str(s, "type")), entities.ExecutionPhase(atptest.Str(s, "phase")))
	task.EstimatedHours = atptest.Field(s, "hours").(float64)
	task.FileReferences = atptest.Strs(atptest.Field(s, "files"))
	task.AcceptanceCriteria = atptest.Strs(atptest.Field(s, "criteria"))
	task.TechnicalRequirements = atptest.Strs(atptest.Field(s, "tech"))
	task.Risks = atptest.Strs(atptest.Field(s, "risks"))
	task.Assumptions = atptest.Strs(atptest.Field(s, "assumptions"))
	task.Tags = atptest.Strs(atptest.Field(s, "tags"))
	task.Priority = atptest.Str(s, "priority")
	task.EstimatedComplexity = atptest.Str(s, "complexity")
	refs := atptest.Map(atptest.Field(s, "code_refs"))
	for _, k := range refs.Keys() {
		v, _ := refs.Get(k)
		task.CodeReferences.Set(k, atptest.Strs(v))
	}
	if a := atptest.Field(s, "assign"); a != nil {
		var eff *tmentities.OrderedMap[float64]
		if e := atptest.Field(a, "effort"); e != nil {
			eff = tmentities.NewOrderedMap[float64]()
			em := atptest.Map(e)
			for _, k := range em.Keys() {
				v, _ := em.Get(k)
				eff.Set(k, v.(float64))
			}
		}
		task.AgentAssignment = entities.NewAgentAssignment(atptest.Str(a, "primary"), atptest.Strs(atptest.Field(a, "supporting")), eff)
	}
	return task
}

func sortedAgents(d *tmentities.OrderedMap[any]) {
	v, _ := d.Get("required_agents")
	s := append([]string{}, v.([]string)...)
	sort.Strings(s)
	d.Set("required_agents", s)
}

func TestTaskPlanParity(t *testing.T) {
	for i, c := range atptest.Items(atptest.Field(atptest.Fixture(t), "plan")) {
		spec := atptest.Field(c, "in")
		plan := entities.NewTaskPlan("p1", "pr", "P", "PD")
		var built []*entities.PlannedTask
		for _, s := range atptest.Items(atptest.Field(spec, "tasks")) {
			task := buildTask(t, s)
			built = append(built, task)
			plan.AddTask(task)
		}
		for _, d := range atptest.Items(atptest.Field(spec, "deps")) {
			row := atptest.Items(d)
			plan.AddDependency(row[0].(string), row[1].(string), row[2].(string), int(row[3].(int64)))
		}
		for _, s := range atptest.Items(atptest.Field(spec, "subs")) {
			row := atptest.Items(s)
			built[row[0].(int64)].AddSubtask(built[row[1].(int64)])
		}
		dict0 := plan.ToDict()
		sortedAgents(dict0)
		req := plan.RequiredAgents.Items()
		sort.Strings(req)
		mcp := []any{}
		par := []any{}
		for _, x := range plan.Tasks {
			mcp = append(mcp, x.ToMCPTaskRequest())
			row := []any{}
			for _, y := range plan.Tasks {
				row = append(row, x.CanRunInParallel(y))
			}
			par = append(par, row)
		}
		roots := []string{}
		for _, r := range plan.GetRootTasks() {
			roots = append(roots, r.ID)
		}
		subtasks := []any{}
		for _, p := range plan.Tasks {
			ids := []string{}
			for _, s := range plan.GetSubtasks(p.ID) {
				ids = append(ids, s.ID)
			}
			subtasks = append(subtasks, ids)
		}
		byID := []any{}
		for _, id := range []string{"t0", "ghost", "zz"} {
			byID = append(byID, plan.GetTaskByID(id) != nil)
		}
		ok, errs := plan.ValidatePlan()
		groups := plan.FindParallelExecutionGroups()
		cp, cerr := plan.CalculateCriticalPath()
		var critical any
		if cerr != nil {
			critical = atptest.ErrMap(cerr)
		} else {
			critical = atptest.Obj("ok", cp)
		}
		dict1 := plan.ToDict()
		sortedAgents(dict1)
		got := atptest.Result(atptest.Obj("dict0", dict0, "required", req, "mcp", mcp, "par", par, "roots", roots,
			"subtasks", subtasks, "by_id", byID, "validate", []any{ok, errs}, "groups", groups, "critical", critical, "dict1", dict1), nil)
		compare(t, "plan #"+string(rune('0'+i%10)), got, atptest.Field(c, "out"))
	}
}
