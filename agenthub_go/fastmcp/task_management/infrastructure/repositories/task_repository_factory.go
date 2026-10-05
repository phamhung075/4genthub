package repositories

import (
	"strings"

	"agenthub/fastmcp/task_management/infrastructure/database"
	"agenthub/fastmcp/utilities"

	domainrepos "agenthub/fastmcp/task_management/domain/repositories"
)

// TaskRepositoryFactoryBackend is the central RepositoryFactory.get_task_repository used by
// the factory. The Go central factory needs a session manager, so it is registered here.
type TaskRepositoryFactoryBackend interface {
	GetTaskRepository(projectID, gitBranchName, userID *string) (domainrepos.TaskRepository, error)
}

var taskRepoFactoryBackend TaskRepositoryFactoryBackend

// SetTaskRepositoryFactoryBackend registers the central repository factory.
func SetTaskRepositoryFactoryBackend(backend TaskRepositoryFactoryBackend) {
	taskRepoFactoryBackend = backend
}

// TaskRepositoryFactory ports task_repository_factory.TaskRepositoryFactory.
type TaskRepositoryFactory struct {
	ProjectRoot   string
	BasePath      string
	DefaultUserID *string
	// Sessions backs the direct ORM construction in create_sqlite_task_repository /
	// create_temporary_repository (Python reads it from get_db_config()).
	Sessions *database.SessionManager
}

// NewTaskRepositoryFactory mirrors the constructor with optional base_path, default_user_id
// and project_root. Python's domain.constants.validate_user_id is not yet ported; the local
// helper keeps the None/empty ValueError but not the UUID normalization.
func NewTaskRepositoryFactory(basePath, defaultUserID, projectRoot *string, sessions *database.SessionManager) (*TaskRepositoryFactory, error) {
	root := FindProjectRoot()
	if projectRoot != nil && *projectRoot != "" {
		root = *projectRoot
	}
	base := utilities.PyJoin(root, ".cursor", "rules", "tasks")
	if basePath != nil && *basePath != "" {
		base = *basePath
	}
	if defaultUserID != nil {
		validated, err := taskRepoFactoryValidateUserID(defaultUserID, "Task repository factory initialization")
		if err != nil {
			return nil, err
		}
		defaultUserID = &validated
	}
	return &TaskRepositoryFactory{ProjectRoot: root, BasePath: base, DefaultUserID: defaultUserID, Sessions: sessions}, nil
}

// Create is the classmethod factory for integration tests.
func (f *TaskRepositoryFactory) Create(projectID, gitBranchName, userID string) (domainrepos.TaskRepository, error) {
	return f.CreateRepository(projectID, gitBranchName, &userID)
}

// CreateRepository creates a task repository for a user/project/tree.
func (f *TaskRepositoryFactory) CreateRepository(projectID, gitBranchName string, userID *string) (domainrepos.TaskRepository, error) {
	if projectID == "" {
		return nil, &ValueError{Msg: "project_id is required"}
	}
	if gitBranchName == "" {
		gitBranchName = "main"
	}
	if userID == nil {
		userID = f.DefaultUserID
	}
	if taskRepoFactoryBackend == nil {
		return nil, &ValueError{Msg: "RepositoryFactory is not registered"}
	}
	return taskRepoFactoryBackend.GetTaskRepository(&projectID, &gitBranchName, userID)
}

// CreateRepositoryWithGitBranchID ports create_repository_with_git_branch_id. Python ignores
// git_branch_id and delegates to the central factory, so this does too.
func (f *TaskRepositoryFactory) CreateRepositoryWithGitBranchID(projectID, gitBranchName, userID, gitBranchID string) (domainrepos.TaskRepository, error) {
	return f.CreateRepository(projectID, gitBranchName, &userID)
}

// CreateSQLiteTaskRepository creates a task repository (the ORM is always used when a session
// is available, otherwise the mock repository).
func (f *TaskRepositoryFactory) CreateSQLiteTaskRepository(projectID, gitBranchName string, userID *string, dbPath *string) (domainrepos.TaskRepository, error) {
	_ = dbPath
	if projectID == "" {
		return nil, &ValueError{Msg: "project_id is required"}
	}
	if gitBranchName == "" {
		gitBranchName = "main"
	}
	if userID == nil {
		userID = f.DefaultUserID
	}
	if f.Sessions != nil {
		return NewORMTaskRepository(f.Sessions, nil, &projectID, &gitBranchName, userID, false)
	}
	return NewMockTaskRepository(), nil
}

// CreateTemporaryRepository creates a temporary task repository for testing.
func (f *TaskRepositoryFactory) CreateTemporaryRepository() (domainrepos.TaskRepository, error) {
	if f.Sessions != nil {
		return NewORMTaskRepository(f.Sessions, nil, nil, nil, nil, false)
	}
	return NewMockTaskRepository(), nil
}

// taskRepoFactoryValidateUserID is the subset of domain.constants.validate_user_id that is
// ported: a nil or empty user id raises ValueError; otherwise the stripped value is returned.
// The UUID normalization step is not ported (normalize_user_id_to_uuid has no Go port).
func taskRepoFactoryValidateUserID(userID *string, operation string) (string, error) {
	if userID == nil {
		return "", &ValueError{Msg: operation + " requires user authentication. No user ID was provided."}
	}
	s := strings.TrimSpace(*userID)
	if s == "" {
		return "", &ValueError{Msg: operation + " requires user authentication. No user ID was provided."}
	}
	return s, nil
}
