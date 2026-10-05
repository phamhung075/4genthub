package services

import (
	"context"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// chvGlobalSingletonUUID mirrors GLOBAL_SINGLETON_UUID from the Python models.
const chvGlobalSingletonUUID = "00000000-0000-0000-0000-000000000001"

// HierarchyContextRepo is the minimal duck-typed repository surface the Python
// validator relies on: get(id) and list().
type HierarchyContextRepo interface {
	Get(ctx context.Context, id string) (any, error)
	List(ctx context.Context) ([]any, error)
}

// ContextHierarchyValidator validates context hierarchy requirements.
type ContextHierarchyValidator struct {
	GlobalRepo  HierarchyContextRepo
	ProjectRepo HierarchyContextRepo
	BranchRepo  HierarchyContextRepo
	TaskRepo    HierarchyContextRepo
	UserID      *string
}

// NewContextHierarchyValidator mirrors ContextHierarchyValidator.__init__.
func NewContextHierarchyValidator(globalRepo, projectRepo, branchRepo, taskRepo HierarchyContextRepo, userID *string) *ContextHierarchyValidator {
	return &ContextHierarchyValidator{GlobalRepo: globalRepo, ProjectRepo: projectRepo, BranchRepo: branchRepo, TaskRepo: taskRepo, UserID: userID}
}

// ValidateHierarchyRequirements mirrors validate_hierarchy_requirements.
func (v *ContextHierarchyValidator) ValidateHierarchyRequirements(level value_objects.ContextLevel, contextID string, data *entities.OrderedMap[any]) (bool, *string, *entities.OrderedMap[any]) {
	switch level {
	case value_objects.ContextLevelGlobal:
		return true, nil, nil
	case value_objects.ContextLevelProject:
		return v.validateProjectRequirements(contextID)
	case value_objects.ContextLevelBranch:
		return v.validateBranchRequirements(contextID, data)
	case value_objects.ContextLevelTask:
		return v.validateTaskRequirements(contextID, data)
	}
	msg := "Unknown context level: " + level.String()
	return false, &msg, nil
}

func (v *ContextHierarchyValidator) validateProjectRequirements(projectID string) (bool, *string, *entities.OrderedMap[any]) {
	globalContext, err := v.GlobalRepo.Get(context.Background(), chvGlobalSingletonUUID)
	if err != nil {
		globalContext = nil
	}
	if globalContext == nil {
		globalContexts, lerr := v.GlobalRepo.List(context.Background())
		if lerr == nil && len(globalContexts) > 0 {
			globalContext = globalContexts[0]
		}
	}
	if globalContext == nil {
		m := entities.NewOrderedMap[any]()
		m.Set("warning", "Global context will be auto-created")
		m.Set("explanation", "The system will automatically create a global context if needed during project context creation.")
		m.Set("auto_creation", true)
		m.Set("recommended_action", "Consider creating global context explicitly for better control")
		m.Set("command", `manage_context(action="create", level="global", context_id="global", data={"autonomous_rules": {}, "security_policies": {}})`)
		return true, nil, m
	}
	return true, nil, nil
}

func (v *ContextHierarchyValidator) validateBranchRequirements(branchID string, data *entities.OrderedMap[any]) (bool, *string, *entities.OrderedMap[any]) {
	if data == nil {
		data = entities.NewOrderedMap[any]()
	}
	var projectID string
	if val, ok := data.Get("project_id"); ok {
		if s, ok := val.(string); ok {
			projectID = s
		}
	}
	if projectID == "" {
		if val, ok := data.Get("parent_project_id"); ok {
			if s, ok := val.(string); ok {
				projectID = s
			}
		}
	}
	if projectID == "" && v.BranchRepo != nil {
		gitBranch, err := v.BranchRepo.Get(context.Background(), branchID)
		if err == nil && gitBranch != nil {
			if pid, ok := chvProjectID(gitBranch); ok {
				projectID = pid
				data.Set("project_id", projectID)
			}
		}
	}
	if projectID == "" {
		isAuto := false
		if val, ok := data.Get("source"); ok {
			if s, ok := val.(string); ok && s == "task_creation_auto_create" {
				isAuto = true
			}
		}
		if val, ok := data.Get("auto_created"); ok {
			if b, ok := val.(bool); ok && b {
				isAuto = true
			}
		}
		if isAuto {
			m := entities.NewOrderedMap[any]()
			m.Set("warning", "Branch context created without project_id for task creation auto-creation")
			m.Set("explanation", "Branch context auto-created to prevent foreign key violations during task creation. Project_id will be set when git branch is created.")
			m.Set("auto_creation", true)
			return true, nil, m
		}
		msg := "Branch context requires project_id"
		m := entities.NewOrderedMap[any]()
		m.Set("error", "Missing required field: project_id")
		m.Set("explanation", "Branch contexts must be associated with a project. Could not auto-resolve project_id from git_branch_id.")
		rf := entities.NewOrderedMap[any]()
		rf.Set("project_id", "The ID of the parent project (auto-detection failed)")
		m.Set("required_fields", rf)
		m.Set("auto_resolution_failed", "Attempted to resolve project_id from git_branch_id '"+branchID+"' but the branch was not found or has no project_id.")
		m.Set("solutions", []string{
			"Provide project_id explicitly in the data parameter",
			"Ensure the git branch exists before creating its context",
			"Create the git branch first using manage_git_branch",
		})
		m.Set("example", `manage_context(action="create", level="branch", context_id="`+branchID+`", data={"git_branch_name": "feature/branch"})`)
		m.Set("example_with_project", `manage_context(action="create", level="branch", context_id="`+branchID+`", data={"project_id": "your-project-id", "git_branch_name": "feature/branch"})`)
		return false, &msg, m
	}

	projectContext, err := v.ProjectRepo.Get(context.Background(), projectID)
	if err != nil {
		msg := "Project context must exist first"
		m := entities.NewOrderedMap[any]()
		m.Set("error", "Cannot verify project context: "+projectID)
		m.Set("suggestion", "Create the project context first, then retry creating the branch context")
		return false, &msg, m
	}
	if projectContext == nil {
		m := entities.NewOrderedMap[any]()
		m.Set("warning", "Parent project context '"+projectID+"' will be auto-created")
		m.Set("explanation", "The system will automatically create the required project context during branch context creation")
		m.Set("hierarchy", "Global → Project → Branch → Task")
		m.Set("auto_creation", true)
		actions := []any{}
		a1 := entities.NewOrderedMap[any]()
		a1.Set("description", "Ensure global context exists")
		a1.Set("command", `manage_context(action="get", level="global", context_id="global")`)
		actions = append(actions, a1)
		a2 := entities.NewOrderedMap[any]()
		a2.Set("description", "Create project context explicitly for better control")
		a2.Set("command", `manage_context(action="create", level="project", context_id="`+projectID+`", data={"project_name": "Your Project"})`)
		actions = append(actions, a2)
		a3 := entities.NewOrderedMap[any]()
		a3.Set("step", 3)
		a3.Set("description", "Then create your branch context")
		a3.Set("command", `manage_context(action="create", level="branch", context_id="`+branchID+`", data={"project_id": "`+projectID+`", "git_branch_name": "your-branch"})`)
		actions = append(actions, a3)
		m.Set("recommended_actions", actions)
		return true, nil, m
	}
	return true, nil, nil
}

func (v *ContextHierarchyValidator) validateTaskRequirements(taskID string, data *entities.OrderedMap[any]) (bool, *string, *entities.OrderedMap[any]) {
	branchID := ""
	if data != nil {
		for _, key := range []string{"branch_id", "parent_branch_id", "git_branch_id"} {
			if val, ok := data.Get(key); ok {
				if s, ok := val.(string); ok && s != "" {
					branchID = s
					break
				}
			}
		}
	}
	if branchID == "" {
		msg := "Missing required field: branch_id (or parent_branch_id or git_branch_id)"
		m := entities.NewOrderedMap[any]()
		m.Set("error", "Missing required field: branch_id (or parent_branch_id or git_branch_id)")
		m.Set("explanation", "Task contexts must be associated with a git branch (task tree)")
		rf := entities.NewOrderedMap[any]()
		rf.Set("branch_id", "The ID of the parent git branch")
		rf.Set("alternative_names", []string{"parent_branch_id", "git_branch_id"})
		m.Set("required_fields", rf)
		m.Set("example", `manage_context(action="create", level="task", context_id="`+taskID+`", data={"branch_id": "your-branch-id", "task_data": {"title": "Task Title"}})`)
		m.Set("tip", `You can find branch IDs using: manage_git_branch(action="list", project_id="your-project-id")`)
		return false, &msg, m
	}

	gitBranch, err := v.BranchRepo.Get(context.Background(), branchID)
	if err != nil {
		msg := "Cannot verify branch context: " + branchID
		m := entities.NewOrderedMap[any]()
		m.Set("warning", "Cannot verify branch context: "+branchID+" - allowing creation")
		m.Set("explanation", "The system will attempt to create necessary parent contexts automatically")
		m.Set("auto_creation", true)
		m.Set("error_details", err.Error())
		return true, &msg, m
	}
	if gitBranch == nil {
		projectHint := ""
		if data != nil {
			if val, ok := data.Get("project_id"); ok {
				if s, ok := val.(string); ok {
					projectHint = `, project_id="` + s + `"`
				}
			}
		}
		m := entities.NewOrderedMap[any]()
		m.Set("warning", "Parent branch context '"+branchID+"' will be auto-created")
		m.Set("explanation", "The system will automatically create the required branch context during task context creation if possible")
		m.Set("hierarchy", "Global → Project → Branch → Task")
		m.Set("auto_creation", true)
		m.Set("context_creation_order", []string{
			"1. Global context (auto-created)",
			"2. Project context (auto-created)",
			"3. Branch context (auto-created)",
			"4. Task context (current)",
		})
		actions := []any{}
		a1 := entities.NewOrderedMap[any]()
		a1.Set("description", "Create branch context explicitly for better control")
		a1.Set("command", `manage_context(action="create", level="branch", context_id="`+branchID+`", data={"project_id": "your-project-id"`+projectHint+`})`)
		actions = append(actions, a1)
		a2 := entities.NewOrderedMap[any]()
		a2.Set("description", "Alternative: Create git branch first")
		a2.Set("command", `manage_git_branch(action="create", project_id="your-project-id", git_branch_name="feature/branch")`)
		actions = append(actions, a2)
		m.Set("recommended_actions", actions)
		m.Set("alternative", "If you're unsure of the branch_id, list available branches using manage_git_branch")
		return true, nil, m
	}
	return true, nil, nil
}

// GetHierarchyStatus mirrors ContextHierarchyValidator.get_hierarchy_status.
func (v *ContextHierarchyValidator) GetHierarchyStatus() *entities.OrderedMap[any] {
	status := entities.NewOrderedMap[any]()
	status.Set("hierarchy_levels", []string{"global", "project", "branch", "task"})
	currentState := entities.NewOrderedMap[any]()
	status.Set("current_state", currentState)

	globalCtx, err := v.GlobalRepo.Get(context.Background(), "global_singleton")
	if err != nil {
		currentState.Set("global", chvExistsState(false))
	} else {
		g := entities.NewOrderedMap[any]()
		g.Set("exists", globalCtx != nil)
		g.Set("id", "global_singleton")
		currentState.Set("global", g)
	}

	projects, err := v.ProjectRepo.List(context.Background())
	if err != nil {
		p := entities.NewOrderedMap[any]()
		p.Set("count", 0)
		currentState.Set("projects", p)
	} else {
		p := entities.NewOrderedMap[any]()
		p.Set("count", len(projects))
		p.Set("hint", "Use manage_project(action='list') for details")
		currentState.Set("projects", p)
	}

	branches, err := v.BranchRepo.List(context.Background())
	if err != nil {
		b := entities.NewOrderedMap[any]()
		b.Set("count", 0)
		currentState.Set("branches", b)
	} else {
		b := entities.NewOrderedMap[any]()
		b.Set("count", len(branches))
		b.Set("hint", "Use manage_git_branch(action='list') for details")
		currentState.Set("branches", b)
	}

	tasks, err := v.TaskRepo.List(context.Background())
	if err != nil {
		t := entities.NewOrderedMap[any]()
		t.Set("count", 0)
		currentState.Set("tasks", t)
	} else {
		t := entities.NewOrderedMap[any]()
		t.Set("count", len(tasks))
		t.Set("hint", "Use manage_task(action='list') for details")
		currentState.Set("tasks", t)
	}
	return status
}

func chvExistsState(exists bool) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("exists", exists)
	return m
}

// chvProjectID extracts project_id from a repository result, mirroring
// hasattr(git_branch, "project_id").
func chvProjectID(v any) (string, bool) {
	switch b := v.(type) {
	case *entities.GitBranch:
		return b.ProjectID, true
	}
	if p, ok := v.(interface{ GetProjectID() string }); ok {
		return p.GetProjectID(), true
	}
	if p, ok := v.(interface{ ProjectID() string }); ok {
		return p.ProjectID(), true
	}
	return "", false
}
