-- Create project_summaries_mv materialized view
CREATE MATERIALIZED VIEW IF NOT EXISTS project_summaries_mv AS
SELECT
    p.id as project_id,
    p.name as project_name,
    p.description as project_description,
    COALESCE(branch_stats.total_branches, 0) as total_branches,
    COALESCE(branch_stats.active_branches, 0) as active_branches,
    COALESCE(task_stats.total_tasks, 0) as total_tasks,
    COALESCE(task_stats.completed_tasks, 0) as completed_tasks,
    CASE
        WHEN COALESCE(task_stats.total_tasks, 0) = 0 THEN 0
        ELSE ROUND((COALESCE(task_stats.completed_tasks, 0)::numeric / task_stats.total_tasks) * 100, 2)
    END as overall_progress_percentage
FROM projects p
LEFT JOIN (
    SELECT
        project_id,
        COUNT(*) as total_branches,
        COUNT(CASE WHEN status != 'archived' THEN 1 END) as active_branches
    FROM git_branches
    GROUP BY project_id
) branch_stats ON p.id = branch_stats.project_id
LEFT JOIN (
    SELECT
        gb.project_id,
        COUNT(t.id) as total_tasks,
        COUNT(CASE WHEN t.status = 'done' THEN 1 END) as completed_tasks
    FROM git_branches gb
    LEFT JOIN tasks t ON gb.id = t.git_branch_id
    GROUP BY gb.project_id
) task_stats ON p.id = task_stats.project_id;

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_project_summaries_mv_project_id
ON project_summaries_mv (project_id);

-- Insert into migration tracking
INSERT INTO applied_migrations (migration_name, applied_at)
VALUES ('add_project_summaries_materialized_view', NOW())
ON CONFLICT (migration_name) DO NOTHING;