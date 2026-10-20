package services

import (
	"context"
	"database/sql"
	"fmt"
	"net/url"
	"os"
	"strings"
	"testing"
	"time"

	"agenthub/fastmcp/session_stream/testdb"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

func wsTestSessions(t *testing.T) (*database.SessionManager, *sql.DB) {
	t.Helper()
	admin := os.Getenv("AGENTHUB_TEST_PG_URL")
	if admin == "" {
		t.Skip("SKIPPED, NOT PASSED: AGENTHUB_TEST_PG_URL is unset, so this case did NOT run - " +
			"bash tools/testpg/start.sh prints a URL to pass to it")
	}
	adm, err := sql.Open("pgx", admin)
	if err != nil {
		t.Fatal(err)
	}
	name := fmt.Sprintf("agenthub_ws_%d", time.Now().UnixNano())
	if _, err := adm.Exec("CREATE DATABASE " + name); err != nil {
		t.Fatal(err)
	}
	u, _ := url.Parse(admin)
	u.Path = "/" + name
	env := map[string]string{"DATABASE_TYPE": "postgresql", "DATABASE_HOST": "x", "DATABASE_PASSWORD": "x"}
	database.ResetInstance()
	deps := database.Deps{
		Getenv: func(k string) (string, bool) { v, ok := env[k]; return v, ok },
		Sleep:  func(time.Duration) {},
		Open: func(string, database.EngineOptions) (*sql.DB, error) {
			return database.PgxOpener(u.String(), database.EngineOptions{PoolSize: 4, MaxOverflow: 4, PoolRecycle: 60})
		},
	}
	cfg, err := database.GetInstance(context.Background(), deps)
	if err != nil {
		t.Fatal(err)
	}
	testdb.CreateSchema(t, cfg)
	t.Cleanup(func() {
		database.ResetInstance()
		_, _ = adm.Exec("DROP DATABASE IF EXISTS " + name + " WITH (FORCE)")
		adm.Close()
	})
	direct, err := sql.Open("pgx", u.String())
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { direct.Close() })
	return database.NewSessionManager(cfg), direct
}

func TestDBWebSocketContextProvider(t *testing.T) {
	sm, db := wsTestSessions(t)
	const (
		proj   = "11111111-1111-4111-8111-111111111111"
		branch = "22222222-2222-4222-8222-222222222222"
		task   = "33333333-3333-4333-8333-333333333333"
		sub    = "44444444-4444-4444-8444-444444444444"
		user   = "user-1"
	)
	mustExec := func(q string, a ...any) {
		if _, err := db.Exec(q, a...); err != nil {
			t.Fatalf("%v\n%s", err, q)
		}
	}
	mustExec(`INSERT INTO projects (id,name,description,created_at,updated_at,user_id,status,metadata)
		VALUES ($1,'p','',now(),now(),$2,'active','{}')`, proj, user)
	mustExec(`INSERT INTO project_git_branchs (id, project_id, name, description, created_at, updated_at, priority, status, metadata, task_count, completed_task_count, user_id)
		VALUES ($1,$2,'feat','', now(), now(), 'medium','todo','{}',4,1,$3)`, branch, proj, user)
	mustExec(`INSERT INTO tasks (id,title,description,git_branch_id,status,priority,estimated_effort,created_at,updated_at,completion_summary,testing_notes,progress_percentage,progress_state,user_id)
		VALUES ($1,'My task','',$2,'todo','medium','',now(),now(),'','',0,'INITIAL',$3)`, task, branch, user)
	mustExec(`INSERT INTO subtasks (id,task_id,title,description,status,priority,assignees,progress_percentage,progress_state,progress_notes,blockers,completion_summary,impact_on_parent,insights_found,user_id,created_at,updated_at)
		VALUES ($1,$2,'My sub','','todo','medium','[]',0,'INITIAL','','','','','[]',$3,now(),now())`, sub, task, user)

	p := &DBWebSocketContextProvider{Sessions: sm}
	ctx := context.Background()
	u := user

	get := func(m *entities.OrderedMap[any], k string) any { v, _ := m.Get(k); return v }

	tc := p.GetTaskContext(ctx, task, &u)
	if get(tc, "task_title") != "My task" || get(tc, "parent_branch_id") != branch ||
		get(tc, "parent_branch_title") != "feat" || get(tc, "parent_project_id") != proj || get(tc, "task_user_id") != user {
		t.Fatalf("task context: %v", tc.Keys())
	}
	other := "someone-else"
	tc = p.GetTaskContext(ctx, task, &other)
	if get(tc, "task_title") != "Task 33333333" || get(tc, "parent_branch_title") != "Unknown Branch" || get(tc, "parent_branch_id") != nil {
		t.Fatalf("task fallback: %v", get(tc, "task_title"))
	}
	sc := p.GetSubtaskContext(ctx, sub, task, &u)
	if get(sc, "subtask_title") != "My sub" || get(sc, "parent_task_title") != "My task" || get(sc, "parent_task_id") != task {
		t.Fatalf("subtask context")
	}
	sc = p.GetSubtaskContext(ctx, "nope", task, &u)
	if get(sc, "subtask_title") != "Subtask nope" {
		t.Fatalf("subtask fallback: %v", get(sc, "subtask_title"))
	}
	bc := p.GetBranchContext(ctx, branch, &u)
	if get(bc, "branch_title") != "feat" {
		t.Fatalf("branch context")
	}
	if get(p.GetBranchContext(ctx, branch, &other), "branch_title") != "Branch 22222222" {
		t.Fatalf("branch fallback")
	}
	// Python runs ROUND(double precision, integer) on PostgreSQL, which does not exist:
	// the helper returns None.
	if c := p.GetBranchCascadeData(ctx, branch, &u); c != nil {
		t.Fatalf("cascade should be nil on PostgreSQL, got %v", c.Keys())
	}
}

type wsCapture struct {
	events []string
	meta   []*entities.OrderedMap[any]
	data   []any
}

func (c *wsCapture) BroadcastDataChange(_ context.Context, eventType, entityType, entityID, userID string, data any, metadata *entities.OrderedMap[any]) error {
	c.events = append(c.events, eventType+"/"+entityType+"/"+entityID)
	c.meta = append(c.meta, metadata)
	c.data = append(c.data, data)
	return nil
}

type wsFakeProvider struct{ cascade *entities.OrderedMap[any] }

func (f wsFakeProvider) GetTaskContext(context.Context, string, *string) *entities.OrderedMap[any] {
	return wsTaskContextFallback("abcdefghij")
}
func (f wsFakeProvider) GetSubtaskContext(context.Context, string, string, *string) *entities.OrderedMap[any] {
	return wsSubtaskContextFallback("s1", "t1")
}
func (f wsFakeProvider) GetBranchContext(context.Context, string, *string) *entities.OrderedMap[any] {
	return wsBranchContextFallback("b1")
}
func (f wsFakeProvider) GetBranchCascadeData(context.Context, string, *string) *entities.OrderedMap[any] {
	return f.cascade
}

func TestSyncBroadcastTaskCompletionAndCascade(t *testing.T) {
	cap := &wsCapture{}
	cascade := entities.NewOrderedMap[any]()
	cascade.Set("task_count", 3)
	s := &WebSocketNotificationService{Provider: wsFakeProvider{cascade: cascade}, Broker: cap}
	data := entities.NewOrderedMap[any]()
	data.Set("completion_summary", "done it")
	branch := "b-1"
	if err := s.SyncBroadcastTask(context.Background(), SyncTaskEventParams{
		EventType: "completed", TaskID: "t-complete", UserID: "u", TaskData: data, GitBranchID: &branch}); err != nil {
		t.Fatal(err)
	}
	m := cap.meta[0]
	keys := m.Keys()
	want := []string{"git_branch_id", "timestamp", "task_title", "parent_branch_id", "parent_branch_title",
		"status", "title", "completion_summary", "testing_notes", "progress_percentage",
		"assignees", "description", "insights_found", "blockers"}
	if fmt.Sprint(keys) != fmt.Sprint(want) {
		t.Fatalf("keys %v", keys)
	}
	if v, _ := m.Get("status"); v != "done" {
		t.Fatalf("status %v", v)
	}
	// duplicate within 5s is skipped
	if err := s.SyncBroadcastTask(context.Background(), SyncTaskEventParams{EventType: "completed", TaskID: "t-complete", UserID: "u"}); err != nil || len(cap.events) != 1 {
		t.Fatalf("dedup failed: %v", cap.events)
	}
	if err := s.SyncBroadcastTask(context.Background(), SyncTaskEventParams{
		EventType: "created", TaskID: "t-create", UserID: "u", GitBranchID: &branch}); err != nil {
		t.Fatal(err)
	}
	c, ok := cap.meta[1].Get("cascade")
	if !ok || c.(*entities.OrderedMap[any]) == nil {
		t.Fatalf("cascade missing")
	}
}

func TestSyncBroadcastTaskCarriesAFlatDeltaAndCapsIt(t *testing.T) {
	wsNotificationCacheMu.Lock()
	wsNotificationCache = map[string]float64{}
	wsNotificationCacheMu.Unlock()
	cap := &wsCapture{}
	s := &WebSocketNotificationService{Broker: cap}
	full := entities.NewOrderedMap[any]()
	full.Set("id", "t-delta")
	full.Set("title", "a task")
	full.Set("status", "in_progress")
	full.Set("description", "bench")
	full.Set("updated_at", "2026-10-19T12:00:00Z")
	if err := s.SyncBroadcastTask(context.Background(), SyncTaskEventParams{
		EventType: "updated", TaskID: "t-delta", UserID: "u", TaskData: full,
		Changed: []string{"status", "details"},
	}); err != nil {
		t.Fatal(err)
	}
	delta, ok := cap.data[0].(*entities.OrderedMap[any])
	if !ok {
		t.Fatalf("primary type = %T, want an OrderedMap delta", cap.data[0])
	}
	if keys := delta.Keys(); fmt.Sprint(keys) != fmt.Sprint([]string{"id", "updated_at", "status", "details_changed"}) {
		t.Fatalf("delta keys = %v", keys)
	}
	if v, _ := delta.Get("title"); v != nil {
		t.Fatalf("unchanged title reached the delta: %#v", v)
	}

	// An over-cap delta is replaced by the refetch shape, never sent truncated.
	big := entities.NewOrderedMap[any]()
	big.Set("id", "t-big")
	big.Set("description", strings.Repeat("x", WebSocketTaskPayloadCap))
	big.Set("updated_at", "2026-10-19T12:00:01Z")
	if err := s.SyncBroadcastTask(context.Background(), SyncTaskEventParams{
		EventType: "updated", TaskID: "t-big", UserID: "u", TaskData: big, Changed: []string{"description"},
	}); err != nil {
		t.Fatal(err)
	}
	refetch, _ := cap.data[1].(*entities.OrderedMap[any])
	if refetch == nil {
		t.Fatalf("primary type = %T, want the refetch map", cap.data[1])
	}
	if keys := refetch.Keys(); fmt.Sprint(keys) != fmt.Sprint([]string{"id", "refetch"}) {
		t.Fatalf("refetch keys = %v", keys)
	}
	if v, _ := refetch.Get("refetch"); v != true {
		t.Fatalf("refetch = %#v", v)
	}
}

func TestSyncBroadcastTaskDeduplicatesOneWriteNotTwo(t *testing.T) {
	wsNotificationCacheMu.Lock()
	wsNotificationCache = map[string]float64{}
	wsNotificationCacheMu.Unlock()
	cap := &wsCapture{}
	s := &WebSocketNotificationService{Broker: cap}
	event := func(stamp, user string) SyncTaskEventParams {
		full := entities.NewOrderedMap[any]()
		full.Set("id", "t-dedup")
		full.Set("updated_at", stamp)
		return SyncTaskEventParams{EventType: "updated", TaskID: "t-dedup", UserID: user, TaskData: full, Changed: []string{"updated_at"}}
	}
	// The two emitter families stamp one write differently ("system" and the acting user); the
	// updated_at they share is what makes it one write.
	if err := s.SyncBroadcastTask(context.Background(), event("stamp-1", "system")); err != nil {
		t.Fatal(err)
	}
	if err := s.SyncBroadcastTask(context.Background(), event("stamp-1", "u-actor")); err != nil {
		t.Fatal(err)
	}
	if len(cap.events) != 1 {
		t.Fatalf("one write emitted %d frames, want 1", len(cap.events))
	}
	// A second write inside the TTL carries a new stamp and must reach the client.
	if err := s.SyncBroadcastTask(context.Background(), event("stamp-2", "system")); err != nil {
		t.Fatal(err)
	}
	if len(cap.events) != 2 {
		t.Fatalf("two writes emitted %d frames, want 2", len(cap.events))
	}
}

func TestSyncBroadcastSubtaskCompletion(t *testing.T) {
	cap := &wsCapture{}
	s := &WebSocketNotificationService{Provider: wsFakeProvider{}, Broker: cap}
	data := entities.NewOrderedMap[any]()
	data.Set("title", "T")
	if err := s.SyncBroadcastSubtaskEvent(context.Background(), "completed", "s1", "t1", "u", data); err != nil {
		t.Fatal(err)
	}
	m := cap.meta[0]
	if v, _ := m.Get("is_subtask"); v != true {
		t.Fatalf("is_subtask")
	}
	if v, _ := m.Get("title"); v != "T" {
		t.Fatalf("title")
	}
}
