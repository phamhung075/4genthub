// Package entities ports ai_task_planning/domain/entities.
package entities

import (
	"fmt"
	"time"

	tmentities "agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// ComplexityLevel is the task complexity classification.
type ComplexityLevel string

const (
	ComplexityTrivial  ComplexityLevel = "trivial"  // single action, <5 min
	ComplexitySimple   ComplexityLevel = "simple"   // single agent, <1 hour
	ComplexityModerate ComplexityLevel = "moderate" // multiple steps, <1 day
	ComplexityComplex  ComplexityLevel = "complex"  // multiple agents, days
	ComplexityEpic     ComplexityLevel = "epic"     // multiple features, weeks
)

var complexityLevels = []ComplexityLevel{ComplexityTrivial, ComplexitySimple, ComplexityModerate, ComplexityComplex, ComplexityEpic}

// ParseComplexityLevel is ComplexityLevel(value).
func ParseComplexityLevel(v string) (ComplexityLevel, error) {
	for _, l := range complexityLevels {
		if string(l) == v {
			return l, nil
		}
	}
	return "", &tmvo.ValueError{Msg: tmvo.PyRepr(v) + " is not a valid ComplexityLevel"}
}

// PlanningContext is the context for the planning request.
type PlanningContext string

const (
	PlanningContextNewFeature  PlanningContext = "new_feature"
	PlanningContextBugFix      PlanningContext = "bug_fix"
	PlanningContextRefactoring PlanningContext = "refactoring"
	PlanningContextMaintenance PlanningContext = "maintenance"
	PlanningContextResearch    PlanningContext = "research"
	PlanningContextIntegration PlanningContext = "integration"
)

var planningContexts = []PlanningContext{PlanningContextNewFeature, PlanningContextBugFix, PlanningContextRefactoring, PlanningContextMaintenance, PlanningContextResearch, PlanningContextIntegration}

// ParsePlanningContext is PlanningContext(value).
func ParsePlanningContext(v string) (PlanningContext, error) {
	for _, c := range planningContexts {
		if string(c) == v {
			return c, nil
		}
	}
	return "", &tmvo.ValueError{Msg: tmvo.PyRepr(v) + " is not a valid PlanningContext"}
}

// strs keeps empty Python lists serialising as [] instead of null.
func strs(s []string) []string {
	if s == nil {
		return []string{}
	}
	return s
}

// RequirementItem is an individual requirement within a planning request.
type RequirementItem struct {
	ID                  string
	Description         string
	Priority            string // low, medium, high, critical
	AcceptanceCriteria  []string
	Constraints         []string
	RelatedFiles        []string
	EstimatedComplexity *ComplexityLevel
}

// NewRequirementItem applies the Python defaults.
func NewRequirementItem(id, description string) *RequirementItem {
	return &RequirementItem{ID: id, Description: description, Priority: "medium",
		AcceptanceCriteria: []string{}, Constraints: []string{}, RelatedFiles: []string{}}
}

// PlanningRequest captures all information needed to generate a task breakdown.
type PlanningRequest struct {
	ID           string
	Title        string
	Description  string
	Requirements []*RequirementItem
	Context      PlanningContext

	ProjectID   *string
	GitBranchID *string
	UserID      *string

	Deadline          *time.Time
	AvailableAgents   []string
	PreferredApproach *string
	RiskTolerance     string // low, medium, high

	RelatedTasks      []string
	DocumentationRefs []string
	CodeReferences    *tmentities.OrderedMap[[]string] // file -> line ranges

	CreatedAt time.Time
	CreatedBy *string
	Tags      []string
}

// NewPlanningRequest applies the Python defaults (created_at is now, UTC).
func NewPlanningRequest(id, title, description string) *PlanningRequest {
	return &PlanningRequest{ID: id, Title: title, Description: description,
		Requirements: []*RequirementItem{}, Context: PlanningContextNewFeature, AvailableAgents: []string{},
		RiskTolerance: "medium", RelatedTasks: []string{}, DocumentationRefs: []string{},
		CodeReferences: tmentities.NewOrderedMap[[]string](), CreatedAt: time.Now().UTC(), Tags: []string{}}
}

// AddRequirement adds a new requirement with id "<id>_req_<n>"; nil criteria become [].
func (p *PlanningRequest) AddRequirement(description, priority string, acceptanceCriteria []string) *RequirementItem {
	r := NewRequirementItem(fmt.Sprintf("%s_req_%d", p.ID, len(p.Requirements)+1), description)
	r.Priority = priority
	if len(acceptanceCriteria) > 0 {
		r.AcceptanceCriteria = acceptanceCriteria
	}
	p.Requirements = append(p.Requirements, r)
	return r
}

// AddCodeReference appends line ranges for a file.
func (p *PlanningRequest) AddCodeReference(filePath string, lineRanges []string) {
	if p.CodeReferences == nil {
		p.CodeReferences = tmentities.NewOrderedMap[[]string]()
	}
	cur, ok := p.CodeReferences.Get(filePath)
	if !ok {
		cur = []string{}
	}
	p.CodeReferences.Set(filePath, append(cur, lineRanges...))
}

var complexityScores = map[ComplexityLevel]int{ComplexityTrivial: 1, ComplexitySimple: 2, ComplexityModerate: 3, ComplexityComplex: 4, ComplexityEpic: 5}

// EstimateOverallComplexity estimates complexity from the requirements.
func (p *PlanningRequest) EstimateOverallComplexity() ComplexityLevel {
	if len(p.Requirements) == 0 {
		return ComplexitySimple
	}
	total := 0
	for _, r := range p.Requirements {
		switch n := len(r.AcceptanceCriteria); {
		case r.EstimatedComplexity != nil:
			total += complexityScores[*r.EstimatedComplexity]
		case n > 5:
			total += 4
		case n > 2:
			total += 3
		default:
			total += 2
		}
	}
	avg := float64(total) / float64(len(p.Requirements))
	switch {
	case avg >= 4.5:
		return ComplexityEpic
	case avg >= 3.5:
		return ComplexityComplex
	case avg >= 2.5:
		return ComplexityModerate
	case avg >= 1.5:
		return ComplexitySimple
	default:
		return ComplexityTrivial
	}
}

func optStr(s *string) any {
	if s == nil {
		return nil
	}
	return *s
}

func optISO(t *time.Time) any {
	if t == nil {
		return nil
	}
	return tmvo.IsoFormat(*t)
}

// ToDict converts to the serialisable dictionary.
func (p *PlanningRequest) ToDict() *tmentities.OrderedMap[any] {
	reqs := make([]any, 0, len(p.Requirements))
	for _, r := range p.Requirements {
		var ec any
		if r.EstimatedComplexity != nil {
			ec = string(*r.EstimatedComplexity)
		}
		m := tmentities.NewOrderedMap[any]()
		m.Set("id", r.ID)
		m.Set("description", r.Description)
		m.Set("priority", r.Priority)
		m.Set("acceptance_criteria", strs(r.AcceptanceCriteria))
		m.Set("constraints", strs(r.Constraints))
		m.Set("related_files", strs(r.RelatedFiles))
		m.Set("estimated_complexity", ec)
		reqs = append(reqs, m)
	}
	refs := tmentities.NewOrderedMap[any]()
	if p.CodeReferences != nil {
		for _, k := range p.CodeReferences.Keys() {
			v, _ := p.CodeReferences.Get(k)
			refs.Set(k, strs(v))
		}
	}
	d := tmentities.NewOrderedMap[any]()
	d.Set("id", p.ID)
	d.Set("title", p.Title)
	d.Set("description", p.Description)
	d.Set("requirements", reqs)
	d.Set("context", string(p.Context))
	d.Set("project_id", optStr(p.ProjectID))
	d.Set("git_branch_id", optStr(p.GitBranchID))
	d.Set("user_id", optStr(p.UserID))
	d.Set("deadline", optISO(p.Deadline))
	d.Set("available_agents", strs(p.AvailableAgents))
	d.Set("preferred_approach", optStr(p.PreferredApproach))
	d.Set("risk_tolerance", p.RiskTolerance)
	d.Set("related_tasks", strs(p.RelatedTasks))
	d.Set("documentation_refs", strs(p.DocumentationRefs))
	d.Set("code_references", refs)
	d.Set("created_at", tmvo.IsoFormat(p.CreatedAt))
	d.Set("created_by", optStr(p.CreatedBy))
	d.Set("tags", strs(p.Tags))
	return d
}

// dict-reading helpers for FromDict. Python's `.get(k, default)` returns the stored value
// even when it is null or of another type; the typed Go port rejects a wrong type.
func dictStr(m *tmentities.OrderedMap[any], key, def string) (string, error) {
	v, ok := m.Get(key)
	if !ok {
		return def, nil
	}
	s, isStr := v.(string)
	if !isStr {
		return "", fmt.Errorf("%s must be a string", key)
	}
	return s, nil
}

func dictReqStr(m *tmentities.OrderedMap[any], key string) (string, error) {
	if !m.Has(key) {
		return "", fmt.Errorf("KeyError: %s", tmvo.PyRepr(key))
	}
	return dictStr(m, key, "")
}

func dictOptStr(m *tmentities.OrderedMap[any], key string) (*string, error) {
	v, _ := m.Get(key)
	if v == nil {
		return nil, nil
	}
	s, ok := v.(string)
	if !ok {
		return nil, fmt.Errorf("%s must be a string or null", key)
	}
	return &s, nil
}

func dictStrList(m *tmentities.OrderedMap[any], key string) ([]string, error) {
	v, ok := m.Get(key)
	if !ok {
		return []string{}, nil
	}
	items, isList := v.([]any)
	if !isList {
		return nil, fmt.Errorf("%s must be a list of strings", key)
	}
	out := make([]string, 0, len(items))
	for _, it := range items {
		s, isStr := it.(string)
		if !isStr {
			return nil, fmt.Errorf("%s must be a list of strings", key)
		}
		out = append(out, s)
	}
	return out, nil
}

func dictTime(m *tmentities.OrderedMap[any], key string) (*time.Time, error) {
	s, err := dictOptStr(m, key)
	if err != nil || s == nil || *s == "" {
		return nil, err
	}
	t, err := tmvo.ParseISO(*s)
	if err != nil {
		return nil, &tmvo.ValueError{Msg: "Invalid isoformat string: " + tmvo.PyRepr(*s)}
	}
	return &t, nil
}

// PlanningRequestFromDict creates a request from its dictionary form. Wrong value types
// are errors (Python stores them unvalidated); ISO strings are parsed by tmvo.ParseISO,
// so naive datetimes are read as UTC.
func PlanningRequestFromDict(data *tmentities.OrderedMap[any]) (*PlanningRequest, error) {
	var reqs []*RequirementItem
	if raw, ok := data.Get("requirements"); ok {
		items, isList := raw.([]any)
		if !isList {
			return nil, fmt.Errorf("requirements must be a list")
		}
		for _, it := range items {
			rm, isMap := it.(*tmentities.OrderedMap[any])
			if !isMap {
				return nil, fmt.Errorf("requirement must be an object")
			}
			r, err := requirementFromDict(rm)
			if err != nil {
				return nil, err
			}
			reqs = append(reqs, r)
		}
	}
	id, err := dictReqStr(data, "id")
	if err != nil {
		return nil, err
	}
	title, err := dictReqStr(data, "title")
	if err != nil {
		return nil, err
	}
	description, err := dictReqStr(data, "description")
	if err != nil {
		return nil, err
	}
	ctxText, err := dictStr(data, "context", string(PlanningContextNewFeature))
	if err != nil {
		return nil, err
	}
	ctx, err := ParsePlanningContext(ctxText)
	if err != nil {
		return nil, err
	}
	p := NewPlanningRequest(id, title, description)
	if reqs != nil {
		p.Requirements = reqs
	}
	p.Context = ctx
	if p.ProjectID, err = dictOptStr(data, "project_id"); err != nil {
		return nil, err
	}
	if p.GitBranchID, err = dictOptStr(data, "git_branch_id"); err != nil {
		return nil, err
	}
	if p.UserID, err = dictOptStr(data, "user_id"); err != nil {
		return nil, err
	}
	if p.Deadline, err = dictTime(data, "deadline"); err != nil {
		return nil, err
	}
	if p.AvailableAgents, err = dictStrList(data, "available_agents"); err != nil {
		return nil, err
	}
	if p.PreferredApproach, err = dictOptStr(data, "preferred_approach"); err != nil {
		return nil, err
	}
	if p.RiskTolerance, err = dictStr(data, "risk_tolerance", "medium"); err != nil {
		return nil, err
	}
	if p.RelatedTasks, err = dictStrList(data, "related_tasks"); err != nil {
		return nil, err
	}
	if p.DocumentationRefs, err = dictStrList(data, "documentation_refs"); err != nil {
		return nil, err
	}
	if raw, ok := data.Get("code_references"); ok {
		cm, isMap := raw.(*tmentities.OrderedMap[any])
		if !isMap {
			return nil, fmt.Errorf("code_references must be an object")
		}
		for _, k := range cm.Keys() {
			lines, err := dictStrList(cm, k)
			if err != nil {
				return nil, err
			}
			p.CodeReferences.Set(k, lines)
		}
	}
	// created_at: a missing key defaults to now; a present value is parsed strictly
	// (datetime.fromisoformat), so "" and null are errors.
	if raw, ok := data.Get("created_at"); ok {
		str, isStr := raw.(string)
		if !isStr {
			return nil, &tmvo.TypeError{Msg: "fromisoformat: argument must be str"}
		}
		t, err := tmvo.ParseISO(str)
		if err != nil {
			return nil, &tmvo.ValueError{Msg: "Invalid isoformat string: " + tmvo.PyRepr(str)}
		}
		p.CreatedAt = t
	}
	if p.CreatedBy, err = dictOptStr(data, "created_by"); err != nil {
		return nil, err
	}
	if p.Tags, err = dictStrList(data, "tags"); err != nil {
		return nil, err
	}
	return p, nil
}

func requirementFromDict(m *tmentities.OrderedMap[any]) (*RequirementItem, error) {
	id, err := dictReqStr(m, "id")
	if err != nil {
		return nil, err
	}
	description, err := dictReqStr(m, "description")
	if err != nil {
		return nil, err
	}
	r := NewRequirementItem(id, description)
	if r.Priority, err = dictStr(m, "priority", "medium"); err != nil {
		return nil, err
	}
	if r.AcceptanceCriteria, err = dictStrList(m, "acceptance_criteria"); err != nil {
		return nil, err
	}
	if r.Constraints, err = dictStrList(m, "constraints"); err != nil {
		return nil, err
	}
	if r.RelatedFiles, err = dictStrList(m, "related_files"); err != nil {
		return nil, err
	}
	ec, err := dictOptStr(m, "estimated_complexity")
	if err != nil {
		return nil, err
	}
	if ec != nil && *ec != "" {
		level, err := ParseComplexityLevel(*ec)
		if err != nil {
			return nil, err
		}
		r.EstimatedComplexity = &level
	}
	return r, nil
}
