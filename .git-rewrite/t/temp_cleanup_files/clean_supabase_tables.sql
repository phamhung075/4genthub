-- Clean All Data from Supabase Public Tables
-- WARNING: This will DELETE ALL DATA from the tables!
-- Make sure you have backups if needed

-- Disable foreign key checks temporarily
SET session_replication_role = 'replica';

-- Clean tables in dependency order (child tables first, parent tables last)

-- 1. Clean task-related child tables
TRUNCATE TABLE public.task_subtasks CASCADE;
TRUNCATE TABLE public.task_dependencies CASCADE;
TRUNCATE TABLE public.task_assignees CASCADE;
TRUNCATE TABLE public.task_labels CASCADE;

-- 2. Clean main task table
TRUNCATE TABLE public.tasks CASCADE;

-- 3. Clean git branch assignments and related tables
TRUNCATE TABLE public.git_branch_agent_assignments CASCADE;
TRUNCATE TABLE public.git_branchs CASCADE;

-- 4. Clean agent-related tables
TRUNCATE TABLE public.registered_agents CASCADE;

-- 5. Clean project table
TRUNCATE TABLE public.projects CASCADE;

-- 6. Clean context-related tables
TRUNCATE TABLE public.hierarchical_contexts CASCADE;
TRUNCATE TABLE public.context_delegations CASCADE;
TRUNCATE TABLE public.context_insights CASCADE;
TRUNCATE TABLE public.context_progress CASCADE;

-- 7. Clean rule-related tables
TRUNCATE TABLE public.rule_contents CASCADE;
TRUNCATE TABLE public.rule_clients CASCADE;
TRUNCATE TABLE public.rule_sync_logs CASCADE;

-- 8. Clean authentication/token tables
TRUNCATE TABLE public.mcp_tokens CASCADE;
TRUNCATE TABLE public.auth_tokens CASCADE;

-- 9. Clean audit/compliance tables
TRUNCATE TABLE public.audit_logs CASCADE;
TRUNCATE TABLE public.compliance_records CASCADE;

-- 10. Clean session/cache tables
TRUNCATE TABLE public.user_sessions CASCADE;
TRUNCATE TABLE public.cache_entries CASCADE;

-- Re-enable foreign key checks
SET session_replication_role = 'origin';

-- Verify counts (should all be 0)
SELECT 'projects' as table_name, COUNT(*) as row_count FROM public.projects
UNION ALL
SELECT 'tasks', COUNT(*) FROM public.tasks
UNION ALL
SELECT 'task_subtasks', COUNT(*) FROM public.task_subtasks
UNION ALL
SELECT 'git_branchs', COUNT(*) FROM public.git_branchs
UNION ALL
SELECT 'registered_agents', COUNT(*) FROM public.registered_agents
UNION ALL
SELECT 'hierarchical_contexts', COUNT(*) FROM public.hierarchical_contexts
UNION ALL
SELECT 'mcp_tokens', COUNT(*) FROM public.mcp_tokens
ORDER BY table_name;