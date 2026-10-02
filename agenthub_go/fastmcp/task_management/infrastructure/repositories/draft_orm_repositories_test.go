package repositories

// Real-PostgreSQL tests for this worker's ORM repositories (label, template, cascade data
// provider, Supabase-optimized task repository).

import (
	"context"
	"errors"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/services/protocols"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

func draftRepoSetup(t *testing.T, sessions *database.SessionManager, userID string) (projectID, branchID, taskID string) {
	t.Helper()
	projectID, branchID, taskID = tmvo.NewUUIDv4(), tmvo.NewUUIDv4(), tmvo.NewUUIDv4()
	now := time.Now().UTC()
	err := sessions.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		if _, err := s.ExecContext(ctx,
			`INSERT INTO projects (id,name,description,created_at,updated_at,user_id,status,metadata) VALUES ($1::uuid,$2,$3,$4,$5,$6,$7,$8::json)`,
			projectID, "P", "", now, now, userID, "active", "{}"); err != nil {
			return err
		}
		if _, err := s.ExecContext(ctx,
			`INSERT INTO project_git_branchs (id,project_id,name,description,created_at,updated_at,priority,status,metadata,task_count,completed_task_count,user_id) VALUES ($1::uuid,$2::uuid,$3,$4,$5,$6,$7,$8,$9::json,0,0,$10)`,
			branchID, projectID, "B", "", now, now, "medium", "todo", "{}", userID); err != nil {
			return err
		}
		if _, err := s.ExecContext(ctx,
			`INSERT INTO tasks (id,title,description,git_branch_id,status,priority,progress_history,progress_count,estimated_effort,created_at,updated_at,completion_summary,testing_notes,progress_percentage,progress_state,user_id) VALUES ($1::uuid,$2,$3,$4::uuid,$5,$6,$7::json,$8,$9,$10,$11,$12,$13,$14,$15,$16)`,
			taskID, "T", "desc", branchID, "todo", "medium", "{}", 0, "2 hours", now, now, "", "", 0, "INITIAL", userID); err != nil {
			return err
		}
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
	return
}

func draftRepoAddTask(t *testing.T, sessions *database.SessionManager, userID, branchID, title string) string {
	t.Helper()
	taskID := tmvo.NewUUIDv4()
	now := time.Now().UTC()
	err := sessions.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		_, err := s.ExecContext(ctx,
			`INSERT INTO tasks (id,title,description,git_branch_id,status,priority,progress_history,progress_count,estimated_effort,created_at,updated_at,completion_summary,testing_notes,progress_percentage,progress_state,user_id) VALUES ($1::uuid,$2,$3,$4::uuid,$5,$6,$7::json,$8,$9,$10,$11,$12,$13,$14,$15,$16)`,
			taskID, title, "desc", branchID, "todo", "medium", "{}", 0, "2 hours", now, now, "", "", 0, "INITIAL", userID)
		return err
	})
	if err != nil {
		t.Fatal(err)
	}
	return taskID
}

func draftRepoAddSubtask(t *testing.T, sessions *database.SessionManager, userID, taskID, title string) string {
	t.Helper()
	subtaskID := tmvo.NewUUIDv4()
	now := time.Now().UTC()
	err := sessions.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		_, err := s.ExecContext(ctx,
			`INSERT INTO subtasks (id,task_id,title,description,status,priority,assignees,progress_percentage,progress_history,progress_count,progress_state,progress_notes,blockers,completion_summary,impact_on_parent,insights_found,user_id,created_at,updated_at) VALUES ($1::uuid,$2::uuid,$3,$4,$5,$6,$7::json,$8,$9::json,$10,$11,$12,$13,$14,$15,$16::json,$17,$18,$19)`,
			subtaskID, taskID, title, "", "todo", "medium", "[]", 0, "{}", 0, "INITIAL", "", "", "", "", "[]", userID, now, now)
		return err
	})
	if err != nil {
		t.Fatal(err)
	}
	return subtaskID
}

func strPtr(s string) *string { return &s }

// ---- label repository ---------------------------------------------------------

func TestDraftLabelRepoCreateGetList(t *testing.T) {
	sessions := newTestRepoEnv(t)
	uid := "label-user"
	repo, err := NewORMLabelRepository(sessions, &uid)
	if err != nil {
		t.Fatal(err)
	}
	ctx := context.Background()

	beta, err := repo.CreateLabel(ctx, "beta", "", "second")
	if err != nil {
		t.Fatal(err)
	}
	if beta.ID == "" || beta.Color != "#0066cc" || beta.Description != "second" {
		t.Fatalf("unexpected label: %+v", beta)
	}
	if beta.CreatedAt.IsZero() || beta.UpdatedAt.IsZero() {
		t.Fatalf("timestamps not set: %+v", beta)
	}
	alpha, err := repo.CreateLabel(ctx, "alpha", "#ff0000", "")
	if err != nil {
		t.Fatal(err)
	}

	got, err := repo.GetLabel(ctx, beta.ID)
	if err != nil || got == nil || got.Name != "beta" {
		t.Fatalf("GetLabel: %v %+v", err, got)
	}
	byName, err := repo.GetLabelByName(ctx, "alpha")
	if err != nil || byName == nil || byName.ID != alpha.ID {
		t.Fatalf("GetLabelByName: %v %+v", err, byName)
	}
	if none, err := repo.GetLabel(ctx, tmvo.NewUUIDv4()); err != nil || none != nil {
		t.Fatalf("missing GetLabel: %v %+v", err, none)
	}
	if none, err := repo.GetLabelByName(ctx, "nope"); err != nil || none != nil {
		t.Fatalf("missing GetLabelByName: %v %+v", err, none)
	}

	list, err := repo.ListLabels(ctx, nil, nil)
	if err != nil || len(list) != 2 {
		t.Fatalf("ListLabels: %v %d", err, len(list))
	}
	if list[0].Name != "alpha" || list[1].Name != "beta" {
		t.Fatalf("ordering: %s %s", list[0].Name, list[1].Name)
	}
	lim := 1
	off := 1
	page, err := repo.ListLabels(ctx, &lim, &off)
	if err != nil || len(page) != 1 || page[0].Name != "beta" {
		t.Fatalf("pagination: %v %+v", err, page)
	}

	if _, err := repo.CreateLabel(ctx, "beta", "", ""); err == nil {
		t.Fatal("expected duplicate name error")
	} else {
		var ve *exceptions.ValidationError
		if !errors.As(err, &ve) {
			t.Fatalf("duplicate error type: %T %v", err, err)
		}
	}

	noUser, err := NewORMLabelRepository(sessions, nil)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := noUser.CreateLabel(ctx, "x", "", ""); err == nil {
		t.Fatal("expected user_id ValueError")
	} else {
		var ve *tmvo.ValueError
		if !errors.As(err, &ve) {
			t.Fatalf("user error type: %T %v", err, err)
		}
	}
}

func TestDraftLabelRepoUpdateDelete(t *testing.T) {
	sessions := newTestRepoEnv(t)
	uid := "label-user"
	repo, err := NewORMLabelRepository(sessions, &uid)
	if err != nil {
		t.Fatal(err)
	}
	ctx := context.Background()
	label, err := repo.CreateLabel(ctx, "beta", "", "")
	if err != nil {
		t.Fatal(err)
	}
	other, err := repo.CreateLabel(ctx, "alpha", "", "")
	if err != nil {
		t.Fatal(err)
	}

	updated, err := repo.UpdateLabel(ctx, label.ID, strPtr("gamma"), strPtr("#00ff00"), nil)
	if err != nil || updated.Name != "gamma" || updated.Color != "#00ff00" || updated.Description != "" {
		t.Fatalf("UpdateLabel: %v %+v", err, updated)
	}
	if _, err := repo.UpdateLabel(ctx, tmvo.NewUUIDv4(), strPtr("x"), nil, nil); err == nil {
		t.Fatal("expected NotFoundError")
	} else {
		var nf *exceptions.NotFoundError
		if !errors.As(err, &nf) {
			t.Fatalf("not found type: %T %v", err, err)
		}
	}
	if _, err := repo.UpdateLabel(ctx, label.ID, strPtr("alpha"), nil, nil); err == nil {
		t.Fatal("expected duplicate ValidationError")
	}
	if _, err := repo.UpdateLabel(ctx, label.ID, strPtr(""), nil, nil); err == nil {
		t.Fatal("expected empty name ValueError")
	}
	if _, err := repo.UpdateLabel(ctx, label.ID, nil, strPtr("#zzz"), nil); err == nil {
		t.Fatal("expected invalid color ValueError")
	}

	deleted, err := repo.DeleteLabel(ctx, other.ID)
	if err != nil || !deleted {
		t.Fatalf("DeleteLabel: %v %v", err, deleted)
	}
	deleted, err = repo.DeleteLabel(ctx, other.ID)
	if err != nil || deleted {
		t.Fatalf("second DeleteLabel: %v %v", err, deleted)
	}
}

func TestDraftLabelRepoTaskAssignment(t *testing.T) {
	sessions := newTestRepoEnv(t)
	uid := "label-user"
	repo, err := NewORMLabelRepository(sessions, &uid)
	if err != nil {
		t.Fatal(err)
	}
	ctx := context.Background()
	_, _, taskID := draftRepoSetup(t, sessions, uid)
	label, err := repo.CreateLabel(ctx, "assigned", "", "")
	if err != nil {
		t.Fatal(err)
	}

	ok, err := repo.AssignLabelToTask(ctx, taskID, label.ID)
	if err != nil || !ok {
		t.Fatalf("AssignLabelToTask: %v %v", err, ok)
	}
	ok, err = repo.AssignLabelToTask(ctx, taskID, label.ID)
	if err != nil || ok {
		t.Fatalf("second assign: %v %v", err, ok)
	}
	labels, err := repo.GetLabelsByTask(ctx, taskID)
	if err != nil || len(labels) != 1 || labels[0].Name != "assigned" {
		t.Fatalf("GetLabelsByTask: %v %+v", err, labels)
	}
	tasks, err := repo.GetTasksByLabel(ctx, label.ID)
	if err != nil || len(tasks) != 1 || tasks[0].Title != "T" {
		t.Fatalf("GetTasksByLabel: %v %+v", err, tasks)
	}
	if tasks[0].Status.Value != "todo" || tasks[0].Priority.Value != "medium" {
		t.Fatalf("task status/priority: %+v", tasks[0])
	}
	removed, err := repo.RemoveLabelFromTask(ctx, taskID, label.ID)
	if err != nil || !removed {
		t.Fatalf("RemoveLabelFromTask: %v %v", err, removed)
	}
	removed, err = repo.RemoveLabelFromTask(ctx, taskID, label.ID)
	if err != nil || removed {
		t.Fatalf("second remove: %v %v", err, removed)
	}

	if _, err := repo.AssignLabelToTask(ctx, tmvo.NewUUIDv4(), label.ID); err == nil {
		t.Fatal("expected missing task error")
	}
	if _, err := repo.AssignLabelToTask(ctx, taskID, tmvo.NewUUIDv4()); err == nil {
		t.Fatal("expected missing label error")
	}
	if _, err := repo.GetTasksByLabel(ctx, tmvo.NewUUIDv4()); err == nil {
		t.Fatal("expected missing label error")
	}
	if _, err := repo.GetLabelsByTask(ctx, tmvo.NewUUIDv4()); err == nil {
		t.Fatal("expected missing task error")
	}
}

// ---- template repository ------------------------------------------------------

func draftNewTemplate(t *testing.T, name, description, content string, tt tmvo.TemplateType, cat tmvo.TemplateCategory) *entities.Template {
	t.Helper()
	id := tmvo.GenerateNewTemplateId()
	st := tmvo.TemplateStatusActive
	pr := tmvo.TemplatePriorityMedium
	tmpl, err := entities.NewTemplate(entities.Template{
		ID: &id, Name: name, Description: description, Content: content,
		TemplateType: &tt, Category: &cat, Status: &st, Priority: &pr,
		CompatibleAgents: []string{"agent-a"}, FilePatterns: []string{"*.go"},
		Variables: []string{"var1"}, Metadata: map[string]any{"key": "value"},
	})
	if err != nil {
		t.Fatal(err)
	}
	return tmpl
}

func TestDraftTemplateRepoCRUD(t *testing.T) {
	sessions := newTestRepoEnv(t)
	repo, err := NewORMTemplateRepository(sessions)
	if err != nil {
		t.Fatal(err)
	}
	ctx := context.Background()
	tmpl := draftNewTemplate(t, "one", "d1", "c1", tmvo.TemplateTypeTask, tmvo.TemplateCategoryGeneral)

	ok, err := repo.Save(ctx, tmpl)
	if err != nil || !ok {
		t.Fatalf("Save: %v %v", err, ok)
	}
	got, err := repo.GetByID(ctx, *tmpl.ID)
	if err != nil || got == nil {
		t.Fatalf("GetByID: %v %+v", err, got)
	}
	if got.Name != "one" || got.Description != "d1" || got.Content != "c1" {
		t.Fatalf("round-trip: %+v", got)
	}
	if got.TemplateType == nil || *got.TemplateType != tmvo.TemplateTypeTask ||
		got.Category == nil || *got.Category != tmvo.TemplateCategoryGeneral {
		t.Fatalf("enums: %+v", got)
	}
	if got.Version == nil || *got.Version != 1 || got.IsActive == nil || !*got.IsActive {
		t.Fatalf("defaults: %+v", got)
	}
	if got.Metadata["key"] != "value" {
		t.Fatalf("metadata: %+v", got.Metadata)
	}

	if _, err := repo.IncrementUsageCount(ctx, *tmpl.ID); err != nil {
		t.Fatal(err)
	}
	got.Name = "one-updated"
	got.Description = "d2"
	ok, err = repo.Save(ctx, got)
	if err != nil || !ok {
		t.Fatalf("update Save: %v %v", err, ok)
	}
	after, err := repo.GetByID(ctx, *tmpl.ID)
	if err != nil || after.Name != "one-updated" || after.Description != "d2" {
		t.Fatalf("after update: %v %+v", err, after)
	}
	stats, err := repo.GetUsageStats(ctx, *tmpl.ID)
	if err != nil {
		t.Fatal(err)
	}
	if v, _ := stats.Get("total_usage"); v != int64(1) {
		t.Fatalf("usage preserved: %v", v)
	}
	if v, _ := stats.Get("template_id"); v != tmpl.ID.Value {
		t.Fatalf("stats id: %v", v)
	}

	if got, err := repo.GetByID(ctx, tmvo.GenerateNewTemplateId()); err != nil || got != nil {
		t.Fatalf("missing GetByID: %v %+v", err, got)
	}
}

func TestDraftTemplateRepoListAndAnalytics(t *testing.T) {
	sessions := newTestRepoEnv(t)
	repo, err := NewORMTemplateRepository(sessions)
	if err != nil {
		t.Fatal(err)
	}
	ctx := context.Background()
	a := draftNewTemplate(t, "aaa", "d", "c", tmvo.TemplateTypeTask, tmvo.TemplateCategoryGeneral)
	b := draftNewTemplate(t, "bbb", "d", "c", tmvo.TemplateTypeCode, tmvo.TemplateCategoryDevelopment)
	for _, tmpl := range []*entities.Template{a, b} {
		if ok, err := repo.Save(ctx, tmpl); err != nil || !ok {
			t.Fatalf("Save: %v %v", err, ok)
		}
	}
	if _, err := repo.IncrementUsageCount(ctx, *b.ID); err != nil {
		t.Fatal(err)
	}

	all, err := repo.ListTemplates(ctx, nil, nil, nil, nil, nil, nil)
	if err != nil || len(all) != 2 {
		t.Fatalf("ListTemplates: %v %d", err, len(all))
	}
	if all[0].Name != "bbb" || all[1].Name != "aaa" {
		t.Fatalf("usage ordering: %s %s", all[0].Name, all[1].Name)
	}
	// status/priority are ignored by the Python ORM implementation.
	ignored := tmvo.TemplateStatusDraft
	ignoredPriority := tmvo.TemplatePriorityCritical
	all, err = repo.ListTemplates(ctx, nil, nil, &ignored, &ignoredPriority, nil, nil)
	if err != nil || len(all) != 2 {
		t.Fatalf("ignored filters: %v %d", err, len(all))
	}
	typ := tmvo.TemplateTypeCode
	filtered, err := repo.ListTemplates(ctx, &typ, nil, nil, nil, nil, nil)
	if err != nil || len(filtered) != 1 || filtered[0].Name != "bbb" {
		t.Fatalf("type filter: %v %+v", err, filtered)
	}
	byType, err := repo.GetTemplatesByType(ctx, tmvo.TemplateTypeTask)
	if err != nil || len(byType) != 1 || byType[0].Name != "aaa" {
		t.Fatalf("GetTemplatesByType: %v %+v", err, byType)
	}
	byCat, err := repo.GetTemplatesByCategory(ctx, tmvo.TemplateCategoryDevelopment)
	if err != nil || len(byCat) != 1 || byCat[0].Name != "bbb" {
		t.Fatalf("GetTemplatesByCategory: %v %+v", err, byCat)
	}

	tags, err := repo.SearchTemplatesByTags(ctx, []string{"x"})
	if err != nil || len(tags) != 0 {
		t.Fatalf("SearchTemplatesByTags: %v %+v", err, tags)
	}
	tags, err = repo.SearchTemplatesByTags(ctx, nil)
	if err != nil || len(tags) != 0 {
		t.Fatalf("SearchTemplatesByTags empty: %v %+v", err, tags)
	}

	analytics, err := repo.GetAnalytics(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if v, _ := analytics.Get("total_templates"); v != int64(2) {
		t.Fatalf("total_templates: %v", v)
	}
	typeStats, _ := analytics.Get("templates_by_type")
	tm, ok := typeStats.(*entities.OrderedMap[any])
	if !ok {
		t.Fatalf("templates_by_type type: %T", typeStats)
	}
	if v, _ := tm.Get("task"); v != int64(1) {
		t.Fatalf("type stats: %v", v)
	}
	mostUsed, _ := analytics.Get("most_used_templates")
	items, ok := mostUsed.([]*entities.OrderedMap[any])
	if !ok || len(items) != 2 {
		t.Fatalf("most_used: %T %+v", mostUsed, mostUsed)
	}
	if v, _ := items[0].Get("name"); v != "bbb" {
		t.Fatalf("most used first: %v", v)
	}
	if v, _ := analytics.Get("generated_at"); v == nil {
		t.Fatal("generated_at missing")
	}

	// SaveUsage increments the count.
	if ok, err := repo.SaveUsage(ctx, entities.TemplateUsage{TemplateID: *a.ID}); err != nil || !ok {
		t.Fatalf("SaveUsage: %v %v", err, ok)
	}
	if ok, err := repo.IncrementUsageCount(ctx, tmvo.GenerateNewTemplateId()); err != nil || ok {
		t.Fatalf("increment missing: %v %v", err, ok)
	}
	if ok, err := repo.Delete(ctx, *a.ID); err != nil || !ok {
		t.Fatalf("Delete: %v %v", err, ok)
	}
	if ok, err := repo.Delete(ctx, *a.ID); err != nil || ok {
		t.Fatalf("second Delete: %v %v", err, ok)
	}
}

func TestDraftTemplateRepoQuirks(t *testing.T) {
	sessions := newTestRepoEnv(t)
	repo, err := NewORMTemplateRepository(sessions)
	if err != nil {
		t.Fatal(err)
	}
	ctx := context.Background()
	// Missing enums make _entity_to_model_dict raise, which save swallows into false.
	id := tmvo.GenerateNewTemplateId()
	broken, err := entities.NewTemplate(entities.Template{
		ID: &id, Name: "x", Description: "d", Content: "c",
	})
	if err != nil {
		t.Fatal(err)
	}
	if ok, err := repo.Save(ctx, broken); err != nil || ok {
		t.Fatalf("Save broken: %v %v", err, ok)
	}
	// GetUsageStats for a missing template is an empty map.
	stats, err := repo.GetUsageStats(ctx, tmvo.GenerateNewTemplateId())
	if err != nil || stats.Len() != 0 {
		t.Fatalf("missing stats: %v %d", err, stats.Len())
	}
}

// ---- cascade data provider ----------------------------------------------------

func TestDraftCascadeDataProvider(t *testing.T) {
	sessions := newTestRepoEnv(t)
	uid := "cascade-user"
	projectID, branchID, taskID := draftRepoSetup(t, sessions, uid)
	subtaskID := draftRepoAddSubtask(t, sessions, uid, taskID, "S1")
	provider := NewSQLAlchemyCascadeDataProvider(sessions)
	ctx := context.Background()

	taskData, err := provider.GetTaskCascadeData(ctx, taskID)
	if err != nil || taskData == nil {
		t.Fatalf("GetTaskCascadeData: %v %+v", err, taskData)
	}
	if taskData.GitBranchID != branchID || taskData.ProjectID != projectID || taskData.ContextID != nil {
		t.Fatalf("task data: %+v", taskData)
	}
	if missing, err := provider.GetTaskCascadeData(ctx, tmvo.NewUUIDv4()); err != nil || missing != nil {
		t.Fatalf("missing task data: %v %+v", err, missing)
	}

	subtaskData, err := provider.GetSubtaskCascadeData(ctx, subtaskID)
	if err != nil || subtaskData == nil || subtaskData.TaskID != taskID || subtaskData.ProjectID != projectID {
		t.Fatalf("GetSubtaskCascadeData: %v %+v", err, subtaskData)
	}

	subtaskIDs, err := provider.GetTaskSubtaskIDs(ctx, taskID)
	if err != nil || len(subtaskIDs) != 1 || subtaskIDs[0] != subtaskID {
		t.Fatalf("GetTaskSubtaskIDs: %v %+v", err, subtaskIDs)
	}

	branchData, err := provider.GetBranchCascadeData(ctx, branchID)
	if err != nil || branchData == nil || branchData.ProjectID != projectID {
		t.Fatalf("GetBranchCascadeData: %v %+v", err, branchData)
	}
	if !branchData.TaskIDs.Has(taskID) || !branchData.SubtaskIDs.Has(subtaskID) {
		t.Fatalf("branch ids: %+v", branchData)
	}
	if missing, err := provider.GetBranchCascadeData(ctx, tmvo.NewUUIDv4()); err != nil || missing != nil {
		t.Fatalf("missing branch: %v %+v", err, missing)
	}

	projectData, err := provider.GetProjectCascadeData(ctx, projectID)
	if err != nil || projectData == nil || !projectData.BranchIDs.Has(branchID) ||
		!projectData.TaskIDs.Has(taskID) || !projectData.SubtaskIDs.Has(subtaskID) {
		t.Fatalf("GetProjectCascadeData: %v %+v", err, projectData)
	}

	contextIDs, err := provider.GetRelatedContextIDs(ctx, branchID, projectID)
	if err != nil || len(contextIDs) != 0 {
		t.Fatalf("GetRelatedContextIDs: %v %+v", err, contextIDs)
	}
	// The project_id argument is unused; a bogus branch is not an error ([] on failure).
	if ids, err := provider.GetRelatedContextIDs(ctx, "not-a-uuid", projectID); err != nil || len(ids) != 0 {
		t.Fatalf("bad related contexts: %v %+v", err, ids)
	}

	// GetTaskParentTaskIDs reproduces the nonexistent dependency_id column.
	if ids, err := provider.GetTaskParentTaskIDs(ctx, taskID); err == nil {
		t.Fatalf("expected dependency_id error, got %+v", ids)
	}

	kind, err := provider.DetectEntityType(ctx, taskID)
	if err != nil || kind == nil || *kind != protocols.EntityTypeTask {
		t.Fatalf("detect task: %v %v", err, kind)
	}
	kind, err = provider.DetectEntityType(ctx, subtaskID)
	if err != nil || kind == nil || *kind != protocols.EntityTypeSubtask {
		t.Fatalf("detect subtask: %v %v", err, kind)
	}
	kind, err = provider.DetectEntityType(ctx, branchID)
	if err != nil || kind == nil || *kind != protocols.EntityTypeBranch {
		t.Fatalf("detect branch: %v %v", err, kind)
	}
	kind, err = provider.DetectEntityType(ctx, projectID)
	if err != nil || kind == nil || *kind != protocols.EntityTypeProject {
		t.Fatalf("detect project: %v %v", err, kind)
	}
	kind, err = provider.DetectEntityType(ctx, tmvo.NewUUIDv4())
	if err != nil || kind == nil || *kind != protocols.EntityTypeContext {
		t.Fatalf("detect context: %v %v", err, kind)
	}
}

func TestDraftCascadeContextData(t *testing.T) {
	sessions := newTestRepoEnv(t)
	uid := "cascade-user"
	projectID, branchID, taskID := draftRepoSetup(t, sessions, uid)
	contextID := tmvo.NewUUIDv4()
	ctx := context.Background()
	if err := sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		_, err := s.ExecContext(ctx, `UPDATE tasks SET context_id = $1::uuid WHERE id = $2::uuid`, contextID, taskID)
		return err
	}); err != nil {
		t.Fatal(err)
	}
	subtaskID := draftRepoAddSubtask(t, sessions, uid, taskID, "S1")
	provider := NewSQLAlchemyCascadeDataProvider(sessions)

	data, err := provider.GetContextCascadeData(ctx, contextID)
	if err != nil || data == nil {
		t.Fatalf("GetContextCascadeData: %v %+v", err, data)
	}
	if !data.TaskIDs.Has(taskID) || !data.BranchIDs.Has(branchID) || !data.ProjectIDs.Has(projectID) || !data.SubtaskIDs.Has(subtaskID) {
		t.Fatalf("context ids: %+v", data)
	}
	if missing, err := provider.GetContextCascadeData(ctx, tmvo.NewUUIDv4()); err != nil || missing != nil {
		t.Fatalf("missing context: %v %+v", err, missing)
	}
	taskData, err := provider.GetTaskCascadeData(ctx, taskID)
	if err != nil || taskData.ContextID == nil || *taskData.ContextID != contextID {
		t.Fatalf("task context id: %v %+v", err, taskData)
	}
	ids, err := provider.GetRelatedContextIDs(ctx, branchID, projectID)
	if err != nil || len(ids) != 1 || ids[0] != contextID {
		t.Fatalf("related context: %v %+v", err, ids)
	}
}

// ---- supabase optimized repository -------------------------------------------

func TestDraftSupabaseListTasksMinimal(t *testing.T) {
	sessions := newTestRepoEnv(t)
	uid := "sb-user"
	projectID, branchID, taskID := draftRepoSetup(t, sessions, uid)
	_ = projectID
	subtaskID := draftRepoAddSubtask(t, sessions, uid, taskID, "S1")
	if _, err := NewORMLabelRepository(sessions, &uid); err != nil {
		t.Fatal(err)
	}
	repo := NewSupabaseOptimizedRepository(sessions, &branchID)
	ctx := context.Background()
	_ = subtaskID

	rows, err := repo.ListTasksMinimal(ctx, nil, nil, nil, nil, nil)
	if err != nil || len(rows) != 1 {
		t.Fatalf("ListTasksMinimal: %v %d", err, len(rows))
	}
	row := rows[0]
	if v, _ := row.Get("id"); v != taskID {
		t.Fatalf("id: %v", v)
	}
	if v, _ := row.Get("title"); v != "T" {
		t.Fatalf("title: %v", v)
	}
	if v, _ := row.Get("subtask_count"); v != int64(1) {
		t.Fatalf("subtask_count: %v", v)
	}
	if v, _ := row.Get("has_relationships"); v != true {
		t.Fatalf("has_relationships: %v", v)
	}
	if v, ok := row.Get("created_at"); !ok || v == nil {
		t.Fatalf("created_at: %v", v)
	}

	status := "todo"
	rows, err = repo.ListTasksMinimal(ctx, &status, nil, nil, nil, nil)
	if err != nil || len(rows) != 1 {
		t.Fatalf("status filter: %v %d", err, len(rows))
	}
	other := "done"
	rows, err = repo.ListTasksMinimal(ctx, &other, nil, nil, nil, nil)
	if err != nil || len(rows) != 0 {
		t.Fatalf("status filter miss: %v %d", err, len(rows))
	}
	limit, offset := -5, -5
	rows, err = repo.ListTasksMinimal(ctx, nil, nil, nil, &limit, &offset)
	if err != nil || len(rows) != 1 {
		t.Fatalf("clamped limits: %v %d", err, len(rows))
	}
	badBranch := tmvo.NewUUIDv4()
	repo2 := NewSupabaseOptimizedRepository(sessions, &badBranch)
	rows, err = repo2.ListTasksMinimal(ctx, nil, nil, nil, nil, nil)
	if err != nil || len(rows) != 0 {
		t.Fatalf("branch filter: %v %d", err, len(rows))
	}
}

func TestDraftSupabaseNoRelationsAndCounts(t *testing.T) {
	sessions := newTestRepoEnv(t)
	uid := "sb-user"
	_, branchID, taskID := draftRepoSetup(t, sessions, uid)
	repo := NewSupabaseOptimizedRepository(sessions, &branchID)
	ctx := context.Background()

	entitiesList, err := repo.ListTasksNoRelations(ctx, nil, nil, nil, nil)
	if err != nil || len(entitiesList) != 1 {
		t.Fatalf("ListTasksNoRelations: %v %d", err, len(entitiesList))
	}
	if entitiesList[0].Title != "T" || len(entitiesList[0].Subtasks) != 0 || len(entitiesList[0].Assignees) != 0 {
		t.Fatalf("minimal entity: %+v", entitiesList[0])
	}
	status := "todo"
	entitiesList, err = repo.ListTasksNoRelations(ctx, &status, nil, nil, nil)
	if err != nil || len(entitiesList) != 1 {
		t.Fatalf("status filter: %v %d", err, len(entitiesList))
	}

	if got, err := repo.GetTaskWithCounts(ctx, "not-a-uuid"); err != nil || got != nil {
		t.Fatalf("invalid uuid: %v %+v", err, got)
	}
	if got, err := repo.GetTaskWithCounts(ctx, tmvo.NewUUIDv4()); err != nil || got != nil {
		t.Fatalf("missing task: %v %+v", err, got)
	}
	if _, err := repo.GetTaskWithCounts(ctx, taskID); err == nil {
		t.Fatal("expected details AttributeError")
	} else if err.Error() != "'Row' object has no attribute 'details'" {
		t.Fatalf("error text: %v", err)
	}
}
