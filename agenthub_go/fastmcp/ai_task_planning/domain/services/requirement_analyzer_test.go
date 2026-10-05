package services_test

import (
	"sort"
	"testing"

	"agenthub/fastmcp/ai_task_planning/domain/entities"
	"agenthub/fastmcp/ai_task_planning/domain/internal/atptest"
	"agenthub/fastmcp/ai_task_planning/domain/services"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
)

func toItem(v any) *entities.RequirementItem {
	r := entities.NewRequirementItem(atptest.Str(v, "id"), atptest.Str(v, "description"))
	r.AcceptanceCriteria = atptest.Strs(atptest.Field(v, "acceptance_criteria"))
	r.Constraints = atptest.Strs(atptest.Field(v, "constraints"))
	return r
}

func adict(a *services.AnalyzedRequirement) *tmentities.OrderedMap[any] {
	pats := make([]string, len(a.DetectedPatterns))
	for i, p := range a.DetectedPatterns {
		pats[i] = string(p)
	}
	agents := append([]string{}, a.SuggestedAgents...)
	sort.Strings(agents)
	return atptest.Obj("orig", a.OriginalRequirement.ID, "patterns", pats, "indicators", a.ComplexityIndicators,
		"agents", agents, "effort", a.EstimatedEffortHours, "risks", a.RiskFactors, "deps", a.Dependencies,
		"tech", a.TechnicalConsiderations)
}

func TestRequirementAnalyzerParity(t *testing.T) {
	an := services.NewRequirementAnalyzer()
	for i, c := range atptest.Items(atptest.Field(atptest.Fixture(t), "analyzer")) {
		in := atptest.Items(atptest.Field(c, "in"))
		var got any
		if atptest.Str(c, "kind") == "single" {
			got = atptest.Result(adict(an.AnalyzeRequirement(toItem(in[0]))), nil)
		} else {
			items := make([]*entities.RequirementItem, len(in))
			for j, r := range in {
				items[j] = toItem(r)
			}
			analyzed := an.AnalyzeRequirementsBatch(items)
			batch := []any{}
			for _, a := range analyzed {
				batch = append(batch, adict(a))
			}
			ins := an.GeneratePlanningInsights(analyzed)
			rec, _ := ins.Get("agent_recommendations")
			recMap := rec.(*tmentities.OrderedMap[any])
			keys := recMap.Keys()
			sort.Strings(keys)
			sorted := tmentities.NewOrderedMap[any]()
			for _, k := range keys {
				v, _ := recMap.Get(k)
				sorted.Set(k, v)
			}
			ins.Set("agent_recommendations", sorted)
			risks, _ := ins.Get("risk_summary")
			rs := append([]string{}, risks.([]string)...)
			sort.Strings(rs)
			ins.Set("risk_summary", rs)
			got = atptest.Result(atptest.Obj("batch", batch, "insights", ins), nil)
		}
		if g, w := atptest.Canon(t, got), atptest.Canon(t, atptest.Field(c, "out")); g != w {
			t.Fatalf("case %d (%v):\n got  %s\n want %s", i, in, g, w)
		}
	}
}
