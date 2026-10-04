package utilities

import (
	"os"
	"path/filepath"
	"strings"

	"agenthub/fastmcp"
	"agenthub/fastmcp/task_management/domain/entities"
	pypath "agenthub/fastmcp/utilities"
)

// findProjectRootMarkers are the markers find_project_root looks for.
var findProjectRootMarkers = []string{".git", "pyproject.toml", "setup.py", "package.json", "requirements.txt"}

// FindProjectRootByMarkers is path_resolver.find_project_root: it walks up from startPath
// (or the process working directory when startPath is nil) looking for the markers above,
// and returns the current working directory when none is found at or above startPath.
func FindProjectRootByMarkers(e Env, startPath *string) string {
	start := e.Cwd
	if startPath != nil {
		start = *startPath
	}
	current := pyResolve(e.Cwd, start)
	// Python loops `while current != current.parent`, so the filesystem root is never checked.
	for pypath.PyParent(current) != current {
		for _, marker := range findProjectRootMarkers {
			if e.Exists(current + "/" + marker) {
				return current
			}
		}
		current = pypath.PyParent(current)
	}
	return e.Cwd
}

// pyResolve is Path(p).resolve(): absolute (against cwd), with the symlinks of the longest
// existing prefix resolved (non-strict) and "."/".." collapsed.
func pyResolve(cwd, p string) string {
	if !pypath.PyIsAbs(p) {
		p = pypath.PyJoin(cwd, p)
	}
	p = filepath.Clean(p)
	rest := ""
	cur := p
	for {
		if resolved, err := filepath.EvalSymlinks(cur); err == nil {
			return filepath.Join(resolved, rest)
		}
		parent := filepath.Dir(cur)
		if parent == cur {
			return p
		}
		rest = filepath.Join(filepath.Base(cur), rest)
		cur = parent
	}
}

// EnsureProjectStructure is path_resolver.ensure_project_structure: it creates
// <projectRoot>/.cursor/rules and returns it.
func EnsureProjectStructure(projectRoot string) (string, error) {
	dir := projectRoot + "/.cursor/rules"
	if err := os.MkdirAll(dir, 0o777); err != nil {
		return "", err
	}
	return dir, nil
}

// pathResolverRulesProvider returns the dual-mode rules directory. It is a package
// variable so tests can substitute the process-wide dual-mode configuration.
var pathResolverRulesProvider = fastmcp.GetRulesDirectory

// pathResolverIsHTTPMode reports whether the process runs in HTTP mode; a package
// variable for the same reason as pathResolverRulesProvider.
var pathResolverIsHTTPMode = fastmcp.IsHTTPMode

// PathResolver handles dynamic path resolution and directory management for multiple
// projects (path_resolver.PathResolver).
type PathResolver struct {
	ProjectRoot    string
	CursorRulesDir string
	BrainDir       string
	ProjectsFile   string

	env Env
}

// NewPathResolver mirrors PathResolver.__init__, including creating the brain
// directory and (when missing) the projects file.
func NewPathResolver() (*PathResolver, error) {
	e := DefaultEnv()
	root := FindProjectRootByMarkers(e, nil)

	cursorDir, err := EnsureProjectStructure(root)
	if err != nil {
		return nil, err
	}

	r := &PathResolver{ProjectRoot: root, CursorRulesDir: cursorDir, env: e}

	brain := ".cursor/rules/brain"
	if v, ok := e.Getenv("BRAIN_DIR_PATH"); ok {
		brain = v
	}
	r.BrainDir = r.resolve(brain)

	projectsDefault := r.BrainDir + "/projects.json"
	if v, ok := e.Getenv("PROJECTS_FILE_PATH"); ok {
		projectsDefault = v
	}
	r.ProjectsFile = r.resolve(projectsDefault)

	if err := os.MkdirAll(r.BrainDir, 0o777); err != nil {
		return nil, err
	}
	if err := r.ensureProjectsFile(); err != nil {
		return nil, err
	}
	return r, nil
}

// resolve is PathResolver._resolve_path: an absolute path is used as-is, a relative one
// is joined to the project root.
func (r *PathResolver) resolve(path string) string {
	if strings.HasPrefix(path, "/") {
		return pypath.PyPath(path)
	}
	return pypath.PyJoin(r.ProjectRoot, path)
}

// EnsureBrainDir is PathResolver.ensure_brain_dir.
func (r *PathResolver) EnsureBrainDir() error { return os.MkdirAll(r.BrainDir, 0o777) }

// ensureProjectsFile is PathResolver._ensure_projects_file.
func (r *PathResolver) ensureProjectsFile() error {
	if r.env.Exists(r.ProjectsFile) {
		return nil
	}
	defaultProjects := "{\n  \"projects\": {},\n  \"metadata\": {\n    \"version\": \"1.0\",\n    \"created_at\": \"auto-generated\",\n    \"description\": \"Project management configuration\"\n  }\n}"
	if err := os.MkdirAll(pypath.PyParent(r.ProjectsFile), 0o777); err != nil {
		return err
	}
	if err := os.WriteFile(r.ProjectsFile, []byte(defaultProjects), 0o666); err != nil {
		// Python falls back to the project-relative path when the environment-specified
		// path is not writable (PermissionError / OSError).
		fallback := pypath.PyJoin(r.ProjectRoot, ".cursor/rules/brain/projects.json")
		if mkErr := os.MkdirAll(pypath.PyParent(fallback), 0o777); mkErr != nil {
			return mkErr
		}
		if fbErr := os.WriteFile(fallback, []byte(defaultProjects), 0o666); fbErr != nil {
			return fbErr
		}
		r.ProjectsFile = fallback
	}
	return nil
}

// GetTasksJSONPath is PathResolver.get_tasks_json_path.
func (r *PathResolver) GetTasksJSONPath(projectID, gitBranchName string, userID *string) (string, error) {
	var tasksPath string
	if projectID != "" {
		user := "None" // f"{user_id}" for a None user id
		if userID != nil {
			user = *userID
		}
		tasksPath = r.resolve(".cursor/rules/tasks/" + user + "/" + projectID + "/" + gitBranchName + "/tasks.json")
	} else {
		def := ".cursor/rules/tasks/tasks.json"
		if v, ok := r.env.Getenv("TASKS_JSON_PATH"); ok {
			def = v
		}
		tasksPath = r.resolve(def)
	}
	if err := os.MkdirAll(pypath.PyParent(tasksPath), 0o777); err != nil {
		return "", err
	}
	return tasksPath, nil
}

// GetLegacyTasksJSONPath is PathResolver.get_legacy_tasks_json_path.
func (r *PathResolver) GetLegacyTasksJSONPath() string {
	return r.resolve(".cursor/rules/tasks/tasks.json")
}

// GetAutoRulePath is PathResolver.get_auto_rule_path.
func (r *PathResolver) GetAutoRulePath() string {
	def := ".cursor/rules/auto_rule.mdc"
	if v, ok := r.env.Getenv("AUTO_RULE_PATH"); ok {
		def = v
	}
	return r.resolve(def)
}

// GetRulesDirectoryFromSettings is PathResolver.get_rules_directory_from_settings. Any error
// while reading or interpreting a settings file aborts the lookup and yields the dual-mode default.
func (r *PathResolver) GetRulesDirectoryFromSettings() string {
	defaultRules := pathResolverRulesProvider()
	if r.env.Exists(defaultRules) {
		return defaultRules
	}
	if !pathResolverIsHTTPMode() {
		rules, found, ok := r.settingsRulesPath()
		if !ok {
			return defaultRules
		}
		if found {
			return rules
		}
		if v, ok := r.env.Getenv("DOCUMENT_RULES_PATH"); ok {
			return r.resolve(v)
		}
	}
	return defaultRules
}

// settingsRulesPath reads DOCUMENT_RULES_PATH from the first existing of
// 00_RULES/core/settings.json and .cursor/settings.json. found is false when neither file
// exists; ok is false when the file exists but cannot be read or interpreted.
func (r *PathResolver) settingsRulesPath() (path string, found, ok bool) {
	for _, rel := range []string{"00_RULES/core/settings.json", ".cursor/settings.json"} {
		file := pypath.PyJoin(r.ProjectRoot, rel)
		if !r.env.Exists(file) {
			continue
		}
		data, err := os.ReadFile(file)
		if err != nil {
			return "", true, false
		}
		decoded, err := entities.DecodeJSON(data)
		if err != nil {
			return "", true, false
		}
		settings, isDict := decoded.(*entities.OrderedMap[any])
		if !isDict {
			return "", true, false
		}
		var rulesPath any = "00_RULES"
		if rcRaw, has := settings.Get("runtime_constants"); has {
			rc, isDict := rcRaw.(*entities.OrderedMap[any])
			if !isDict {
				return "", true, false
			}
			if v, has := rc.Get("DOCUMENT_RULES_PATH"); has {
				rulesPath = v
			}
		}
		str, isStr := rulesPath.(string)
		if !isStr {
			return "", true, false
		}
		return r.resolve(str), true, true
	}
	return "", false, true
}
