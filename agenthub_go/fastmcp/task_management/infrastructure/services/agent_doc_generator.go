package services

import (
	"os"
	"path/filepath"
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	infrautil "agenthub/fastmcp/task_management/infrastructure/utilities"
	"agenthub/fastmcp/utilities"
	"agenthub/fastmcp/utilities/pyyaml"
)

// AgentDocGenerator converts YAML agent definitions to MDC format
// (agent_doc_generator.AgentDocGenerator).
type AgentDocGenerator struct {
	AgentYAMLLib    string
	AgentsOutputDir string
	ProjectRoot     string
	ConvertScript   string
}

// DefaultAgentYAMLLib and DefaultAgentsOutputDir are the module level constants computed
// from the project root at Python import time.
var (
	DefaultAgentYAMLLib    = defaultAgentYAMLLib()
	DefaultAgentsOutputDir = utilities.PyJoin(infrautil.DefaultEnv().FindProjectRoot(), ".cursor/rules/agents")
	DefaultConvertScript   = utilities.PyJoin(DefaultAgentYAMLLib, "convert_yaml_to_mdc_format.py")
)

func defaultAgentYAMLLib() string {
	root := infrautil.DefaultEnv().FindProjectRoot()
	if utilities.PyName(root) == "agenthub_main" {
		return utilities.PyJoin(root, "agent-library")
	}
	return utilities.PyJoin(root, "agenthub_main/agent-library")
}

// NewAgentDocGenerator resolves the YAML library and output directory the same way as
// AgentDocGenerator.__init__: explicit argument, then environment variable, then default.
func NewAgentDocGenerator(agentYAMLLib, agentsOutputDir *string) *AgentDocGenerator {
	projectRoot := infrautil.DefaultEnv().FindProjectRoot()
	resolve := func(path string) string {
		if utilities.PyIsAbs(path) {
			return utilities.PyPath(path)
		}
		return utilities.PyJoin(projectRoot, path)
	}

	yamlLib := ""
	if agentYAMLLib != nil {
		yamlLib = resolve(*agentYAMLLib)
	} else if env, ok := os.LookupEnv("AGENT_LIBRARY_DIR_PATH"); ok {
		yamlLib = resolve(env)
	} else if utilities.PyName(projectRoot) == "agenthub_main" {
		yamlLib = utilities.PyJoin(projectRoot, "agent-library")
	} else {
		yamlLib = utilities.PyJoin(projectRoot, "agenthub_main/agent-library")
	}

	output := ""
	if agentsOutputDir != nil {
		output = resolve(*agentsOutputDir)
	} else if env, ok := os.LookupEnv("AGENTS_OUTPUT_DIR"); ok {
		output = resolve(env)
	} else {
		output = utilities.PyJoin(projectRoot, ".cursor/rules/agents")
	}

	return &AgentDocGenerator{
		AgentYAMLLib:    yamlLib,
		AgentsOutputDir: output,
		ProjectRoot:     projectRoot,
		ConvertScript:   utilities.PyJoin(yamlLib, "convert_yaml_to_mdc_format.py"),
	}
}

// ClearAgentsOutputDir is AgentDocGenerator.clear_agents_output_dir.
func (g *AgentDocGenerator) ClearAgentsOutputDir() error {
	fi, err := os.Stat(g.AgentsOutputDir)
	if err != nil || !fi.IsDir() {
		return nil
	}
	entries, err := os.ReadDir(g.AgentsOutputDir)
	if err != nil {
		return err
	}
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		if err := os.Remove(filepath.Join(g.AgentsOutputDir, entry.Name())); err != nil {
			return err
		}
	}
	return nil
}

// ConvertYAMLToMDC is AgentDocGenerator.convert_yaml_to_mdc. On any error it returns the
// Python "(Error converting <name> to MDC: <err>)" text alongside the error.
func (g *AgentDocGenerator) ConvertYAMLToMDC(yamlFile string) (string, error) {
	data, err := os.ReadFile(yamlFile)
	if err != nil {
		return "(Error converting " + utilities.PyName(yamlFile) + " to MDC: " + err.Error() + ")", err
	}
	parsed, err := entities.LoadYAML(data)
	if err != nil {
		return "(Error converting " + utilities.PyName(yamlFile) + " to MDC: " + err.Error() + ")", err
	}
	out, err := pyyaml.Dump(parsed, true)
	if err != nil {
		return "(Error converting " + utilities.PyName(yamlFile) + " to MDC: " + err.Error() + ")", err
	}
	return out, nil
}

// GenerateAgentDocs is AgentDocGenerator.generate_agent_docs. A named agent that does not
// exist returns the Python "Agent directory '<name>' not found." error.
func (g *AgentDocGenerator) GenerateAgentDocs(agentName *string, clearAll bool) error {
	if err := os.MkdirAll(g.AgentsOutputDir, 0o777); err != nil {
		return err
	}
	if clearAll {
		if err := g.ClearAgentsOutputDir(); err != nil {
			return err
		}
	}

	var agentDirs []string
	if agentName != nil && *agentName != "" {
		target := utilities.PyJoin(g.AgentYAMLLib, *agentName)
		fi, err := os.Stat(target)
		if err != nil || !fi.IsDir() {
			return &value_objects.ValueError{Msg: "Agent directory '" + *agentName + "' not found."}
		}
		agentDirs = []string{target}
	} else {
		entries, err := os.ReadDir(g.AgentYAMLLib)
		if err != nil {
			return err
		}
		for _, entry := range entries {
			if entry.IsDir() && strings.HasSuffix(entry.Name(), "_agent") {
				agentDirs = append(agentDirs, filepath.Join(g.AgentYAMLLib, entry.Name()))
			}
		}
	}

	for _, agentDir := range agentDirs {
		if err := g.generateSingleAgentDoc(agentDir); err != nil {
			return err
		}
	}
	return nil
}

// generateSingleAgentDoc is AgentDocGenerator._generate_single_agent_doc.
func (g *AgentDocGenerator) generateSingleAgentDoc(agentDir string) error {
	jobDescFile := filepath.Join(agentDir, "job_desc.yaml")
	if _, err := os.Stat(jobDescFile); err != nil {
		return nil
	}
	data, err := os.ReadFile(jobDescFile)
	if err != nil {
		return nil
	}
	parsed, err := entities.LoadYAML(data)
	if err != nil {
		return nil
	}
	jobDesc := mapOfAny(parsed)

	dirName := utilities.PyName(agentDir)
	name := jobDescString(jobDesc, "name", dirName)
	mdLines := []string{"# " + name + "\n"}
	mdLines = append(mdLines, "**Slug:** `"+jobDescString(jobDesc, "slug", dirName)+"`  ")

	if v, ok := jobDesc["role_definition"]; ok {
		mdLines = append(mdLines, "**Role Definition:** "+value_objects.PyStr(v)+"  ")
	}
	if v, ok := jobDesc["when_to_use"]; ok {
		mdLines = append(mdLines, "**When to Use:** "+value_objects.PyStr(v)+"  ")
	}
	if v, ok := jobDesc["groups"]; ok {
		mdLines = append(mdLines, "**Groups:** "+strings.Join(stringList(v), ", ")+"  ")
	}

	mdLines = append(mdLines, "\n---\n")

	for _, subdir := range []string{"contexts", "rules", "tools", "output_format"} {
		subdirPath := filepath.Join(agentDir, subdir)
		fi, err := os.Stat(subdirPath)
		if err != nil || !fi.IsDir() {
			continue
		}
		mdLines = append(mdLines, "## "+value_objects.PyTitle(subdir)+"\n")
		matches, _ := filepath.Glob(filepath.Join(subdirPath, "*.yaml"))
		for _, file := range matches {
			mdLines = append(mdLines, "### "+stem(file)+"\n")
			section, _ := g.ConvertYAMLToMDC(file)
			mdLines = append(mdLines, section)
		}
	}

	outputFile := filepath.Join(g.AgentsOutputDir, dirName+".mdc")
	return os.WriteFile(outputFile, []byte(strings.Join(mdLines, "\n")), 0o666)
}

// GenerateDocsForAssignees is AgentDocGenerator.generate_docs_for_assignees.
func (g *AgentDocGenerator) GenerateDocsForAssignees(assignees []string, clearAll bool) error {
	if len(assignees) == 0 {
		return nil
	}
	seen := map[string]bool{}
	for _, assignee := range assignees {
		assigneeName := assignee
		if strings.HasPrefix(assignee, "@") {
			assigneeName = assignee[1:]
		}
		agentName := assigneeName
		if !strings.HasSuffix(assigneeName, "_agent") {
			agentName = assigneeName + "_agent"
		}
		if seen[agentName] {
			continue
		}
		seen[agentName] = true
		if err := g.GenerateAgentDocs(&agentName, clearAll); err != nil {
			return err
		}
	}
	return nil
}

func jobDescString(m map[string]any, key, def string) string {
	if v, ok := m[key].(string); ok {
		return v
	}
	return def
}

func stringList(v any) []string {
	switch x := v.(type) {
	case []any:
		out := make([]string, 0, len(x))
		for _, item := range x {
			out = append(out, value_objects.PyStr(item))
		}
		return out
	case []string:
		return x
	case *entities.OrderedMap[any]:
		return x.Keys()
	}
	return nil
}

func stem(path string) string {
	base := utilities.PyName(path)
	if i := strings.LastIndex(base, "."); i > 0 {
		return base[:i]
	}
	return base
}

// ClearAgentsOutputDir is the module level clear_agents_output_dir helper.
func ClearAgentsOutputDir() error {
	return NewAgentDocGenerator(nil, &DefaultAgentsOutputDir).ClearAgentsOutputDir()
}

// ConvertYAMLToMDC is the module level convert_yaml_to_mdc helper.
func ConvertYAMLToMDC(yamlFile string) (string, error) {
	return NewAgentDocGenerator(nil, nil).ConvertYAMLToMDC(yamlFile)
}

// GenerateAgentDocs is the module level generate_agent_docs helper.
func GenerateAgentDocs(agentName *string, clearAll bool) error {
	return NewAgentDocGenerator(&DefaultAgentYAMLLib, &DefaultAgentsOutputDir).GenerateAgentDocs(agentName, clearAll)
}

// GenerateDocsForAssignees is the module level generate_docs_for_assignees helper that
// logs and swallows generator errors, like Python.
func GenerateDocsForAssignees(assignees []string, clearAll bool) {
	_ = NewAgentDocGenerator(&DefaultAgentYAMLLib, &DefaultAgentsOutputDir).GenerateDocsForAssignees(assignees, clearAll)
}
