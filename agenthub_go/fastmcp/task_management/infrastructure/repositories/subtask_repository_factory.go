package repositories

// Subtask Repository Factory (Python repositories/subtask_repository_factory.py): builds
// subtask repositories scoped to a user/project/task tree. The central RepositoryFactory
// (repository_factory.py) is not yet ported, so create_subtask_repository and
// create_sqlite_subtask_repository delegate to the SubtaskRepositoryFactoryBackend hook.

import (
	"os"
	"runtime"

	"agenthub/fastmcp/task_management/infrastructure/database"
	"agenthub/fastmcp/utilities"

	domainrepos "agenthub/fastmcp/task_management/domain/repositories"
)

// SubtaskRepositoryFactoryBackend is the central RepositoryFactory.get_subtask_repository used
// by the factory (not yet ported).
type SubtaskRepositoryFactoryBackend interface {
	GetSubtaskRepository(userID *string) (domainrepos.SubtaskRepository, error)
}

var subtaskRepoFactoryBackend SubtaskRepositoryFactoryBackend

// SetSubtaskRepositoryFactoryBackend registers the central repository factory.
func SetSubtaskRepositoryFactoryBackend(backend SubtaskRepositoryFactoryBackend) {
	subtaskRepoFactoryBackend = backend
}

// SubtaskRepositoryFactory creates subtask repositories for a user/project/tree.
type SubtaskRepositoryFactory struct {
	ProjectRoot   string
	BasePath      string
	DefaultUserID *string
	// Sessions is the Go counterpart of the session created by ORMSubtaskRepository itself.
	Sessions *database.SessionManager
}

// NewSubtaskRepositoryFactory mirrors the constructor with optional base_path, default_user_id
// and project_root.
func NewSubtaskRepositoryFactory(basePath, defaultUserID, projectRoot *string, sessions *database.SessionManager) *SubtaskRepositoryFactory {
	root := FindProjectRoot()
	if projectRoot != nil {
		root = *projectRoot
	}
	base := utilities.PyJoin(root, ".cursor", "rules", "subtasks")
	if basePath != nil && *basePath != "" {
		base = *basePath
	}
	return &SubtaskRepositoryFactory{ProjectRoot: root, BasePath: base, DefaultUserID: defaultUserID, Sessions: sessions}
}

// FindProjectRoot is _find_project_root.
func FindProjectRoot() string {
	_, file, _, _ := runtime.Caller(0)
	currentPath := utilities.PyPath(file)
	for utilities.PyParent(currentPath) != currentPath {
		if subtaskRepoFactoryPathExists(utilities.PyJoin(currentPath, "agenthub_main")) {
			return currentPath
		}
		currentPath = utilities.PyParent(currentPath)
	}
	cwd, _ := os.Getwd()
	cwd = utilities.PyPath(cwd)
	if subtaskRepoFactoryPathExists(utilities.PyJoin(cwd, "agenthub_main")) {
		return cwd
	}
	currentPath = utilities.PyPath(file)
	for utilities.PyParent(currentPath) != currentPath {
		if utilities.PyName(currentPath) == "agenthub_main" {
			return utilities.PyParent(currentPath)
		}
		currentPath = utilities.PyParent(currentPath)
	}
	dataPath := subtaskRepoFactoryGetenv("AGENTHUB_DATA_PATH", "/data")
	if !subtaskRepoFactoryPathExists(dataPath) {
		cwd, _ := os.Getwd()
		cwd = utilities.PyPath(cwd)
		if subtaskRepoFactoryPathExists(utilities.PyJoin(cwd, "agenthub_main")) {
			return cwd
		}
		current := utilities.PyPath(file)
		for utilities.PyParent(current) != current {
			if subtaskRepoFactoryPathExists(utilities.PyJoin(current, "agenthub_main")) {
				return current
			}
			current = utilities.PyParent(current)
		}
		return "/tmp/agenthub_project"
	}
	return dataPath
}

// Create is the classmethod factory for integration tests.
func (f *SubtaskRepositoryFactory) Create(projectID, gitBranchName, userID string) (domainrepos.SubtaskRepository, error) {
	return f.CreateSubtaskRepository(projectID, gitBranchName, &userID)
}

// CreateSubtaskRepository creates a subtask repository for a user/project/tree.
func (f *SubtaskRepositoryFactory) CreateSubtaskRepository(projectID, gitBranchName string, userID *string) (domainrepos.SubtaskRepository, error) {
	if projectID == "" {
		return nil, &ValueError{Msg: "project_id is required"}
	}
	if gitBranchName == "" {
		gitBranchName = "main"
	}
	if userID == nil {
		userID = f.DefaultUserID
	}
	if subtaskRepoFactoryBackend == nil {
		return nil, &ValueError{Msg: "RepositoryFactory is not registered"}
	}
	return subtaskRepoFactoryBackend.GetSubtaskRepository(userID)
}

// CreateSQLiteSubtaskRepository creates a subtask repository (the ORM is always used).
func (f *SubtaskRepositoryFactory) CreateSQLiteSubtaskRepository(projectID, gitBranchName string, userID *string, dbPath *string) (domainrepos.SubtaskRepository, error) {
	return f.CreateSubtaskRepository(projectID, gitBranchName, userID)
}

// CreateORMSubtaskRepository creates an ORM subtask repository.
func (f *SubtaskRepositoryFactory) CreateORMSubtaskRepository(userID *string) (*ORMSubtaskRepository, error) {
	if userID == nil {
		userID = f.DefaultUserID
	}
	return NewORMSubtaskRepository(f.Sessions, userID)
}

// ValidateUserProjectTree always returns true for the ORM repositories.
func (f *SubtaskRepositoryFactory) ValidateUserProjectTree(projectID, gitBranchName string, userID *string) bool {
	return true
}

// GetSubtaskDBPath is get_subtask_db_path.
func (f *SubtaskRepositoryFactory) GetSubtaskDBPath(projectID, gitBranchName string, userID *string) string {
	if userID == nil {
		userID = f.DefaultUserID
	}
	if envDBPath := subtaskRepoFactoryGetenv("MCP_DB_PATH", ""); envDBPath != "" {
		return envDBPath
	}
	return utilities.PyJoin(f.ProjectRoot, "agenthub_main", "database", "data", "agenthub.db")
}

// ---- helpers -------------------------------------------------------------------

func subtaskRepoFactoryGetenv(key, fallback string) string {
	if v, ok := os.LookupEnv(key); ok {
		return v
	}
	return fallback
}

func subtaskRepoFactoryPathExists(path string) bool {
	_, err := os.Stat(path)
	return err == nil
}
