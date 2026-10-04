// Package interfacelayer ports task_management/interface/ddd_compliant_mcp_tools.py.
package interfacelayer

import (
	"context"
	"fmt"
	"os"
	"strings"

	seatcontrollers "agenthub/fastmcp/seat_management/interface/mcp_controllers"
	"agenthub/fastmcp/task_management/application/services"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/configuration"
	"agenthub/fastmcp/task_management/infrastructure/utilities"
	"agenthub/fastmcp/task_management/interface/mcp_controllers/agent_mcp_controller"
	branchctl "agenthub/fastmcp/task_management/interface/mcp_controllers/git_branch_mcp_controller"
	projectctl "agenthub/fastmcp/task_management/interface/mcp_controllers/project_mcp_controller"
	projectfactories "agenthub/fastmcp/task_management/interface/mcp_controllers/project_mcp_controller/factories"
	projecthandlers "agenthub/fastmcp/task_management/interface/mcp_controllers/project_mcp_controller/handlers"
	subtaskctl "agenthub/fastmcp/task_management/interface/mcp_controllers/subtask_mcp_controller"
	subtaskfactories "agenthub/fastmcp/task_management/interface/mcp_controllers/subtask_mcp_controller/factories"
	subtaskhandlers "agenthub/fastmcp/task_management/interface/mcp_controllers/subtask_mcp_controller/handlers"
	taskctl "agenthub/fastmcp/task_management/interface/mcp_controllers/task_mcp_controller"
	taskfactories "agenthub/fastmcp/task_management/interface/mcp_controllers/task_mcp_controller/factories"
	contextctl "agenthub/fastmcp/task_management/interface/mcp_controllers/unified_context_controller"
	"agenthub/fastmcp/task_management/interface/mcp_controllers/workflow_hint_enhancer"
	"agenthub/fastmcp/task_management/interface/utils"
)

// DDDCompliantMCPTools orchestrates the MCP controllers for DDD-compliant tools.
type DDDCompliantMCPTools struct {
	Config               *configuration.ToolConfig
	PathResolver         *utilities.PathResolver
	FacadeService        *services.FacadeService
	TaskController       *taskctl.TaskMCPController
	SubtaskController    *subtaskctl.SubtaskMCPController
	ProjectController    *projectctl.ProjectMCPController
	GitBranchController  *branchctl.GitBranchMCPController
	AgentController      *agent_mcp_controller.AgentMCPController
	ManageSeatController *seatcontrollers.ManageSeatController
	CallSeatController   *seatcontrollers.CallSeatController
	ContextController    *contextctl.UnifiedContextMCPController // nil when the database is unavailable
	WorkflowHintEnhancer *workflow_hint_enhancer.WorkflowHintEnhancer
}

// Dependencies are the pieces Python obtains from module-level singletons
// (FacadeService.get_instance(), get_db_config()).
type Dependencies struct {
	FacadeService *services.FacadeService
	// DatabaseAvailable mirrors `get_db_config().SessionLocal` succeeding.
	DatabaseAvailable bool
	ManageSeat        *seatcontrollers.ManageSeatController
	CallSeat          *seatcontrollers.CallSeatController
}

// NewDDDCompliantMCPTools ports __init__(projects_file_path, config_overrides,
// enable_vision_system). The first parameter is ignored in Python and absent
// here; the Vision System is permanently disabled in Python (the argument is
// ignored) and so is not a parameter.
func NewDDDCompliantMCPTools(deps Dependencies, configOverrides map[string]any) (*DDDCompliantMCPTools, error) {
	cfg, err := configuration.NewToolConfig(toOrderedData(configOverrides))
	if err != nil {
		return nil, err
	}
	resolver, err := utilities.NewPathResolver()
	if err != nil {
		return nil, err
	}
	facadeService := deps.FacadeService
	if facadeService == nil {
		facadeService = services.GetInstance()
	}
	if facadeService == nil {
		return nil, fmt.Errorf("a FacadeService is required (services.SetInstance was never called)")
	}
	wireAuthHooks()
	wireWorkflowGuidance()
	t := &DDDCompliantMCPTools{Config: cfg, PathResolver: resolver, FacadeService: facadeService, ManageSeatController: deps.ManageSeat, CallSeatController: deps.CallSeat}
	formatter := utils.NewMCPResponseFormatter()
	if err := t.initControllers(deps, formatter); err != nil {
		return nil, err
	}
	t.WorkflowHintEnhancer = workflow_hint_enhancer.NewWorkflowHintEnhancer()
	return t, nil
}

func (t *DDDCompliantMCPTools) initControllers(deps Dependencies, formatter *utils.MCPResponseFormatter) error {
	task := taskResponseFormatter{formatter}
	meta := metaResponseFormatter{formatter}
	var err error

	if t.TaskController, err = taskctl.NewTaskMCPController(t.FacadeService,
		taskOperationAdapter{taskfactories.NewOperationFactory(task, nil)}, task, hintEnhancerAdapter{workflow_hint_enhancer.NewWorkflowHintEnhancer()}, t.Config); err != nil {
		return err
	}

	subtaskCRUD := subtaskhandlers.NewSubtaskCRUDHandler(meta, nil, nil, nil)
	subtaskProgress := subtaskhandlers.NewProgressHandler(nil, nil)
	subtaskctl.DefaultOperationFactory = subtaskfactories.NewSubtaskOperationFactory(meta, subtaskCRUDAdapter{subtaskCRUD}, subtaskProgressAdapter{subtaskProgress}, nil, nil)
	if t.SubtaskController, err = subtaskctl.NewSubtaskMCPController(t.FacadeService, nil, nil, nil, t.Config, meta); err != nil {
		return err
	}

	// Auto-create the global context on startup with a system user id (Python
	// swallows every failure of this step).
	if deps.DatabaseAvailable {
		if systemUserID := os.Getenv("SYSTEM_USER_ID"); systemUserID != "" {
			_, _ = t.FacadeService.GetContextFacade(&systemUserID, nil, nil)
		}
		t.ContextController = contextctl.NewUnifiedContextMCPController(t.FacadeService, meta)
	}

	projectCRUD := projecthandlers.NewProjectCRUDHandler(meta)
	projectMaintenance := projecthandlers.NewProjectMaintenanceHandler(meta)
	projectOperations := projectOperationAdapter{
		factory: projectfactories.NewProjectOperationFactory(meta, projectCRUDAdapter{projectCRUD}, projectMaintenanceAdapter{projectMaintenance}),
		crud:    projectCRUD, maintenance: projectMaintenance,
	}
	t.ProjectController = projectctl.NewProjectMCPController(nil, t.FacadeService, meta, projectOperations,
		projectfactories.NewProjectResponseFactory(meta))

	if t.GitBranchController, err = branchctl.NewGitBranchMCPController(t.FacadeService, t.Config, meta); err != nil {
		return err
	}
	if t.AgentController, err = agent_mcp_controller.NewAgentMCPController(t.FacadeService, t.Config, meta); err != nil {
		return err
	}
	return nil
}

// MCPServer is the tool-registration surface of the server (the FastMCP port
// belongs to the server context): Tool(name, description, fn).
type MCPServer interface {
	Tool(name string, description string, fn any)
}

// SchemaMCPServer is implemented by servers that publish the tool inputSchema
// (Python's FastMCP derives it from the function signature; Go carries it in
// ToolDefinition.Parameters). RegisterTools prefers it over Tool.
type SchemaMCPServer interface {
	MCPServer
	ToolWithSchema(name string, description string, inputSchema *entities.OrderedMap[any], fn any)
}

// ToolHandler is the signature of every tool function registered here: the
// decoded JSON arguments in, the controller's response out.
type ToolHandler func(ctx context.Context, args *entities.OrderedMap[any]) *entities.OrderedMap[any]

// ToolDefinition is one MCP tool: Python derives the input schema from the
// function signature; Go carries the explicit JSON schema (the controllers'
// *_description Parameters) next to the handler.
type ToolDefinition struct {
	Name        string
	Description string
	Parameters  *entities.OrderedMap[any]
	Handler     ToolHandler
}

func argString(args *entities.OrderedMap[any], key string) *string { return kwOptString(args, key) }

// argBool coerces the Python bool-ish tool arguments ("true", "1", "yes", "on").
func argBool(args *entities.OrderedMap[any], key string) *bool {
	if args == nil {
		return nil
	}
	var b bool
	switch v := args.GetAny(key).(type) {
	case nil:
		return nil
	case bool:
		b = v
	default:
		switch strings.ToLower(strings.TrimSpace(value_objects.PyStr(v))) {
		case "true", "1", "yes", "on":
			b = true
		}
	}
	return &b
}

func argsWithout(args *entities.OrderedMap[any], keys ...string) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	if args == nil {
		return out
	}
	skip := map[string]bool{}
	for _, k := range keys {
		skip[k] = true
	}
	for _, k := range args.Keys() {
		if !skip[k] {
			out.Set(k, args.GetAny(k))
		}
	}
	return out
}

func toAnyMap(args *entities.OrderedMap[any]) map[string]any {
	m := map[string]any{}
	if args != nil {
		for _, k := range args.Keys() {
			m[k] = args.GetAny(k)
		}
	}
	return m
}

func asOrdered(v any) *entities.OrderedMap[any] {
	if m, ok := v.(*entities.OrderedMap[any]); ok {
		return m
	}
	return toOrderedData(v)
}

// ToolDefinitions lists the tools Python's register_tools registers (manage_seat and
// call_seat are registered by their own controllers).
func (t *DDDCompliantMCPTools) ToolDefinitions() []ToolDefinition {
	defs := []ToolDefinition{
		{Name: "manage_task", Description: taskctl.GetManageTaskDescription(), Parameters: taskctl.GetManageTaskParameters(),
			Handler: func(ctx context.Context, a *entities.OrderedMap[any]) *entities.OrderedMap[any] {
				return t.TaskController.ManageTask(ctx, kwString(a, "action"), argString(a, "user_id"), argsWithout(a, "action", "user_id"))
			}},
		{Name: "manage_subtask", Description: subtaskctl.GetManageSubtaskDescription(), Parameters: subtaskctl.GetManageSubtaskParameters(),
			Handler: func(ctx context.Context, a *entities.OrderedMap[any]) *entities.OrderedMap[any] {
				return t.SubtaskController.ManageSubtask(ctx, kwString(a, "action"), kwString(a, "task_id"), argString(a, "user_id"), argsWithout(a, "action", "task_id", "user_id"))
			}},
	}
	if t.ContextController != nil {
		defs = append(defs, ToolDefinition{Name: "manage_context", Description: contextctl.GetManageUnifiedContextDescription(), Parameters: contextctl.GetManageUnifiedContextParameters(),
			Handler: func(ctx context.Context, a *entities.OrderedMap[any]) *entities.OrderedMap[any] {
				return t.ContextController.ManageContext(ctx, toAnyMap(a))
			}})
	}
	defs = append(defs,
		ToolDefinition{Name: "manage_project", Description: projectctl.GetManageProjectDescription(), Parameters: projectctl.GetManageProjectParameters(),
			Handler: func(ctx context.Context, a *entities.OrderedMap[any]) *entities.OrderedMap[any] {
				return t.ProjectController.ManageProject(ctx, kwString(a, "action"), argString(a, "project_id"), argString(a, "name"),
					argString(a, "description"), argBool(a, "force"), argString(a, "user_id"))
			}},
		ToolDefinition{Name: "manage_git_branch", Description: branchctl.GetManageGitBranchDescription(), Parameters: asOrdered(branchctl.GetManageGitBranchParameters()),
			Handler: func(ctx context.Context, a *entities.OrderedMap[any]) *entities.OrderedMap[any] {
				return t.GitBranchController.ManageGitBranch(ctx, kwString(a, "action"), argString(a, "project_id"), argString(a, "git_branch_id"),
					argString(a, "git_branch_name"), argString(a, "git_branch_description"), argString(a, "agent_id"), argString(a, "user_id"))
			}},
		ToolDefinition{Name: "manage_agent", Description: agent_mcp_controller.GetManageAgentDescription(), Parameters: asOrdered(agent_mcp_controller.GetManageAgentParameters()),
			Handler: func(ctx context.Context, a *entities.OrderedMap[any]) *entities.OrderedMap[any] {
				return t.AgentController.ManageAgent(ctx, kwString(a, "action"), argString(a, "project_id"), argString(a, "agent_id"),
					argString(a, "name"), argString(a, "call_agent"), argString(a, "git_branch_id"), argString(a, "user_id"))
			}},
	)
	for i := range defs {
		defs[i].Parameters = toolInputSchema(defs[i].Name, defs[i].Parameters)
	}
	return defs
}

// RegisterTools ports register_tools(mcp): task, subtask, context, project, git
// branch and agent tools, then manage_seat and call_seat through their own controllers.
func (t *DDDCompliantMCPTools) RegisterTools(mcp MCPServer) {
	schemaServer, withSchema := mcp.(SchemaMCPServer)
	for _, def := range t.ToolDefinitions() {
		if withSchema {
			schemaServer.ToolWithSchema(def.Name, def.Description, def.Parameters, def.Handler)
		} else {
			mcp.Tool(def.Name, def.Description, def.Handler)
		}
	}
	if t.ManageSeatController != nil {
		t.ManageSeatController.RegisterTools(mcp)
	}
	if t.CallSeatController != nil {
		t.CallSeatController.RegisterTools(mcp)
	}
}

// Wrapper methods kept by Python for tests and legacy callers.

// ManageProject delegates to the project controller.
func (t *DDDCompliantMCPTools) ManageProject(ctx context.Context, action string, projectID, name, description *string, force *bool, userID *string) *entities.OrderedMap[any] {
	return t.ProjectController.ManageProject(ctx, action, projectID, name, description, force, userID)
}

// ManageGitBranch delegates to the git branch controller.
func (t *DDDCompliantMCPTools) ManageGitBranch(ctx context.Context, action string, projectID, gitBranchID, gitBranchName, gitBranchDescription, agentID, userID *string) *entities.OrderedMap[any] {
	return t.GitBranchController.ManageGitBranch(ctx, action, projectID, gitBranchID, gitBranchName, gitBranchDescription, agentID, userID)
}

// ManageTask delegates to the task controller.
func (t *DDDCompliantMCPTools) ManageTask(ctx context.Context, action string, userID *string, kwargs *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	return t.TaskController.ManageTask(ctx, action, userID, kwargs)
}

// ManageSubtask delegates to the subtask controller.
func (t *DDDCompliantMCPTools) ManageSubtask(ctx context.Context, action, taskID string, userID *string, kwargs *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	return t.SubtaskController.ManageSubtask(ctx, action, taskID, userID, kwargs)
}

// ManageContext delegates to the context controller (nil when the database is unavailable,
// where Python raises AttributeError on None).
func (t *DDDCompliantMCPTools) ManageContext(ctx context.Context, kwargs map[string]any) *entities.OrderedMap[any] {
	return t.ContextController.ManageContext(ctx, kwargs)
}

// ManageAgent delegates to the agent controller.
func (t *DDDCompliantMCPTools) ManageAgent(ctx context.Context, action string, projectID, agentID, name, callAgent, gitBranchID, userID *string) *entities.OrderedMap[any] {
	return t.AgentController.ManageAgent(ctx, action, projectID, agentID, name, callAgent, gitBranchID, userID)
}
