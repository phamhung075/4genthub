package rule

// Rule Workflow Guidance Implementation
// (Python workflow_guidance/rule/rule_workflow_guidance.py).

import (
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/interface/mcp_controllers/workflow_guidance"
)

// RuleWorkflowGuidance ports RuleWorkflowGuidance.
type RuleWorkflowGuidance struct {
	workflow_guidance.BaseWorkflowGuidance
}

// GenerateGuidance ports generate_guidance.
func (g *RuleWorkflowGuidance) GenerateGuidance(action string, context *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	out.Set("current_state", g.determineState(action, context))
	out.Set("rules", g.getRuleRules())
	out.Set("next_actions", g.getNextActions(action, context))
	out.Set("hints", g.getHints(action))
	out.Set("warnings", g.getWarnings(action))
	out.Set("examples", g.getExamples(action, context))
	out.Set("parameter_guidance", g.getParameterGuidance(action))
	return out
}

func (g *RuleWorkflowGuidance) determineState(action string, context *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	phaseMap := map[string]string{
		"list":                     "rule_listing",
		"backup":                   "rule_backup",
		"restore":                  "rule_restoration",
		"clean":                    "rule_cleanup",
		"info":                     "rule_information",
		"load_core":                "core_rule_loading",
		"parse_rule":               "rule_parsing",
		"analyze_hierarchy":        "hierarchy_analysis",
		"get_dependencies":         "dependency_analysis",
		"enhanced_info":            "enhanced_information",
		"compose_nested_rules":     "rule_composition",
		"resolve_rule_inheritance": "inheritance_resolution",
		"validate_rule_hierarchy":  "hierarchy_validation",
		"build_hierarchy":          "hierarchy_building",
		"load_nested":              "nested_loading",
		"cache_status":             "cache_inspection",
		"register_client":          "client_registration",
		"authenticate_client":      "client_authentication",
		"sync_client":              "client_synchronization",
		"client_diff":              "difference_calculation",
		"resolve_conflicts":        "conflict_resolution",
		"client_status":            "client_status_check",
		"client_analytics":         "analytics_retrieval",
	}
	phase, ok := phaseMap[action]
	if !ok {
		phase = "unknown"
	}
	out := entities.NewOrderedMap[any]()
	out.Set("phase", phase)
	out.Set("action", action)
	out.Set("context", "rule_management")
	return out
}

func (g *RuleWorkflowGuidance) getRuleRules() []any {
	return []any{
		"📜 RULE: Rules define operational guidelines and constraints for the system",
		"🎯 RULE: Core rules are loaded from predefined system configurations",
		"🏗️ RULE: Rules can have hierarchical relationships and dependencies",
		"🔄 RULE: Rule inheritance allows child rules to extend parent rules",
		"✅ RULE: Rule hierarchy must be validated to prevent circular dependencies",
		"💾 RULE: Always backup rules before making significant changes",
		"🔍 RULE: Parse and analyze rules before applying them to the system",
		"🤝 RULE: Client synchronization ensures all connected clients have consistent rules",
	}
}

func (g *RuleWorkflowGuidance) getNextActions(action string, context *entities.OrderedMap[any]) []any {
	target := workflow_guidance.ContextGet(context, "target")

	nextActions := []any{}

	switch action {
	case "list":
		nextActions = append(nextActions,
			ruleNext("high", "Get detailed rule information", "View specific rule details and structure",
				ruleExample("manage_rule", ruleParams(
					"action", "info",
					"target", "rule_name",
				))),
			ruleNext("medium", "Backup rules", "Create a backup before making changes",
				ruleExample("manage_rule", ruleParams(
					"action", "backup",
				))),
			ruleNext("medium", "Analyze rule hierarchy", "Understand rule relationships and dependencies",
				ruleExample("manage_rule", ruleParams(
					"action", "analyze_hierarchy",
				))),
		)
	case "backup":
		nextActions = append(nextActions,
			ruleNext("high", "Modify rules safely", "Now safe to make changes with backup available",
				ruleExample("manage_rule", ruleParams(
					"action", "parse_rule",
					"target", "new_rule",
					"content", "rule_content",
				))),
			ruleNext("medium", "View backup status", "Confirm backup was successful",
				ruleExample("manage_rule", ruleParams(
					"action", "info",
					"target", "backup",
				))),
		)
	case "restore":
		nextActions = append(nextActions,
			ruleNext("high", "Verify restoration", "Check that rules were restored correctly",
				ruleExample("manage_rule", ruleParams(
					"action", "list",
				))),
			ruleNext("medium", "Validate rule hierarchy", "Ensure restored rules are valid",
				ruleExample("manage_rule", ruleParams(
					"action", "validate_rule_hierarchy",
				))),
		)
	case "load_core":
		nextActions = append(nextActions,
			ruleNext("high", "List loaded rules", "See what core rules are now active",
				ruleExample("manage_rule", ruleParams(
					"action", "list",
				))),
			ruleNext("medium", "Sync with clients", "Update connected clients with new rules",
				ruleExample("manage_rule", ruleParams(
					"action", "sync_client",
					"target", "client_id",
				))),
		)
	case "parse_rule":
		nextActions = append(nextActions,
			ruleNext("high", "Validate parsed rule", "Check that the rule is valid",
				ruleExample("manage_rule", ruleParams(
					"action", "validate_rule_hierarchy",
					"target", workflow_guidance.OrValue(target, "parsed_rule"),
				))),
			ruleNext("medium", "Check dependencies", "Identify rule dependencies",
				ruleExample("manage_rule", ruleParams(
					"action", "get_dependencies",
					"target", workflow_guidance.OrValue(target, "parsed_rule"),
				))),
		)
	case "register_client":
		nextActions = append(nextActions,
			ruleNext("high", "Authenticate client", "Verify client credentials",
				ruleExample("manage_rule", ruleParams(
					"action", "authenticate_client",
					"target", "registered_client_id",
				))),
			ruleNext("high", "Sync rules to client", "Send current rules to the new client",
				ruleExample("manage_rule", ruleParams(
					"action", "sync_client",
					"target", "registered_client_id",
				))),
		)
	}
	return nextActions
}

func (g *RuleWorkflowGuidance) getHints(action string) []any {
	hints := map[string][]any{
		"list": {
			"💡 Review all active rules to understand system constraints",
			"🔍 Look for rules that might conflict with your intended changes",
			"📊 Consider the rule hierarchy and dependencies",
		},
		"backup": {
			"💾 Backup creates a snapshot of the current rule state",
			"🕐 Include timestamp in backup name for easy identification",
			"📦 Store backups in a safe location",
		},
		"restore": {
			"♻️ Restore overwrites current rules with backed up version",
			"⚠️ Any changes since backup will be lost",
			"✅ Always verify restoration was successful",
		},
		"info": {
			"📋 Provides detailed information about specific rules",
			"🔍 Use target parameter to specify which rule to inspect",
			"📊 Shows rule structure, dependencies, and metadata",
		},
		"load_core": {
			"🎯 Loads predefined system core rules",
			"🔄 This may override custom rules",
			"📋 Review loaded rules after operation",
		},
		"parse_rule": {
			"✏️ Parses rule content into system format",
			"🔍 Validates rule syntax and structure",
			"⚠️ Check for conflicts with existing rules",
		},
		"analyze_hierarchy": {
			"🏗️ Shows parent-child relationships between rules",
			"🔄 Identifies circular dependencies",
			"📊 Helps understand rule precedence",
		},
		"validate_rule_hierarchy": {
			"✅ Ensures rule hierarchy is valid and consistent",
			"🚫 Detects circular dependencies",
			"⚠️ Identifies missing parent rules",
		},
		"sync_client": {
			"🔄 Synchronizes rules with connected clients",
			"📡 Ensures all clients have consistent rule set",
			"⏱️ May take time for large rule sets",
		},
		"cache_status": {
			"💾 Shows current cache state and statistics",
			"🔍 Helps identify performance issues",
			"🔄 Consider clearing cache if stale",
		},
	}
	if v, ok := hints[action]; ok {
		return v
	}
	return []any{"💡 Check action parameter for available operations"}
}

func (g *RuleWorkflowGuidance) getWarnings(action string) []any {
	warnings := []any{}
	switch action {
	case "restore":
		warnings = append(warnings,
			"🚨 CRITICAL: This will overwrite all current rules!",
			"⚠️ Any changes since the backup will be lost",
			"💡 Consider backing up current rules first")
	case "clean":
		warnings = append(warnings,
			"⚠️ This will remove unused or invalid rules",
			"📋 Some functionality may be affected")
	case "load_core":
		warnings = append(warnings,
			"🔄 This may override custom rules",
			"💾 Backup current rules before loading core")
	case "resolve_conflicts":
		warnings = append(warnings,
			"⚠️ Conflict resolution may change rule behavior",
			"📋 Review resolution results carefully")
	case "compose_nested_rules":
		warnings = append(warnings,
			"🏗️ Complex operation that may affect rule hierarchy",
			"✅ Validate hierarchy after composition")
	}
	return warnings
}

func (g *RuleWorkflowGuidance) getExamples(action string, context *entities.OrderedMap[any]) []any {
	examples := []any{}
	switch action {
	case "list":
		examples = append(examples, ruleCodeExample("List all active rules",
			`manage_rule(
    action="list"
)`))
	case "backup":
		examples = append(examples, ruleCodeExample("Create a backup of current rules",
			`manage_rule(
    action="backup",
    target="backup_20250711"
)`))
	case "info":
		examples = append(examples, ruleCodeExample("Get information about a specific rule",
			`manage_rule(
    action="info",
    target="authentication_rule"
)`))
	case "parse_rule":
		examples = append(examples, ruleCodeExample("Parse and validate a new rule",
			`manage_rule(
    action="parse_rule",
    target="new_security_rule",
    content="rule: enforce_https { require: protocol == 'https' }"
)`))
	case "sync_client":
		examples = append(examples, ruleCodeExample("Synchronize rules with a client",
			`manage_rule(
    action="sync_client",
    target="client_abc123"
)`))
	}
	return examples
}

func (g *RuleWorkflowGuidance) getParameterGuidance(action string) *entities.OrderedMap[any] {
	baseParams := entities.NewOrderedMap[any]()
	baseParams.Set("action", ruleParamInfo(
		"REQUIRED",
		"String (valid action name)",
		"Specify the rule operation to perform",
	))

	actionParams := map[string]*entities.OrderedMap[any]{
		"list": ruleParams(),
		"backup": ruleParams(
			"target", ruleParamInfo(
				"OPTIONAL",
				"String",
				"Backup name/identifier (e.g., 'backup_20250711')",
			),
		),
		"restore": ruleParams(
			"target", ruleParamInfo(
				"OPTIONAL",
				"String",
				"Backup to restore from",
			),
		),
		"info": ruleParams(
			"target", ruleParamInfo(
				"OPTIONAL",
				"String",
				"Rule name or 'backup' for backup info",
			),
		),
		"parse_rule": ruleParams(
			"target", ruleParamInfo(
				"OPTIONAL",
				"String",
				"Name for the parsed rule",
			),
			"content", ruleParamInfo(
				"OPTIONAL",
				"String (rule syntax)",
				"Rule content to parse",
			),
		),
		"analyze_hierarchy": ruleParams(
			"target", ruleParamInfo(
				"OPTIONAL",
				"String",
				"Specific rule to analyze or empty for all",
			),
		),
		"get_dependencies": ruleParams(
			"target", ruleParamInfo(
				"OPTIONAL",
				"String",
				"Rule name to get dependencies for",
			),
		),
		"register_client": ruleParams(
			"target", ruleParamInfo(
				"OPTIONAL",
				"String",
				"Client identifier",
			),
			"content", ruleParamInfo(
				"OPTIONAL",
				"String (JSON)",
				"Client registration data",
			),
		),
		"sync_client": ruleParams(
			"target", ruleParamInfo(
				"OPTIONAL",
				"String",
				"Client ID to sync with",
			),
		),
	}

	params := baseParams.Copy()
	if extra, ok := actionParams[action]; ok {
		for _, k := range extra.Keys() {
			v, _ := extra.Get(k)
			params.Set(k, v)
		}
	} else {
		params.Set("target", ruleParamInfo(
			"OPTIONAL (default: '')",
			"String",
			"Target for the action",
		))
		params.Set("content", ruleParamInfo(
			"OPTIONAL (default: '')",
			"String",
			"Content for the action",
		))
	}
	return params
}

// --- local builders (unique to package rule) ---

func ruleParams(kv ...any) *entities.OrderedMap[any] {
	om := entities.NewOrderedMap[any]()
	for i := 0; i+1 < len(kv); i += 2 {
		om.Set(kv[i].(string), kv[i+1])
	}
	return om
}

func ruleExample(tool string, params *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	e := entities.NewOrderedMap[any]()
	e.Set("tool", tool)
	e.Set("params", params)
	return e
}

func ruleNext(priority, action, description string, example *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	a := entities.NewOrderedMap[any]()
	a.Set("priority", priority)
	a.Set("action", action)
	a.Set("description", description)
	a.Set("example", example)
	return a
}

func ruleCodeExample(description, code string) *entities.OrderedMap[any] {
	e := entities.NewOrderedMap[any]()
	e.Set("description", description)
	e.Set("code", code)
	return e
}

func ruleParamInfo(requirement, format, tip string) *entities.OrderedMap[any] {
	p := entities.NewOrderedMap[any]()
	p.Set("requirement", requirement)
	p.Set("format", format)
	p.Set("tip", tip)
	return p
}
